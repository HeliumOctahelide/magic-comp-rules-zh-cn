"""提交已有产物，并通过 GitHub CLI 发布 rules.json。"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote
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
        args += ['-H', f'Content-Type: {content_type}', '--input', '-']
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
    artifact = f'scripts/{version}.json'
    if not (root / artifact).is_file():
        raise RuntimeError(f'找不到已编译的 {artifact}，请先运行编译命令。')
    repo = repository_from_origin(root)
    branch = git(root, 'symbolic-ref', '--short', 'HEAD').stdout.decode().strip()
    tag = tag or f'cr-{version}'
    git(root, 'check-ref-format', f'refs/tags/{tag}')
    title = f'完整规则 {version}'
    if dry_run:
        print(f'发布预览：{repo}，分支 {branch}，标签 {tag}')
        print(git(root, 'status', '--short').stdout.decode(), end='')
        print(f'将提交所有未忽略的仓库变更，推送分支及标签，创建草稿，'
              f'上传 {artifact} 为 rules.json，核对附件后正式发布并设为 latest。')
        return None

    command(root, ['gh', 'auth', 'status', '--hostname', 'github.com'])
    if git(root, 'show-ref', '--verify', '--quiet', f'refs/tags/{tag}', check=False).returncode == 0:
        raise RuntimeError(f'本地标签 {tag} 已存在，请选择新的修订标签。')
    releases = f'repos/{repo}/releases'
    existing = api(root, 'GET', f'{releases}/tags/{quote(tag, safe="")}', check=False)
    if existing.returncode == 0:
        raise RuntimeError(f'Release {tag} 已存在，请选择新的修订标签。')
    if 'HTTP 404' not in existing.stderr.decode('utf-8', errors='replace'):
        raise RuntimeError(existing.stderr.decode('utf-8', errors='replace').strip())

    git(root, 'add', '--all')
    if git(root, 'diff', '--cached', '--quiet', check=False).returncode:
        git(root, 'commit', '-m', message or f'Update comprehensive rules {version}')
    commit = git(root, 'rev-parse', 'HEAD').stdout.decode().strip()
    payload = git(root, 'show', f'{commit}:{artifact}').stdout
    git(root, 'tag', '-a', '-m', title, '--', tag)
    git(root, '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential',
        'push', '--atomic', 'origin', f'HEAD:refs/heads/{branch}', f'refs/tags/{tag}')

    draft = api(root, 'POST', releases, body=json_body({
        'tag_name': tag, 'target_commitish': commit, 'name': title,
        'body': f'规则版本：{version}\n\n完整数据附件：rules.json',
        'draft': True, 'prerelease': False, 'make_latest': 'false',
    }))
    release_id = draft['id']
    print(f'已创建草稿：{draft["html_url"]}')
    asset = api(root, 'POST',
                f'https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name=rules.json',
                body=payload)
    if (asset['name'], asset['content_type'], asset['size']) != ('rules.json', 'application/json', len(payload)):
        raise RuntimeError('附件名称、类型或长度不符，Release 保留为草稿。')
    downloaded = api(root, 'GET', f'{releases}/assets/{asset["id"]}', binary=True)
    if downloaded != payload:
        raise RuntimeError('附件与已提交 JSON 的字节内容不同，Release 保留为草稿。')
    api(root, 'PATCH', f'{releases}/{release_id}', body=json_body({
        'draft': False, 'prerelease': False, 'make_latest': 'true',
    }))
    latest = api(root, 'GET', f'{releases}/latest')
    if latest['id'] != release_id or latest['draft'] or latest['prerelease']:
        raise RuntimeError('Release 已发布，但 latest 接口未返回本次正式版本，请检查 GitHub。')
    assets = [item for item in latest['assets'] if item['name'] == 'rules.json']
    if len(assets) != 1 or assets[0]['content_type'] != 'application/json':
        raise RuntimeError('Release 已发布，但 latest 附件列表不符合约定。')
    with urlopen(assets[0]['browser_download_url'], timeout=60) as response:
        if response.read() != payload:
            raise RuntimeError('Release 已发布，但正式附件下载内容不一致。')
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
