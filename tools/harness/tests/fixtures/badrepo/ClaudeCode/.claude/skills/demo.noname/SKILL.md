---
description: name: 完全欠落時に warning（error ではない）となることの検出テスト用（検査B skill版）。
---

# demo.noname

検査B（skill name frontmatter 一致）の異常系フィクスチャその2。
`name:` フィールド自体が存在しない場合、`check_skill_name_frontmatter` は
`error` ではなく `warning` を出すことを確認する。
