# XDDPツール 改善点分析レポート

**作成日:** 2026-06-19  
**対象バージョン:** 現行実装（2026-06-19 時点）  
**観点:** ユーザビリティ・保守性・AI駆動開発における効率性

---

## 概要

全スキル（xddp.01〜xddp.close）・エージェント定義・xddp.common を精査し、生成 AI による開発プロセス運用の視点から改善点を分類した。重要度は 🔴 高 / 🟡 中 / 🔵 低（提案）で示す。

---

## 1. ユーザビリティ

### U-01 🔴 スキル番号とプロセス工程番号の不一致が認知負荷を生む

**現状:** `xddp.09.test` が工程11〜14を、`xddp.07.code` が工程9〜10を実行するなど、スキルファイル番号とprogress.md工程番号の体系が乖離している。CLAUDE.md で注記されているが、初見ユーザーと AI エージェントへの説明コストが高い。

**影響範囲:** 全スキル・全ユーザー  
**改善案:** 工程番号体系をスキルファイル番号に統合するか、スキルの `description:` フロントマターに「実行工程: 11〜14」を明示してツールチップ的に機能させる。

**対応状況:** PLAN-20260704-u01 で対応（工程番号側をスキル番号に合わせて 1〜11＋サブ番号に再編。テスト工程を xddp.09.test/xddp.10.test-run に分割し `xddp.10.specs` を `xddp.11.specs` にリネーム）。

---

### [済] U-02 🔴 `xddp.08.verify` と `xddp.07.code` 内検証の役割が不明確

**現状:** `xddp.07.code` Step B で静的検証を自動実行し、`xddp.08.verify` は「人が手動実行する場合（同一内容）」と CLAUDE.md に記述されている。しかし「いつ手動実行するのか」の判断基準がスキル説明に不足している。  
`xddp.08.verify` は独立した SKILL.md を持つが内容が確認できなかった（本分析の調査範囲）。

**影響範囲:** コーディング工程  
**改善案:** `xddp.08.verify` の `description:` に「コーディング途中で単独検証したい場合に使う（`xddp.07.code` の Step B と同一処理）」と明記し、`xddp.07.code` の Step B で自動実行される旨へのリファレンスを追加する。

---

### [済] U-03 🟡 ヒューマンレビューゲートのメッセージパターンが工程ごとに重複

**現状:** xddp.02〜xddp.09 の全スキルが同一構造の Human Review Gate（成果物パスの列挙 → 「レビュー完了」待ち → 変更があれば最終 AI レビュー）を独立して記述している。

**影響範囲:** xddp.02, 03, 04, 05, 06, 09 の SKILL.md  
**改善案:** xddp.common に `## Human Review Gate` プロシージャを追加し、各スキルから `apply` で呼び出す形に統一する。パラメータは `ARTIFACTS`（ファイルリスト）・`REVISE_COMMAND`・`STEP_NUM` 程度で十分。

---

### [済] U-04 🟡 xddp.10.specs の分割実行継続ロジックが複雑でユーザーが迷う

**現状:** Step 0 の「分割実行継続マーカーの確認」で UC / OV / MOD / CROSS の完了状態を読み取り、各ステップのスキップ条件を個別に記述している。どのステップがどのファイルに何を書き込んでいるかをユーザーが把握するのが難しい。

**影響範囲:** xddp.10.specs 全体  
**改善案:** 分割実行メモのフォーマットを正規化し、`/xddp.status {CR}` で「工程15の残タスク」を一覧表示できるようにする。または分割実行時に「次回コマンド: `/xddp.10.specs {CR} --resume`」を自動提示する。

---

### U-05 🔵 `--re-discover` の ENTRY_POINTS チェックが CR 解決後に実施される

**現状:** `xddp.04.specout` の RE_DISCOVER フラグ解析は CR 解決行の直後にあるが、エントリポイント必須チェック（ENTRY_POINTS が空の場合にエラー停止）は CR 解決完了後になる。  
エントリポイントなしで起動した場合、CR の自動検出処理が走ってから初めてエラーになる。

