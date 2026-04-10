---
description: "利用可能なツールの検出と記録"
---

# ツール検出

利用可能な CLI ツールと MCP サーバーを検出し、`.claude/context/available_tools.md` に記録してください。

## 検出手順

以下のコマンドを Bash で実行し、各ツールの利用可否を確認:

```bash
echo "=== Research Survey Tool Check ==="
echo ""

echo "[PaperQA2]"
command -v pqa && pqa --version 2>/dev/null || echo "NOT INSTALLED (pip install paper-qa>=5)"

echo ""
echo "[arxiv-dl]"
command -v paper && echo "OK" || echo "NOT INSTALLED (pip install arxiv-dl)"

echo ""
echo "[marker-pdf]"
command -v marker_single && echo "OK" || echo "NOT INSTALLED (pip install marker-pdf)"

echo ""
echo "[semanticscholar]"
python -c "import semanticscholar; print('OK')" 2>/dev/null || python3 -c "import semanticscholar; print('OK')" 2>/dev/null || echo "NOT INSTALLED (pip install semanticscholar)"

echo ""
echo "[bibcure]"
command -v bibcure && echo "OK" || echo "NOT INSTALLED (pip install bibcure)"

echo ""
echo "[Pandoc]"
command -v pandoc && pandoc --version | head -1 || echo "NOT INSTALLED (winget install --id JohnMacFarlane.Pandoc)"
```

## 出力

検出結果を `.claude/context/available_tools.md` に保存:

```markdown
# Available Tools

検出日: YYYY-MM-DD

## CLI ツール
| ツール | 状態 | バージョン |
|--------|------|-----------|
| PaperQA2 | ✓ / ✗ | ... |
| arxiv-dl | ✓ / ✗ | ... |
| marker-pdf | ✓ / ✗ | ... |
| semanticscholar | ✓ / ✗ | ... |
| bibcure | ✓ / ✗ | ... |
| Pandoc | ✓ / ✗ | ... |

## MCP サーバー
（MCP ツールが利用可能な場合は記載）

## ツール選択方針
- ✓ のツールを優先使用
- ✗ のツールは WebSearch/WebFetch でフォールバック
```

## 未インストールツールの案内

✗ のツールについて、インストールコマンドを案内する。
全ツール一括: `pip install paper-qa>=5 arxiv-dl marker-pdf semanticscholar bibcure`
