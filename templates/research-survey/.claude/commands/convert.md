---
description: "Markdown → LaTeX 変換（Pandoc + bibcure）"
---

# Markdown → LaTeX 変換

## 入力

- `$ARGUMENTS`: 変換オプション（省略可）

## 前提

- `.claude/context/draft.md` が存在すること
- `.claude/context/available_tools.md` を参照し利用可能なツールを確認

## プロンプト

以下の手順で draft.md を LaTeX に変換してください。

## 手順

### 1. BibTeX ファイルの生成

draft.md 末尾の References セクション（BibTeX エントリ）を抽出し `output/references.bib` に保存。

### 2. BibTeX 正規化（bibcure 利用可能な場合）

```bash
bibcure -i output/references.bib -o output/references.bib
```

bibcure が利用不可の場合はスキップ。

### 3. 本文の前処理

- References セクション（BibTeX エントリ）を draft.md から除去した一時ファイルを作成
- `\cite{key}` が正しく残っていることを確認

### 4. Pandoc 変換

```text
<python-launcher> ~/.claude/scripts/survey-convert.py .claude/context/draft.md output/survey.tex
```

`<python-launcher>` には `python`, `python3`, `py -3` など，環境で使える Python 3.11+ launcher を入れる．

Pandoc が利用不可の場合はインストール手順を案内:
- Windows: `winget install --id JohnMacFarlane.Pandoc`
- macOS: `brew install pandoc`

### 5. 変換結果の確認

- `output/survey.tex` が生成されたか
- `\cite{}` が正しく挿入されているか
- 表が `\begin{table}` に変換されているか
- Figure プレースホルダ `[Figure: 説明]` → `% TODO: Figure - 説明` に変換

### 6. 変換できなかった箇所の報告

変換エラーや手動対応が必要な箇所をリストアップ。

## 出力

- `output/survey.tex` — LaTeX ファイル
- `output/references.bib` — BibTeX ファイル

## 次のステップ

> output/survey.tex と output/references.bib を確認してください。
> LaTeX のコンパイル:
> ```
> cd output && pdflatex survey && bibtex survey && pdflatex survey && pdflatex survey
> ```
