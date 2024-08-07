import re, json

def plain_text_to_json(en_text, zh_text, output_file, version):
    '''
    将纯文本的规则文本转化为JSON格式。
    *注意！输入的英文和中文文本需要严格按行对齐。*
    args:
        en_text: 英文文本文件路径
        zh_text: 中文文本文件路径
        output_file: 输出文件路径
        version: 一个YYYYMMDD格式的字符串，表示规则的版本。
    '''
    # 读取英文和中文文件内容
    with open(en_text) as f:
        en_lines = f.readlines()
    with open(zh_text) as f:
        zh_lines = f.readlines()
    
    # 去除每行两端的空格或换行符
    en_lines = [line.strip() for line in en_lines]
    zh_lines = [line.strip() for line in zh_lines]

    # 移除目录部分
    en_lines = en_lines[:en_lines.index('Contents')] + en_lines[en_lines.index('Credits')+1:]
    zh_lines = zh_lines[:zh_lines.index('目录')] + zh_lines[zh_lines.index('版权信息')+1:]

    # 将文件内容按章节分段
    en_intro = en_lines[:en_lines.index('1. Game Concepts')]
    zh_intro = zh_lines[:zh_lines.index('1. 游戏概念')]
    en_main = en_lines[en_lines.index('1. Game Concepts'):en_lines.index('Glossary')]
    zh_main = zh_lines[zh_lines.index('1. 游戏概念'):zh_lines.index('词汇表')]
    en_glossary = en_lines[en_lines.index('Glossary')+1:en_lines.index('Credits')]
    zh_glossary = zh_lines[zh_lines.index('词汇表')+1:zh_lines.index('版权信息')]
    en_credits = en_lines[en_lines.index('Credits'):]
    zh_credits = zh_lines[zh_lines.index('版权信息'):]

    # 将介绍部分转换为JSON格式
    intro = {
        'contents': [{
            'en': en_line,
            'zh': zh_line,
        } for en_line, zh_line in zip(en_intro, zh_intro) if en_line and zh_line],
    }

    # 将主要规则部分转换为JSON格式
    main = []
    last_object = None

    for en_line, zh_line in zip(en_main, zh_main):
        en_number = en_line.split(' ')[0]
        zh_number = zh_line.split(' ')[0]
        en_text = ' '.join(en_line.split(' ')[1:]) if en_line and (en_line[0] in '123456789') else en_line
        zh_text = ' '.join(zh_line.split(' ')[1:]) if zh_line and (zh_line[0] in '123456789') else zh_line
        if en_number != zh_number and en_number != 'Example:':
            print(en_number, zh_number)
            # return 0
        if re.match(r'^\w\.$', zh_number):
            last_object = {
                'chapter': zh_number,
                'en': en_text,
                'zh': zh_text,
                'subrules': []
            }
            main.append(last_object)
        elif re.match(r'^\w+\.$', zh_number):
            last_object = {
                'chapter': zh_number,
                'en': en_text,
                'zh': zh_text,
                'subrules': []
            }
            main[-1]['subrules'].append(last_object)
        elif re.match(r'^\w+\.\w+\.$', zh_number):
            last_object = {
                'chapter': zh_number,
                'en': en_text,
                'zh': zh_text,
                'subrules': []
            }
            main[-1]['subrules'][-1]['subrules'].append(last_object)
        elif re.match(r'^\w+\.\w+[a-z]$', zh_number):
            last_object = {
                'chapter': zh_number,
                'en': en_text,
                'zh': zh_text
            }
            main[-1]['subrules'][-1]['subrules'][-1]['subrules'].append(last_object)
        elif zh_number:
            if 'extras' not in last_object:
                last_object['extras'] = [{
                    'en': en_text,
                    'zh': zh_text
                }]
            else:
                last_object['extras'].append({
                    'en': en_text,
                    'zh': zh_text
                })

    # 将词汇部分转换为JSON格式
    glossary = []
    last_object = None
    for en_line, zh_line in zip(en_glossary, zh_glossary):
        if not en_line and not zh_line:
            if last_object and last_object['enname']: glossary.append(last_object)
            last_object = {
                'enname': None,
                'zhname': None,
                'en': None,
                'zh': None
            }
        elif last_object['enname'] == None and last_object['zhname'] == None:
            last_object['enname'] = en_line
            last_object['zhname'] = zh_line
        elif last_object['en'] == None and last_object['zh'] == None:
            last_object['en'] = en_line
            last_object['zh'] = zh_line
        else:
            last_object['en'] += '\n' + en_line
            last_object['zh'] += '\n' + zh_line

    # 将版权信息部分转换为JSON格式
    credits = {
        'contents': [{
            'en': en_line,
            'zh': zh_line,
        } for en_line, zh_line in zip(en_credits, zh_credits) if en_line and zh_line],
    }
    # 将所有部分组合成一个JSON对象
    output = {
        'version': version,
        'intro': intro,
        'main': main,
        'glossary': glossary,
        'credits': credits,
    }
    json.dump(output, open(output_file, 'w'), ensure_ascii=False, indent=4)


if __name__ == '__main__':
    plain_text_to_json('../plain_text/20240802_En.txt', '../plain_text/20240802_Zh.txt', './20240802.json', '20240802')