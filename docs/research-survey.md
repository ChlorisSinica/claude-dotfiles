# Research Survey

研究サーベイ用テンプレートの概要です．

## 初期化

```text
python ~/.claude/scripts/init-project.py survey-cv  # Computer Vision 分野
python ~/.claude/scripts/init-project.py survey-ms  # 材料科学分野
```

Claude Code からは `/init-project survey-cv` / `/init-project survey-ms` でも同じ template を生成できます．

## ワークフロー

```text
python ~/.claude/scripts/init-project.py survey-cv
→ /scope <topic> → /search → /read → /outline
→ /draft → /review → survey-convert.py
```

## 前提

- `survey-convert.py` には Pandoc が必要
- 研究テンプレートでは `.claude/settings.local.json.bak` が生成される

Pandoc 導入例:

```bash
winget install --id JohnMacFarlane.Pandoc
```

## 承認が増えやすい箇所

- `/search` — `WebSearch`
- `/read` — `WebFetch`, `Bash(pqa/paper/marker_single)`
- `/review` — `Bash(python -c ... semanticscholar)`, `WebSearch`
- `survey-convert.py`（`/convert` から呼び出し）— `Bash(pandoc/bibcure)`

## 関連ページ

- [Claude Workflow](./claude-workflow.md)
