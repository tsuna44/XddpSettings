# XDDP ツール分析レポート（2026-08-10）

> **目的:** AI 支援ソフトウェア開発ツールとしての XddpSettings の有用性・不足機能・不具合・改善点・トークン削減施策を、忖度なく分析する。
> **分析方法:** 全 SKILL.md（24 個・約 6,400 行）・全エージェント定義（17 個・約 3,200 行）・主要 Python スクリプト（9 本）・テンプレート群（約 4,900 行）・docs/・plans/・tools/harness/ を並列調査エージェント 3 系統で読了し、重要指摘を本セッションで grep 裏取りした。
> **検証レベル凡例:**
> - ✅ = 本レポート作成時に grep/Read で直接裏取り済み（行番号付き。2026-08-10 時点の行番号であり編集でずれる）
> - ● = 調査エージェントがファイル読了の上で報告（個別の行単位再確認はしていません）
> - **[対策済み YYYY-MM-DD]** = 原文の指摘後に追記した確認結果。原文（当時の指摘内容）はそのまま残し、後日 grep/Read で解消を直接確認できたものにのみ付記する
>
> 前回の自己分析 [xddp-ai-devtool-analysis-2026-07.md](xddp-ai-devtool-analysis-2026-07.md)（W1〜W11・P1〜P10）との重複は避け、解決状況の突き合わせのみ行う。
>
> **2026-08-22 追跡調査:** セクション3・4の全項目について現在のリポジトリ状態を grep/Read で再確認し、解消済みのものに **[対策済み 2026-08-22]** を追記した（原文は当時の指摘のまま保持）。結果概要: §4.1 の実在バグ 9 件は全件対策済み。§4.2 は CLAUDE.md/README の L4/L5 矛盾のみ対策済み（four-tools-comparison.md は依然乖離）。§3 は CR 規模テーラリング（quick profile）のみ対策済みで、他 9 件（git/CI 統合・工程8実ツール実行・全工程テレメトリ・CR 破棄フロー・並行 CR 制御・オンボーディング・baseline_docs ガード等）は未対策。§4.3（設計上の問題）は全件未対策。§2.2／§6#9 の ARTIFACT_LINK 全工程統一も `plans/PLAN-20260815-artifact-link-unification.md`（実装完了）で対策済みと追加確認した。
>
> **2026-08-23 追跡調査:** §4.3「保守メモがロジックを侵食」（`DESIGN_SPEC_PARAMS_BASE` 等）を `plans/PLAN-20260823-maintenance-memo-declutter.md`（実装完了）で対策済み。§4.3 の他項目（close-promote の LLM 転写・funcmap 二重集計・ツール権限過不足・close のスモーク対象外・編集履歴メタコメント残存）は本対応の範囲外で未対策のまま。

---

## 0. 総評（忖度なし）

**specout（工程4a）は競合ツールに類例のない水準に到達している。一方、リポジトリ全体は「specout という 1 工程の研究プロジェクト」に最適化されつつあり、プロセスツールとしての完全性側の負債（小規模 CR パス不在・git/CI 統合ゼロ・close の検証不能・参照整合バグ）が無計画のまま積み上がっている。**

- 過去分析の最優先提言（P1 スクリプト化・P2 テストハーネス）を 1 ヶ月で実装し切った実行力は本物。ADR-0008〜0010 に見る「等価性を fixture で保証してから縮退・並列化する」進め方は模範的。
- しかし `ClaudeCode/.claude/**/*.md` の総量は 7 月時点の約 9,700 行から **約 15,000 行へ 5 割増**（● wc -l 実測）。スクリプト化で LLM の実行責務は減ったが、**読ませる量は増え続けており、過去分析が警告した「規則積み増し→コンテキスト税増」の成長様式自体は止まっていない**。
- plans/ には承認待ち 7 本・草案 2 本が滞留し、実装完了しているのは specout 性能系のみ。W3（軽量パス）・W7（テレメトリ）・W8（工程8実ツール）は**指摘から 1 ヶ月経過して plans/ にすら載っていない**。
- 参照整合の実在バグが複数残っている（§4）。`make lint`（refcheck）は apply 見出し・subagent 契約は検査するが、**設定キーの契約（Load Config の Output と各スキルの reuse 宣言の一致）とセクション番号参照はスコープ外**であり、そこにバグが集中している。

---

## 1. 良い点（維持すべき差別化要素）

