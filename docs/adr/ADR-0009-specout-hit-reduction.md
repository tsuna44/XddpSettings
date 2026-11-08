# ADR-0009: Discovery BFS のヒット削減（前倒し縮退・簡易 module-priority）

Status: Accepted
Date: 2026-08-07

## Context

Discovery BFS（`xddp.04.specout/scripts/specout_bfs.py`）は、リポジトリが大規模／1波のヒット数が
多い場合、LLM の classification（各波・全ヒット行の意味判定）がトークン・時間コストの支配要因になる
（`PLAN-20260804-specout-performance.md` で確認済みの痛点。Phase 0/1 実装完了）。

既存の高ノイズ機構（`cmd_commit_wave` の `noisy_keys` 判定）は「1エントリ（symbol+scope）の異なる
ファイル数 > `SPECOUT_MAX_FILES_PER_MODULE`」を条件に **next_frontier への伝播だけ**を抑止するが、
**分類自体は全ヒットに対して実施**するため、多数ヒットするホットシンボルの LLM トークン消費を削減
できない。

`PLAN-20260806-specout-phase2-noise-priority.md` で行った等価性分析により、以下が実コードから確認された。

- **confirmed_files（確定影響ファイル台帳）は `hits` を走査して構築される**ため、hits に現れない
  ファイルは確定台帳に載らない（＝漏れ）。ここが前倒し縮退を導入する上で最重要の不変条件になる。
- **`SPECOUT_MAX_FILES_PER_MODULE ≥ 1` の実運用下では、MEDIUM エントリ（scope=単一ファイル）は
  決してノイズにならない**。ノイズシンボルは常に HIGH（scope=None）であり、同名 MEDIUM 多スコープの
  ケースA/B/C分岐（`case_a_symbols`）とは集合として排他である。
  → ノイズシンボルの分類結果は「抑止済みの伝播」「discovery-log 行表示」「classified_locations
  （dedup 用）」にしか影響しないため、**confirmed_files のファイル網羅さえ守れば**、分類対象を
  代表サブセットへ絞ってもフロンティア・ケースA分岐の等価性は保たれる見込みが立つ。

## Decision

### 2A: 前倒し縮退（等価性保持）

`cmd_search` の HIGH 処理を、dedup/フィルタ適用後の **emitted 候補**を symbol 単位でグルーピングし
直すよう変更した。

- **トリガ指標:** `_process_command`（dedup/フィルタ）適用後の emitted hits における「1 HIGH シンボル
  の異なるファイル数 > `max_files_per_module`」。**commit-wave の `noisy_keys` と同一入力・同一指標**
  であり、生ヒット数（dedup/フィルタ前）は使わない。生ヒット数を使うと、生では閾値超だが post-filter
  では閾値以下になる境界シンボルを誤って抑止し、現行が探索する派生シンボルを取りこぼす。
- **代表抽出:** pre-noisy と判定されたシンボルは、emitted ヒットファイル集合を**ファイルパス昇順で
  先頭 `max_files_per_module` 件・各ファイル最大1行**の代表サブセットのみを LLM 分類対象（hits）へ
  積む。残りは `filtered_out`（reason=`noise-collapse`）として `command_id` 単位で監査記録する。
- **confirmed_files 網羅の維持:** pre-noisy シンボルの emitted 全ファイル集合を `module_files`
  （`{symbol: [file,...]}`）として `commit-wave` へ渡し、代表サブセットに現れないファイルも
  confirmed_files へ登録する（confidence は HIGH。全 pre-noisy シンボルは HIGH のため）。
- **伝播抑止の等価性維持:** 代表サブセット化により hits のファイル数が過小計上され、commit-wave が
  再計算する `noisy_keys` から漏れて伝播が復活するのを防ぐため、`pre_noisy` 集合を `hits_payload`
  経由で commit-wave へ渡し、`noisy_keys ← noisy_keys ∪ pre_noisy` として伝播抑止条件を評価する。
- **件数一致検証の拡張:** 「生 = 記録 + dedup除外 + フィルタ除外 + noise-collapse除外」
  （`command_id` 単位）へ拡張し、`specout_verify_counts.py` の独立回帰チェックも追従させた。

**不変条件（equivalence fixture で保証）:** 縮退前後で `confirmed_files`・`next_frontier`・
ケースA分岐が完全一致する（`test_specout_bfs.py`
`test_2a_confirmed_files_and_frontier_equivalent_to_pre_collapse`）。

