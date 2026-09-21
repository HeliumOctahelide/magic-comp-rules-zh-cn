"""从逐行对应的中英文源文件编译完整规则数据。"""

import re
from datetime import datetime
from itertools import groupby
from pathlib import Path
from string import ascii_letters

from pypinyin import lazy_pinyin, load_phrases_dict

load_phrases_dict({'重置': [['chóng'], ['zhì']]})
RULE = re.compile(r'^([1-9]\.|[1-9]\d{2}\.|[1-9]\d{2}\.\d+(?:\.|[a-z]+)) (.+)$')
PARAGRAPH = re.compile(r'^(\d+)\.\s')


class RulesError(ValueError):
    """可直接向维护者显示的源文件或契约错误。"""


def rule_date(value):
    if not re.fullmatch(r'[0-9]{8}', value):
        raise RulesError('规则日期须为 YYYYMMDD。')
    try:
        datetime.strptime(value, '%Y%m%d')
    except ValueError as exc:
        raise RulesError(f'无效规则日期：{value}') from exc
    return value


def split_source(path, language):
    path = Path(path)
    lines = [(i, text.strip()) for i, text in enumerate(
        path.read_text(encoding='utf-8-sig').splitlines(), 1)]
    labels = ('Contents', '1. Game Concepts', 'Glossary', 'Credits') if language == 'en' else (
        '目录', '1. 游戏概念', '词汇表', '版权信息')
    positions = []
    for label, count in zip(labels, (1, 2, 2, 2)):
        found = [i for i, (_, text) in enumerate(lines) if text == label]
        if len(found) != count:
            raise RulesError(f'{path}:1: 应有 {count} 处“{label}”，实际 {len(found)} 处。')
        positions.append(found)
    contents, chapters, glossary, credits = positions
    boundaries = [contents[0], chapters[0], glossary[0], credits[0],
                  chapters[1], glossary[1], credits[1]]
    if boundaries != sorted(boundaries):
        raise RulesError(f'{path}:1: 目录、正文、词汇表或版权信息的区段顺序错误。')
    return {
        'intro': lines[:contents[0]],
        'contents': lines[contents[0]:credits[0] + 1],
        'main': lines[chapters[1]:glossary[1]],
        'glossary': lines[glossary[1] + 1:credits[1]],
        'credits': lines[credits[1]:],
    }


def paired_lines(en, zh, section, en_path, zh_path):
    def fail(index, reason):
        a = en[min(index, len(en) - 1)] if en else (1, '')
        b = zh[min(index, len(zh) - 1)] if zh else (1, '')
        raise RulesError(f'{section}: {reason}\n'
                         f'{en_path}:{a[0]}: {a[1]}\n{zh_path}:{b[0]}: {b[1]}')

    if len(en) != len(zh):
        mismatch = min(len(en), len(zh))
        for i, (a, b) in enumerate(zip(en, zh)):
            x, y = RULE.fullmatch(a[1]), RULE.fullmatch(b[1])
            if bool(a[1]) != bool(b[1]) or (x[1] if x else None) != (y[1] if y else None):
                mismatch = i
                break
        fail(mismatch, f'中英行数不同（英文 {len(en)}，中文 {len(zh)}）。')
    for i, (a, b) in enumerate(zip(en, zh)):
        if bool(a[1]) != bool(b[1]):
            fail(i, '空行或段落边界不对应。')
        if section in ('main', 'contents'):
            en_rule, zh_rule = RULE.fullmatch(a[1]), RULE.fullmatch(b[1])
            en_id = en_rule[1] if en_rule else None
            zh_id = zh_rule[1] if zh_rule else None
            if en_id != zh_id:
                fail(i, f'规则编号不对应（{en_id!r} / {zh_id!r}）。')
            if a[1][:1].isdigit() and not en_rule:
                fail(i, '无法识别规则编号或规则正文。')
            if b[1][:1].isdigit() and not zh_rule:
                fail(i, '无法识别规则编号或规则正文。')
        if section == 'main' and a[1].startswith('Example:') != b[1].startswith('例如'):
            fail(i, '例子与正文的段落类型不对应。')
        yield a[0], b[0], a[1], b[1]


