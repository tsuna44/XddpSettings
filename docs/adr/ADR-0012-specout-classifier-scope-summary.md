# ADR-0012: classifier への CRS 全文配布をやめスコープ要約をチャンク JSON に埋め込む理由

Status: Accepted
Date: 2026-08-29

## Context

ADR-0010 は、classifier のチャンク並列化後も `out-of-scope-discard` 判定に必要な変更スコープの
理解を単一コンテキスト時と同等に保つため、`CRS_FILE`（`CRS-{CR}.md` 全文）を classifier の
Inputs として都度渡す方式（判定入力の等価性の回復策）を採用した
（`docs/adr/ADR-0010-specout-parallel-classification.md`「判定入力の等価性」節）。

`docs/xddp-tool-analysis-2026-08.md` §5「トークン使用量削減施策（効果見込み順）」#1 で、この方式には
以下の残存コストが指摘された:

1. 各 classifier は独立コンテキストで動くため、プロンプトキャッシュのヒット有無に関わらず CRS 全文が
   そのコンテキストウィンドウに読み込まれる（キャッシュは入力トークンの課金を安くするだけで、
   コンテキスト占有・出力品質への希釈影響は減らない）。
2. キャッシュヒットはコールドスタート・TTL 失効・バッチタイミングのずれに依存する。
3. `Read` ツール呼び出し自体の回数（K チャンク×波数×repo）は変わらない。

なお、ADR-0010 の Consequences が指摘するとおり、プロンプトキャッシュ設計要件
（`xddp.04.specout/SKILL.md`「プロンプトキャッシュ有効化のための設計要件」）を満たす場合、
CRS 全文複製の **$ コスト** はキャッシュ共有により実質無害化されている。したがって本 ADR の主目的は
コスト削減ではなく、上記1〜3の残存コスト（コンテキスト占有・キャッシュ依存リスク・Read 回数）の
解消である。

## Decision

`known_symbols`（ADR-0010「判定入力の等価性」節で導入済みの配布パターン）と同一のパターンで
`scope_summary` を導入し、classifier の `CRS_FILE` Input を廃止する。

- discovery-setup（`xddp-specout-agent` MODE: discovery-setup, Step 1）が、Wave 0 構築時に
  既に読み込んでいる CRS 本文（追加の Read は不要）から、変更概要・対象UR一覧を3〜10行程度に
  要約し `_scope-summary.md` へ Write する。
- `specout_bfs.py cmd_init` が `--scope-summary-file` の内容を `bfs-state.json` の
  `scope_summary` に一度だけ保存する。
- `cmd_search` が `known_symbols` と同様、`hits_payload`/`chunk_payload` の双方へ
  `scope_summary` を毎波・毎チャンク複製配布する（`scope_summary` は CR 単位で不変のため、
  `known_symbols` と異なり波ごとの再計算は不要）。

要約による圧縮は、本来 in-scope の変更を classifier が誤って `out-of-scope-discard` してしまう
リスク（偽陰性）を原理的に伴う。これを吸収するため、`scope_summary` が空、または当該ヒットが
スコープ内か判断するのに情報が不足する場合は `out-of-scope-discard` を選ばず通常の伝播種別判定へ
フォールバックする保守的な判定ルールをセットで導入する（既存の `is_external_api` 判定が採用する
「誤検出より漏れを防ぐことを優先する」方針と同じ考え方）。

## Consequences

- 実測手段は `make smoke-full PHASE=04` の before/after 比較（`--metrics-out` の
  `total_tokens`/`cache_read_input_tokens`/`cache_creation_input_tokens`）に限られる。ライブ実行中
  セッションからの実トークン計測は非対応のため（`plans/PLAN-20260829-phase-telemetry-minimal.md`
  で非ゴールと明示済み）。
- `bfs-state.json` に `scope_summary` フィールドが追加される。後方互換性ポリシー上、既存の
  `bfs-state.json`（`scope_summary` を持たない）は `.get("scope_summary", "")` で空文字列として
  扱われエラーにはならないが、途中から本施策を適用した CR では、既存波までは `CRS_FILE` 無し・
  `scope_summary` 空で判定することになる。実害は上記の保守的フォールバックにより discard の
  誤判定が起きないことで吸収される。
- `cmd_import`（checkpoint.md からの手動復旧）は `scope_summary` を復元しないため、既存の
  `warnings` リストへ喪失注記を追加する。`cmd_re_discover` は既存状態をそのまま引き継ぐため対象外。
- この決定により、ADR-0010「判定入力の等価性」節の `CRS_FILE` 都度渡し方式は本 ADR に置き換えられる
  （ADR-0010 側には参照注記を追加する。§3.9 参照）。