（2026-11-07 追記: `confirmed_files` の完全一致は、縮退なしで判定するとヒットがすべて `false-positive` になるファイルが、
pre-noisy シンボルの全ファイル（`module_files`）に無い場合に限る。`commit-wave` は `false-positive` のヒットだけの
ファイルを確定させないが、`module_files` は代表行が `false-positive` でも確定させる（代表行以外は判定しないため
保守的に確定させる）。そのため、そのようなファイルがあると、縮退ありの `confirmed_files` は縮退なしの上位集合になる。
同じ理由で、縮退ありの `false_positive_files` は縮退なしより少なくなる。この2つの挙動と、縮退した波の `commit-wave`
直後の `frontier` が等しいことは、`test_specout_bfs.py`
`test_pre_collapse_confirmed_files_are_superset_and_frontier_equal` が固定している。
その後の探索は縮退なしと変わりうる（コードを読んだ推論で、テストでは確かめていない）。Wave 0 の後に作る
`module_priority_map`（catalog 経路・2B の simple 経路とも）は確定ファイルから作るため、縮退なしより HIGH が増える
ことがある。次の波のシンボルのモジュール（`symbol_module`）は、そのシンボルを挙げたヒットのファイルから決めるため、
非代表行のヒットが無い縮退ありでは割り当てが変わることがある。探すシンボルの並びが変わると、1波の予算
（`wave_hit_budget`・`llm_hit_budget`）や波数上限で打ち切るシンボルも変わりうる。そのため、縮退した波の直後に
上位集合であっても、探索の最後まで縮退なしの確定ファイルを含むとは言えない。打ち切ったシンボルは `truncated` と
discovery-log に記録される。）

### 2B: catalog 不在時の簡易 module-priority

`module_catalog_file` が空のとき、Wave 0 完了時点の `confirmed_files` から求めたディレクトリ集合の
近傍（同一・親・子ディレクトリ、深度1固定）を HIGH とする簡易 `module_priority_map` を構築する
（`_simple_neighbor_priority`）。module granularity は catalog 経路（`_module_dir_for_file`＝トップ
階層ディレクトリのみ）とは異なり、ファイルの直接の親ディレクトリ（`_dir_for_file`）を単位とする。

マップに無いディレクトリ（近傍外）は、simple モードでは既定 LOW として扱い（catalog モードの既定
HIGH とは異なる。既存 catalog 経路は不変）、`low_priority_frontier` へ退避する。退避は既存の
LOW 退避・後続波での処理ロジックをそのまま再利用するため、**取りこぼしにはならない**（探索順が
非効率化しうるだけ）。新規 config キーは設けない（深度1固定。チューニング需要が不明確なため、
後方互換不要ポリシーの下で必要時に後続プランで追加する）。

（2026-11-07 追記: 「取りこぼしにはならない」は、低優先のシンボルが1波の予算と波数上限で打ち切られない場合に限る。
`search` は今の波に探すシンボルが無いときだけ `low_priority_frontier` をまとめて1つの波で探す。その波の候補全体に
1波の予算（`wave_hit_budget`・`llm_hit_budget`）がかかり、予算を超えたシンボルは打ち切りとして記録されるだけで
frontier に戻らない（`_apply_budget`）。別々の波で退避したシンボルが1つの波の予算を取り合うので、退避しなければ
探されたシンボルが打ち切られることがある（コードを読んだ推論で、テストでは確かめていない）。また、波数上限に達すると
残りのシンボルを打ち切りとして記録して探索を終える（`_complete_at_wave_limit`）。打ち切ったシンボルは `truncated` と
discovery-log に記録される。）

## Consequences

- 大規模リポジトリ・多ヒット波での LLM classification トークンを、ノイズ HIGH シンボルについて
  「代表 N 行」まで削減できる。削減量は metrics.jsonl の `noise_collapse_removed` で計測できる。
  探索網羅（confirmed_files・波及ファイル一覧）は不変のため、correctness を犠牲にしない。
  （2026-11-07 追記: 確定ファイルは不変ではない。縮退した波の直後は縮退なしの上位集合になることがあり、その後の
  探索（優先度・1波の予算・波数上限による打ち切り）は縮退なしと変わりうる。そのため「correctness を犠牲にしない」は、
  縮退した波の直後の確定ファイルについてだけ言える。探索の最後の確定ファイルが縮退なしを含むかは、確かめていない。
  「### 2A」の不変条件の段落の後の追記を参照。）
- 2A は `cmd_search`/`cmd_commit_wave` の内部実装変更のみであり、LLM の classification 契約
  （`wave-{N}-class.json` スキーマ）・discovery-log の主要見出し体系は変更しない。件数一致検証テーブル
  にのみ列が追加される（`specout_verify_counts.py` は列が無い旧ログを 0 とみなし後方互換で照合）。
- 2B は module-catalog 未整備のリポジトリでも frontier の段階処理（近傍優先探索）を可能にするが、
  catalog 経路の挙動には一切影響しない（`module_priority_mode` フィールドで経路を分岐）。
- **再検討条件:** 深度1固定のヒューリスティックが実運用で不十分と判明した場合、
  `SPECOUT_NEIGHBOR_DEPTH` 等の設定キー追加を後続プランで検討する（本 ADR の時点では見送り）。
  参照解決バックエンドの偽陽性削減は別軸（ADR-0008・`PLAN-20260801-p5s2-specout-ctags-backend.md`）
  であり、本 ADR のスコープ外。

> **2026-10-04 注記:** [ADR-0019](ADR-0019-specout-static-slicer.md) で一部を置き換えた（前倒し縮退と高ノイズによる波及停止を、LLM 分類に回るヒットだけに適用する。件数一致検証の照合式の「フィルタ除外」に、予算による除外を含める）。
