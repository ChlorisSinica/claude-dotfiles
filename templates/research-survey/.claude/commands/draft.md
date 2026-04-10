---
description: "Phase 5: サーベイ執筆（Paper Card を参照しセクションごとに記述）"
---

# サーベイ執筆

## 入力

- `$ARGUMENTS`: セクション番号（省略可）
  - 空の場合: outline.md の次の未執筆セクションを自動選択
  - 例: `/draft 3` — セクション3を執筆
  - 例: `/draft all` — 全セクションを順に執筆

## 前提

- `.claude/context/outline.md` が存在すること
- `.claude/context/notes.md` が存在すること（Paper Card 形式）
- `.claude/context/scope.md` が存在すること
- `.claude/context/available_tools.md` を参照し利用可能なツールを確認

## 研究分野情報

- **ドメイン**: {{DOMAIN}}

## プロンプト

outline.md の構成に従い、notes.md の Paper Card を参照してサーベイのセクションを執筆してください。

## 全体フロー

**全セクションが完了するまで自律的にループする。セクションごとにユーザーに確認を取らない。**

```
LOOP（未執筆セクションがなくなるまで）:
  1) outline.md から次の未執筆セクションを選択
  2) notes.md から該当論文の Paper Card を参照
  3) セクションを執筆
  4) draft.md に追記
  5) outline.md の該当セクションを [x] に更新
  6) 次の未執筆セクションへ
END LOOP
```

## 執筆ルール

### 引用形式

- **本文中**: `\cite{bibtex_key}` 形式（例: `\cite{he2016deep}`）
- **BibTeX Key**: notes.md の Paper Card で割り当て済みのキーを使用
- **References セクション**: draft.md 末尾に BibTeX エントリを集約

```bibtex
@inproceedings{he2016deep,
  title={Deep Residual Learning for Image Recognition},
  author={He, Kaiming and Zhang, Xiangyu and Ren, Shaoqing and Sun, Jian},
  booktitle={CVPR},
  year={2016}
}
```

### 事実確認（PaperQA2 利用可能な場合）

数値や比較結果を記述する際、確信が持てない場合:
```bash
pqa ask "What is the top-5 error rate of ResNet-152 on ImageNet?"
```

### その他

- **論理構成**: 各セクションは「概要 → 詳細 → まとめ」の流れ
- **比較表**: 手法の比較が有用な場合は表形式で整理
- **図表の指示**: 図が必要な箇所には `[Figure: 説明]` プレースホルダを挿入
- **RQ への言及**: 各セクションの冒頭で対応する RQ を明示
- **セクション間の接続**: 前セクションとの関連、次セクションへの導入を含める
- **Paper Card 参照**: 全文ではなく Paper Card の蒸留情報を参照して執筆（必要な場合のみ原文に戻る）

### ドメイン固有ルール

{{SURVEY_RULES}}

## ルール

- notes.md の Paper Card 情報を正確に引用する — 数値の改変禁止
- 存在しない論文や結果を捏造しない
- 引用のない主張は避ける（一般的な事実を除く）
- BibTeX Key は notes.md で定義済みのものを使用する

## 出力

`.claude/context/draft.md` — 以下の構成:

```markdown
# [サーベイタイトル]

## 1. Introduction
...

## 2. Background
...

（本論セクション）

## N. Discussion
...

## N+1. Conclusion
...

## References

@inproceedings{he2016deep,
  ...
}
...
```

## 次のステップ

> draft.md を確認してください。
> 修正はインラインコメント（`[CHANGE: 説明]`, `[ADD: 説明]` 等）で指示してください。
> 問題なければ `/review` で品質レビューに進んでください。