1. **specout の三層防御設計** ●: `specout_bfs.py`（帳簿完全スクリプト化・fail-loud ガード）＋ `merge_classification.py`（コミット前全数検証）＋ `specout_verify_counts.py`（書き出されたログテキストの独立再突合）。影響範囲調査の機械化は spec-kit / OpenSpec / cc-sdd / spec-workflow-mcp のいずれも持たない。
2. **人レビューゲートの CHANGED 機械判定** ●（`xddp_gate_snapshot.py`）: LLM の自己申告に頼らない差分検出。レビューブリーフ自動生成（`xddp_review_brief.py`）も人レビュー体験として競合優位。
3. **サブエージェントの越権を構造で防ぐ入出力契約** ●: chd-sync の `.pending` ステージング、close 系の「人への確認をエージェント内で行わない」統一契約、classifier の最小権限（Read/Grep/Write）＋「時計を持たせない」設計。
4. **プロンプトキャッシュを意識した並列 classifier 設計** ●（`xddp.04.specout/SKILL.md` 波ループ）: プレフィクスをバイト同一に保ち初回バッチでキャッシュ書き込みを先行させる指示は、実効的なコスト最適化として珍しい。
5. **UR/SR/SP 多層トレーサビリティ＋機械照合**（`chd_sp_coverage.py`・artifact_lint L1〜L13）と、`source: ai-inferred` 等による AI 不確実性の構造的開示。

---

## 2. 機能は十分か？ — 工程網羅性は高いが、受け渡しに断絶がある

要求→分析→CRS→specout→方式→設計→実装→静的検証→テスト設計→テスト実行→最新仕様書→クローズの直列フローに欠番はなく、差し戻し経路（工程7 の設計エラー分岐、工程10 の CHD/CRS 変更提案分岐）も定義済み。ただし以下の断絶がある。

### 2.1 設定キーの契約不一致（参照切れ・実在）

- ✅ **`SPECOUT_HIT_FILTER` の契約欠落**: `xddp.04.specout/SKILL.md:45` は「lookup done in xddp.common『## CR Resolution』; reuse … SPECOUT_HIT_FILTER」と宣言するが、`xddp.common/SKILL.md` の「## Load Config」には同キーが存在しない（grep で 0 件）。テンプレート `xddp.01.init/templates/xddp.config.md:200` にはキーがあるため、実行時に LLM が未定義変数をデフォルト値で埋めるか幻覚するかは不定。
- ✅ **`xddp.06.design/SKILL.md:122`**: 「Read `{CR_PATH}/xddp.config.md` lookup already done in CR Resolution」— config の実体は `{WORKSPACE_ROOT}/xddp.config.md` であり `{CR_PATH}` 配下には存在しない。かつ `DESIGN_MAX_SP_PER_FILE`・`DESIGN_MAX_SYMBOLS_PER_FILE` は Load Config バンドル外で「lookup 済み」も成立していない。
- ● `xddp.09.test` の `TEST_FRAMEWORK_REPOS` も同様にバンドル外で、どのファイルをいつ読むのか未指示。
- ● `xddp-test-writer-agent.md` は「`MIN_COVERAGE` の cwd 自己読みは絶対にしない」と明記した直後の「Load Project Config」節で `TEST_FRAMEWORK` 等 4 キーを cwd 自己読みさせており、同一ファイル内でポリシーが矛盾。

### 2.2 進捗・成果物追跡の退化

- ✅ **ARTIFACT_LINK を設定するスキルは 3 つのみ**（`xddp.02.analysis`・`xddp.06.design`・`xddp.common` の定義部。grep 実測）。`xddp.03.req`・`04.specout`・`05.arch`・`07.code`・`09.test` 等は完了時に成果物リンクを渡さないため、`xddp.status` の「Artifact checklist」（リンク有無で ✅/⬜ 判定）は**大半の完了工程を ⬜ と表示する**。
  **[対策済み 2026-08-22]** `plans/PLAN-20260815-artifact-link-unification.md`（ステータス: 実装完了）で工程3・4a・4b・5・6a・7・8・9・10a・10c・11 に ARTIFACT_LINK 付与を追加し、既存4行の壊れた値（生パス文字列・相対パス起点誤り）も修正済み。`xddp.status/SKILL.md` にも生パス文字列を ⬜ 判定する第3規則を追加。grep実測で `ARTIFACT_LINK:` 使用箇所が10ファイル19行に拡大していることを確認（10b＝不具合修正は固有成果物を持たないため意図的に対象外、➖表示で区別）。
