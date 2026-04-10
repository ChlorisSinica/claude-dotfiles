# 研究サーベイ ツール設定ガイド

このプロジェクトでは、以下のツールを組み合わせて論文サーベイを効率化します。
**全てオプション** — ツールがなくても WebSearch/WebFetch で動作しますが、あると精度・速度が向上します。

---

## ツール優先度

1. **WebSearch / WebFetch**（組み込み）— 常に利用可能
2. **CLI ツール** — pip でインストール、Bash から呼び出し
3. **MCP サーバー** — CLI 代替がない場合のみ

---

## 推奨 CLI ツール

### 論文検索・ダウンロード

| ツール | 用途 | インストール | 利用フェーズ |
|--------|------|-------------|-------------|
| **PaperQA2** | 学術RAG、論文QA、検索 | `pip install paper-qa>=5` | /search, /draft |
| **arxiv-dl** | arXiv/CVPR/ICCV/ECCV DL + BibTeX取得 | `pip install arxiv-dl` | /read |

### PDF 解析

| ツール | 用途 | インストール | 利用フェーズ |
|--------|------|-------------|-------------|
| **marker-pdf** | PDF→Markdown 高精度変換 | `pip install marker-pdf` | /read |

### 引用管理・検証

| ツール | 用途 | インストール | 利用フェーズ |
|--------|------|-------------|-------------|
| **semanticscholar** | Semantic Scholar API（引用検証） | `pip install semanticscholar` | /read, /review |
| **bibcure** | BibTeX 正規化・DOI補完 | `pip install bibcure` | /convert |

### 変換

| ツール | 用途 | インストール | 利用フェーズ |
|--------|------|-------------|-------------|
| **Pandoc** | Markdown→LaTeX 変換 | `winget install --id JohnMacFarlane.Pandoc` | /convert |

---

## MCP サーバー（CLI 代替がない場合のみ）

| MCP サーバー | 用途 | 導入方法 | 利用条件 |
|---|---|---|---|
| **paper-search-mcp** | 24ソース横断検索 | `claude mcp add paper-search -- uvx paper-search-mcp` | PaperQA2 未インストール時 |
| **arxiv-mcp-server** | arXiv 検索+全文読解 | `claude mcp add arxiv -- uvx arxiv-mcp-server` | arxiv-dl + marker-pdf 未インストール時 |

---

## 一括インストール

```bash
# 推奨 CLI ツール（全部入り）
pip install paper-qa>=5 arxiv-dl marker-pdf semanticscholar bibcure

# Pandoc（Windows）
winget install --id JohnMacFarlane.Pandoc

# Pandoc（macOS）
brew install pandoc
```

---

## ツール検出

`/check-tools` コマンドで利用可能なツールを確認できます。
結果は `.claude/context/available_tools.md` に保存され、各コマンドが参照します。
