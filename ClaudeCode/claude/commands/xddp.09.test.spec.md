---
description: XDDP フェーズ5: テストケースを生成する
---

`.claude/skills/xddp-testcase/SKILL.md` を読み込み、テストケースを生成する。

## 実行内容

1. `.claude/skills/xddp-testcase/SKILL.md` を読み込む
2. 変更設計書・スペックアウト資料・変更要求仕様書を読み込む
3. 以下の3種類のテストケースを生成する：
   - ホワイトボックステスト（変更関数の条件分岐・境界値）
   - 回帰テスト（既存機能のデグレード確認）
   - 統合テスト（関連モジュールとの連携確認）
4. `templates/テストケース-template.md` をベースに出力する

## 引数
$ARGUMENTS