- ● `⏸`（カバレッジ未達中断）が CR Resolution の「in progress」判定（🔄/👀/🔁）に含まれず、複数 CR 環境で中断中 CR が自動検出されない。

### 2.3 cross 成果物の修正経路欠落

- ● `xddp.04.specout` は cross SPO に対し `/xddp.revise {CR} specout` を案内するが、`xddp.revise` の解決テーブルは `{repo}/SPO-{CR}.md` のみで cross のファイル名（`SPO-{CR}-cross.md`）を解決できない。cross DSN/CHD/TSP も同様に revise 対象外。案内と実装の矛盾。

---

## 3. AI 支援開発ツールとして不足している機能

優先度順。上 3 つは「XDDP プロセスの外で発生する現実」への対応であり、欠けている限り**ツール外での修正→知識ベース腐敗**という破綻シナリオ（前回分析 W3）が生き続ける。

| # | 不足機能 | 内容 | 状態 |
|---|---|---|---|
| 1 | **CR 規模テーラリング（軽量パス）** | 1 行修正にも 12 工程が強制される。`PROFILE: quick`（工程 2+3 統合・4 簡略・5 省略等）に相当する仕組みが皆無（grep 実測 0 件）。前回分析 W3・four-tools-comparison §8 で「優先度: 高」とされて 3 ヶ月未着手、**plans/ にも載っていない** | **[対策済み 2026-08-22]** `CR_PROFILE`（`full`/`quick`）が `CLAUDE.md` に定義され、`ClaudeCode/.claude/skills/xddp.set-profile/SKILL.md` を新設。`xddp.01.init`・`xddp.02.analysis`・`xddp.03.req`・`xddp.04.specout`・`xddp.05.arch`・`xddp.06.design`・`xddp.09.test` 各 SKILL.md に quick 分岐を確認（grep） |
| 2 | **git ブランチ/コミット統合** | 工程 7 でコードを書くのにブランチ作成・コミット・PR の指示がどのスキルにもない ●。CR 単位ブランチ、工程完了時コミット、差し戻し時のコード巻き戻し（工程 10 で test-runner が当てた修正の取り消し）が未定義 | 計画中（未対策）: `plans/PLAN-20260813-vcs-abstraction-branch-commit.md` が存在するが、ステータス欄は雛形のまま「承認待ち」で未承認・未実装（`xddp_vcs.py` 等の実装ファイルは存在せず、`xddp.07.code`・`xddp.close` は依然 git を直叩き） |
| 3 | **CI 連携** | `.github/` には copilot-instructions のみ。(a) ツール自身: `make test` が数秒・0 トークンなのに GitHub Actions がない。(b) 利用者側: 工程 8/10 が既存 CI パイプラインの結果を取り込む口がない | 計画なし（未対策）: `.github/` は `copilot-instructions.md`・`instructions/mermaid.instructions.md` のみで、`.github/workflows/` は依然存在しない（2026-08-22 実測） |
| 4 | **工程 8 の実ツール実行**（前回 W8） | lint・ビルド・型検査を実行する記述が `xddp.07.code`/`xddp.08.verify` にない ●。LLM の目視レビューだけで「静的検証」を名乗っている | 計画なし（未対策・2026-08-22 grep 再確認） |
| 5 | **全工程テレメトリ**（前回 W7） | metrics は specout の per-wave `metrics.jsonl` のみ。工程別トークンコスト・レビュー指摘的中率・ラウンド数の計測がなく、「AI レビュー 3 ラウンドは 2 ラウンドより良いのか」を検証する術がない | 計画なし（未対策・`metrics.jsonl` は依然 specout 限定と 2026-08-22 grep 確認） |
| 6 | **CR の中止・破棄フロー** | `xddp.close` は正常完了専用。`xddp.11.specs` は AI_INDEX を close 前に先行更新するため、CR 破棄で索引に幽霊エントリが残る ● | 計画なし（未対策） |
| 7 | **並行 CR の競合制御** | 「逐次実行を推奨」の注意書きのみで、ロック・機械検出なし（`xddp.11.specs` 自身が implementation comment で自認 ●）。MEMORY 上も複数セッション同時運用が現実に起きている | 計画なし（未対策）: `xddp.11.specs/SKILL.md` の「逐次実行を推奨…将来的なロック機構は improvement-backlog に記録する（今回スコープ外）」の文言は 2026-08-22 時点も同一のまま |
| 8 | **中断再開の工程間不均一** | specout は `bfs-state.json` で厳密再開できるが、工程 2〜6 のレビュー・ループ途中や Gate 待ちで中断した場合の再開・再実行時の上書き/差分更新方針が未規定 ● | 未確認（2026-08-22。工程横断の再開規約文書は grep 範囲では見つからず、対策済みとは断定できない） |
| 9 | **オンボーディング** | チュートリアル・用語集・USDM/XDDP 前提知識の説明が README にない。約 10 種の成果物略称（ANA/CRS/SPO/DSN/CHD/TSP/TRS/TM…）に一覧ページがない ● | 計画なし（未対策・README に用語集/チュートリアル節なしと 2026-08-22 grep 確認） |
| 10 | **baseline_docs 直接編集の消失ガード** | document-flow §7-3 が footgun を誠実に文書化しているが文書化止まり。close 時 upsert 前の非マスター側差分検出で機械ガード可能 ● | 計画なし（未対策・2026-08-22 時点でも close 系に該当ガードは確認できず） |

