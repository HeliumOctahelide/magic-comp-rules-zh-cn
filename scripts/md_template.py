INTRO_TEMPLATE = """[返回完整规则目录](./)

# 前言

{content}

[第一章 - 游戏概念 Game Concepts](./1)"""

MAIN_TEMPLATE = """[返回完整规则目录](./) | {prev_next_chapter}

{content}

[返回完整规则目录](./) | {prev_next_chapter}"""

GLOSSARY_PINYIN_TEMPLATE = """[返回完整规则目录](./)
# 词汇表（按拼音首字母排序）

{content}"""

GLOSSARY_ALPHABET_TEMPLATE = """[返回完整规则目录](./)
# 词汇表（按英文首字母排序） 

{content}"""

CREDITS_TEMPLATE = """[返回完整规则目录](./)

# 版权信息 
{content}"""

CATALOG_TEMPLATE = """# 目录

*{effective_time}*

[前言](./intro)

{content}

词汇表 Glossary - [按英文首字母排序](./glossary) | [按拼音首字母排序](./glossarycn)

[暂译名称列表](./translatedterms)

[版权信息](./credits)
"""