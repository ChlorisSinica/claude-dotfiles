# Statusline

2 行構成の Claude Code 用カスタムステータスラインです。

```text
Opus 4.6 (1M context)
ctx ⣄        5% (50k/1.0M) │ 5h ⣤        6% (2h55m) │ 7d ⣿⣿⣿⣤     44% (1d6h)
```

## 表示内容

- 1 行目: モデル名
- 2 行目: context 使用量 / 5 時間レート制限 / 7 日レート制限
- Braille ドットバーを緑 → 黄 → 赤で着色

## セットアップ

```bash
bash ~/claude-dotfiles/setup.sh --statusline
bash ~/claude-dotfiles/setup-statusline.sh
bash ~/claude-dotfiles/setup-statusline.sh -f
```