なお、**不具合修正フロー・別機種移植・CR 非依存母体調査**は plans/（PLAN-20260808-cr-mode-and-defect-flow ほか）で計画済みであり方向性は正しい。問題は承認待ち 7 本・草案 2 本の滞留で、リソースが specout 局所最適に吸われていること。

---

## 4. 改善すべき点（不具合・設計問題）

### 4.1 実在バグ（修正推奨・優先度順）

**→ 以下 9 件は 2026-08-22 時点で全件、修正が入っていることを grep/Read で直接確認した（各項目末尾の追記を参照）。**

1. ✅ **CHD セクション番号の参照ドリフト**: CHD テンプレートの実体は §5=データ設計（`06_change-design-document-template.md:147`）・§6=インタフェース設計（`:175`）・§7=確認項目（`:186`）。しかし `xddp-verifier-agent.md:37` は「確認項目チェックリスト (from CHD Section 6)」、`xddp-reviewer.md:142` は「Every 確認項目 in CHD Section 6」と旧番号を参照。**検証者・レビュアーが確認項目の網羅チェックを誤ったセクション（インタフェース設計）に対して行い空振りする**実害級。リポジトリ自身の「相互参照のルール」（行番号禁止）の精神どおり、セクション番号でなく見出し名参照へ統一すべき。
   **[対策済み 2026-08-22]** `xddp-verifier-agent.md:37`「CHD Section 7 確認項目（テスト観点）」・`:67`「CHD Section 6」、`xddp-reviewer.md:145`「Section 6（インタフェース設計）」・`:149`「CHD Section 7（確認項目（テスト観点）」に修正済み。テンプレート実体（§6/§7）と一致。
2. ✅ **`artifact_lint.py:213-214` の Mermaid 点線エッジ誤検出**: `if "->" in line and "-->" not in line` のため、正当な `-.->` を「エッジ記法破損」と誤報する。`xddp-reviewer.md` は「LINT_RESULTS の項目は confirmed finding として転記せよ」と指示しているため、**正しい図への偽指摘が自動的にレビュー指摘へ昇格し、Fixer が「修正」しにいく自走経路が成立している**。
   **[対策済み 2026-08-22]** `artifact_lint.py:213-214` は `if "->" in line and "-->" not in line and ".->" not in line:` に修正済み（`-.->`/`-..->`/`-. text .->` を正当な記法として除外する旨のコメント付き）。
3. ✅ **`crs_md2excel.py` が `- **仕様：**` フィールド非対応**（grep 0 件）: `DEVELOPMENT_MODE: new` の CRS（Before/After ではなく単一「仕様」記述）を Excel 化すると**仕様本文が丸ごと欠落する**。`artifact_lint.py` 側は対応済みで片落ち。
   **[対策済み 2026-08-22]** `crs_md2excel.py:406` に `spec: str = ""` フィールドを追加、`:578` で `('spec', ('仕様',))` パースに対応済み。
