---
description: XDDP フェーズ4: 変更設計書に基づいてコーディングを実施する
---

`.claude/skills/xddp-coding/SKILL.md` を読み込み、コーディングを実施する。

## 実行内容

1. `.claude/skills/xddp-coding/SKILL.md` を読み込む
2. `.claude/skills/xddp-coding/coding-rules.md` を読み込み、変更コメント規約を把握する
3. 変更設計書の対象エントリからソースファイル・変更箇所を特定する
4. 変更前コードと実ファイルの一致を確認する（不一致の場合は中断・報告）
5. 規約に従いADD/MOD/DELタグを付与してコードを変更する
6. 変更設計書にないコード変更は絶対に行わない

## 引数
$ARGUMENTS
