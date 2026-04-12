---
description: "Phase 5: tasks.md に従って全タスクを順に実装"
---

# Implementation

## 入力

- `$ARGUMENTS`: タスク番号（省略可）
  - 空の場合: `.claude/context/tasks.md` の次の未完了タスク（`[ ]`）を自動選択

## 前提

- `.claude/context/tasks.md` が存在し、Codex レビュー済みであること
- `.claude/context/research.md` のデータフローセクションを参照可能であること

## 全体フロー

**全タスクが完了するまで自律的にループする。タスクごとにユーザーに確認を取らない。**

```
LOOP（未完了タスクがなくなるまで）:
  0) .claude/context/tasks.md から次の未完了タスク（[ ]）を選択
  1) 1タスクを最小変更で実装
     - import エラーが発生した場合: 依存先が別タスクで追加予定なら、そのタスクを先に実行する
  2) 毎回必ず検証コマンドを実行:
     - まず tasks.md の該当タスクの DoD コマンドを実行
     - 次に全体検証: `{{VERIFY_CMD}}`
  3) エラーが出たら **ログ自動読み取り**（後述）を実行し、原因を特定して修正→再実行
     - エラーが消えるまで次へ進まない
  4) PASS したら tasks.md の該当タスクを [x] に更新
  5) 同種失敗が3回続いたら停止して .claude/context/failure_report.md に報告 → ユーザーに通知
  6) 次の未完了タスクへ（手順0に戻る）
END LOOP

全タスク完了後:
  1) tasks.md 内の全 [ ] をスキャン — サブ項目含め残りがあれば LOOP に戻る
  2) /codex-impl-review で全変更ファイルをまとめてレビュー
  3) APPROVED 取得後、自動でコミット & プッシュ（下記参照）
```

## 検証失敗時のログ自動読み取り

検証コマンドが非ゼロで終了した場合、以下の手順でログからエラー原因を特定する:

1. **stderr/stdout を確認**（Bash ツールが自動キャプチャ）
2. **ログファイルを検索**: 以下の各パターンを **1つずつ** Glob ツールに渡して検索する:
   {{LOG_PATTERNS}}
   （カンマ区切りの各パターンを個別に実行。例: まず `**/*.log`、次に `**/*.status`、次に `logs/**`）
3. **最新ログを読む**: 見つかったファイルのうち更新日時が最新のものを Read ツールで末尾 30 行を確認
4. **ステータスファイルを確認**: `.status` ファイルが見つかった場合は `done=`, `cancelled=`, `stage=` 行を確認
5. エラー内容に基づいて修正し、再検証

stderr だけでは原因が分からない場合（「失敗しました」のみ等）、ログファイルの確認は**必須**。

## ユーザーによる検証でエラーが発生した場合

ユーザーがスクリーンショットの代わりにログを渡せるよう、以下を案内する:

> エラーが発生した場合、以下のログファイルを貼り付けてください:
> - ログファイル: `{{LOG_PATTERNS}}` に一致するファイル（特に最新のもの）
> - ステータスファイル: `*.status`（存在する場合）
> - stderr 出力: ターミナルのエラーメッセージ
>
> 確認コマンド（最新ログの末尾を表示）:
> ```
> # Git Bash / Linux / macOS:
> find . \( -name "*.log" -o -name "*.status" \) | xargs ls -lt 2>/dev/null | head -5
> tail -30 <最新のログファイル>
>
> # PowerShell:
> Get-ChildItem -Recurse -Include {{LOG_PATTERNS}} | Sort-Object LastWriteTime -Descending | Select-Object -First 5
> Get-Content <最新のログファイル> -Tail 30
> ```

## ルール

- 変更は surgical に（必要最小限）
- hidden fallback / silent degrade 禁止
- データフローの変更時は、上流（呼び出し元）と下流（呼び出し先）への影響を必ず確認すること
- 新規パラメータを追加した場合、その値の**生成元 → 伝播経路 → 消費先**が全て繋がっていることを確認すること
- import の追加/変更時は、依存先ファイルの存在と公開インターフェースを確認すること

## コミット

codex-impl-review が APPROVED を返したら:

1. `git diff --name-only` で変更ファイル一覧を取得
2. **ソースコードの変更のみ** `git add`（`.claude/context/` 配下は Git 管理しない）
3. 変更内容を分析してコミットメッセージを自動生成（`feat:` / `fix:` / `refactor:` プレフィックス）
4. プッシュはユーザーに確認してから行う

**Co-Authored-By**: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` をコミットメッセージ末尾に付与。

## 出力

- コード変更
- `.claude/context/tasks.md` の全タスクを `[x]` に更新
- Codex レビュー APPROVED 後、ソースコードのみコミット