**影響範囲:** xddp.04.specout  
**改善案:** フラグチェックを CR 解決前（Arguments セクション直後）に移動する（エラーメッセージに CR 番号は不要なため）。ただし現状でも実害は軽微なため優先度は低。

---

## 2. 保守性

### [済] M-01 🔴 CRS Excel 再生成コードが複数スキルに重複

**現状:** `python ~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py` の呼び出しブロックが **xddp.03.req Step C / xddp.04.specout Step C / xddp.05.arch Step D / xddp.06.design Step D** の 4 箇所に完全重複して存在していた。

**経緯（一度「済」を撤回した記録）:** コミット `8f42f08`（2026-06-20）で `xddp.03.req`・`xddp.04.specout` の2ファイルのみ `apply "## Regenerate CRS Excel"` 呼び出しに置換されたが、`xddp.common/SKILL.md` に当該見出しが追加されておらず実行時に破綻していた（ダングリング参照）。`xddp.05.arch`・`xddp.06.design` の2ファイルも移行されておらず重複が残存していたため、いったん「済」表記を撤回した。[plans/PLAN-20260621-m01-e01-fix-incomplete-refactor.md](../plans/PLAN-20260621-m01-e01-fix-incomplete-refactor.md)（2026-06-23 承認・実装完了）で `xddp.common` に `## Regenerate CRS Excel` を追加し、4ファイルすべてを `apply` 呼び出しに統一して解消した。

**影響範囲:** xddp.03, 04, 05, 06 の SKILL.md  
**改善案:** xddp.common に `## Regenerate CRS Excel` プロシージャを追加し、各スキルから `apply` で呼び出す形に統一する。パラメータは `CRS_PATH`・`EXCEL_PATH` のみ。

---

### [済] M-02 🔴 Maintenance note が廃止済みの commands/ を参照している（死んだ記述）

**現状:** xddp.02〜xddp.09 の各 SKILL.md 末尾に  
`> **Maintenance note:** When modifying this file, also update '.claude/commands/xddp.XX.md'.`  
が記述されている。しかし `.claude/commands/` は廃止済みで実体が存在しない（スキル名がそのままスラッシュコマンド名になる方式に移行済み）。この Maintenance note は同期不要な対象を指す死んだ記述であり、修正時に誤って commands/ を探しに行く・存在しないファイルを更新しようとする等の混乱を招く。

**影響範囲:** xddp.01, 02, 03, 04, 05, 06, 07, 09, close, xddp.fill-rulebook, xddp.review, xddp.08.verify, xddp.templates/xddp.skill-template.md の SKILL.md（commands/ への言及を含む全ファイル）  
**改善案:** 同期は不要なので、対象ファイルから Maintenance note の行を削除する。`xddp.templates/xddp.skill-template.md`（新規スキル作成時のひな形）からも該当行を削除し、以後のスキルに死んだ記述が再生産されないようにする。

---

### M-03 🟡 `AFFECTED_REPOS` の決定ロジックが各スキルで微妙に異なる

**現状:**
- xddp.04.specout: `AFFECTED_REPOS = all REPOS_KEYS` → Step 0.5 でユーザーが絞り込み可能
- xddp.07.code / xddp.09.test: `AFFECTED_REPOS = all REPOS_KEYS`（絞り込みなし）
- xddp.10.specs: Step 0-4 で「SPO 存在リポジトリ + CHD cross 影響リポジトリ」として確定

この違いが意図的なものか設計上の揺れかが不明確で、メンテナンス時に混乱を招く。

**影響範囲:** xddp.04, 07, 09, 10, close の SKILL.md  
**改善案:** xddp.common に `## Resolve Affected Repos` プロシージャを追加し、`FILTER_BY_SPO`（true = SPO 存在チェックあり）フラグで動作を制御する。各スキルの決定意図をコメントで明示する。

---

### [済] M-04 🟡 `xddp.rules/` ファイルの読み取り方が統一されていない

