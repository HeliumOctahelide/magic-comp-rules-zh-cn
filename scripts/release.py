"""提交仓库内容，并通过 GitHub CLI 发布 rules.json 和中文 rules.txt。"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def command(root, args, *, input=None, check=True):
    result = subprocess.run(args, cwd=root, input=input, capture_output=True)
    if check and result.returncode:
        message = result.stderr.decode('utf-8', errors='replace').strip()
        raise RuntimeError(f'{args[0]} 操作失败：{message}')
    return result


def git(root, *args, **kwargs):
    return command(root, ['git', *args], **kwargs)


def repository_from_origin(root):
    remote = git(root, 'remote', 'get-url', '--push', 'origin').stdout.decode().strip()
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?', remote)
    if not match:
        raise RuntimeError('origin 的推送地址须为 GitHub 仓库的 HTTPS 或 SSH 地址。')
    return match[1]


def api(root, method, endpoint, *, body=None, content_type='application/json', binary=False, check=True):
    args = ['gh', 'api', '--method', method, endpoint,
            '-H', 'Accept: ' + ('application/octet-stream' if binary else 'application/vnd.github+json')]
    if body is not None:
        args += ['-H', f'Content-Type: {content_type}',
                 '-H', f'Content-Length: {len(body)}', '--input', '-']
    result = command(root, args, input=body, check=check)
    if not check:
        return result
    return result.stdout if binary else json.loads(result.stdout)


def json_body(value):
    return json.dumps(value, ensure_ascii=False).encode('utf-8')


def publish(version, *, root=ROOT, tag=None, message=None, dry_run=False):
    root = Path(root)
    if not re.fullmatch(r'[0-9]{8}', version):
        raise ValueError('规则日期须为 YYYYMMDD。')
    datetime.strptime(version, '%Y%m%d')
    artifacts = [
        (f'scripts/{version}.json', 'rules.json', 'application/json'),
        (f'plain_text/{version}_Zh.txt', 'rules.txt', 'text/plain'),
    ]
    for path, _, _ in artifacts:
        if not (root / path).is_file():
            raise RuntimeError(f'找不到 {path}，请先准备源文件并运行编译命令。')
    repo = repository_from_origin(root)
    branch = git(root, 'symbolic-ref', '--short', 'HEAD').stdout.decode().strip()
    tag = tag or f'cr-{version}'
    git(root, 'check-ref-format', f'refs/tags/{tag}')
    title = f'完整规则 {version}'
    tag_exists = git(root, 'show-ref', '--verify', '--quiet', f'refs/tags/{tag}', check=False).returncode == 0
    if dry_run:
        print(f'发布预览：{repo}，分支 {branch}，标签 {tag}')
        print(git(root, 'status', '--short').stdout.decode(), end='')
        if tag_exists:
            print('将尝试继续已有 Release 草稿，使用该标签中的 JSON 和中文源文件，核对附件后正式发布并设为 latest。')
        else:
            print('将提交所有未忽略的仓库变更，推送分支及标签，创建草稿，'
                  '上传 rules.json 和中文 rules.txt，核对附件后正式发布并设为 latest。')
        return None

    command(root, ['gh', 'auth', 'status', '--hostname', 'github.com'])
    releases = f'repos/{repo}/releases'
    existing = api(root, 'GET', f'{releases}?per_page=100')
    draft = next((item for item in existing if item['tag_name'] == tag), None)
    if draft is not None:
        if not draft['draft']:
            raise RuntimeError(f'Release {tag} 已正式发布，请选择新的修订标签。')
        commit = git(root, 'rev-parse', f'refs/tags/{tag}^{{commit}}').stdout.decode().strip()
        print(f'继续草稿：{draft["html_url"]}')
        print(f'沿用标签 {tag} 的提交 {commit[:7]}，直接继续附件发布。', flush=True)
    else:
        if tag_exists:
            raise RuntimeError(f'本地标签 {tag} 已存在，但没有对应草稿，请选择新的修订标签。')
        git(root, 'add', '--all')
        if git(root, 'diff', '--cached', '--quiet', check=False).returncode:
            git(root, 'commit', '-m', message or f'Update comprehensive rules {version}')
        commit = git(root, 'rev-parse', 'HEAD').stdout.decode().strip()
        git(root, 'tag', '-a', '-m', title, '--', tag)
        git(root, '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential',
            'push', '--atomic', 'origin', f'HEAD:refs/heads/{branch}', f'refs/tags/{tag}')
        print(f'Git 推送成功：origin/{branch}，标签 {tag}，提交 {commit[:7]}。', flush=True)
        draft = api(root, 'POST', releases, body=json_body({
            'tag_name': tag, 'target_commitish': commit, 'name': title,
            'body': f'规则版本：{version}\n\n完整数据：rules.json\n中文文本：rules.txt',
            'draft': True, 'prerelease': False, 'make_latest': 'false',
        }))
        print(f'已创建草稿：{draft["html_url"]}')
    release_id = draft['id']
    payloads = {}
    for path, name, content_type in artifacts:
        payload = git(root, 'show', f'{commit}:{path}').stdout
        payloads[name] = payload
        asset = next((item for item in draft['assets'] if item['name'] == name), None)
        if asset is None:
            asset = api(root, 'POST',
                        f'https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={name}',
                        body=payload, content_type=content_type)
        if (asset['name'], asset['content_type'], asset['size']) != (name, content_type, len(payload)):
            raise RuntimeError(f'{name} 的名称、类型或长度不符，Release 保留为草稿。')
        downloaded = api(root, 'GET', f'{releases}/assets/{asset["id"]}', binary=True)
        if downloaded != payload:
            raise RuntimeError(f'{name} 与已提交文件的字节内容不同，Release 保留为草稿。')
        print(f'附件已核对：{name}', flush=True)
    api(root, 'PATCH', f'{releases}/{release_id}', body=json_body({
        'draft': False, 'prerelease': False, 'make_latest': 'true',
    }))
    latest = api(root, 'GET', f'{releases}/latest')
    if latest['id'] != release_id or latest['draft'] or latest['prerelease']:
        raise RuntimeError('Release 已发布，但 latest 接口未返回本次正式版本，请检查 GitHub。')
    for _, name, content_type in artifacts:
        assets = [item for item in latest['assets'] if item['name'] == name]
        if len(assets) != 1 or assets[0]['content_type'] != content_type:
            raise RuntimeError(f'Release 已发布，但 latest 附件列表中的 {name} 不符合约定。')
        with urlopen(assets[0]['browser_download_url'], timeout=60) as response:
            if response.read() != payloads[name]:
                raise RuntimeError(f'Release 已发布，但 {name} 的正式下载内容不一致。')
    print(f'发布完成：{latest["html_url"]}')
    return latest['html_url']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('date', help='已编译的规则版本日期')
    parser.add_argument('--tag', help='默认 cr-YYYYMMDD；同日修订可指定 cr-YYYYMMDD-r2')
    parser.add_argument('-m', '--message', help='Git 提交说明')
    parser.add_argument('--dry-run', action='store_true', help='只显示发布计划，不提交、推送或发布')
    args = parser.parse_args()
    try:
        publish(args.date, tag=args.tag, message=args.message, dry_run=args.dry_run)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f'发布未完成：{exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