4. ✅ §2.1 の設定キー契約不一致（`SPECOUT_HIT_FILTER`・`DESIGN_MAX_SP_PER_FILE` 等）。
   **[対策済み 2026-08-22]** `xddp.common/SKILL.md` の「## Load Config」に `SPECOUT_HIT_FILTER`・`DESIGN_MAX_SP_PER_FILE`／`DESIGN_MAX_SYMBOLS_PER_FILE`・`TEST_FRAMEWORK`／`TEST_FRAMEWORK_REPOS` を追加済み。`xddp.06.design/SKILL.md:138` の `{CR_PATH}` 誤記も `{WORKSPACE_ROOT}/xddp.config.md` に修正済み。
5. ✅ **`specout_bfs.py escape_symbol` の語境界問題**: 先頭/末尾が非単語文字のシンボル（`$state`・`operator+` 等）では `\b` が境界を成立させず **grep が黙って 0 ヒット**になる。エージェント文書がまさに `$state`・`operator+` をエスケープ例に挙げているのに、その種のシンボルが波及探索から無音で欠落しうる。「安全側」が信条の specout で最も直すべき箇所。
   **[対策済み 2026-08-22]** `specout_bfs.py:227` に `_word_boundary(sym)` 関数を新設し、先頭・末尾が非単語文字の場合は当該側の `\b` を省略する実装に修正済み（無音 0 ヒットを防止）。
6. ● **`xddp-specout-agent.md` Phase 0 のエスケープ例が有害**: 「`List<A>` → `List\<A\>`」と例示するが `escape_symbol` の specials に `<>` は含まれず、GNU grep -E で `\<` は語境界メタ文字。例に従うと意味が変わる。バッチサイズも文書 100 / スクリプト 50 で乖離。
   **[対策済み 2026-08-22]** `xddp-specout-agent.md:111` の例示は「`_word_boundary` によって語境界が制御される（例: `List<A>` はそのまま `List<A>` として扱う）」に修正済み（誤ったエスケープ例は解消）。バッチサイズは `specout_bfs.py:791` で `batch_size = 20 if avg_len > 50 else 50` の動的決定に変更されており、固定値の記載自体が解消されている。
7. ● **`specout_bfs.py cmd_import`（checkpoint.md からの復元）が `confirmed_files`・`symbol_origin_map`・`classified_locations` を無警告で全損**する（md ビューに存在しないため）。復元不能である旨の警告出力がない。
   **[対策済み 2026-08-22]** `specout_bfs.py:1779-1789` で warnings リストを追加し、該当フィールドが初期化される旨を明示。discovery-log.md が存在する場合は「> ⚠️ import 警告:」として追記する処理も追加済み。
8. ● artifact_lint の小穴: L6 重複判定が new モード SP（after 空）を素通し／`_lint_ana` の `"/latest-specs/"` 先頭スラッシュ付き部分一致は相対パス表記を検出漏れ。
   **[対策済み 2026-08-22]** `artifact_lint.py:463-465` で「変更モードでは After、new モードでは仕様が本体」の spec_empty 判定を追加。`ANA_LATEST_SPECS_RE = re.compile(r"(^|/)latest-specs/")`（`:537`）で先頭一致・相対パス一致の両方を検出するよう修正済み。
9. ● `xddp.10.test-run` Step -1 の TSP 存在チェックが「全 repo 欠落」のみ検出し、一部 repo 欠落で存在しない TSP をエージェントに渡す。
   **[対策済み 2026-08-22]** `xddp.10.test-run/SKILL.md:35-39` で `AFFECTED_REPOS` を repo 単位にループし、存在しない repo を `MISSING_TSP_REPOS` に個別追加する構造に修正済み（一部 repo 欠落も検出可能）。

### 4.2 ドキュメントの乖離（信頼性の問題）

- ✅ **CLAUDE.md と README の矛盾**: CLAUDE.md「ハーネス実行」節は L4/L5 を「校正ラン完了後に有効化される」と未来形のまま。README は「校正済み・有効化済み（2026-07-26）」。CLAUDE.md の更新漏れ。
  **[対策済み 2026-08-22]** `CLAUDE.md:183-184`「`make smoke-full`（L4/L5）は...2026-07-26 に校正済み・有効化済みであり」に修正済み。README.md:91 の記述と一致。
- ✅ **document-flow.md が `bfs-state.json` を知らない**（checkpoint.md のみ記載）。→ 現状は `bfs-state.json` もファイル一覧に記載済み（役割の注記は引き続き補完可能）。
  **[対策済み 2026-08-22]** `docs/document-flow.md:250`「bfs-state.json （BFS 実行状態ファイル。中間ファイル）」で記載継続を再確認。