**現状:**
- xddp.05.arch Step A0: `Read ~/.claude/skills/xddp.rules/xddp.arch.rules.md to get ARCH_RULES`（直接 Read → 変数に保存）
- xddp.06.design Step A: `DESIGN_TASK: {pass DESIGN_RULES content as-is}`（Read 後に文字列として注入）
- xddp.07.code Step 0: `Read ~/.claude/skills/xddp.rules/xddp.coding.rules.md to get CODING_RULES`（直接 Read）

呼び出し形式が統一されておらず、rules/ ファイルのパス変更時に影響範囲が不明確。

**影響範囲:** xddp.05, 06, 07 の SKILL.md  
**改善案:** xddp.common に `## Load Rules` プロシージャを追加する。または rules ファイルをフロントマターで参照できるようにする。

---

### [済] M-05 🟡 cross/ 処理のボイラープレートが各工程で独立して繰り返される

**現状:** SPO / DSN / CHD / TSP / TRS すべての工程で「HAS_CROSS = (IS_MULTI and …)」判定と cross/ 用エージェント呼び出しブロックが独立して書かれている。判定条件の微妙な違い（SPO ベース・CHD ベース・ファイル存在ベース）が意図的なものか揺れなのかも判別しにくい。

**影響範囲:** xddp.04, 05, 06, 07, 09, 10 の SKILL.md  
**改善案:** cross/ の判定ロジックを xddp.common にまとめ、各工程は「HAS_CROSS フラグ」だけを受け取って動作する構造にする。判定条件の違いにはコメントで根拠を添える。

**スコープ分割（2026-07-05）:** 本項目は「①`HAS_CROSS` 判定ロジックの重複」と「②cross/ 用エージェント
呼び出しブロックの重複」の2点を含むが、実装調査の結果、性質が異なることが判明した。
- ①: [PLAN-20260704-m05-resolve-has-cross](../plans/PLAN-20260704-m05-resolve-has-cross.md) で対応（実装完了・2026-07-05 承認）。
- ②: 対応不要と結論。実態を調査したところ、6スキールの cross/ 処理方式は不均質
  （`xddp.04/05/06/10` はagent呼び出しなしで直接生成、`xddp.07/09` のみ `REPO_NAME: cross` で
  per-repo呼び出しパターンを再利用）であり、共通化すべき「重複ブロック」は実質 `07.code`/`09.test` の
  2スキルに限られる。この2スキルは既に同一パラメータ形状（`REPO_NAME: cross`）で十分にDRYであり、
  他4スキルまで無理に統合すると成果物ごとに異なるテンプレート・レビューフロー・progress更新ロジックを
  1プロシージャに詰め込むことになり、可読性低下のリスクが対応価値を上回ると判断した。

---

### M-06 🔵 テンプレートパスが全スキルでハードコード

**現状:** `~/.claude/skills/xddp.XX.YY/templates/*.md` のパスが各スキル内にハードコードされている。setup.sh のインストール先を変更した場合に全スキルファイルの修正が必要。

**影響範囲:** 全スキル  
**改善案:** xddp.common に `SKILLS_ROOT = ~/.claude/skills` 定数を定義し、各スキルは `{SKILLS_ROOT}/...` 形式でパスを記述する。または setup.sh 実行時にパスを環境変数として xddp.config.md に書き込む。

---

### [済] M-07 🟡 xddp.10.specs Step 0 にダングリング参照が存在する

**現状:** `xddp.10.specs/SKILL.md` Step 0-6（`{DOCS}/AI_INDEX.md` の存在確認）に「Section 3-6-1 のセクション構成スケルトンとして新規作成し」という記述があるが、現行の SKILL.md・関連ドキュメントのいずれにも「Section 3-6-1」という見出しは存在しない（PLAN-20260619-a01-split-long-skills の実機検証中に発見）。実体のない参照先のため、AI_INDEX.md 初回生成時に AI が何を基準にスケルトンを構成すべきかが曖昧になっている。

