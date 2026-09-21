import re
import md_template

def escape_list_number(text):
    return re.sub(r'^(\d+)\.(?=\s)', r'\1\\.', text)

def render(data, output_dir):
    '''
    将完整 JSON 数据渲染为 Markdown，并分章节输出。
    如果规则的九个大章节有变化，需要修改模板中的对应部分。
    input:
        data: 已校验的完整 JSON 对象
        output_dir: 输出目录
    '''
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
                if rule['zh'].strip() == "∞（无限）":
                    return True
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

    # 两种视图共享正文，顺序完全由完整 JSON 决定。
    entries = {item['enname']: item for item in glossary}
    for view, filename, template in [
        ('en', 'glossary.md', md_template.GLOSSARY_ALPHABET_TEMPLATE),
        ('zh', 'glossarycn.md', md_template.GLOSSARY_PINYIN_TEMPLATE),
    ]:
        content = ''
        for group in data['glossaryGroups'][view]:
            content += f"## {group['label']}\n"
            for name in group['entries']:
                item = entries[name]
                names = (item['enname'], item['zhname']) if view == 'en' else (item['zhname'], item['enname'])
                content += f"### <span id='{names[0]}'>{names[0]}</span> / <span id='{names[1]}'>{names[1]}</span>\n"
                for en_line, zh_line in zip(item['en'].split('\n'), item['zh'].split('\n')):
                    content += f"{match_rule_num(escape_list_number(zh_line))}   \n"
                    content += f"{escape_list_number(en_line)}\n\n"
                if view == 'en':
                    content += '----\n'
        with open(f'{output_dir}/{filename}', 'w', encoding='utf-8') as f:
            f.write(template.format(content=content))

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

    catalog_text = md_template.CATALOG_TEMPLATE.format(effective_time=intro['contents'][1]['zh'], content=catalog_content, homepage=data['homepage'])
    with open(f'{output_dir}/index.md', 'w', encoding='utf-8') as f:
        f.write(catalog_text)

    render_terms(data['translatedterms'], output_dir)

def render_terms(data, output_dir):
    """
    接收一个包含 mainGlossary 和 unfinityDoctorGlossary 两个键的 JSON 对象，
    会自动按照 English 字段进行字母顺序排序，然后输出完整 Markdown 字符串：
    1) 标题 # 暂译名称列表
    2) 原本的说明文字
    3) 第一张表格（mainGlossary）
    4) 中间过渡文本
    5) 第二张表格（unfinityDoctorGlossary）
    """
    # 原本 Markdown 文件中的说明文本
    title = "# 暂译名称列表\n"
    intro_text = '\n\n' + data['introductions']['mainGlossary'] + '\n\n'

    between_tables_text = '\n\n' + data['introductions']['unfinityDoctorGlossary'].replace('Unfinity', '*Unfinity*').replace('无疆新宇宙：神秘博士', '*无疆新宇宙：神秘博士*') + '\n\n'

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
