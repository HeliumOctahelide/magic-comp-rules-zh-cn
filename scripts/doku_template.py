INTRO_TEMPLATE = """[[:完整规则|返回完整规则目录]]

====== 前言 ======

{content}

[[cr:1|第一章 - 游戏概念 Game Concepts]]
{{{{page>:规则和文档索引&nofooter}}}}"""

MAIN_TEMPLATE = """[[:完整规则|返回完整规则目录]] | {prev_next_chapter}
{content}

[[:完整规则|返回完整规则目录]] | {prev_next_chapter}

{{{{page>:规则和文档索引&nofooter}}}}"""

GLOSSARY_PINYIN_TEMPLATE = """[[:完整规则|返回完整规则目录]]
====== 词汇表（按拼音首字母排序） ======
<WRAP centeralign>
{navigation}</WRAP>
----

{content}
----
{{{{page>:规则和文档索引&nofooter}}}}
"""

GLOSSARY_ALPHABET_TEMPLATE = """[[:完整规则|返回完整规则目录]]
====== 词汇表（按英文首字母排序） ======
<WRAP centeralign>
{navigation}</WRAP>
----

{content}
----
{{{{page>:规则和文档索引&nofooter}}}}
"""

CREDITS_TEMPLATE = """[[:完整规则|返回完整规则目录]]

====== 版权信息 ======
{content}
"""

CATALOG_TEMPLATE = """====== 万智牌完整规则 Magic Comprehensive Rules ======

{homepage}

===== 目录 =====
//{effective_time}//

[[CR:Intro|前言]]

{content}

词汇表 Glossary - [[CR:Glossary|按英文首字母排序]] | [[CR:Glossarycn|按拼音首字母排序]]

[[CR:credits|版权信息]]

  * [[CR:TranslatedTerms|暂译名称列表]]
  * [[cr:updates:index|CR更新摘要索引]]

{{{{page>规则和文档索引&nofooter}}}}"""