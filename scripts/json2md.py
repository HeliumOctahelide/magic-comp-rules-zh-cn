import json, re
import md_template
from pypinyin import lazy_pinyin, load_phrases_dict

load_phrases_dict({'重置': [['chóng'], ['zhì']]})

def plain_text_to_markdown(json_file, output_dir):
    '''
    将json格式的规则文本转化为markdown格式，并分章节输出。
    如果规则的九个大章节有变化，需要修改模板中的对应部分。
    input:
        json_file: json文件路径
        output_dir: 输出目录
    '''
    data = json.load(open(json_file, 'r', encoding='utf-8'))
    intro = data['intro']
    main = data['main']
    glossary = data['glossary']
    credits = data['credits']
    catalog_content = ''
    # 生成main
    HANZI_NUM = '一二三四五六七八九'
    for i in range(len(main)):
        catalog_content += f"- [第{HANZI_NUM[i]}章 - {main[i]['zh']} {main[i]['en']}](/cr/{i+1}/)\n"
        if i == 0:
            prev_next_chapter = f"[第{HANZI_NUM[i+1]}章 - {main[i+1]['zh']} {main[i+1]['en']}](/cr/{i+2}/)"
        elif i == 8:
            prev_next_chapter = f"[第{HANZI_NUM[i-1]}章 - {main[i-1]['zh']} {main[i-1]['en']}](/cr/{i}/)"
        else:
            prev_next_chapter = f"[第{HANZI_NUM[i-1]}章 - {main[i-1]['zh']} {main[i-1]['en']}](/cr/{i}/) | [第{HANZI_NUM[i+1]}章 - {main[i+1]['zh']} {main[i+1]['en']}](/cr/{i+2}/)"
        
        content = ''

        def create_md_text(rule):
            nonlocal content
            nonlocal catalog_content

            def content_is_not_a_sentence(rule):
                return rule['en'].strip()[-1] not in ".)”:" and rule['zh'].strip()[-1] not in "。）”："

            if re.match(r'^\w\.$', rule['chapter']):
                content += f"# {rule['chapter']} {rule['zh']} {rule['en']}\n"
            elif re.match(r'^\w+\.$', rule['chapter']):
                content += f"## <span id='cr{chapter_num_to_bookmark(rule['chapter'])}'>{rule['chapter']}</span> {rule['zh']} {rule['en']}\n"
                catalog_content += f"    - [{rule['chapter']} {rule['zh']} {rule['en']}](/cr/{rule['chapter'][0]}/#cr{rule['chapter'][:-1]})  \n"
            elif content_is_not_a_sentence(rule):
                content += f"### <span id=cr{chapter_num_to_bookmark(rule['chapter'])}>{rule['chapter']}"
                content += f" {rule['zh']} {rule['en']}</span>\n" if rule['en'] != rule['zh'] else f" {rule['zh']}</span>\n"
            else:
                content += f"<b id='cr{chapter_num_to_bookmark(rule['chapter'])}'>{rule['chapter']}</b> {match_rule_num(rule['zh'])}   \n"
                content += f"<b>{rule['chapter']}</b> {rule['en']}\n"
                content += '\n'
            if 'extras' in rule and rule['extras']:
                for extra in rule['extras']:
                    content += f"{match_rule_num(extra['zh'])}   \n"
                    content += f"{extra['en']}\n"
                    content += '\n'
            if 'subrules' in rule and rule['subrules']:
                for subrule in rule['subrules']:
                    create_md_text(subrule)
            
        def chapter_num_to_bookmark(chapter_num):
            if chapter_num[-1] == '.': chapter_num = chapter_num[:-1]
            return chapter_num.replace('.', '-')

        def chapter_num_to_link(chapter_match: re.Match):
            startwith = chapter_match.group(1)
            chapter_num = chapter_match.group(2)
            if chapter_num[-1] == '.': chapter_num = chapter_num[:-1]
            return f"{startwith}[{chapter_num}](/cr/{chapter_num[0]}/#cr{chapter_num_to_bookmark(chapter_num.split('-')[0])})"

        def format_url(match):
            url = match.group(0)
            if not url.startswith(("http://", "https://")):
                url = "http://" + url
            return f"[{url}]"

        def match_rule_num(text):
            text = re.sub(r'第(\d)章', r'[第\1章](/cr/\1/)', text)
            text = re.sub(r'([规则|和|及|与|、|，])(\d{3}\.?\d*[a-z\.]?\-?\d*[a-z\.]?)', chapter_num_to_link, text)
            text = re.sub(r'([\dA-z]+\.)?wizards\.com[\dA-z\-/]*', format_url, text, flags=re.IGNORECASE)
            return text

        create_md_text(main[i])

        catalog_content += "\n"

        main_text = md_template.MAIN_TEMPLATE.format(prev_next_chapter=prev_next_chapter, content=content)
        with open(f'{output_dir}/{i+1}.md', 'w', encoding='utf-8') as f:
            f.write(main_text)

    # 生成glossary
    ## 按英文字母排序
    sorted_glossary = sorted(glossary, key=lambda x: x['enname'])
    current_letter = ''
    content = ''
    
    for item in sorted_glossary:
        if item['enname'][0] != current_letter:
            current_letter = item['enname'][0]
            content += f"## {current_letter}\n"
        content += f"### <span id='{item['enname']}'>{item['enname']}</span> / <span id='{item['zhname']}'>{item['zhname']}</span>\n"
        # content += f"<b id='{item['enname']}'>{item['enname']}</b>   \n"
        # content += f"<b id='{item['zhname']}'>{item['zhname']}</b>\n"
        # content += '\n'
        for en_line, zh_line in zip(item['en'].split('\n'), item['zh'].split('\n')):
            content += f"{match_rule_num(zh_line)}   \n"
            content += f"{en_line}\n"
            content += '\n'
        content += '----\n'
    glossary_text = md_template.GLOSSARY_ALPHABET_TEMPLATE.format(content=content)    
    with open(f'{output_dir}/glossary.md', 'w', encoding='utf-8') as f:
        f.write(glossary_text)

    glossary_zh_with_letter = [i for i in glossary if i['zhname'][0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz']
    glossary_zh = [i for i in glossary if i['zhname'][0] not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz']

    sorted_glossary_zh = sorted(glossary_zh_with_letter, key=lambda x: x['zhname']) + sorted(glossary_zh, key=lambda x: ''.join([f"{i:0<10}" for i in lazy_pinyin(x['zhname'])]))
    current_letter = ''
    content = ''
    
    for item in sorted_glossary_zh:
        if item['zhname'][0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz':
            if not current_letter: content += f"## 字母\n"
            current_letter = '字母'
        elif ''.join([f"{i:0<10}" for i in lazy_pinyin(item['zhname'])])[0].upper() != current_letter:
            current_letter = lazy_pinyin(item['zhname'][0])[0][0].upper()
            content += f"## {current_letter}\n"
        content += f"### <span id='{item['zhname']}'>{item['zhname']}</span> / <span id='{item['enname']}'>{item['enname']}</span>\n"    
        # content += f"<b id='{item['enname']}'>{item['enname']}</b>   \n"
        # content += f"<b id='{item['zhname']}'>{item['zhname']}</b>\n"
        # content += '\n'
        for en_line, zh_line in zip(item['en'].split('\n'), item['zh'].split('\n')):
            content += f"{match_rule_num(zh_line)}   \n"
            content += f"{en_line}\n"
            content += '\n'
    glossarycn_text = md_template.GLOSSARY_PINYIN_TEMPLATE.format(content=content)  
    with open(f'{output_dir}/glossarycn.md', 'w', encoding='utf-8') as f:
        f.write(glossarycn_text)

    # 生成intro和credits
    def format_bold_and_italic(text):
        text = text.replace("万智牌游戏原始设计", "**万智牌游戏原始设计**")
        text = text.replace("完整规则设计与开发", "**完整规则设计与开发**")
        text = text.replace("编辑", "**编辑**")
        text = text.replace("万智牌规则经理", "**万智牌规则经理**")
        text = text.replace("感谢我们所有的队伍成员", "**感谢**我们所有的队伍成员")
        text = text.replace("此规则于", "*此规则于")
        text = text.replace("日起生效。", "日起生效。*")
        text = text.replace("万智牌", "*万智牌*")
        return text

    content = ''
    for item in intro['contents'][3:]: # 头三行是标题和生效时间等，不需要
        content += f"{item['zh']}   \n"
        content += f"{item['en']}\n"
        content += '\n'

    intro_text = md_template.INTRO_TEMPLATE.format(content=format_bold_and_italic(content))
    with open(f'{output_dir}/intro.md', 'w', encoding='utf-8') as f:
        f.write(intro_text)

    content = ''
    for item in credits['contents'][1:]: # 第一行是标题，不需要
        content += f"{item['zh']}\n"
        # content += f"{item['en']}\n"
        content += '\n'
    
    credits_text = md_template.CREDITS_TEMPLATE.format(content=format_bold_and_italic(content))
    with open(f'{output_dir}/credits.md', 'w', encoding='utf-8') as f:
        f.write(credits_text)

    catalog_text = md_template.CATALOG_TEMPLATE.format(effective_time=intro['contents'][1]['zh'], content=catalog_content)
    with open(f'{output_dir}/index.md', 'w', encoding='utf-8') as f:
        f.write(catalog_text)

def terms_to_markdown(json_data, output_dir):
    """
    接收一个包含 mainGlossary 和 unfinityDoctorGlossary 两个键的 JSON 对象，
    会自动按照 English 字段进行字母顺序排序，然后输出完整 Markdown 字符串：
    1) 标题 # 暂译名称列表
    2) 原本的说明文字
    3) 第一张表格（mainGlossary）
    4) 中间过渡文本
    5) 第二张表格（unfinityDoctorGlossary）
    """
    data = json.load(open(json_data, 'r'))
    # 原本 Markdown 文件中的说明文本
    title = "# 暂译名称列表\n"
    intro_text = (
        "\n\n下列名称暂未有正式中文译名，以下中文名称为暂译名称。\n\n"
    )
    between_tables_text = (
        "\n\n下列出现于*Unfinity*、*无疆新宇宙：神秘博士*系列中的名词之译名在官网文章中出现，但未出现于卡牌上。\n\n"
    )

    # 定义一个字符串模板，用于拼接 Markdown 表格的头部
    table_header_template = """| English | 中文 |
| --- | --- |"""

    # 将列表中的每条记录格式化为 Markdown 表格行
    def dict_list_to_md_rows(dict_list):
        md_lines = []
        # 按 English 字段进行字母顺序排序
        sorted_list = sorted(dict_list, key=lambda x: x.get("English", "").lower())
        for item in sorted_list:
            english = item.get("English", "")
            chinese = item.get("Chinese", "")
            md_lines.append(f"| {english} | {chinese} |")
        return "\n".join(md_lines)

    # 取出 mainGlossary 列表并转换为 Markdown
    main_data = data.get("mainGlossary", [])
    main_table_body = dict_list_to_md_rows(main_data)
    main_table_md = f"{table_header_template}\n{main_table_body}"

    # 取出 unfinityDoctorGlossary 列表并转换为 Markdown
    unfinity_data = data.get("unfinityDoctorGlossary", [])
    unfinity_table_body = dict_list_to_md_rows(unfinity_data)
    unfinity_table_md = f"{table_header_template}\n{unfinity_table_body}"

    # 将各部分拼接成完整 Markdown 内容
    markdown_output = (
        title
        + intro_text
        + main_table_md
        + between_tables_text
        + unfinity_table_md
    )

    with open(f'{output_dir}/translatedterms.md', 'w', encoding='utf-8') as f:
        f.write(markdown_output)

if __name__ == '__main__':
    # plain_text_to_markdown('./20250207.json', '../markdown')
    # terms_to_markdown('./translatedterms.json', '../markdown')
    import argparse
    parser = argparse.ArgumentParser(description='Convert JSON to Markdown.')
    parser.add_argument('date', type=str, help='Date of the JSON file (e.g., 20250207)')
    args = parser.parse_args()

    plain_text_to_markdown(f'./{args.date}.json', '../markdown')
    terms_to_markdown(f'./translatedterms.json', '../markdown')