# scratch-workspace-min（トークン最小・無害確認用フィクスチャペア）

任意のXDDPスキル・エージェント修正を、素早く・低コストで・無害に確認するための最小構成フィクスチャ。
`multi/`（マルチリポジトリ・`IS_MULTI=true`）と `single/`（シングルリポジトリ・`IS_MULTI=false`）の
2つの独立したワークスペースルート（`xddp.config.md` を持つディレクトリ）で構成される。

## なぜ2つ必要か（重要な設計上の制約）

`IS_MULTI` は `xddp.config.md` の `REPOS:` エントリ数（≥2 で true）によって**ワークスペース単位に
固定**される値であり（[xddp.common/SKILL.md:35](../../ClaudeCode/.claude/skills/xddp.common/SKILL.md#L35)）、
1つのワークスペース内で `repo` 引数を絞り込んでも `IS_MULTI` は変わらない。したがって
`IS_MULTI=false` 時の挙動（`HAS_CROSS` が常にfalse・cross処理を一切試みない等）を確認するには、
`REPOS:` エントリが1件だけの**別のワークスペースルート**が必須である。

一方で、リポジトリのソースコード自体は使い回せる。`single/xddp.config.md` は
`REPOS: svc-a: ../multi/svc-a` と相対パスで `multi/` 側の `svc-a/` を直接参照しており、
ソースコードの二重管理を避けている。ただし対象ファイルは `single/` 用に専用の `src/mod_a2.py`
（`multi/` 側は `src/mod_a.py`）を使い分けており、`code` DOC_TYPE のような git diff ベースの
検証を multi/single で同時に行っても互いのファイルが競合しないようにしている。

## 構成

```
scratch-workspace-min/
├── multi/                          # IS_MULTI=true（HAS_CROSS 検証を含む）
│   ├── xddp.config.md              # REPOS: svc-a, svc-b（2件）
│   ├── svc-a/src/mod_a.py          # multi用の対象ファイル
│   ├── svc-a/src/mod_a2.py         # single用（multiからは未参照）
│   ├── svc-b/src/mod_b.py
│   └── xddp/CR-2026-960/           # CRS+DSN(+cross)+CHD(+cross)+TSP(+cross) 一式（フィードバック前）
└── single/                         # IS_MULTI=false
    ├── xddp.config.md              # REPOS: svc-a: ../multi/svc-a（1件、相対パスで共有）
    └── xddp/CR-2026-961/           # CRS+DSN+CHD+TSP 一式（フィードバック前、cross一切なし）
```

各CRは UR-001 / SR-001-001 / SP-001-001.001 の1本のみで構成し、DSN・CHD・TSPそれぞれに
「CRS未反映の項目」を1件ずつ意図的に埋め込んである（`検証用に意図的に追加した未反映項目` という
文言で検索可能）。`multi/CR-2026-960` はさらに cross/ 版の DSN・CHD・TSP を持ち、`HAS_CROSS=true`
時の挙動（cross由来の抽出・`[cross]`タグ付与等）も確認できる。

## 使い方の例（`/xddp.feedback` の場合）

```
cd test-fixtures/scratch-workspace-min/multi
# /xddp.feedback CR-2026-960 arch svc-a    → DSNの性能制約(NFR)を抽出できるか
# /xddp.feedback CR-2026-960 design svc-a  → CHDのエラーログ仕様を抽出できるか
# /xddp.feedback CR-2026-960 test svc-a    → TSPのTC-102（通常のTCとの判別）を抽出できるか
# /xddp.feedback CR-2026-960 arch          → repo省略時、cross/DSNの契約も一括抽出できるか（HAS_CROSS=true）

cd ../single
# /xddp.feedback CR-2026-961 arch          → single-repoでcross処理を一切試みないことを確認
```

他のスキル（`xddp.05.arch`／`xddp.06.design`／`xddp.09.test` 等）の修正確認にも同様に使える
（`xddp.config.md` の `REVIEW_MAX_ROUNDS` は全種別1round・`FIX_STRATEGY` は全種別 `ideal` に
設定してあり、確認セッションが無駄に長引かないようにしてある）。

## リセット手順

このフィクスチャは初回コミット時点の内容を「フィードバック前」の基準状態とする。検証セッションで
CRS/CHD/TM等を書き換えた後、基準状態に戻す場合：

```
git checkout -- test-fixtures/scratch-workspace-min/
```

**注意:** 上記はコミット済みの内容に戻すコマンドである。このフィクスチャに手を加えた後、
基準状態として確定する場合は必ずコミットしておくこと（コミットしていない状態で
`git checkout --` を実行すると変更前の状態＝直近のコミットに戻る点に注意）。

## 確認済み・未確認の項目

- [PLAN-20260711-feedback-to-crs-skill](../../plans/PLAN-20260711-feedback-to-crs-skill.md) の
  実装確認は、専用の一時フィクスチャ（`scratch-workspace` 内に作成。CR-2026-900 が現行CHDスキーマ
  未対応だったため新設したが、確認後は使い捨てとして削除済み）で先に実施済み。本フィクスチャ自体は
  まだ `/xddp.feedback` を実行して確認していない（作成のみ）
- `code` DOC_TYPE（git diffベースのCHD同期）はソースファイル（`mod_a.py`/`mod_a2.py`）が
  `pass` スタブのままなので、実際に検証する際は先にコードを実装してから diff を発生させること
