---
description: "セッション引き継ぎ文書 .claude/context/HANDOVER.md の生成・更新"
---

# Handover — セッション引き継ぎ

`.claude/context/HANDOVER.md` を生成または更新してください。次のセッションがすばやくコンテキストを復元できるようにします。

## 記載項目

以下のセクションを必ず含めてください:

### 1. Work Completed（完了した作業）
- 今セッションで完了したタスクとファイルパスを列挙
- 各タスクの DoD 達成状況

### 2. Failed Attempts / Bugfix History（失敗・修正履歴）
- 試みたが失敗したアプローチ（理由付き）
- デバッグ中に発見した知見

### 3. Decisions（設計判断）
- 重要な設計判断とその根拠
- 却下した代替案

### 4. Unresolved Issues（未解決の問題）
- P0（ブロッカー）/ P1（重要）/ P2（低優先度）で分類
- 各課題の再現手順と仮説

### 5. Next Actions（次のアクション）
- 優先度順に次セッションでやるべきことを列挙
- 最初に実行すべきコマンドがあれば記載

### 6. Verification Status（検証状況）
- 実行済み / 未実行の検証コマンド
- テスト結果のサマリー

### 7. Current Plan/Tasks Status（計画・タスク状況）
- `.claude/context/plan.md` / `.claude/context/tasks.md` の進捗サマリー
- 残りタスク数と見通し

## 出力先

`.claude/context/HANDOVER.md` に書き出してください。既存の内容がある場合は最新セッション分で上書きしてください。

## 追加コンテキスト

$ARGUMENTS
