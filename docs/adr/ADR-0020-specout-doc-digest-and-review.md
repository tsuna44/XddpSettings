# ADR-0020: 工程4a の資料の確定を「スクリプトが作る材料＋モジュールごとの LLM」にし、SPO レビューの LLM のチェックを L1・L2 に絞る理由

Status: Accepted（承認済み）
Date: 2026-10-04

- プラン: [plans/PLAN-20261003-specout-doc-digest-and-review.md](../../plans/PLAN-20261003-specout-doc-digest-and-review.md)
- 前提 ADR: [ADR-0019](ADR-0019-specout-static-slicer.md)（波紋調査の判定の置き換え）、[ADR-0018](ADR-0018-specout-prelim-phase.md)（下調べ・成長型の配置）
- 調査記録: [docs/specout-static-slicing-study-2026-10.md](../specout-static-slicing-study-2026-10.md)

## Context

ADR-0019 により波紋調査は LLM をほぼ使わない決定的な処理になり、完全スライスで影響する機能が浅い波で出そろうようになった。
その後段の「資料の確定（Step A-Document）」と「SPO レビュー（Step A2）」には次の問題が残った。

- **資料の確定。** repo ごとに1つの `xddp-specout-document-agent` が、新しく確定したファイルをすべて Read して観察し、モジュール資料・
  SPO サマリー・funcmap を書き、テストファイルの検索と検証スイープまで行っていた。読むファイル数に上限も分割も無い
  （`SPECOUT_MAX_AFFECTED_FILES` 超過は警告だけ）。完全スライスの試作評価では確定ファイルが 197〜911 件
  （frr・3シード・5波。`tools/prototypes/specout-slicer/results/eval-feature-level.txt`）になり、1つのエージェントでは読み切れず、
  時間がかかるうえにコンテキスト枯渇で止まるおそれがある。
- **SPO レビュー。** `xddp-reviewer` が discovery-log の抜粋・funcmap・funcmap の機械算出値・`modules/` の全資料を読み、
  チェックリストの全項目を判定していた。突き合わせ・存在確認・件数の照合も LLM が行い、読む量に上限が無かった。
- 実際の CR で残っている SPO レビュー結果（u1-eval CR-2026-819）の指摘2件は、どちらも「波紋調査が要求の成否を左右する経路
  （`script.c` / `server.c`）を取りこぼした」という内容だった。それ以外の項目で指摘が出た実績は無い（根拠はこの1件だけ）。

## Decision

ユーザー判断（プラン §1.2 の D13・D14）に基づき、次のとおりにする。

### 1. 資料の確定は、スクリプトが機能（モジュール）単位の材料を作り、document agent をモジュールごとに起動する（D13）

- `specout_bfs.py doc-digest` が、確定ファイル・関数・伝播経路・打ち切り・関数本文の抜粋（`enclosing_range` の範囲。無ければ前後10行）・
  対応するテストファイルの候補を、`work/digest/index.md`（機能一覧）と `work/digest/modules/{モジュール}.md`（1モジュールの材料）に書く。
  件数・一覧はスクリプトが数えた値を書き、LLM に数えさせない。
- document agent は `DOC_MODE: module`（1モジュールの資料。同時起動は `SPECOUT_DOC_PARALLEL`）と `DOC_MODE: summary`
  （SPO サマリーの LLM が書く欄と funcmap）の2つの起動形に作り直す。ソースは読まず、材料の抜粋だけを読む。抜粋で分からない項目は
  「材料外（未確認）」と書き、推測で埋めない。
- LLM が読む量には上限を設ける。`SPECOUT_DOC_LINE_BUDGET`（1モジュールの抜粋の合計行数。既定 `2000`・暫定）と
  `SPECOUT_DOC_MAX_MODULES`（材料を作るモジュール数。既定 `30`・暫定）。超えた分は discovery-log の「## 打ち切り記録」・state の
  `truncated` に理由 `doc-limit` で記録し（件数照合の対象外）、SPO §1.x（調査の打ち切り）と §5.0（機能一覧）にも載せる（D8）。
  直接影響（第0波）のファイルを含むモジュールは `SPECOUT_DOC_MAX_MODULES` の対象外で、行数上限でも第0波の関数を最優先にする。
  変更設計で手を入れるのはそのモジュールであり、SPO レビューの L1 が読むため。
- 決定的な処理をスクリプトに移す: 配置判定（成長型）と統合→分割の移し替え・SPO サマリーのスクリプトが書く欄（§1.x・§5.0〜§5.2・
  §5.5 のテストファイルの候補・§8・§9 への転記）・台帳と累積観察メモのマージ（`assemble-spo`）、検証スイープ（`verify-sweep`）。
  並列起動でも台帳・累積観察メモが衝突しないよう、module 起動はモジュール別の一時ファイルに書き、`assemble-spo` がまとめてマージする。
