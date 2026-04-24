# Research Survey

研究サーベイ用テンプレートの概要です．

## 呼び出し方

```text
/init-project survey-cv  # Computer Vision 分野
/init-project survey-ms  # 材料科学分野
```

## ワークフロー

```text
/init-project survey-cv → /scope <topic>
                        → /search → /read → /outline
                        → /draft → /review → /convert
```

## 前提

- `/convert` には Pandoc が必要
- 研究テンプレートでは `.claude/settings.local.json.bak` が生成される

Pandoc 導入例:

```bash
winget install --id JohnMacFarlane.Pandoc
```

## 承認が増えやすい箇所

- `/search` — `WebSearch`
- `/read` — `WebFetch`, `Bash(pqa/paper/marker_single)`
- `/review` — `Bash(python -c ... semanticscholar)`, `WebSearch`
- `/convert` — `Bash(pandoc/bibcure)`

## 関連ページ

- [Claude Workflow](./claude-workflow.md)
