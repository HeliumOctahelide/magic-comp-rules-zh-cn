"""一个命令完成源文件检查、完整 JSON 和全部派生格式的生成。"""

import argparse
import json
from pathlib import Path
import sys
import tempfile

import json2doku
import json2md
from plain2json import RulesError, compile_rules, flatten_rules, rule_date, validate_document, walk_rules

ROOT = Path(__file__).resolve().parents[1]


def json_text(data, indent=4):
    return json.dumps(data, ensure_ascii=False, indent=indent) + '\n'


def build(version, root=ROOT):
    version = rule_date(version)
    root = Path(root)
    homepage = (root / 'scripts/homepage.html').read_text(encoding='utf-8').strip()
    terms = json.loads((root / 'scripts/translatedterms.json').read_text(encoding='utf-8'))
    data = compile_rules(root / f'plain_text/{version}_En.txt',
                         root / f'plain_text/{version}_Zh.txt', version, homepage, terms)
    # 所有校验与渲染成功后，才替换工作区内的产物。
    with tempfile.TemporaryDirectory(prefix='cr-build-') as directory:
        stage = Path(directory)
        (stage / 'scripts').mkdir()
        output = stage / f'scripts/{version}.json'
        output.write_text(json_text(data), encoding='utf-8')
        data = json.loads(output.read_text(encoding='utf-8'))
        validate_document(data)
        (stage / 'scripts/plain_rules.json').write_text(
            json_text(flatten_rules(data), indent=None), encoding='utf-8')
        for folder, renderer in [('markdown', json2md.render), ('dokuwiki', json2doku.render)]:
            destination = stage / folder
            destination.mkdir()
            renderer(data, destination)
        for source in sorted(stage.rglob('*')):
            if source.is_file():
                target = root / source.relative_to(stage)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('date', help='规则版本日期，例如 20260925')
    args = parser.parse_args()
    try:
        data = build(args.date)
    except (RulesError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f'编译失败：{exc}', file=sys.stderr)
        return 1
    print(f'编译完成：{data["version"]}，9 章，'
          f'{sum(1 for _ in walk_rules(data["main"]))} 个规则节点，'
          f'{len(data["glossary"])} 个词条。')
    print(f'完整 JSON：{ROOT / "scripts" / (data["version"] + ".json")}')
    print('已生成 Markdown、DokuWiki 和搜索 JSON。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
