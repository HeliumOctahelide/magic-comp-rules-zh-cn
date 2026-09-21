import re
from html.parser import HTMLParser
import doku_template

class HomepageParser(HTMLParser):
    """将首页的段落、列表和链接写成 DokuWiki 文本。"""

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.parts.append(f"[[{dict(attrs)['href']}|")
        elif tag == 'li':
            self.parts.append('  * ')
        elif tag == 'br':
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag == 'a':
            self.parts.append(']]')
        elif tag in ('p', 'ul'):
            self.parts.append('\n\n')
        elif tag == 'li':
            self.parts.append('\n')

    def handle_data(self, text):
        if text.strip():
            self.parts.append(text)

def render(data, output_dir):
    '''
    将完整 JSON 数据渲染为 DokuWiki，并分章节输出。
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
        catalog_content += f"[[CR:{i+1}|第{HANZI_NUM[i]}章 - {main[i]['zh']} {main[i]['en']}]]\n"
        if i == 0:
            prev_next_chapter = f"[[cr:{i+2}|第{HANZI_NUM[i+1]}章 - {main[i+1]['zh']} {main[i+1]['en']}]]"
        elif i == 8:
            prev_next_chapter = f"[[cr:{i}|第{HANZI_NUM[i-1]}章 - {main[i-1]['zh']} {main[i-1]['en']}]]"
        else:
            prev_next_chapter = f"[[cr:{i}|第{HANZI_NUM[i-1]}章 - {main[i-1]['zh']} {main[i-1]['en']}]] | [[cr:{i+2}|第{HANZI_NUM[i+1]}章 - {main[i+1]['zh']} {main[i+1]['en']}]]"
        
        content = ''

        def create_doku_text(rule):
            nonlocal content
            nonlocal catalog_content
            if re.match(r'^\w\.$', rule['chapter']):
                content += f"====== {rule['chapter']} {rule['zh']} {rule['en']} ======\n"
            elif re.match(r'^\w+\.$', rule['chapter']):
                content += f"===== {rule['chapter']} {rule['zh']} {rule['en']} =====\n"
                catalog_content += f"  * [[CR:{rule['chapter'][0]}#{rule['zh']}_{rule['en'].lower().replace(' ', '_')}|{rule['chapter']} {rule['zh']} {rule['en']}]]\n"

            content += f"<BOOKMARK:cr{chapter_num_to_bookmark(rule['chapter'])}>{rule['chapter']} {rule['en']}\\\\ \n"
            content += f"{rule['chapter']} {match_rule_num(rule['zh'])}\n"
            content += '\n'
            if 'extras' in rule and rule['extras']:
                for extra in rule['extras']:
                    content += f"{extra['en']}\\\\ \n"
                    content += f"{match_rule_num(extra['zh'])}\n"
                    content += '\n'
            if 'subrules' in rule and rule['subrules']:
                for subrule in rule['subrules']:
                    create_doku_text(subrule)
            
        def chapter_num_to_bookmark(chapter_num):
            if chapter_num[-1] == '.': chapter_num = chapter_num[:-1]
            return chapter_num.replace('.', '-')

        def chapter_num_to_link(chapter_match: re.Match):
            startwith = chapter_match.group(1)
            chapter_num = chapter_match.group(2)
            if chapter_num[-1] == '.': chapter_num = chapter_num[:-1]
            return f"{startwith}[[cr:{chapter_num[0]}#cr{chapter_num_to_bookmark(chapter_num.split('-')[0])}|{chapter_num}]]"

        def format_url(match):
            url = match.group(0)
            if not url.startswith(("http://", "https://")):
                url = "http://" + url
            return f"[url]{url}[/url]"

        def match_rule_num(text):
            text = re.sub(r'第(\d)章', r'[[cr:\1|第\1章]]', text)
            text = re.sub(r'([规则|和|及|与|、|，])(\d{3}\.?\d*[a-z\.]?\-?\d*[a-z\.]?)', chapter_num_to_link, text)
            text = re.sub(r'([\dA-z]+\.)?wizards\.com[\dA-z\-/]*', format_url, text, flags=re.IGNORECASE)
            return text

        create_doku_text(main[i])

        catalog_content += "\n"

        main_text = doku_template.MAIN_TEMPLATE.format(prev_next_chapter=prev_next_chapter, content=content)
        with open(f'{output_dir}/{i+1}.txt', 'w', encoding='utf-8') as f:
            f.write(main_text)

    # 两种视图共享正文，顺序完全由完整 JSON 决定。
    entries = {item['enname']: item for item in glossary}
    for view, filename, template in [
        ('en', 'glossary.txt', doku_template.GLOSSARY_ALPHABET_TEMPLATE),
        ('zh', 'glossarycn.txt', doku_template.GLOSSARY_PINYIN_TEMPLATE),
    ]:
        content = ''
        for group in data['glossaryGroups'][view]:
            content += f"=== {group['label']} ===\n"
            for name in group['entries']:
                item = entries[name]
                content += f"{item['enname']}\\\\ \n{item['zhname']}\n\n"
                for en_line, zh_line in zip(item['en'].split('\n'), item['zh'].split('\n')):
                    content += f"{en_line}\\\\ \n{match_rule_num(zh_line)}\n\n"
                content += '----\n'
        with open(f'{output_dir}/{filename}', 'w', encoding='utf-8') as f:
            page = filename.removesuffix('.txt')
            navigation = ' - '.join(
                f"[[cr:{page}#{group['label'].lower()}|{group['label']}]]"
                for group in data['glossaryGroups'][view])
            f.write(template.format(content=content, navigation=navigation))

    # 生成intro和credits
    def format_bold_and_italic(text):
        text = text.replace("万智牌游戏原始设计：", "**万智牌游戏原始设计：**")
        text = text.replace("完整规则设计与开发：", "**完整规则设计与开发：**")
        text = text.replace("编辑：", "**编辑：**")
        text = text.replace("万智牌规则经理：", "**万智牌规则经理：**")
        text = text.replace("感谢我们所有的队伍成员", "**感谢**我们所有的队伍成员")
        text = text.replace("此规则于", "//此规则于")
        text = text.replace("日起生效。", "日起生效。//")
        text = text.replace("万智牌", "//万智牌//")
        return text

    content = ''
    for item in intro['contents'][3:]: # 头三行是标题和生效时间等，不需要
        content += f"{item['zh']}\\\\ \n"
        content += f"{item['en']}\n"
        content += '\n'

    intro_text = doku_template.INTRO_TEMPLATE.format(content=format_bold_and_italic(content))
    with open(f'{output_dir}/intro.txt', 'w', encoding='utf-8') as f:
        f.write(intro_text)

    content = ''
    for item in credits['contents'][1:]: # 第一行是标题，不需要
        content += f"{item['zh']}\n"
        # content += f"{item['en']}\n"
        content += '\n'
    
    credits_text = doku_template.CREDITS_TEMPLATE.format(content=format_bold_and_italic(content))
    with open(f'{output_dir}/credits.txt', 'w', encoding='utf-8') as f:
        f.write(credits_text)

    parser = HomepageParser()
    parser.feed(data['homepage'])
    homepage = ''.join(parser.parts).strip()
    catalog_text = doku_template.CATALOG_TEMPLATE.format(effective_time=intro['contents'][1]['zh'], content=catalog_content, homepage=homepage)
    with open(f'{output_dir}/catalog.txt', 'w', encoding='utf-8') as f:
        f.write(catalog_text)

    render_terms(data['translatedterms'], output_dir)

def render_terms(data, output_dir):
    """
    接收一个包含 mainGlossary 和 unfinityDoctorGlossary 两个键的 JSON 文件，
    会自动按照 English 字段进行字母顺序排序，然后输出 DOKUWIKI 格式文本：
      1) 返回完整规则目录的链接
      2) 标题
      3) 说明文字
      4) 第一张表（mainGlossary）
      5) 中间说明文字（提及 *Unfinity* / 无疆新宇宙：神秘博士）
      6) 第二张表（unfinityDoctorGlossary）
      7) 最后插入 "规则和文档索引" 的 nofooter 页面
    """
    # 读取 JSON 数据

    # 1) 返回完整规则目录的链接
    back_link = "[[:完整规则|返回完整规则目录]]\n"

    # 2) 标题
    title = "====== 暂译名称列表 ======\n\n"

    # 3) 第一段说明文字
    intro_text = '\n\n' + data['introductions']['mainGlossary'] + '\n\n'

    # 4) 第一张表（mainGlossary）
    #    DOKUWIKI 使用 ^ 作为表格的单元格边界
    #    表头举例：^英文名^暂译中文名^
    def glossary_to_dokuwiki_table(entries):
        """
        将 glossary 列表转换为 DOKUWIKI 表格
        """
        # 先按 English 字段做排序
        sorted_entries = sorted(entries, key=lambda x: x.get("English", "").lower())
        lines = []
        # 表头
        lines.append("^英文名^暂译中文名^")
        # 表体
        for item in sorted_entries:
            english = item.get("English", "")
            chinese = item.get("Chinese", "")
            # 每一行示例： ^Ante|押注（用作动词）/赌注（用作名词）|
            lines.append(f"^{english}|{chinese}|")
        return "\n".join(lines)

    main_data = data.get("mainGlossary", [])
    main_table = glossary_to_dokuwiki_table(main_data)

    # 5) 第二段说明文字（中间过渡文本）
    #    DOKUWIKI 的斜体用 // 来表示
    #    这里与 Markdown 不同，需要将 * 替换为 //
    between_tables_text = '\n\n' + data['introductions']['unfinityDoctorGlossary'].replace('Unfinity', '//Unfinity//').replace('无疆新宇宙：神秘博士', '//无疆新宇宙：神秘博士//') + '\n\n'

    # 6) 第二张表（unfinityDoctorGlossary）
    unfinity_data = data.get("unfinityDoctorGlossary", [])
    unfinity_table = glossary_to_dokuwiki_table(unfinity_data)

    # 7) 最后插入 nofooter 页面
    nofooter_text = "\n\n{{page>:规则和文档索引&nofooter}}\n"

    # 拼接成完整 DOKUWIKI 内容
    dokuwiki_output = (
        back_link
        + title
        + intro_text
        + main_table
        + between_tables_text
        + unfinity_table
        + nofooter_text
    )
    
    # 写出到目标文件
    with open(f'{output_dir}/translatedterms.txt', 'w', encoding='utf-8') as f:
        f.write(dokuwiki_output)