**影響範囲:** xddp.10.specs/SKILL.md Step 0  
**改善案:** 「Section 3-6-1」という参照を削除し、生成すべきセクション構成（「ユースケース一覧」「モジュール別最新仕様」+ IS_MULTI 時は「クロスインタフェース一覧」）を Step 0 内に直接列挙する。または `xddp-close-promote-agent.md` の AI_INDEX.md 全セクション定義（Section 3.6 Output Format 付近）への参照に差し替える。

---

## 3. AI 駆動開発における効率性

### [済] E-01 🔴 lessons-learned.md を 4 工程で毎回全読み取り

**現状:** xddp.02（Step A0）・xddp.05（Step A0）・xddp.06（Step A0）・xddp.09（Step A0）の 4 箇所で `{XDDP_DIR}/lessons-learned.md` を全読み取りしてタグフィルタリングを行っていた。エントリ数が上限（100件）に近づくとコンテキスト消費が無視できなくなる。

**経緯（一度「済」を撤回した記録）:** コミット `8f42f08`（2026-06-20）で改善案①に着手したが、(1) `xddp.02.analysis`・`xddp.09.test` の2ファイルのみ `apply "## Load Lessons Context"` 呼び出しに置換され `xddp.common/SKILL.md` 側の見出し追加が漏れていたため実行時に破綻、(2) `lessons-learned-template.md` の「## タグ別インデックス」テーブルを自動更新する処理が `xddp.close/SKILL.md` Step C に存在せずテーブルが常に空、(3) `xddp.05.arch`・`xddp.06.design` が未移行で全文読み取りが残存、の3点が未完了だったため「済」表記を撤回した。[plans/PLAN-20260621-m01-e01-fix-incomplete-refactor.md](../plans/PLAN-20260621-m01-e01-fix-incomplete-refactor.md)（2026-06-23 承認・実装完了）で `xddp.common` への見出し追加・`xddp.close` Step C のタグ別インデックス自動更新実装・`xddp.05.arch`/`xddp.06.design` の移行をすべて完了し解消した。

**影響範囲:** xddp.02, 05, 06, 09  
**改善案①:** `lessons-learned.md` にタグ別インデックスセクションを追加し（xddp.close で自動更新）、各スキルはインデックスを読んでから対象エントリのみを選択的に読み取る。  
**改善案②:** `xddp.codemap` のように lessons-learned の「タグ別抜粋ファイル」（例: `lessons-learned-#設計.md`）を xddp.close が自動生成する。

---

### [済] E-02 🔴 xddp.close Step A の全 .md ファイル一括読み取りがコンテキストを圧迫

**現状:** Step A で CR フォルダ以下の全 .md ファイル（要求書・ANA・CRS・全リポジトリの SPO/DSN/CHD/CODING/VERIFY/TSP/TRS・latest-specs 配下）を読み取る。大型 CR（3リポジトリ × 複数モジュール）では 50〜80 ファイルに及ぶ可能性があり、AI の有効コンテキストが著しく圧迫される。

**影響範囲:** xddp.close Step A  
**改善案:** 「気づき・提案メモ」セクションを含まないファイル（schema.md・*-seq.md・crud.md・dfd.md）は冒頭に「気づきメモあり/なし」フラグ（フロントマターキー: `has_insights: false`）を持たせ、Step A でフラグのみを確認してスキップする。

---

### [済] E-03 🟡 xddp.09.test Step A（TSP 生成）が順次実行で並列化の余地あり

**現状:** xddp.09.test Step A で各リポジトリの TSP 生成を順次実行している。各リポジトリの TSP は独立して生成できるため（依存なし）、並列化可能。xddp.04.specout の Discovery Phase で並列化を採用している先例がある。

**影響範囲:** xddp.09.test Step A  
**改善案:** `IS_MULTI = true` の場合は xddp.04.specout と同様に Agent tool を並列呼び出しする。cross TSP は per-repo TSP 完了後に順次呼び出し（クロス依存があるため現状通り）。

---

### [済] E-04 🟡 xddp.10.specs Step DONE の AI_INDEX.md 先行更新が xddp.close Step C2 と二重更新

