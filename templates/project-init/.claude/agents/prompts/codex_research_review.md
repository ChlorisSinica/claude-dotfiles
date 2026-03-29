# Codex Research Review Prompt

> 使用法: `codex exec --full-auto` でプロンプト+research.md を送信

---

`.agents` と `.context` と `.claude` 以外のこのプロジェクトのファイルを全てじっくり読み，仕組みや役割，そしてすべての特徴を深く理解してください．

それが終わったら，opus が作成した `.claude/context/research.md` をレビューし，以下の観点で不足分や差分を記述して更新してください:

1. **網羅性**: 全ファイルがカバーされているか（ファイル名からの推測ではなく実際の内容に基づく）
2. **正確性**: 事実と推測が区別されているか（不確かなものは「要確認」とマークされているか）
3. **深度**: 関数シグネチャだけでなく内部実装まで読み込んでいるか
4. **依存関係**: モジュール間の import 依存グラフが正確か
5. **データフロー**: スクリプト間の変数の行き来が網羅されているか
   - コールバックのシグネチャと実体の対応
   - 設定値の伝播経路（生成 → 加工 → 消費）
   - ファイル I/O の構造（JSON/CSV/チェックポイントのフィールド名と型）
   - ハードコードされた値 vs 設定から取得される値の区別
6. **欠落インターフェース**: 統合時に必要だが未実装のメソッド/パラメータが特定されているか
7. **リスクマップ**: 潜在的なバグや脆弱な箇所が特定されているか

Feature: $FEATURE

Rules:
- Separate facts from guesses. If unsure, mark as "要確認".
- Read actual file contents; never infer from filenames alone.
- "Deeply" means reading function internals, not just signatures.
- Do NOT fabricate bugs. If no bugs are found, say so explicitly.
- 既存の research.md を削除せず、レビュー結果と不足分で更新すること.
