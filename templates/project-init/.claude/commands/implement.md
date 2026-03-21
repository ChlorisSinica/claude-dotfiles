---
description: "Phase 5: tasks.md に従って全タスクを順に実装"
---

# Implementation

## 入力

- `$ARGUMENTS`: タスク番号（省略可）
  - 空の場合: `.context/tasks.md` の次の未完了タスク（`[ ]`）を自動選択

## 前提

- `.context/tasks.md` が存在し、Codex レビュー済みであること
- `.context/research.md` のデータフローセクションを参照可能であること

## 全体フロー

**全タスクが完了するまで自律的にループする。タスクごとにユーザーに確認を取らない。**

```
LOOP（未完了タスクがなくなるまで）:
  0) .context/tasks.md から次の未完了タスク（[ ]）を選択
  1) 1タスクを最小変更で実装
     - import エラーが発生した場合: 依存先が別タスクで追加予定なら、そのタスクを先に実行する
  2) 毎回必ず検証コマンドを実行:
     - まず tasks.md の該当タスクの DoD コマンドを実行
     - 次に全体検証: {{VERIFY_CMD}}
  3) エラーが出たら修正して再実行（エラーが消えるまで次へ進まない）
  4) PASS したら tasks.md の該当タスクを [x] に更新
  5) 同種失敗が3回続いたら停止して .context/failure_report.md に報告 → ユーザーに通知
  6) 次の未完了タスクへ（手順0に戻る）
END LOOP

全タスク完了後:
  1) tasks.md 内の全 [ ] をスキャン — サブ項目含め残りがあれば LOOP に戻る
  2) /codex-impl-review で全変更ファイルをまとめてレビュー
  3) APPROVED 取得後、自動でコミット & プッシュ（下記参照）
```

## ルール

- 変更は surgical に（必要最小限）
- hidden fallback / silent degrade 禁止
- データフローの変更時は、上流（呼び出し元）と下流（呼び出し先）への影響を必ず確認すること
- 新規パラメータを追加した場合、その値の**生成元 → 伝播経路 → 消費先**が全て繋がっていることを確認すること
- import の追加/変更時は、依存先ファイルの存在と公開インターフェースを確認すること

## 自動コミット & プッシュ

codex-impl-review が APPROVED を返したら、ユーザー確認なしで自動実行:

1. `git diff --name-only` で変更ファイル一覧を取得
2. 変更ファイルを `git add`（`.context/` 配下も含む、ただし `data/`, `logs/` 等の生成物は除外）
3. 変更内容を分析してコミットメッセージを自動生成（`feat:` / `fix:` / `refactor:` プレフィックス）
4. `git push`
5. コミット・プッシュ完了をユーザーに報告

**Co-Authored-By**: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` をコミットメッセージ末尾に付与。

**除外ルール**: `.gitignore` に記載されたパターン、および untracked のバイナリ/データファイルは `git add` しない。

## 出力

- コード変更
- `.context/tasks.md` の全タスクを `[x]` に更新
- Codex レビュー APPROVED 後、自動コミット & プッシュ