**現状:** xddp.10.specs Step DONE が「モジュール別最新仕様」「ユースケース一覧」「クロスインタフェース一覧」を先行 upsert し、xddp.close Step C2 が「全セクション upsert」を実施する。同一ファイルへの二重書き込みが発生し、xddp.close で同じ処理を再実行するコストが生じる。

**影響範囲:** xddp.10.specs Step DONE, xddp.close Step C2  
**改善案:** xddp.10.specs の先行 upsert は「セクション単位のフラグ」を progress.md に記録し、xddp.close Step C2 ではフラグが立っているセクションをスキップする（差分更新化）。

---

### [済] E-05 🟡 各スキル冒頭の xddp.config.md 多段読み取りが非効率

**現状:** 各スキルが xddp.common の CR Resolution で XDDP_DIR・CR_PREFIX を読み取った後、さらに個別に `REPOS:`・`DOCS_DIR:`・`DEVELOPMENT_MODE:`・`SPECOUT_*` パラメータ等を読み取っている（6〜8 項目）。xddp.config.md へのアクセスが各スキルで 2〜3 回発生する。

**影響範囲:** 全スキル  
**改善案:** xddp.common の CR Resolution で xddp.config.md の全標準キーを一括取得し、WORKSPACE_ROOT・XDDP_DIR とともに返す形式にする。各スキルは CR Resolution 結果を再利用するだけにする。

---

### E-06 🔵 xddp.close Step A の latest-specs 収集フィルターが事後除外方式

**現状:** latest-specs 配下のファイル収集時に、まず全 `.md` ファイルを列挙してから「気づきメモなしファイルの除外フィルター」（`*-seq.md`・`schema.md`・`crud.md`・`dfd.md`）を適用する。ファイル数が多い場合は列挙コストが先行する。

**影響範囲:** xddp.close Step A  
**改善案:** glob パターン段階で除外する（例: `find ... -name "*.md" ! -name "*-seq.md" ! -name "schema.md" ...`）。または前述の `has_insights:` フロントマターフラグ方式と統合する。

---

## 4. AI 特有の設計課題

### [済] A-01 🔴 スキルファイルが長大でエージェントのコンテキスト消費が増大

**現状:** xddp.10.specs/SKILL.md は約 580 行、xddp.close/SKILL.md は約 650 行。スキル自体が AI のコンテキストウィンドウを大量消費し、エージェントに渡せる実データ（SPO・CRS・CHD 等）の余地が減少する。

**影響範囲:** xddp.10.specs, xddp.close  
**改善案:** 各スキルを「オーケストレーター（スリム版 SKILL.md）」と「サブエージェント仕様（詳細ロジック）」に分割する。オーケストレーターは高レベルの制御フローのみを持ち、詳細ロジックはサブエージェント（エージェント定義ファイル）に移譲する。

**対応:** PLAN-20260619-a01-split-long-skills で実装・実機検証済み（xddp.10.specs: 578→471行、xddp.close: 652→365行）。
実機検証で2件の新たな課題（A-06・A-07）が見つかったため、それぞれ別途記録した。

---

### A-02 🟡 「機械的先決基準」が実際には AI 判断に依存している

**現状:** xddp.10.specs Step MOD のバージョン判定に「機械的先決基準を最初に適用し、AI セマンティック判断はその結果を上書き昇格する方向にのみ使用する」と記述されているが、「Mermaid ブロックのノード数/エッジ数カウント」「テキスト行数の 20% 変化」は AI が自然言語で指示されて行う計算であり、真の意味で機械的ではない。誤判定リスクがある。

**影響範囲:** xddp.10.specs Step MOD, Step OV  
**改善案:** 本当に機械的に判定したい場合は Python スクリプト（`xddp.md2excel/scripts/` に倣う）を用意する。または「Mermaid ブロック数の変化のみ」に絞って機械的判定の対象を限定し、それ以外は AI 判断に任せると明記する。

---

### [済] A-03 🟡 「処理は中断しない」という指示が AI に通じにくい