- ● **four-tools-comparison.md（2026-05-11）が現実と乖離**: 「15 工程・9 スキル」「✅ MULTI_REPO フラグ」（現行 CLAUDE.md は「廃止」と明記）。この文書を意思決定に使うのは危険。
  **未対策（2026-08-22 再確認）**: `docs/four-tools-comparison.md:3` は「最終更新: 2026-05-11」のまま、`:36`「15工程（厳格）」・`:40`「✅ MULTI_REPO フラグ」・`:128`「XDDP（15工程・9スキル）」も未更新で残存。CLAUDE.md の現行記述（CR_PROFILE・REPOS: 等）と乖離したまま。
- ● CLAUDE.md のファイル構成表セルに specout 仕様が数百語ベタ書きされ、事実上メンテ不能な密度。表のセルは仕様記述の置き場ではない。
  未確認（2026-08-22。今回は個別に再検証していません）。
- **示唆:** これらはいずれも refcheck（L1/L3）の守備範囲外。**「docs/ の記述とスキル実体の整合」を検査する refcheck 検査 E の追加**が構造的な対策になる。

### 4.3 設計上の問題

**未対策（2026-08-22 再確認）**: 本節の指摘はいずれも未着手のまま。`xddp-close-promote-agent.md` の tools は依然 Read/Write/Edit/Glob のみ（Bash なし）で `promote.py` 相当のスクリプトも repo 全体に存在しない。funcmap の二重集計（specout-agent と reviewer 双方が独自集計）も構造は変わらず。`xddp.06.design/SKILL.md:173,179,237,243` の `DESIGN_SPEC_PARAMS_BASE` 保守メモも ADR へ移設されず残存。

**[対策済み 2026-08-23]** 直下の「保守メモがロジックを侵食」項目（`DESIGN_SPEC_PARAMS_BASE`・`ARCH_AGENT_PATHS`・`TSP_OUTPUT_FILE`・`DESIGN_INDEX_FILE_BASE`）は `plans/PLAN-20260823-maintenance-memo-declutter.md`（実装完了）で解消。grep-and-sync 注記をドキュメンテーションで固定化する代わりに、`xddp.common/SKILL.md` へのプロシージャ抽出（`## Build Design Spec Params`・`## Build Arch Agent Paths`・`## Build TSP Output File`。`DESIGN_INDEX_FILE_BASE` は既存の `## Discover CHD Files` へ統合）で定義を1箇所に統合し、`_BASE`＋grep-and-sync 注記は「xddp.common へ抽出できない場合のみ」のフォールバックへ格下げした（`xddp.skill-template.md`「## 参考: エージェント呼び出し共有パラメータの命名規約」の優先順位を明文化）。本項目以外（close-promote の LLM 転写・funcmap 二重集計・ツール権限過不足・close のスモーク対象外・編集履歴メタコメント残存）は未対策のまま。

- ● **「決定的処理はスクリプト」の方針が close 系・document 系で破れている**（自ルール違反）:
  - `xddp-close-promote-agent.md`: latest-specs→DOCS の**ファイル一式コピーを LLM が Read→Write で全文転写**。AI_INDEX の 7 セクション upsert・「用語数: {行数}」の行数カウントまで LLM 作業。`promote.py` に切り出すべき筆頭。
  - `xddp-specout-agent.md` document モード: funcmap の「直接呼び出し元数」集計（テーブル集計）を LLM が手作業し、**さらに reviewer が同じ集計を再実行して突合せる二重の無駄**。Phase 3 検証スイープ（全シンボル再 grep→集合差分）も `verify-sweep` サブコマンド化候補。
  - `xddp.02.analysis` Step 0（約 140 行の分岐・正規化・キーワード照合）・`xddp.close` Step A（全成果物からの「気づきメモ」見出し切り出し）・`xddp-specs-mod-agent` の「機械的先決基準」（ノード数・行数 20% 変化を LLM に数えさせている）。
