---
description: XDDP フェーズ5: テストNGを変更設計書にフィードバックし修正コーディングを実施する
---

`.claude/skills/xddp-test-feedback/SKILL.md` と `.claude/skills/xddp-coding/SKILL.md` を読み込み、テストNGの修正ループを回す。

## 実行内容

### Step 1: NGフィードバック
1. `.claude/skills/xddp-test-feedback/SKILL.md` を読み込む
2. テスト結果記録からNGを抽出し、原因を4種類に分類する（A:実装ミス、B:設計ミス、C:仕様ミス、D:テスト仕様ミス）
3. 変更設計書に修正エントリを追加する

### Step 2: 修正コーディング
1. `.claude/skills/xddp-coding/SKILL.md` を読み込む
2. `.claude/skills/xddp-coding/coding-rules.md` を読み込む
3. 修正エントリに基づいてソースコードを修正する

### Step 3: 修正ループ管理
- `templates/修正ループ管理-template.md` をベースに修正ループ履歴を記録する
- 3回を超えるループはCR全体の見直しを推奨する

## 引数
$ARGUMENTS