**現状:** xddp.05.arch Step A の SP-ID 照合チェックで「以下のケースで警告を収集する（処理は中断しない）」と記述されているが、AI は警告を発見した時点でユーザーへの確認を挟もうとする傾向がある（Claude の安全指向バイアス）。「警告のみ・続行」の確実な実現には構造的な担保が必要。

**影響範囲:** xddp.05.arch Step A, xddp.10.specs 各所  
**改善案:** 「処理は中断しない」の代わりに「警告を `WARNINGS` リストに追加し、次のステップに進む。ユーザーへの確認は Step B（または Step GATE）でまとめて行う」と明示的に指示する。

---

### A-04 🟡 エージェント呼び出しパラメータが冗長で誤記リスクが高い

**現状:** 各スキルのエージェント呼び出しパラメータが非常に長く（xddp.05.arch の architect-agent 呼び出しは 15 パラメータ以上）、同一パラメータが複数箇所（per-repo ループ内の通常呼び出し・`--detail` モード時の呼び出し・Review Loop 時の FIXER_PARAMS）で繰り返される。スキル修正時に一箇所を変更して他を見落とすリスクがある。

**影響範囲:** xddp.05, 06, 07, 09 の SKILL.md  
**改善案:** 共通パラメータセット（例: `BASE_DSN_PARAMS`）を変数として定義し、呼び出し時にマージする記法を導入する。または per-repo ループの共通部分をサブスキル化する。

---

### A-05 🔵 xddp.common の `apply` 形式がどこまで信頼できるかが不明確

**現状:** `Read ~/.claude/skills/xddp.common/SKILL.md, apply "## CR Resolution" with $ARGUMENTS → let CR, REST_ARGS.` という記法を全スキルが使用しているが、AI が「apply」をどこまで正確に実行できるかは Claude の解釈能力に依存しており、バージョンアップで挙動が変わるリスクがある。

**影響範囲:** xddp.common を使う全スキル  
**改善案:** 定期的に `apply` の実行結果が意図通りかを smoke test で確認するチェックリストを設ける（例: CR 引数なしで各スキルを呼び出し、自動検出が動作するかを確認）。または CR Resolution を明示的なステップとして各スキルに展開する（`apply` に依存しない）。

---

### [済] A-06 🟡 「並行CR保護」の除外条件が通常の陳腐化モジュールも保護してしまう

**現状:** xddp.10.specs Step MOD の廃止モジュール処理は「`last-updated-cr:` が現在の CR と異なるディレクトリ」を並行 CR 保護として廃止候補から除外する。しかし通常運用では「今回 CR で触れていない既存モジュール」の `last-updated-cr` は当然現在 CR と異なる値になるため、この条件は「今まさに並行実行中の別 CR が触れているモジュール」と「単に古くて今回 specout 対象外になった陳腐化モジュール」を区別できない。実機検証（PLAN-20260619-a01-split-long-skills）で、`last-updated-cr` を現在 CR に書き換えない限り `xddp-specs-mod-agent` が廃止候補として検出しないことを確認した。結果として、本来の「並行 CR に削除されないようにする」という意図を超え、通常の棚卸し検出そのものを構造的に妨げている可能性がある。

**影響範囲:** 同一の除外条件が4箇所に存在する — `xddp-specs-mod-agent.md`（廃止モジュール処理・廃止シーケンスファイル処理）、`xddp-specs-uc-agent.md`（廃止UR処理）、`xddp.10.specs/SKILL.md` Step OV（廃止シーケンスファイル処理）・Step CROSS（Step OV と同条件を参照）  
**改善案:** 「並行 CR」を「現在進行中・未クローズの CR」に限定する判定に変更する（例: `{XDDP_DIR}/{last-updated-cr}/progress.md` を読み、CR クローズ済みなら保護対象から除外し通常の廃止候補判定に進む）。CR フォルダが既に存在しない（アーカイブ済み等）場合も保護対象外とする。

---

### [済] A-07 🟡 エージェント分割後、CR クローズの完了ステータスが部分失敗を表現できない

