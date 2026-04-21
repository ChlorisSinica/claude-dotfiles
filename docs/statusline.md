# Statusline

3 行構成の Claude Code 用カスタムステータスラインです．

```text
Opus 4.6 (1M context)
~/claude-dotfiles (master)
ctx ⣄        5% (50k/1.0M) │ 5h ⣤        6% (2h55m) │ 7d ⣿⣿⣿⣤     44% (1d6h)
```

## 表示内容

- 1 行目: モデル名
- 2 行目: プロジェクトパス（`~` 相対）+ Git ブランチ
- 3 行目: context 使用量 / 5 時間レート制限 / 7 日レート制限
- Braille ドットバーを緑 → 黄 → 赤で着色
- ホーム外のパス（例: `C:/myapp`）はフルパス表示

## セットアップ

```bash
python ~/claude-dotfiles/scripts/setup.py --statusline
python ~/claude-dotfiles/scripts/setup.py --statusline -f
```

`python` は例です．環境に応じて `python3` や `py -3` など，Python 3.11+ の launcher に置き換えてください．正規入口は `scripts/setup.py --statusline` です．
