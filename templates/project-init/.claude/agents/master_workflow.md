# プロジェクト マスター手順書

**使用モデル**: Opus 4.6 + Codex
**言語/フレームワーク**: {{LANG}}

---

## 全体フロー

```
Phase 1:   /research                    ← research.md 作成（Claude が全ファイル分析）
Phase 2a:  /plan <機能の説明>            ← plan.md + tasks.md + snippets.md 作成（Claude が設計）
Phase 2b:  /sonnet-dp-research          ← Sonnet subagent が Discussion Points を外部調査
Phase 2c:  Claude が plan を更新         ← 調査結果で Discussion Points を解決
Phase 3:   Annotation cycle             ← 人間がインラインコメントで修正指示
Phase 4a:  /codex-plan-review (Phase A)  ← アーキテクチャレビュー（max 2 cycles）
           ↳ DISCUSS + 新技術論点発生時 → /sonnet-dp-research 再実行（手動トリガー）
Phase 4b:  /codex-plan-review (Phase B)  ← 詳細レビュー（max 3 cycles、Phase A APPROVED 後に自動遷移）
Phase 5:   /implement                   ← 実装（全タスク自律ループ → Codex レビュー → コミット）
Phase 6:   /codex:review               ← 汎用レビュー（codex-plugin-cc 直接使用、任意）
Phase 7:   /handover                    ← セッション終了前
Phase 8:   /retro                       ← 振り返り
```

---

## 1) research.md の作成

### プロンプト

**（開発）**
`.agents` と `.context` と `.claude` 以外のこのプロジェクトのファイルを全てじっくり読み，仕組みや役割，そしてすべての特徴を深く理解してください．それが終わったら，学んだことや発見や知っていることを全て詳細にまとめ，`.claude/context/research.md` を日本語で作成してください．

**（不具合）**
タスクのスケジューリングフローをよく理解し，潜在的なバグを探してください．すべてのバグを見つけるまでフローの調査を続けてください。終わったら，調査結果の詳細な報告書を `research.md` に専用のセクションとして追加してください．

**（更新）**
既に opus 4.6 が作成した `.claude/context/research.md` が存在する場合は削除せず，レビューも行い，不足分や差分を記述して更新してください．

### 必須分析項目

research.md には以下を必ず含めること:

1. **各ファイルの役割と内部実装** — 関数シグネチャだけでなく内部ロジックまで
2. **モジュール間依存グラフ** — import 関係、相互参照
3. **スクリプト間データフロー** — どの関数が何を引数として受け取り、何を返すか
   - コールバックのシグネチャと呼び出し側の実体
   - 設定値（dict/config）の伝播経路（生成 → 加工 → 消費）
   - ファイル I/O の構造（JSON/CSV のフィールド名と型）
4. **重要な変数の行き来** — 各スクリプト間で受け渡される変数名、型、デフォルト値
5. **存在しないが必要なもの** — 呼び出されていないが統合時に必要になるメソッド/パラメータ
6. **潜在的なバグ・リスク** — 事実と推測を区別

### ルール

- Separate facts from guesses. If unsure, mark as "要確認".
- Read actual file contents; never infer from filenames alone.
- "Deeply" means reading function internals, not just signatures.
- Do NOT fabricate bugs. If no bugs are found, say so explicitly.
- **言語制約**: このプロジェクトは {{LANG}} です。他の言語のツールやコマンドを実行しないこと。検証が必要な場合は `{{VERIFY_CMD}}` を使用すること。

---

## 1b) sonnet-dp-research — Discussion Points の外部技術調査

plan.md 作成後、Discussion Points が存在する場合に `/sonnet-dp-research` を実行する。

### 目的
- plan の技術的不確実性を外部知識で補強する
- codex-plan-review に入る前に、根拠の薄い判断を減らす

### タイミング
- /plan 完了後、Annotation cycle の**前に**実行（直列。並行不可）
- Discussion Points が存在しない場合はスキップ可

### 出力
- `.claude/context/sonnet-dp-research.md` — 各論点の調査結果
- plan.md の更新 — 解決した論点は Resolved セクションへ移動

---

## 2) plan.md, tasks.md, snippets.md の作成

**Feature**: [機能の説明]