- ● **保守メモがロジックを侵食**: `xddp.06.design` の `DESIGN_SPEC_PARAMS_BASE` は「2 箇所は完全同一ではない・grep して同期せよ」という説明が本体ロジックより長い。`_BASE` 系複製規約は xddp.common へのプロシージャ抽出で消せる重複をドキュメンテーションで固定化している。実行時不要な設計根拠は ADR へ追い出せばスキル本文を 2〜3 割削れる。**[対策済み 2026-08-23]** `plans/PLAN-20260823-maintenance-memo-declutter.md` 参照。
- ● **ツール権限の過不足**: chd-sync / design-sync は Bash を持つが Process に Bash を要する手順がない（事故半径の無用な拡大）。逆に close-promote は Bash なしの結果、上記の LLM 転写を強いられている。
- ● **close＝知識昇格経路が唯一スモーク対象外**という倒錯（smoke_config.md で advisory 対象外＝手動検証）。最重要かつ最複雑なスキルが一番テストされていない。直近変更でも smoke-full 未実施のまま「実装完了」宣言があり、L4/L5 が変更時ゲートとして機能していない。
- ● エージェント文書内に編集履歴メタコメント残存（`xddp-architect-agent.md`「※ Section 6 のエントリは削除」）、`xddp-close-knowledge-agent.md` に自ルール違反の行番号参照（既にずれている）。

---

## 5. トークン使用量削減施策（効果見込み順)

現状把握: 総プロンプト資産約 15,000 行が 5 割増ペースで成長中。削減の主戦場は「固定で読ませる量」と「同じファイルの重複読み」。

| # | 施策 | 対象 | 効果見込み | 検証 |
|---|---|---|---|---|
| 1 | **classifier への CRS 全文配布をやめ、スコープ要約をチャンク JSON に埋め込む** | `xddp-specout-classifier-agent.md`（out-of-scope 判定のためだけに**チャンクごと×全波で CRS 全文 Read**）。`known_symbols` と同じ配布パターンで `specout_bfs.py search` が数行の要約を埋め込む | **最大**。K チャンク×波数×repo 分の CRS 読込が消える | ● |
| 2 | **`xddp-specout-agent.md`（846 行）のモード分割** | discovery-setup は現在 `specout_bfs.py init` を 1 回叩くだけなのに、document モード専用の約 600 行を毎回ロード | discovery-setup 起動時プロンプト約 7 割減 | ● |
| 3 | **Review Loop の REFERENCE_FILES 削減** | (a) `xddp.06.design`: バッチ×ラウンドごとに CRS 全文＋SPO を再読（UR10 件・2repo・2 ラウンドで reviewer/fixer 起動最大 80 回規模）。(b) `xddp.04.specout`: discovery-log 全文＋modules/ 全 md をレビュー入力に添付（波数比例で肥大）。(c) `xddp.11.specs` Step REV: バッチごとに全 repo の全 CHD を再添付 | 大。CR が大きいほど支配的 | ● |
| 4 | **`xddp-reviewer.md`（349 行）のチェックリスト遅延ロード** | 1 回の起動で使うのは 1 ペルソナ＋1 チェックリスト＋高々 1 downstream。DOCUMENT_TYPE 別ファイルに分割して Read | 毎レビュー呼び出しで 6〜7 割減。レビューは全工程で走るため累積大 | ● |
| 5 | **close-promote の昇格コピーを `promote.py` 化** | LLM Read→Write 転写はトークンが仕様書総量に比例。fidelity リスクも同時に消える | 大（仕様書量比例分が 0 に） | ● |
| 6 | **Load Config へのキー追加**（`SPECOUT_HIT_FILTER`・`DESIGN_MAX_*`・`TEST_FRAMEWORK*`・`REVIEW_MAX_ROUNDS.*`・`FIX_STRATEGY.*`） | 「## Review Loop」がループごとに `xddp.config.md` を再 Read する構造の解消。§2.1 のバグ修正と同時に達成 | 中 | ✅/● |
| 7 | **RULEBOOK_CONTEXT の節単位受け渡し** | architect/designer/coder/verifier 等 6 エージェントが rulebook 全文を受けるが、coder/verifier の実参照は §4・§6 のみ | 中 | ● |
| 8 | **保守メモ・設計根拠の ADR 追い出し** | `xddp.06.design` の `DESIGN_SPEC_PARAMS_BASE` 注記（**[対策済み 2026-08-23]** `plans/PLAN-20260823-maintenance-memo-declutter.md`。xddp.common へのプロシージャ抽出で解消）、`xddp.feedback` の根拠説明、USDM 仕様の 3 箇所重複（spec-writer / artifact_lint ヘッダ / CLAUDE.md）→ lint を単一真実源に（残り2件は未対策） | スキル本文 2〜3 割減 | ● |
| 9 | **決定的処理のスクリプト化そのもの**（§4.3: funcmap 集計・close Step A 見出し抽出・analysis Step 0・AI_INDEX upsert） | LLM の読解対象がスクリプト出力の要約に変わる | 中 | ● |
| 10 | **`xddp.status` の衝突チェック軽量化** | TM 未生成 CR で全 repo×全 CHD を読む。進捗確認という軽量コマンドの期待に反する。TM 生成済みなら TM のみ、未生成なら「未チェック」表示で足りる | 小〜中 | ● |

