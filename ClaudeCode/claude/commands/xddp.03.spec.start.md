---
description: XDDP フェーズ2: スペックアウト（母体調査）を開始する
---

`.claude/skills/xddp-specout/SKILL.md` を読み込み、スペックアウト調査を実施する。

## 実行内容

1. `.claude/skills/xddp-specout/SKILL.md` を読み込む
2. 変更要求仕様書を読み込み、変更対象の識別子（定数・関数・構造体）を特定する
3. ソースコードを起点に波紋検索で影響範囲を調査する
4. `templates/スペックアウト-template.md` をベースにスペックアウト資料を作成する

## 引数
$ARGUMENTS