- 上限・材料・書き手を変えたのは、確定ファイルが数百件になっても、1つのエージェントのコンテキストに収まる単位に分けて、
  完走させるためである。暫定の既定値は計測していない目安で、打ち切り記録に残るので人が気づける。

### 2. 波紋調査の結果に対する LLM のチェックは、影響範囲の十分性（L1）と設計への申し送り（L2）の2項目だけにする（D14）

- 突き合わせ・存在確認・件数の照合は、スクリプト（`artifact_lint.py --doc-type SPO` の F1〜F4・S1〜S5、`verify-sweep`）に移す。
  スクリプトが書く欄のチェックと MODULE-LEVEL に関わるチェックは削除する。
- SPO レビューの LLM に渡すものは、要求書・CRS・`work/digest/index.md`・直接影響のモジュールの資料だけにする。discovery-log の抜粋と
  funcmap は渡さない（`reviewer_call` の `reference_bytes` が小さくなる）。`extract-review-scope` は不要になり削除した
  （ADR-0019 の `extract-review-scope` の記述は当時の判断の記録であり、本 ADR が置き換える）。
- 根拠は CR-2026-819 の指摘2件がどちらも L1 の内容だったこと。ただし根拠はこの1件だけである。機械的な波紋調査の取りこぼしを、
  要求と照らして見つけられるのは LLM のレビューだけであるため、L1 は残す。削除した項目に当たる不備が人のレビュー（Step A3）で
  2件以上見つかった場合は、その項目を `SPO.md` に戻す。

### 3. ADR-0018 から変えた点

- 配置判定（成長型）の規則（閾値・手順）は変えない。資料の確定では、判定と移し替えを document agent ではなく
  `assemble-spo --layout-only` が行い、書き先はモジュール別ファイル（統合パスは `work/module-drafts/`）に一本化する。
- どのモジュールにも属さないファイルは、資料の確定では `doc-targets --auto-assign` が親ディレクトリへ機械的に割り当てる
  （LLM の判断をやめる）。下調べは今までどおり LLM の判断でモジュールを決め、下調べで決めた組はそのまま使われる。
  モジュールが細かく分かれすぎる場合は、人が `work/module-assignments.json` を直して再実行できる。
- MODULE-LEVEL（上限で資料化しなかったモジュールの印）は SPO に書かれなくなる。消費側（SPO・モジュール資料・テンプレート・
  チェックリスト・document agent・工程5の architect agent・`xddp_review_brief.py`）から記述を除き、代わりに SPO §1.x（調査の打ち切り）と
  §5.0（影響する機能一覧）を入力として読ませる。`specout_bfs.py` 内部の MODULE-LEVEL の処理の撤去は別プランで行った（[PLAN-20261004-specout-module-level-cleanup](../../plans/PLAN-20261004-specout-module-level-cleanup.md)）。

## Consequences

- 確定ファイルが数百件でも、モジュールごとに上限つきで読ませるため、工程4a がコンテキスト枯渇で止まりにくくなる。
- SPO のモジュール資料に「材料外（未確認）」が入る場合がある。SPO §5.1・§5.2・§8・§9 はスクリプトが書き、列と並びが決定的になる。
- SPO サマリーに「### 1.x 調査の打ち切り」「### 5.0 影響する機能（モジュール）一覧」が加わり、`work/` に `digest/`
  （`ledger-rows/`・`observation-rows/` を含む）・`module-drafts/` が増える。
- `specout_bfs.py` に `doc-digest`・`verify-sweep`（未記録ヒットありは終了コード 7。件数不一致の終了コード 3 とは別）・`assemble-spo`・
  `doc-targets --auto-assign` が加わり、`extract-review-scope` が無くなる。
- 設定キー `SPECOUT_DOC_LINE_BUDGET`・`SPECOUT_DOC_MAX_MODULES`・`SPECOUT_DOC_PARALLEL` を追加した。
- 後方互換性は保証しない。既存の CR の SPO は再実行で作り直す。
- 前提（ADR-0019）をデプロイしてから本変更をデプロイする。両者の `smoke-full` は合わせて実施する。

## 再検討条件

- `SPECOUT_DOC_LINE_BUDGET`・`SPECOUT_DOC_MAX_MODULES` の既定は暫定値。u1-eval（frr・3シード・予算10,000）で、各 document agent が読んだ量と
  所要時間、`doc-limit` で外れたモジュール数・ファイル数を測って見直す。
- 抜粋の範囲（関数本文・前後10行）が、工程5の入力として足りるかを、今の document agent の資料と比べて確かめる。
- L1・L2 に絞る根拠は CR-2026-819 の1件だけ。指摘漏れが続く場合は、削除した項目を戻す。