**すでに実装済みの削減策**（波内チャンク並列＋キャッシュ整列・保守的ヒットフィルタ・noise-collapse・`status --brief`・lessons-learned のタグ別選択読み込み）は正しい方向であり、上記はその延長線上にある。**ただし施策 1〜4 に着手する前に、W7（テレメトリ）を最小実装して工程別トークンを計測すべき**。smoke 校正で「$2/工程」の実測手段はすでにあるのだから、「推測ではなく計測に基づいて最適化」という自らの理念をツール開発自身に適用する好機。

---

## 6. 推奨アクション（優先度順まとめ)

**即修正（バグ・小工数）:**
1. ✅ CHD セクション番号ドリフト一斉修正 → 見出し名参照へ統一（verifier/reviewer/designer） — **[対策済み 2026-08-22]**
2. ✅ `artifact_lint.py` の `-.->` 誤検出修正（偽指摘の自走経路を断つ） — **[対策済み 2026-08-22]**
3. ✅ Load Config への設定キー追加＋`xddp.06.design` の `{CR_PATH}` 誤記修正 — **[対策済み 2026-08-22]**
4. ✅ `crs_md2excel.py` の「仕様：」フィールド対応（new モードのデータ欠落） — **[対策済み 2026-08-22]**
5. ✅ `escape_symbol` の非単語文字境界の無音 0 ヒット修正 — **[対策済み 2026-08-22]**
6. ✅ CLAUDE.md の L4/L5 記述更新・document-flow.md への bfs-state.json 反映 — **[対策済み 2026-08-22]**
7. GitHub Actions で `make test` を回す（数時間で入る） — 未対策（`.github/workflows/` 依然なし。2026-08-22 確認）

**次の投資先（specout のさらなる高速化より優先すべき）:**
8. **CR 規模テーラリング（PROFILE: quick）** — 最重要。これがない限り小規模修正はツール外で行われ、知識ベースが腐る — **[対策済み 2026-08-22]** `CR_PROFILE` 実装済み（§3-1参照）
9. ARTIFACT_LINK の全工程統一（status の成果物追跡復旧） — **[対策済み 2026-08-22]** `plans/PLAN-20260815-artifact-link-unification.md`（ステータス: 実装完了）で対応済み。`ARTIFACT_LINK:` の使用箇所は3ファイル4行→10ファイル19行に拡大（grep実測）、`xddp.status/SKILL.md:87-93` に第3判定規則（リンク形式でも `-`/空でもない生パス文字列は ⬜）も追加済み
10. git ブランチ/コミット運用の最小統合と CR 中止フロー — 未対策（`plans/PLAN-20260813-vcs-abstraction-branch-commit.md` は承認待ちのまま未実装。CR 中止フローも未実装。2026-08-22 確認）
11. close 系の決定的処理スクリプト化（promote.py）＋ close のスモーク対象化 — 未対策（`xddp-close-promote-agent.md` は依然 Bash なし・`promote.py` 相当は存在せず。2026-08-22 確認）
12. 全工程テレメトリの最小実装（工程別トークン・ラウンド数を metrics.jsonl に記録） — 未対策（`metrics.jsonl` は依然 specout 限定。2026-08-22 確認）
13. トークン削減施策 1〜4（計測後に効果順で） — 未確認（2026-08-22。今回は再検証していません）

---

## 付記: 本分析の限界

- ● 印の指摘は調査エージェントがファイルを読了した上での報告だが、本レポート作成時に行単位の再確認はしていません。修正着手時には対象箇所を必ず実測すること（プラン作成ルールに従う）。
- 実プロジェクトの CR 実行ログに基づく動的検証（実際に LLM が指示を誤解釈するか）は行っていない。§5 の効果見込みは構造からの推定であり、実測（W7）に置き換えるべきもの。