def text_pairs(lines):
    return [{'en': en, 'zh': zh} for _, _, en, zh in lines if en]


def parse_main(lines, en_path, zh_path):
    main, stack, seen = [], [], set()
    last = None
    for en_line, zh_line, en, zh in lines:
        if not en:
            continue
        match = RULE.fullmatch(en)
        if not match:
            if last is None:
                raise RulesError(f'{en_path}:{en_line}: 附加段落没有所属规则。')
            last.setdefault('extras', []).append({'en': en, 'zh': zh})
            continue
        number = match[1]
        if number in seen:
            raise RulesError(f'{zh_path}:{zh_line}: 重复规则编号 {number}。')
        seen.add(number)
        if re.fullmatch(r'[1-9]\.', number):
            depth, parent = 0, None
        elif re.fullmatch(r'\d{3}\.', number):
            depth, parent = 1, number[0] + '.'
        elif number.endswith('.'):
            depth, parent = 2, number.split('.')[0] + '.'
        else:
            depth, parent = 3, re.sub(r'[a-z]+$', '.', number)
        if depth and (len(stack) < depth or stack[depth - 1]['chapter'] != parent):
            raise RulesError(f'{zh_path}:{zh_line}: {number} 缺少当前所属上级规则 {parent}。')
        node = {'chapter': number, 'en': match[2], 'zh': RULE.fullmatch(zh)[2]}
        if depth < 3:
            node['subrules'] = []
        (main if depth == 0 else stack[depth - 1]['subrules']).append(node)
        stack[depth:] = [node]
        last = node
    return main


def parse_glossary(lines, en_path, zh_path):
    glossary, seen, block = [], set(), []

    def finish():
        if not block:
            return
        en_line, zh_line, enname, zhname = block[0]
        if len(block) < 2:
            raise RulesError(f'{en_path}:{en_line}: 词条 {enname!r} 缺少解释。')
        if enname in seen:
            raise RulesError(f'{en_path}:{en_line}: 重复英文词条名 {enname!r}。')
        seen.add(enname)
        for a, b, en, zh in block[1:]:
            x, y = PARAGRAPH.match(en), PARAGRAPH.match(zh)
            if (x[1] if x else None) != (y[1] if y else None):
                raise RulesError(f'{en_path}:{a} / {zh_path}:{b}: '
                                 f'词条 {enname!r} 的解释段落编号不对应。')
        glossary.append({'enname': enname, 'zhname': zhname,
                         'en': '\n'.join(row[2] for row in block[1:]),
                         'zh': '\n'.join(row[3] for row in block[1:])})
        block.clear()

    for row in lines:
        if row[2]:
            block.append(row)
        else:
            finish()
    finish()
    return glossary


def glossary_groups(glossary):
    def pinyin_key(item):
        return ''.join(f'{part:0<10}' for part in lazy_pinyin(item['zhname']))

    english = sorted(glossary, key=lambda item: item['enname'])
    letters = [item for item in glossary if item['zhname'][0] in ascii_letters]
    chinese = [item for item in glossary if item['zhname'][0] not in ascii_letters]
    chinese = sorted(letters, key=lambda item: item['zhname']) + sorted(chinese, key=pinyin_key)

    def groups(items, label):
        return [{'label': key, 'entries': [item['enname'] for item in values]}
                for key, values in groupby(items, key=label)]

    return {
        'en': groups(english, lambda item: item['enname'][0]),
        'zh': groups(chinese, lambda item: '字母' if item['zhname'][0] in ascii_letters
                     else pinyin_key(item)[0].upper()),
    }


def walk_rules(nodes):
    for node in nodes:
        yield node
        yield from walk_rules(node.get('subrules', []))