plan.md, tasks.md must include:

1. Objective (with verifiable success criteria / Definition of Done)
2. Non-objectives (what is explicitly NOT in scope)
3. Approach (technical strategy, alternatives with trade-offs)
4. File-level change list (full paths, what changes in each)
5. Implementation details (code snippets based on actual codebase)
6. **Data flow impact analysis** — 変更によって影響を受けるデータフロー（コールバック、設定値、ファイル I/O）の全経路を明示
7. **Script dependency changes** — 追加/削除/変更される import や関数呼び出しの一覧
8. Risk + rollback plan
9. Verification commands per task
10. TODO list (phased, checkbox format, each task has its own DoD)

### ファイル分離ルール
- plan.md: 設計判断 + アーキテクチャ + テーブル定義
- tasks.md: タスク分解 + DoD（plan.md を参照、コピーしない）
- snippets.md: コードスニペット集（擬似コードとして明記）

Rules:
- Code snippets must be based on actual codebase (don't guess).
- research.md のデータフローセクションを必ず参照し、既存の変数/コールバック/ファイル形式との整合性を確認すること.
- List every affected file with its full path.
- Don't implement yet.
- TODO items must be verifiable granularity.
- **言語制約**: 検証コマンドは `{{VERIFY_CMD}}` を基準に設計すること。他の言語のツールを検証コマンドに含めないこと。

---

## 3) Annotation Cycle

`plan.md` に以下の書式でインラインコメントを追加→修正を繰り返してください。

- `[DELETE]` — このセクションを完全に削除
- `[CHANGE: 説明]` — 記述通りに修正
- `[ADD: 説明]` — 新規コンテンツを追加
- `[QUESTION: 質問]` — この質問に答えてから更新

---

## 4) Opus ↔ Codex の2段階レビューサイクル

`/codex-plan-review` を使用。2段階でクロスレビューを実施する。
snippets.md のコードは擬似コードとして扱い、構文の厳密性は検証しない。

### Phase A: アーキテクチャレビュー（max 2 cycles）

- 設計前提・API実在性・代替案の検証に集中
- 命名・表記・DoD などの詳細は一切扱わない
- 出力: `.claude/context/codex_plan_arch_review.md`
- APPROVED → Phase B に自動遷移
- DISCUSS/REVISE → ユーザー判断

### Phase B: 詳細レビュー（max 3 cycles）

- 記述品質・整合性・DoD の検証に集中
- 設計方針への異議は対象外（Phase A で検証済み）
- 出力: `.claude/context/codex_plan_tasks_review.md`
- APPROVED → sessions.json 記録して終了

### DISCUSS 時の re-research

Phase A で DISCUSS が返り、新しい技術的論点が含まれる場合:
1. Claude が Codex の新論点を plan.md の Discussion Points（未解決）に追記
2. ユーザーにサマリーと共に「/sonnet-dp-research で追加調査しますか？」を提案
3. ユーザー判断で /sonnet-dp-research 実行 → plan 更新 → review 再送信
   または直接修正 → review 再送信
※ 自動ループにはしない（トークン膨張防止）

---

## 5) Implementation

`/implement` を使用。全タスクを自律ループで実装。

```
LOOP（未完了タスクがなくなるまで）:
  0) .claude/context/tasks.md を順番に follow する
  1) 1タスクのみ最小変更で実装
     - import エラー → 依存先タスクを先に実行
  2) 毎回必ず検証コマンドを実行:
     - まず tasks.md の該当タスクの DoD コマンド
     - 次に全体検証: {{VERIFY_CMD}}
  3) エラーが出たら修正して再実行（エラーが消えるまで次へ進まない）
  4) PASS したら [x] 更新
  5) 同種失敗が3回続いたら停止して .claude/context/failure_report.md に報告
END LOOP

全タスク完了後:
  1) tasks.md 全 [ ] スキャン（サブ項目含む）→ 残りがあれば LOOP に戻る
  2) /codex-impl-review → APPROVED まで繰り返し
  3) APPROVED 取得後、自動でコミット & プッシュ
```

### ルール

- 変更は surgical に（必要最小限）
- hidden fallback / silent degrade 禁止
- データフローの変更時は、上流/下流への影響を必ず確認すること
