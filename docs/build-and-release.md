# 编译与发布

需要 Python 3.10+、Git 和已登录的 GitHub CLI（`gh`）。在仓库根目录安装依赖：

```bash
python -m pip install -r requirements.txt
```

## 编译

```bash
python scripts/build.py 20260925
```

日期对应 `plain_text/` 中的中英文源文件。命令校验内容并生成日期命名的完整 JSON、搜索 JSON、Markdown 和 DokuWiki。

## 发布

```bash
python scripts/release.py 20260925
```

命令提交所有未被 Git 忽略的仓库变更，推送到 `origin`，并将已编译的 JSON 以 `rules.json` 发布到最新正式 Release。修改内容后请先重新编译。

可选参数：

- `--dry-run`：仅预览发布计划。
- `--tag cr-20260925-r2`：指定标签，默认 `cr-YYYYMMDD`。
- `--message "修正规则译文"`：指定 Git 提交说明。