def validate_document(data):
    rule_date(data['version'])
    if [node['chapter'] for node in data['main']] != [f'{i}.' for i in range(1, 10)]:
        raise RulesError('正文须按顺序包含第 1–9 章。')
    ids = [node['chapter'] for node in walk_rules(data['main'])]
    if len(ids) != len(set(ids)):
        raise RulesError('正文存在重复规则编号。')
    for section in ('intro', 'credits'):
        if not data[section]['contents']:
            raise RulesError(f'{section} 不能为空。')
    for item in data['glossary']:
        for field in ('enname', 'zhname', 'en', 'zh'):
            if not isinstance(item[field], str) or not item[field]:
                raise RulesError(f'词汇字段 {field} 必须是非空文字。')
        if len(item['en'].splitlines()) != len(item['zh'].splitlines()):
            raise RulesError(f'词条 {item["enname"]!r} 的中英段落数不对应。')
    names = [item['enname'] for item in data['glossary']]
    if not names or len(names) != len(set(names)):
        raise RulesError('词汇表为空或存在重复英文词条名。')
    if data['glossaryGroups'] != glossary_groups(data['glossary']):
        raise RulesError('词汇分组的引用、覆盖或排序不符合约定。')
    homepage = data['homepage']
    if not isinstance(homepage, str) or not homepage.strip():
        raise RulesError('首页内容不能为空。')
    for name in ('mainGlossary', 'unfinityDoctorGlossary'):
        introduction = data['translatedterms']['introductions'][name]
        if not isinstance(introduction, str) or not introduction:
            raise RulesError(f'暂译名称 {name} 缺少说明文字。')
        for entry in data['translatedterms'][name]:
            if not all(isinstance(entry[key], str) and entry[key] for key in ('English', 'Chinese')):
                raise RulesError(f'暂译名称 {name} 存在空白名称。')


def check_coverage(data, sections, en_path, zh_path):
    for language, path, position in [('en', en_path, 2), ('zh', zh_path, 3)]:
        main = []
        for node in walk_rules(data['main']):
            main.append(f'{node["chapter"]} {node[language]}')
            main.extend(extra[language] for extra in node.get('extras', []))
        glossary = []
        for item in data['glossary']:
            glossary.extend([item[language + 'name'], *item[language].split('\n')])
        actual = {'main': main, 'glossary': glossary,
                  'intro': [item[language] for item in data['intro']['contents']],
                  'credits': [item[language] for item in data['credits']['contents']]}
        for section, values in actual.items():
            expected = [(row[position - 2], row[position]) for row in sections[section] if row[position]]
            if len(values) != len(expected):
                raise RulesError(f'{path}:1: {section} 输入内容未被完整保留。')
            for value, (line, text) in zip(values, expected):
                if value != text:
                    raise RulesError(f'{path}:{line}: {section} 的内容或顺序在编译时发生改变。')


def compile_rules(en_path, zh_path, version, homepage, translatedterms):
    version = rule_date(version)
    en = split_source(en_path, 'en')
    zh = split_source(zh_path, 'zh')
    sections = {section: list(paired_lines(en[section], zh[section], section, en_path, zh_path))
                for section in en}
    data = {
        'version': version,
        'intro': {'contents': text_pairs(sections['intro'])},
        'main': parse_main(sections['main'], en_path, zh_path),
        'glossary': parse_glossary(sections['glossary'], en_path, zh_path),
        'credits': {'contents': text_pairs(sections['credits'])},
        'translatedterms': translatedterms,
        'homepage': homepage,
    }
    data['glossaryGroups'] = glossary_groups(data['glossary'])
    validate_document(data)
    check_coverage(data, sections, en_path, zh_path)
    return data


def flatten_rules(data):
    result = []
    for node in walk_rules(data['main']):
        text = f'{node["chapter"]} {node["en"]}\n{node["zh"]}'
        for extra in node.get('extras', []):
            text += f'\n{extra["en"]}\n{extra["zh"]}'
        result.append({'chapter': node['chapter'][0], 'id': node['chapter'], 'content': text})
    for item in data['glossary']:
        result.append({'chapter': 'glossary', 'id': item['enname'],
                       'content': f'{item["enname"]} {item["en"]}\n{item["zhname"]}\n{item["zh"]}'})
    return result