**現状:** `xddp.close/SKILL.md` Step E が `progress.md` に追記する「CR クローズ」セクションの `ステータス:` は `✅ 完了・クローズ済み` の固定文言である。分割前は Step C2〜C7 が単一の同期処理だったため失敗時はその場でエラー停止し、Step E に到達すること自体がなかった。分割後は `xddp-close-promote-agent` が repo 単位で個別に成功/失敗するため、一部 repo が失敗した状態でも人が「クローズ完了」と入力すれば Step E に到達し得る。実機検証（PLAN-20260619-a01-split-long-skills）で、一部 repo 昇格失敗時に Step E のステータス文言をどう書くべきかの記述がないことを確認した（検証時は便宜的に手動で `⚠️` に書き換えた）。

**影響範囲:** xddp.close/SKILL.md Step E  
**改善案:** Step E のステータス文言を `PROMOTE_RESULT` のリポジトリ別処理結果一覧から動的に決定する（全 repo 成功 → `✅ 完了・クローズ済み`、一部失敗 → `⚠️ 完了・クローズ済み（{失敗repo一覧} の昇格が未完了）`）。あわせて、一部失敗が残っている状態で「クローズ完了」の入力を許可すべきかどうかも Step D の文言で再検討する。

---

## 5. 優先対応ロードマップ案

| 優先度 | ID | タイトル | 工数感 |
|---|---|---|---|
| 済 | M-01 | CRS Excel 再生成の共通化（一度未完了と判明 → 再実装で解消） | 小（xddp.common + 4スキルの置換） |
| 済 | E-02 | xddp.close Step A のコンテキスト圧迫軽減 | 中（フラグ導入 + テンプレート変更） |
| 済 | U-03 | ヒューマンレビューゲートの共通化 | 中（xddp.common + 6スキルの置換） |
| 済 | M-02 | 廃止済み commands/ への死んだ Maintenance note 削除 | 小（該当行の削除のみ） |
| 済 | E-01 | lessons-learned タグインデックスの導入（一度未完了と判明 → 再実装で解消） | 中（xddp.close + テンプレート変更） |
| 済 | A-01 | スキルファイルの分割（長大スキル） | 大（設計変更） |
| 済 | E-03 | xddp.09.test Step A の並列化 | 小（3行の変更） |
| 済 | A-03 | 「処理は中断しない」の表現統一 | 小（表現修正のみ） |
| 9 | U-01 | スキル番号と工程番号の統一 | 大（全体設計変更・後方互換なし） |
| 済 | A-06 | 並行CR保護の除外条件見直し（A-01実機検証で発見） | 小（判定条件の修正のみ） |
| 済 | A-07 | CRクローズの部分失敗ステータス表現（A-01実機検証で発見） | 小（Step D/E の表現修正） |
| 済 | M-07 | xddp.10.specs Step 0 のダングリング参照解消（A-01実機検証で発見） | 小（記述の差し替えのみ） |

---

## 付記: 現状の優れた設計判断

以下の設計は生成AI駆動開発の観点から特に優れており、維持すべき。

- **checkpoint.md による BFS 中断・再開:** AI エージェントのコンテキスト切れや中断に対して構造的に回復できる設計は、AI駆動ツールとして必須の信頼性担保になっている
- **xddp.common の CR 解決:** 全スキルが統一された引数解析を持つことで、ユーザー体験の一貫性が保たれている
- **AI_INDEX.md による絞り込み参照:** 毎回 specs/ 以下を全走査するのでなく、インデックス経由で対象モジュールを絞ってから読み取る設計はコンテキスト効率が高い
- **REVIEW_MAX_ROUNDS の設定可能化:** AI レビューの深さをプロジェクトごとに調整できることで、品質と速度のバランスをユーザーが制御できる
- **project-rulebook.md の段階的構築:** xddp.02.analysis Step B3 での候補提示 → xddp.close Step C3.5 での自動 upsert という設計は、知識の蓄積を自然なプロセスとして組み込んでいる
- **FIX_STRATEGY による修正方針の外部化:** AI の修正粒度（ideal/balanced/efficiency）を設定ファイルで制御できる設計は、プロジェクトフェーズに応じた使い分けを可能にする
