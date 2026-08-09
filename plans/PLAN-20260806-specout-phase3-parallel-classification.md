# PLAN-20260806-specout-phase3-parallel-classification

作成日: 2026-08-06  
ステータス: 草案 / 承認待ち / 承認済み（Stage 1） / 実装完了（Stage 1） / 承認済み（Stage 2・2026-08-09） / **実装完了（Stage 2・2026-08-09）。`make test` 緑（specout ユニットテスト 86→132件）・`bash ClaudeCode/setup.sh` でデプロイ済み**

> **実装完了の範囲（2026-08-08）:** §4.9 Stage 1 の手順0（§4.5(g) 非破壊化・再開経路統一）・
> 手順1 の**実装**（§4.5(c)(d) の計測）・手順3（案Y スパイク）は完了し、`make test` は緑
> （specout の unittest は 62 → 86 件）。`bash ClaudeCode/setup.sh` で `~/.claude/` へデプロイ済み。
> **計測（B案）の進捗（2026-08-08）:**
> (1) 手順1 の実測採取 — **1ラン実施済み**（母体 redis・`CR-2026-990`・自然波3波）。
> (2) 手順2 の不変条件1 の基準線採取（同一シード3回実行の ∪ と ∩）— **未了**。
> (3) 除外波の別掲を含む Stage 2 着手ゲートの判定 — **実施済み。§9.2 のゲートは成立**
>     （除外波0件・`classify_wall_ms ≥ 60,000` の波が 100%・該当波の `classified` 中央値 118）。
> 結果の全文は [PLAN-20260806-specout-phase3-stage1-measurement.md](PLAN-20260806-specout-phase3-stage1-measurement.md)。
> **Stage 2 の再承認申請には、なお (2) と §4.9.1 (e) のプロンプトキャッシュ実測が前提となる**
> （§9.3 のゲート成立時アクションが明記）。標本は1リポジトリ・1言語（C）・1 CR の1件のみである点に注意。
>
> **完了（2026-08-08 追加）:** トークン増分の予測上限は **§4.9.1 にパラメトリック版として算出済み**。
> `classified` の実測値を感度表へ当てはめるだけでゲート提示物が完成する。
> **この試算で新たに判明した論点（§4.9.1 (e)）: 費用対効果の分岐点は並列化そのものではなく、
> classifier サブエージェントの安定プレフィクス（分類ルール＋CRS）にプロンプトキャッシュが効くか。**
> キャッシュ無では §6 の「現行実測の2倍以内」を現実的なケースで超過し、キャッシュ有なら現行を下回る。
> Stage 2 再承認時の必須確認事項に追加済み。
>
> **完了（2026-08-09 追加）: §9 に記録された「残作業」（§4.9「Stage 2 再承認時の必須補完事項」の記載と、
> 計測で判明した2点の反映）に対応した。** §4.9.1(c) に**固定ブートストラップ項 `T_boot`**（実測
> ≈33,000〜49,000 トークン／サブエージェント。stage1-measurement.md §5.5 で判明した当初モデルの欠落）を
> 追加し、(d)(e) を実測値・キャッシュ共有の事実に基づき更新した。§4.2 step b・§4.4 に
> **プレフィクスのバイト同一性（チャンク固有情報を末尾配置）とコールドスタート競合窓への対策**を
> 設計要件として明記し、§6 に対応する確認項目を追加した。あわせて §4.5(d)「判定方法〔S2〕」
> （`min_chunk_mtime` 経由の再利用波検出）を確定し、§4.2・§4.6・§6 へ配線した。§4.5(e)・§4.6 にも
> `plans/_template.md` §3 書式の Before/After 枠を追加した。
> ~~**残る未了（Stage 2 再承認までに必要。詳細は §4.9 末尾）: (1) `T_rules`/`T_CRS`/`T_boot` の
> `count_tokens` 実測のみ**（本セッションは API 認証未設定のため未実施）~~ → **2026-08-09 人が判断し受容。**
> 本セッションも `ANTHROPIC_API_KEY` 未設定のため実測は依然できず、人は「文字数ベース推定値
> （±30%誤差見込み）のまま Stage 2 再承認へ進める」ことを選択した（`CLAUDE_CODE_OAUTH_TOKEN` を
> 生 API 呼び出しへ流用する代替案は採らない）。実測との乖離は §6「トークン増分が定量閾値内」の
> 実測ゲート（`make smoke-full PHASE=04` の $/起動）で Stage 2 実装完了時点に捕捉される。詳細は §4.9 末尾。
> ~~(2) CRS が Read ツール経由でもキャッシュ対象になるかの検証~~ → **2026-08-09 完了**
> （stage1-measurement.md §5.7。対象になりうるが確率的。詳細は §4.9.1(e)(5)）。
> ~~(3) `phase04-multi` シードの生成~~ → **2026-08-09 完了**（CR-2026-991・手動最小化フィクスチャ。
> `smoke_full.stage_workspace()` でのステージング検証済み。詳細は §4.9「Stage 2 着手の外部依存」）。
>
> **以上により Stage 2 再承認時の必須補完事項（§4.9 末尾）はすべて解消した。次アクションは
> 人による Stage 2 の正式承認（§8）である。**

> 本プランは親ロードマップ [PLAN-20260804-specout-performance.md](PLAN-20260804-specout-performance.md)
> の **Phase 3** を独立プラン化したもの。親の実装到達点は **Phase 0/1 実装完了**に加え、
> **Phase 2 も個別プラン [PLAN-20260806-specout-phase2-noise-priority.md](PLAN-20260806-specout-phase2-noise-priority.md)
> が「実装完了」**（`specout_bfs.py` に Phase 2A 前倒し縮退・Phase 2B 簡易 module-priority が実装済み）。
> したがって **Stage 1 で採取する計測値は「Phase 1/2 のヒット削減が効いた後の値」**であり、
> ゲート指標の選定（§4.9）はこの前提に立つ。目的は **1波のヒット数が多い場合の壁時計
> レイテンシ短縮**を、classification（LLM 意味判定）の**波内並列化**で実現する。トークン総量はほぼ不変
> （並列化は時間短縮であってトークン削減ではない — 親プラン §3.5・目標対応表を継承）。**波間は BFS の
> データ依存で直列のまま**（波N+1 の frontier は波N の分類結果に依存）。
>
> **本プランは大きな構造変更を含む**（BFS ループの実行主体の移設）。correctness の不変条件は
> 「**チャンク分割によって各行の判定入力が単一コンテキスト時より狭まらないこと**」であり、
> `commit-wave` のスキーマ検証・ケースA判定・frontier 伝播の契約は一切変えない。
>
> **本プランは2段階構成**（§4.9）。**Stage 1 = 計測（`classify_wall_ms` 等の metrics 追加）
> ＋既存不具合の是正（`cmd_search` 非破壊化＝§4.5(g)）＋再開経路の統一**、
> **Stage 2 = 並列化本体**。**Stage 1 は「計測のみ・挙動不変」ではない**（§5 参照）。
> Stage 2 は Stage 1 の実測で費用対効果を確認してから**別途承認**を要する。
>
> **本プランは草案であり、承認前に AI プランレビュー（/xddp.plan-review）と人の確認を要する。**

---

## 1. 背景・目的

### 現状のループ構造（実コード確認）
- BFS ループ（search → LLM 分類 → commit-wave）は **specout エージェント内で完結**する
  （[xddp-specout-agent.md](../ClaudeCode/.claude/agents/xddp-specout-agent.md)「### Step 2: BFS ループ」の
  「ループ本体（frontier が空になり complete になるまで繰り返す）」）。
- specout エージェントのツールは **Read / Grep / Glob / Bash のみ**（frontmatter `tools:`）。**Agent/Task ツールを
  持たない**ため、エージェント自身が並列サブエージェントを起動できない
  （`ClaudeCode/.claude/agents/*.md` の全16定義を確認したが、`tools:` に Agent/Task を含む定義は存在しない）。
- オーケストレータ（[SKILL.md](../ClaudeCode/.claude/skills/xddp.04.specout/SKILL.md)「## Step A」）は repo ごとに
  specout エージェントを**1回**起動する。マルチリポジトリ時は各 repo の Discovery を**並列呼び出し**する
  （同 SKILL の「**Discovery エージェント呼び出し:**」節の `IS_MULTI` = true 分岐。
  [docs/specout-discovery-guide.md](../docs/specout-discovery-guide.md)「分離単位」表も
  「リポジトリ＝分離（独立 Agent コンテキスト。マルチリポ時は並列呼び出し）」を設計方針として明記）。

### 支配的コストと並列化余地
- 1波の分類は、その波の全ヒット行を**単一コンテキスト**で LLM が判定する（親プラン計測の支配項）。
- 「1波のヒット数が多い」場合、この単一コンテキスト判定が壁時計のボトルネック。
- 集約（ケースA昇格・伝播抑止・frontier 算出）は **`commit-wave` 側**が全 classification を見て行う
  （`specout_bfs.py` の `cmd_commit_wave` 内 `case_a_symbols` 構築部および `_is_discarded_scope`）。
  → **分類をチャンク分割しても、`commit-wave` が全チャンクの classification を統合して受け取れば
  下流の集約ロジックは一切変わらない**。

### ただし「行ごとに完全独立」ではない（設計上の最重要制約）
分類手順は**今波の他ヒット行を判定入力に含む**。
[xddp-specout-agent.md](../ClaudeCode/.claude/agents/xddp-specout-agent.md)「**判定手順**」4項:

> `x = f()` 形式は f が visited・前波 frontier・**current-wave-hits（今波の hits 内の他シンボル）**の
> いずれかに含まれる場合のみ x を `propagation-direct` の `next_symbols` に含める

同ファイル「### 伝播種別の判定ルール（まとめ）」の「データフロー（戻り値代入）」「データフロー（ジェネレータ受信）」も
同一条件である。さらに `out-of-scope-discard`（判定手順3 の「スコープ外・調査不要と判断した場合」）は
**CRS が定義する変更スコープの理解**に依存する。現行はこれらを「CRS を読んで Wave 0 を構築した同一コンテキスト」が
継続保持している。したがって**素朴なチャンク分割は判定入力を縮小し、探索漏れまたは探索肥大**を生む。
親プランの不変条件「確定影響ファイルの取りこぼしゼロ」に直接抵触する。
本プランはこれを §4.1 の `known_symbols` 明示配布 ＋ `CRS_FILE` 配布で解決する。

### 効果測定の前提が未整備（着手前提）
現在の metrics.jsonl は `wave` / `search_ms` / `raw_hits` / `dedup_removed` / `filter_removed` /
`noise_collapse_removed` / `classified` / `classified_locations_size` / `next_frontier` の9キーで
（`cmd_search` の `metrics` 初期化と `cmd_commit_wave` の `metrics_line` 生成部）、
**分類区間（search と commit-wave の“間”）の時間は未計測**である。
なお `raw_hits` は dedup・保守的フィルタ・noise-collapse を**適用する前**の生ヒット数、
`classified` は**適用後**の実分類行数（= `len(hits)`）であり、両者は Phase 1/2 の削減が効くほど乖離する。
**チャンク分割の対象になるのは `classified` の側**である（§4.9 のゲート指標選定の前提）。「推測ではなく計測に基づいて最適化」
（CLAUDE.md）に従い、本プランは §4.5(c)(d) の計測を **Stage 1 として並列化本体より先に実装**し、
現状の分類時間を実測してから並列化の投資判断を行う（§4.9）。**Stage 1 には、正しい計測値と正しい基準線を
得るための前提条件として §4.5(g)（`cmd_search` の非破壊化＝既存の取りこぼし不具合の是正）と
§4.7 の再開経路統一（`xddp-specout-agent.md`・`recovery-procedures.md`）も含む**。
したがって Stage 1 は「metrics 追記のみ・挙動不変」ではない（§5）。

### 目的と適用しきい値
1波の classification をチャンク分割して**並列サブエージェント**で判定し、壁時計を短縮する。決定的処理
（search / チャンク分割 / 統合検証 / commit-wave / 帳簿）は Python スクリプトのまま。
波のヒット数が `SPECOUT_CLASSIFY_CHUNK_SIZE` 以下の場合は**分割せず単一チャンク**として処理する
（起動オーバーヘッドが短縮効果を上回るため。既定値の妥当性は Stage 1 の実測で見直す）。

---

## 2. 設計案の選定（確定: 案X）

| 案 | 概要 | トークン増分 | 実装工数 | 切り戻し容易性 | 判定 |
|---|---|---|---|---|---|
| **案X: ループをオーケストレータへ移設** | SKILL（メインループ＝Agent ツール保持）が波ごとに `search`(Bash) → チャンクファイル → **分類専用サブエージェントを並列起動** → 統合検証 → `commit-wave`(Bash) を回す。既存エージェントは `discovery-setup` と `document` を担当 | 中（各チャンクが「分類ルール ＋ CRS」を読むため、概ね チャンク数 × (ルール + CRS) 分が増加。増分の実測は Stage 1 の `chunk_count` 分布と併せて評価する） | 大（SKILL 構造変更＋新規エージェント＋スクリプト2本） | 中（`SPECOUT_CLASSIFY_CHUNK_SIZE: 0` で常に単一チャンクへ縮退。ループ移設自体も定義ファイルの git revert で復元可能だが、移設後に開始した進行中 CR の途中状態は追従しない＝再実行が必要） | **採用** |
| 案Y: specout エージェントに Agent ツール権限を付与 | エージェントが波ごとに分類サブエージェントを並列起動 | 案X と同等 | 中（SKILL 変更は小） | 高（`tools:` から Agent を外せば復帰） | 不採用 |

**案Y を不採用とする根拠:**
1. `ClaudeCode/.claude/agents/` 配下の全16定義を確認した結果、`tools:` に Agent/Task を
   宣言している定義は**1件も存在しない**。ネストしたサブエージェント起動はこのリポジトリに前例がなく、
   分離度・レビュー可能性が未検証である。
   **（2026-08-08 スパイクによる更新・§4.9 Stage 1 手順3）** ネストしたサブエージェント起動そのものは
   **技術的に可能**であることを確認した（`tools: *` を持つ `general-purpose` から子エージェントを起動できた）。
   ただし `tools:` への **Agent の明示列挙**で当該ツールが付与されるかは未検証のまま残る
   （新規エージェント定義はセッション開始時にしか登録されず、同一セッションでは検証できないため）。
   本項の不採用根拠は「実現可否が未検証」から**「このリポジトリに前例がなく、分離度・レビュー可能性が
   未検証」**へ後退するが、下記2・3 は成立したままであり案Y の不採用は維持する。
2. エージェントが「自身の BFS 状態管理」と「子エージェントの並列制御」を同時に担うことになり、
   CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」の役割分離に逆行する。
3. `tools:` の拡張は最小権限方針と要調整。

案X は「決定的処理のスクリプト集約」「状態の単一書き手維持」という既存アーキテクチャ方針に整合する。
ただし案X は「BFS ループをサブエージェントに隔離する」という現行の設計方針を反転させるため、
オーケストレータのコンテキスト蓄積が新たなリスクとなる（§4.2 緩和策・§5 デグレードリスク）。

---

## 3. 変更対象ファイル（確定）

**段階列:** `S1` = Stage 1（計測＋既存不具合の是正＋再開経路統一・本プランの承認対象。**挙動不変ではない**）／
`S2` = Stage 2（並列化本体・実測後に再承認）。

| ファイル | 段階 | 変更種別 | 概要 |
|---|---|---|---|
| `ClaudeCode/.claude/skills/xddp.04.specout/scripts/specout_bfs.py` | S1 | 修正 | (c) `search` が分類開始時刻（`classify_started_at`・`classify_started_wave`）を state に記録＋各遷移で削除（§4.5(c) ライフサイクル表）、(d) `commit-wave` に `--chunk-count` / `--batch-count` / `--parallelism`（いずれも既定 1・挙動不変）を追加し `classify_wall_ms`・**`classify_wall_ms_reused`**・**`classify_wall_ms_suspect`**・`chunk_count`・`batch_count`・`parallelism` を metrics へ記録（§4.5(d)。suspect は閾値 1,800,000ms 超過で `true`／`classify_wall_ms` が `null` なら `null`、reused は classification ファイルの mtime による再利用機械判定）、(g) の `deferred_low` 適用（**discovery-log 生成より前**）と**コミット妥当性 fail-loud（3条件）**（§4.5(g)）。あわせて**モジュール docstring の `Usage:` の `commit-wave` 行**を3フラグ追加後の形へ更新する（Stage 1 で陳腐化するため。`search` 行・プロトコル手順の更新は S2 行が担当） |
| `ClaudeCode/.claude/skills/xddp.04.specout/scripts/tests/test_specout_bfs.py` | S1 | 修正 | **同一 state に対して `search` を2回連続実行しても `low_priority_frontier` が変化せず、`this_wave`・line_id・チャンク構成が完全一致する**（§4.5(g) の回帰検査。入れ替えが起きる波＝`this_wave` が空になるケースを含む）／**`commit-wave` が hits の `deferred_low` を `low_priority_frontier` へ適用し、キー欠損時は既存値を変更しない**／**`classify_wall_ms_suspect` が閾値超過で `true`・通常値で `false`** ／`classify_wall_ms` 記録／`classify_started_at`・`classify_started_wave` 欠損時の `null` フォールバック／**α＝開始時刻の波不一致（`classify_started_wave != wave`）時の `null`**（β＝hits の波不一致とは別物。α を再現するには state の `classify_started_wave` を直接書き換えてから `commit-wave` を実行する。β の入力では exit 非0 となり metrics 行が出ないため α のテストにはならない）／**`commit-wave` 後に2キーが state から削除される**／**波数上限の早期 return で2キーが書かれず既存値が削除される**／**`finish`・`re-discover`・`prune`・`set-state` の4経路で2キーが削除される**（§4.5(c) の二次防御）／**`merge-frontier`・`record-module` では削除されない**／**`import` が2キーを復元しない**／`chunk_count`・`batch_count`・`parallelism` の既定値1が記録される／既存 `classified` がゲート判定に使える値であることのテストを追加（§4.5(c) ライフサイクル表と1対1）。**あわせて以下を追加する:** (1) `classify_wall_ms_reused` — classification ファイルの mtime が `classify_started_at` より古い場合に `true` かつ `classify_wall_ms: null` になる（§4.5(d) 再利用波の判定）／(2) `classify_wall_ms` が `null` の波で `classify_wall_ms_suspect` が `false` ではなく `null` になる／(3) discovery-log の frontier 行 — `next_frontier` が空・`deferred_low` が非空の波で「探索終了」と書かれない、および入れ替えが起きた波（`deferred_low` が空）で「MODULE_PRIORITY_LOW 分へ移行」と書かれず complete と整合する（§4.5(g) の適用位置。現状この行は無防備）／(4) **β＝hits の波不一致**（`hits_payload["wave"] != data["current_wave"]`）の hits を渡すと `commit-wave` が exit 非0 になり、**state も discovery-log も変更されない**（§4.5(g) fail-loud）。**このテストは必ず「`wave_write_complete: false` かつ discovery-log に切り捨て対象となる `## Wave {n}` セクションが既に存在する」state を前提に組むこと** — `_truncate_wave_section` は実コードでは `if not data["wave_write_complete"]:` の下でのみ呼ばれるため、`wave_write_complete: true` の state で組むと**検証を truncate の後ろに置いた実装でも合格してしまい、位置をまったく検査できない**（偽陰性テストになる）／(5) **fail-loud 条件2:** **`state == "complete"` かつ `wave == current_wave > last_completed_wave` かつ `wave_write_complete: false`**（＝当該波の `search` 実行後に `finish` を実行した state）に当該波の hits を再投入すると exit 非0 になる。**この前提でテストを組むこと** — 「最終波コミット後の complete state」で組むと条件3 が先に成立し、**条件2 の実装欠落を検出できない**（最終波コミット後は `last_completed_wave = wave` かつ `wave_write_complete: true` となり条件3 も同時に成立するため）。**副次アサーションを置く場合は、それぞれ以下の前提を満たすこと（満たさないと条件2 の有無にかかわらず成立し、空振りする）:** ①「discovery-log の『## 継続パス C』が切り捨てられない」→ **discovery-log に当該波の書きかけ `## Wave {n}` セクションが存在し、その後ろに `finish` の「## 継続パス C」が追記されている** state を用意する（`## Wave {n}` が無いと `_truncate_wave_section` が早期 return して no-op になる）。**`## Wave {n}` は `search` では書かれず `commit-wave` のみが書くため、log fixture として直接用意するか、`commit-wave` のログ追記直後のクラッシュを模して作ること**（生成経路は §4.5(g) 役割分担表 条件2 行を参照）。②「frontier が復活しない」→ classification を **`propagation-direct` 等で `next_symbols` を非空にする**（または hits に非空の `deferred_low` を載せる）。伝播ゼロの入力では `data["frontier"] = next_frontier` が `[]` を代入するだけで、復活そのものが起こらない／(5-b) 最終波の hits 再投入で discovery-log の Wave セクションと metrics.jsonl の行が二重追記されない（**条件2・3 のいずれかが効いていれば成立する挙動テスト**であり、個々の条件の検査ではない。(5)(6) の代替にはならない）／(6) **fail-loud 条件3:** **`state != "complete"`（`set-state` 相当で `in-progress` に戻した状態）かつ `wave == current_wave == last_completed_wave` かつ `wave_write_complete: true`** の state に当該波の hits を再投入すると exit 非0 になる。**この前提でテストを組むこと** — 「complete 状態」で組むと条件2 が、「古い波の hits」で組むと条件1 が先に成立し、**条件3 の実装を丸ごと落としても緑になる**（(4) と同型の偽陰性テスト）。**さらに既存2テストを更新する（削除してはならない）: `test_2b_search_defers_unlisted_module_as_low_and_keeps_it` と `test_search_defers_low_priority_module` は、いずれも `commit-wave` を実行せず `search` 直後の `bfs-state.json` の `low_priority_frontier` を `assertIn` で検査しており (g) 適用後は必ず失敗する。検査対象を hits ファイルの `deferred_low` へ移し、「LOW 退避が起きること自体」の保証（Phase 2B の回帰検査）は維持すること（`test_2b_catalog_mode_unaffected_when_catalog_present` は `assertNotIn` のため更新不要）。** |
| `ClaudeCode/.claude/skills/xddp.04.specout/scripts/specout_bfs.py` | S1 | 修正 | (g) `cmd_search` の非破壊化 — `low_priority_frontier` の書き戻しを廃し、分割結果を `deferred_low` として hits へ載せ `commit-wave` が適用する。**再 `search` の冪等性を担保する既存不具合の是正**（§4.5(g)・§4.7）。基準線採取より前に適用すること |
| `ClaudeCode/.claude/agents/xddp-specout-agent.md` | S1 | 修正 | 「### Step 2: BFS ループ」の**「クラッシュ再開:」ブロック**を **§4.7.1** の Before/After のとおり改訂する（現行は `search` を飛ばす経路を明示規定しており、これが残ると Stage 1 の `classify_wall_ms` が人の待ち時間で汚染される。§4.7 の経路統一は Stage 1 の時点で成立させる必要がある）。**あわせて「### Wave 0 完了後: モジュールカタログによる BFS 優先度設定」節の LOW 退避の説明を §4.7.1 (3) の Before/After のとおり更新する**（現行は「`search` 実行時、MODULE_PRIORITY_LOW に属する frontier シンボルは自動的に `low_priority_frontier` へ退避され」と書いているが、§4.5(g) 適用後は「`search` が退避対象を判定し `commit-wave` が state へ反映する」となり、`search` 直後の `bfs-state.json`・`checkpoint.md` には退避が現れない。§4.7 の再開手順は人が state を確認する運用を前提とするため、退避漏れと誤認されないよう是正する。docstring `Usage:` 行と同じ陳腐化対策の基準を適用する） |
| `ClaudeCode/.claude/skills/xddp.04.specout/recovery-procedures.md` | S1 | 修正 | **再開経路を「`search` から再開する」の1本に統一する規定**を **§4.7.1** の Before/After のとおり追加する（S2 のループ移設に伴う文言改訂とは別に、Stage 1 の計測品質のため前倒しする）。**Stage 1 時点ではチャンク・`merge_classification.py` が存在しないため、§4.7【S1】の手順のみを書き、S2 成果物を参照しない** |
| （一時追加）`ClaudeCode/.claude/agents/_spike-agent-tool.md` | S1 | 追加→**削除** | 案Y（Agent/Task ツールを持つエージェント）の実現可否スパイク用の使い捨て定義。検証後に削除しコミットしない（§4.9 Stage 1 手順3） |
| `ClaudeCode/.claude/skills/xddp.04.specout/scripts/specout_bfs.py` | S2 | 修正 | (a) `search` が `known_symbols`（素名正規化済み）を hits へ出力、(b) `search --hits-dir` ＋ `--chunk-size` でチャンクファイルを決定的に分割出力、(e) `commit-wave --unsupported-patterns` で grep未対応パターンを単一書き手として discovery-log へ追記、(f) `status --brief` で state 全体ではなく判定に必要な最小キーのみを出力（§4.5）。あわせて**モジュール docstring の「LLM とのプロトコル」手順2〜5 および `Usage:` 節の `search` 行**（現行は `search --path STATE_JSON --hits-out HITS_JSON`）を、SKILL 側ループ・チャンク分割・`--hits-dir` の構成へ更新する（この docstring は `ArgumentParser(description=__doc__)` 経由で `--help` 出力となり、**人が読む契約情報**になるため陳腐化させない。ただし `specout_bfs.py` は `add_subparsers` を持ち、検査Dのフラグ照合は `sub_flags`＝`specout_bfs.py {sub} --help` の出力で行われる（各 `add_parser` に description を渡していないためモジュール docstring は含まれない）。したがって **docstring の陳腐化は `make test` では検出されず、手動更新が必要**である — 検査Dへ寄与するのは `top()` によるサブコマンド名抽出のみ） |
| `ClaudeCode/.claude/skills/xddp.04.specout/SKILL.md` | S2 | 修正 | Step A の波ループをオーケストレータ側に再設計（§4.2）。CR Resolution 受領キー列挙行への設定キー2種の追記、状態テーブルの「Discovery エージェントを再起動する」→「SKILL 側の波ループを再開する」改訂、`in-progress` + RE_DISCOVER=true 分岐と Discovery 完了後の paused 判定節の改訂、**Step A 入口の `specout_bfs.py status --path ...` 呼び出しを `status --brief` へ変更**（§4.5(f) を新設する動機そのもの。ここを変えないとコンテキスト蓄積対策が空振りする） |
| `tools/harness/refcheck.py` | S2 | 修正 | `DETERMINISTIC_SCRIPTS` に `merge_classification.py` を追加する（下記「変更不要と判断したファイル」の検査B/D の区別を参照） |
| `ClaudeCode/.claude/agents/xddp-specout-agent.md` | S2 | 修正 | `MODE: discovery` を `MODE: discovery-setup` に再定義（Wave 0 構築・`init` 実行・code-knowledge 参照まで。BFS ループは持たない）。判定ルール一式を classifier へ移設。判定手順2の「Agent ツールの並列呼び出し」記述を削除（frontmatter と矛盾。ボーイスカウトルール）。`MODE: document` は不変（§4.3）。code-knowledge 参照は `discovery-setup` の外へ**移設せず、`init` 実行の後段に置く**（成果物へ到達しない既存欠陥は §4.3 に記録し別プランで対応） |
| （新規）`ClaudeCode/.claude/agents/xddp-specout-classifier-agent.md` | S2 | 追加 | チャンクファイル1件を読み、classification JSON を書き出す軽量エージェント。`tools: Read / Grep / Write`（§4.4） |
| （新規）`ClaudeCode/.claude/skills/xddp.04.specout/scripts/merge_classification.py` | S2 | 追加 | チャンク classification の結合・line_id 欠落/重複/未知値の検出（`commit-wave` 前段で明示エラー）・`unsupported_patterns` 集約・チャンク `OUT_FILE` の **mtime 収集**（`chunk_mtimes`。実効並列度の裏付け）・**欠落チャンク（classifier が `OUT_FILE` を書かなかった分）の特定と `exit 1`**（§4.6）。引数は `--hits` / **`--hits-chunks`（ヒットチャンク群）** / **`--chunks`（classifier 出力群）** / `--out` / `--unsupported-out` |
| （新規）`ClaudeCode/.claude/skills/xddp.04.specout/scripts/tests/test_merge_classification.py` | S2 | 追加 | 結合・欠落・重複・未知値・空チャンク・**`chunk_mtimes` の出力（mtime 取得不可でもエラーにしない）**・**`--chunks` の指定ファイルが存在しない場合に traceback ではなく欠落 `chunk_id`／期待パス一覧＋`exit 1`**（§4.6 処理8）の単体テスト |
| `ClaudeCode/.claude/skills/xddp.04.specout/scripts/tests/test_specout_bfs.py` | S2 | 修正 | `known_symbols` の素名正規化・チャンク分割の網羅性（全 line_id がちょうど1チャンク・非分割時も1件返る）・ファイル単位グルーピング・`--unsupported-patterns` 追記のテストを追加 |
| `ClaudeCode/.claude/skills/xddp.04.specout/recovery-procedures.md` | S2 | 修正 | 「Discovery エージェントを呼び出す／再起動する」前提の記述を「SKILL 側の波ループを再開する」に改訂（Re-discover Processing 手順3・Paused-at-limit Handling 選択肢A の案内）。あわせて **Stage 1 で追加した「## Wave 途中失敗からの再開（経路統一）」セクション（§4.7.1 (2)）を、§4.7【S2】の手順**（チャンク単位の再利用・`merge_classification.py` による一致判定）**へ差し替える**（経路統一そのものは Stage 1 で成立済み。ここでは S2 成果物に合わせて手順の中身を更新する）。**この差し替えでは、Stage 1 が持ち込んだ手順1 の `status`（state 全体出力）を `status --brief`（§4.5(f)）へ置き換えるか、`search --hits-dir`（§4.5(b)）により波番号の事前取得が不要になるため当該行を削除する** — §6 Stage 2 の確認項目「`recovery-procedures.md` 側に state 全体を出す `status` 呼び出しが残っていないこと」と1対1で対応する |
| `ClaudeCode/.claude/skills/xddp.common/SKILL.md`（`## Load Config`） | S2 | 修正 | `SPECOUT_CLASSIFY_CHUNK_SIZE`（既定 `40`）・`SPECOUT_CLASSIFY_PARALLEL`（既定 `4`）を Output 一覧と Process 手順2へ追加（配線の前例は `SPECOUT_BACKEND`） |
| `ClaudeCode/.claude/skills/xddp.01.init/templates/xddp.config.md` | S2 | 修正 | 上記2キーを `SPECOUT_HIT_FILTER` の隣接位置に追加（既定値・効果・`0` 指定時の挙動を記載） |
| `docs/specout-discovery-guide.md` | S2 | 修正 | 「分離単位」表の「リポジトリ＝独立 Agent コンテキスト」記述と BFS ループの実行主体の説明を、SKILL 側ループ＋ chunk 単位 classifier の構成に更新 |
| `docs/adr/ADR-0010-specout-parallel-classification.md` | S2 | 追加 | 親プランで採番済み。ループ移設・案X採用理由・`known_symbols` による等価性確保・単一書き手維持・コンテキスト蓄積リスクの設計判断を記録 |
| `docs/adr/README.md` | S2 | 修正 | ADR 索引テーブルに ADR-0010 の行を追加（同ファイル末尾に「新規 ADR を追加する場合は連番を1つ進め、本表に追記すること」と明記されているため必須） |
| `CLAUDE.md` | S2 | 修正 | ファイル構成テーブル（`merge_classification.py`・classifier エージェント）、「xddp.config.md の位置付け」節に新設定キー2種 |
| `README.md` | S2 | 修正 | 「## サブエージェント一覧」表への classifier 1件の追記と、工程4a の説明更新に**限定する**（本プランの目的に直接由来する変更のみ） |
| `tools/harness/smoke_config.md` | S2 | 修正 | 「## 工程別実行モデル」表の**工程04 の実測 $/起動**を並列 classifier 込みの値へ更新し、その合計から導出されるグローバル `SMOKE_TOKEN_BUDGET`（現行 `30.0`。工程別の予算上限は存在しない）を再算定する（校正ラン後に確定値を記入） |

**`refcheck.py` の検査B／検査D の区別（上表の `refcheck.py` 行の根拠）:**
- **検査B（サブエージェント契約・改修不要）:** `check_b_subagents` は `agents_dir / "{name}.md"` で
  **自動解決**するため、新規エージェント定義を置くだけで照合対象になる。なお検査Bは
  (1) `subagent_type=` 行**直後の定型 pass ブロック**を解析し、(2) 呼び出し側が渡すキーが
  エージェント定義本文に現れない場合に warning を出す。したがって §4.2 の pass ブロック書式と
  §4.4 の Inputs 節を一致させること。
- **検査D（スキル↔決定的スクリプト結線・要改修）:** `check_d_script_wiring` は
  `_extract_script_calls(lines, deterministic_scripts)` により、モジュール定数
  `DETERMINISTIC_SCRIPTS`（`specout_bfs.py` / `specout_verify_counts.py` / `chd_sp_coverage.py` /
  `artifact_lint.py` / `xddp_gate_snapshot.py` / `xddp_progress.py` / `xddp_review_brief.py` の
  **ハードコード集合**）に載っているスクリプトの呼び出ししか抽出しない。新規追加する
  `merge_classification.py` をこの集合に加えない限り、SKILL.md が書く
  `merge_classification.py --hits … --chunks … --out … --unsupported-out …` のフラグ誤記・引数契約ずれは
  `make test` で violation も warning も出ず**サイレントに素通り**する。本プランは「決定的処理はスクリプト」
  方針に沿って新規スクリプトを1本増やす変更であり、その結線検査を落とすことは CLAUDE.md
  「ツール修正後のハーネス実行（必須）」の趣旨に反するため、**`DETERMINISTIC_SCRIPTS` への追加を S2 の
  変更対象に含める**（上表参照）。
  **ただし登録は必要条件であって十分条件ではない。** 検査Dの有効フラグ集合は、サブコマンドを持つ
  スクリプト（`specout_bfs.py`）では `sub_flags`（`script sub --help`）だが、**サブコマンドを持たない
  スクリプト（`merge_classification.py`）では `top()["flags"]` ＝ `script --help` の全出力**であり、
  `ArgumentParser(description=__doc__)` を使うとモジュール docstring 中のフラグ表記まで有効扱いになる。
  登録と併せて §4.6 の実装制約（docstring にフラグを列挙しない）を満たさない限り、
  docstring と argparse の乖離は検出されない。

**変更不要と判断したファイル（根拠付き）:**
- `tools/harness/run_all.py`: `skills.rglob("scripts/tests")` でテストディレクトリを**自動探索**するため、
  `tests/test_merge_classification.py` を置くだけで `make test` の対象になる。改修不要。
- `ClaudeCode/setup.sh`: `find "$SRC" -type f` で全ファイルを走査するため、新規エージェント定義・
  新規スクリプトは追加設定なしでデプロイされる。改修不要。
- `tools/harness/smoke_full.py`: `PHASE_LABELS` に `04`、`MULTI_PHASES` に `04` が既に含まれており、
  工程04 の single / multi いずれのスモークも既存定義で実行できる。改修不要
  （`smoke_config.md` の**数値の再算定**は別途必要 — 上表参照）。

---

## 4. 変更内容

### 4.1 等価性設計 — `known_symbols` と `CRS_FILE` の明示配布（最重要）

**問題:** §1 のとおり、分類は (i) `f ∈ visited ∪ 前波frontier ∪ current-wave-hits` の判定と、
(ii) CRS が定義する変更スコープの理解、の2つを今波・CRS 文脈に依存して行う。
チャンク分割すると (i) は一部しか見えず、(ii) は別コンテキストへ移るため失われる。

**方針:**
- (i) の集合は**すべて `specout_bfs.py` が決定的に算出できる**。`search` の出力に明示フィールドとして
  持たせ、**全チャンクへ同一内容を複製配布**する。
- (ii) は classifier の Inputs に `CRS_FILE` を渡して回復する（§4.4）。

**変更前（`cmd_search` の `hits_payload`）:**
```python
hits_payload = {
    "wave": wave,
    "commands": commands,
    "hits": hits,
    "frontier_medium_scopes": frontier_medium_scopes,
    "searched_frontier": this_wave,
    "metrics": metrics,
    "filtered_out": filtered_out,
    "pre_noisy": sorted(pre_noisy),
    "module_files": module_files,
}
```

**変更後:**
```python
hits_payload = {
    ...（既存キーはすべて不変）...
    # PLAN-20260806 Phase 3: チャンク並列分類で判定入力が狭まらないよう、
    # 「戻り値代入/ジェネレータ受信」ルールの参照集合を明示配布する。
    # visited / this_wave の要素は `paramName[MEDIUM:{path}]` 形式を含むため、
    # _parse_entry で素のシンボル名へ正規化してから格納する（素名で照合するため）。
    "known_symbols": {
        "visited":            sorted({_parse_entry(e)[0] for e in data["visited"]}),
        "searched_frontier":  sorted({_parse_entry(e)[0] for e in this_wave}),
        # `current_wave` は `searched_frontier` の部分集合（下記「冗長性の記録」参照）。
        # 判定入力を増やさないが、判定ルールの原文「current-wave-hits」との対応を保つため明示する。
        "current_wave":       sorted({h["symbol"] for h in hits}),
    },
}
```

**冗長性の記録（`current_wave ⊆ searched_frontier` の証明）:** `hits` の各要素の `symbol` は
`_matching_symbol(content, sc.candidates)` の戻り値であり、戻り値は必ず `sc.candidates` の要素
（一致なしの場合も `candidates[0]`）である。`sc.candidates` はその波で検索したシンボル群、すなわち
`this_wave` のエントリから導出される素名の集合である。したがって
`current_wave ⊆ {_parse_entry(e)[0] for e in this_wave} = searched_frontier` が常に成り立つ。
**`current_wave` を削除しても不変条件1（判定入力が狭まらない）は破れない**が、判定ルール原文の
「current-wave-hits」という語との対応が読み取れなくなるため、本プランでは**明示のまま残す**。
トークン削減が必要になった場合は、この証明を根拠に削除してよい（削除は等価変換である）。

**理由:** 分類側の判定条件を「この3配列の**和集合**に f が含まれるか」という決定的な参照に置き換える。
素名への正規化が必須なのは、`visited` と `this_wave` の要素が
`paramName[MEDIUM:{定義ファイルパス}]` 形式を含むためである（`cmd_commit_wave` の
`high_visited = {e for e in visited if _parse_entry(e)[1] is None}` および
`xddp-specout-agent.md` 判定手順3 の `"paramName[MEDIUM:...]"` 生成規則で確認）。
正規化しないと classifier が照合する素の `f` と文字列一致せず、MEDIUM 由来のエントリが判定に効かない。
（`h["symbol"]` は既に素名のため `current_wave` は正規化不要。）

**不変条件（本プランの correctness 定義）:**
1. チャンク分割によって、各行の判定入力が単一コンテキスト時より**狭まらない**。
   検証対象は `known_symbols`（素名で照合できること）と `CRS_FILE`（スコープ判断の文脈）の両方。
2. `commit-wave` の入力契約（全 line_id 被覆・`CLASS_VALUES` 列挙）は**不変**。
3. 同一 hits・同一 classification に対する `commit-wave` の出力（確定影響ファイル集合・`next_frontier`・
   ケースA分岐）は**バイト等価**（＝スクリプト側は無変更のため自明。fixture で固定する）。

> LLM 出力そのものの完全一致は非決定的で保証できない。検証は §6 のとおり
> 「決定的層＝統合ヘルパと commit-wave の単体テスト」「意味層＝smoke-full の下流結果一致」の2層に分ける。

### 4.2 波ループの移設（SKILL.md Step A）

**変更前（「**Discovery エージェント呼び出し:**」節）:**
```
IS_MULTI = true の場合: Agent ツールで各リポジトリの Discovery を並列呼び出しする
...
Use the **Agent tool** with `subagent_type=xddp-specout-agent` and pass:
MODE: discovery
...
Discovery エージェント完了後、`specout_bfs.py status --path ...` で状態を確認する。
```

**変更後（骨子）— 「全 repo 同期の波」でリポジトリ間並列を維持する:**
```
1. Setup: AFFECTED_REPOS のうち **`{CR_PATH}/04_specout/{repo}/bfs-state.json` が存在しない repo のみ**を
   対象に、Agent tool `subagent_type=xddp-specout-agent` / `MODE: discovery-setup` を
   （IS_MULTI なら並列で）起動する。Wave 0 シンボル構築・init 実行・code-knowledge 参照まで。
   **state が既に存在する repo は setup をスキップし、そのまま step 2 の波ループへ入る**
   （`specout_bfs.py init` は state 既存時に「bfs-state.json が既に存在します（re-discover か import を
   使用してください）」で異常終了するため、無条件起動すると再開経路でループが停止する。
   同§の状態テーブル `in-progress` 行の改訂内容と一致させること）。

2. Let ACTIVE_REPOS = **state が `in-progress` の repo の集合**。
   `paused-at-limit` / `paused-at-limit-2nd` の repo は**波ループに入れてはならない** —
   `cmd_search` は冒頭で `data["state"] in ("paused-at-limit", "paused-at-limit-2nd")` を検出すると
   `_err`（「prune / finish で継続パスを選択してから search してください」）で異常終了するため、
   「complete でない repo」という広い定義で実装すると再開時に step a でいきなり停止する
   （`paused` フラグ付き JSON が返るのは `current_wave > max_wave_depth` を**新たに踏んだ**場合だけであり、
   既に paused 状態で開始した repo には返らない）。paused 系は**波ループに入る前に** Step A の状態テーブルで
   `recovery-procedures.md` へ振り分け、継続パス選択の結果 `in-progress` に戻った repo のみを
   ACTIVE_REPOS に含める（現行 SKILL Step A が Discovery 呼び出し前に行っている振り分けと同じ前段を維持する）。
   波ループ（ACTIVE_REPOS が空になるまで繰り返す。各周回が「1波」に相当する）:
   a. ACTIVE_REPOS の各 repo について Bash:
        specout_bfs.py search --path {CR_PATH}/04_specout/{repo}/bfs-state.json \
          --hits-dir {CR_PATH}/04_specout/{repo}/ \
          --chunk-size {SPECOUT_CLASSIFY_CHUNK_SIZE}
      （`--hits-dir` はスクリプトが state の `current_wave` から `wave-{N}-hits.json` を組み立てる。
      SKILL 側が **`search` を呼ぶ前に**波番号 {N} を知る必要がなくなり、毎波 `status` を呼ぶ必要もない
      ＝§4.5(f) と併せてメインコンテキストへの state 全体流入を避ける。
      **`search` 実行後の波番号は stdout の既存キー `"wave"` から取得**し、step c/d の出力パス組み立てに使う）
      → `paused` が true の repo は状態に応じて recovery-procedures.md を適用し ACTIVE_REPOS から外す
      → `search` が exit 非0 の repo（`cmd_search` は `frontier が空です`・paused 状態での呼び出し・
        バックエンド不整合等でも `_err` する）は、**stderr を表示したうえでその repo のみを
        ACTIVE_REPOS から外し**、同じ波の他 repo は step b 以降を続行する（step c・step d と同一の停止粒度。
        波ループ全体を止めると、他 repo が巻き添えで停止する）。step a の失敗は当該波が未コミットであり
        state は前波の確定状態のままのため、原因を除去したうえで**そのまま再開して安全である**。
        波ループ終了後に失敗 repo の一覧と stderr を人へ提示する
      → stdout の `hits_file`（実パス）と `chunks`（＝**ヒットチャンク** `wave-{N}-hits-chunk-{K}.json` の
        パス配列。必ず1件以上）を repo ごとに保持する。以降これを **`HITS_CHUNKS`** と呼ぶ
        （step b の `CHUNK_FILE` の供給元。step c で `merge_classification.py --chunks` へ渡す
        **classification 側のファイル群とは別物**であり、混同すると分類結果が1件も読まれない）
   b. **全 ACTIVE_REPOS のチャンク（`HITS_CHUNKS`）を合算**し、classifier を並列起動する
      （同時起動数の上限は {SPECOUT_CLASSIFY_PARALLEL}。超える分は上限件数ずつバッチに分けて起動する。
      リポジトリをまたいでも合算するため、マルチリポジトリ時もリポジトリ間の並列度が失われない）。
      **充填順序を規定する: チャンクは repo 単位で連続するように**（ACTIVE_REPOS の順に、各 repo の
      chunk-0 から昇順に）合算列を作り、その先頭から `{SPECOUT_CLASSIFY_PARALLEL}` 件ずつバッチへ詰める。
      ラウンドロビン的に repo を交互に詰めてはならない（§4.5(d) の判定式
      `ceil(chunk_count/parallelism) + 1` は「当該 repo のチャンクがバッチ列上で連続する」ことを
      前提に成立するため。交互充填では当該 repo が最大 `chunk_count` 個のバッチに分散し、
      並列起動されているのに「逐次」と誤判定する偽陰性が生じる）。
      各 classifier には `CHUNK_FILE` として `HITS_CHUNKS` の1件を、`OUT_FILE` として
      `wave-{N}-chunk-{K}-class.json`（`{K}` は `CHUNK_FILE` と同一）を渡す（§4.4）。
      この `OUT_FILE` の集合を repo ごとに **`CLASS_CHUNKS`** として保持し、step c で使う。
      各バッチの起動直前・完了直後に Bash で `date +%s` を取り、
      `{CR_PATH}/04_specout/{repo}/wave-{N}-batches.json` へ §4.5(d) 記載のスキーマ
      （`batch_index` / `chunk_files` / `started_at` / `ended_at`）で記録する（実効並列度の観測）。

      **プロンプトキャッシュ有効化のための設計要件（実測根拠:
      [PLAN-20260806-specout-phase3-stage1-measurement.md](PLAN-20260806-specout-phase3-stage1-measurement.md) §5.5・§5.6）:**
      各 classifier の起動プロンプトは、**チャンク固有情報（`CHUNK_FILE`・`OUT_FILE`・`chunk_id`）を末尾に置き、
      先頭側（分類ルール・判定手順・`CRS_FILE` に関する指示文）を全チャンクでバイト単位に同一に保つ**こと
      （§4.4 Inputs 節の記載順ではなく、実際に組み立てる起動プロンプト文字列の順序に対する要件である）。
      兄弟サブエージェント間でプロンプトキャッシュが共有されるのは**プレフィクスがバイト同一の場合のみ**であり
      （計測実測 §5.6）、チャンク固有情報が先頭側に混ざるとキャッシュが個体ごとに分離し、
      固定ブートストラップ（サブエージェント1体あたり実測 ≈33,000〜49,000 トークン。§4.9.1(c)）が
      `chunk_count` 倍そのまま複製される。
      **波の最初のバッチは、チャンク0を単独で起動してキャッシュ書き込みを完了させてから
      残りのチャンクを並列起動する**（またはバッチ内の起動タイミングを2〜3秒ずらす）。
      これはコールドスタート時の競合窓（計測実測: 約1〜2.5秒。プレフィクス書き込みが完了する前に
      発行された2体目以降が同じプレフィクスを再度書いてしまう）への対策であり、対策しない場合のコストは
      「CR あたり数体分の余分なプレフィクス書き込み」に留まる（キャッシュは波をまたいで有効なため、
      ミスが起きうるのは CR 最初の1バッチのみ）。
   c. repo ごとに Bash（パスは step a の `hits_file` から導出する）:
        merge_classification.py --hits {hits_file} \
          --hits-chunks {HITS_CHUNKS} --chunks {CLASS_CHUNKS} \
          --out .../wave-{N}-class.json --unsupported-out .../wave-{N}-unsupported.json
      （**`--chunks` は classifier が書いた `OUT_FILE` 群＝`CLASS_CHUNKS`**、
      `--hits-chunks` は `search` が出力したヒットチャンク群＝`HITS_CHUNKS`。
      両者を取り違えるとフラグ名は一致するため `refcheck.py` 検査Dでも `make test` でも検出されない）
      → stdout の `min_chunk_mtime` を保持する（非 `null` なら step d へ `--chunk-mtime-min` として渡す。
      §4.5(d)「判定方法〔S2〕」）。
      → 欠落・重複・未知値があればスクリプトが exit 1。**停止粒度は repo 単位とする**:
        stderr を表示したうえで、**失敗した repo のみを ACTIVE_REPOS から外し**、同じ波の他 repo は
        step d（`commit-wave`）まで完了させる。波ループ終了後に、失敗した repo の一覧と stderr を人へ提示する。
        失敗 repo の state は `wave_write_complete=false` のまま残るため、§4.7 の再開手順
        （既存チャンク結果の再利用＋欠落チャンクのみ再投入）にそのまま接続できる
        （波ループ全体を即時停止すると、成功していた他 repo の分類結果が commit されず捨てられる）
   d. repo ごとに Bash:
        specout_bfs.py commit-wave --path ... --hits ... --classification ... \
          --unsupported-patterns .../wave-{N}-unsupported.json \
          --chunk-count {その repo のチャンク数} --batch-count {実バッチ数} \
          --parallelism {SPECOUT_CLASSIFY_PARALLEL} \
          [--chunk-mtime-min {step c で得た値。非 null の場合のみ渡す}] --today {TODAY}
      （`--chunk-mtime-min` は §4.5(d)「判定方法〔S2〕」の再利用波検出に使う。step c の `min_chunk_mtime` が
      `null` の場合はフラグ自体を渡さない＝`commit-wave` は `--classification` の OS mtime へフォールバックする）
      → stdout の `state` が complete になった repo を ACTIVE_REPOS から外す
      → `commit-wave` が exit 非0 の repo（§4.5(g) の fail-loud・スキーマ検証等）は、
        **stderr を表示したうえでその repo のみを ACTIVE_REPOS から外し**、同じ波の他 repo は
        step d まで完了させる（step a・step c と同一の停止粒度）。失敗 repo の state は
        `wave_write_complete=false` のまま残るため、§4.7 の再開手順にそのまま接続できる。
        波ループ終了後に失敗 repo の一覧と stderr を人へ提示する
   e. ACTIVE_REPOS が空でなければ a に戻る（波番号は repo ごとに独立して進む）
```

**classifier の pass ブロック（`refcheck.py` 検査B の照合対象。§4.4 の Inputs と1対1）:**

**書式要件（必須）:** `refcheck.py` 検査Bの `_parse_payload_keys` は「`subagent_type=` を含む行から
**4行以内にコードフェンスが開始**し、キーはそのフェンス**内**にある」形式のみを解析する。
フェンスが見つからない場合は「pass ブロックが定型でなく契約照合をスキップ（best-effort）」の warning となり、
**契約照合そのものが無効化される**（＝§6 の「pass ブロックと Inputs 節が1対1」「検査Bが緑」が空振りする）。
したがって SKILL.md へ転記する際は、既存の `xddp-specout-agent` 呼び出しと同じく
**「Use the Agent tool …」の説明行をフェンスの外に置き、次行からフェンスを開始する**こと。
以下は転記後の SKILL.md 上の最終形（この体裁のまま転記する）:

Use the **Agent tool** with `subagent_type=xddp-specout-classifier-agent` and pass:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
CHUNK_FILE: {CR_PATH}/04_specout/{repo}/wave-{N}-hits-chunk-{K}.json
OUT_FILE: {CR_PATH}/04_specout/{repo}/wave-{N}-chunk-{K}-class.json
EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}
INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS}
```

**状態テーブル・関連分岐の改訂（同 SKILL の Step A）:**

| 箇所 | 変更前 | 変更後 |
|---|---|---|
| 状態テーブル `in-progress` / false | 「Discovery エージェントが中断している。Discovery エージェントを再起動する（Visited/Frontier は bfs-state.json から自動復元されるため、追加の引数は不要）」 | 「波ループが中断している。`discovery-setup` はスキップし、SKILL 側の波ループを `search` から再開する（Visited/Frontier は bfs-state.json から自動復元されるため、追加の引数は不要）」 |
| 状態テーブル `in-progress` / true | 「`specout_bfs.py merge-frontier` で ENTRY_POINTS を既存 Frontier にマージ（HIGH 平文形式で追記）してから Discovery エージェントを再起動する」 | 「`specout_bfs.py merge-frontier` で ENTRY_POINTS を既存 Frontier にマージ（HIGH 平文形式で追記）してから SKILL 側の波ループを再開する」 |
| `in-progress` + RE_DISCOVER=true の手順末尾 | 「その後 Discovery エージェントを再起動する（下記「Discovery エージェント呼び出し」を参照）」 | 「その後 SKILL 側の波ループを再開する（下記「波ループ」を参照）」 |
| 状態テーブル `paused-at-limit` / `paused-at-limit-2nd` の各行 | （現行の recovery-procedures.md への振り分け） | **不変。ただし「振り分けは波ループに入る前に行い、継続パス選択の結果 `in-progress` に戻った repo のみを ACTIVE_REPOS に含める」ことを明記する**（`cmd_search` は paused 状態で `_err` するため。§4.2 step 2 参照） |
| Discovery 呼び出し節の直後 | 「Discovery エージェント完了後、`specout_bfs.py status ...` で状態を確認する。状態が "paused-at-limit" の場合は …」 | 「波ループが `paused` を返した repo について、`recovery-procedures.md` の該当ハンドリングを適用する（判定は波ループ内 step a で行う）。全 repo が complete になったら Document フェーズへ進む」 |

**recovery-procedures.md の改訂（該当3箇所）:**

| 箇所 | 変更前 | 変更後 |
|---|---|---|
| `## Re-discover Processing` 手順3 | 「Discovery エージェントを通常通り呼び出す（エージェントは `in-progress` として再開ロジックを実行し、次波から BFS を継続する）。」 | 「SKILL 側の波ループを通常通り開始する（状態が `in-progress` のため `discovery-setup` はスキップされ、次波から BFS を継続する）。」 |
| `## Paused-at-limit Handling` 選択肢A の案内文 | 「その後 `/xddp.04.specout {CR}` を再実行すると、スキルが自動で Discovery を再起動します。」 | 「その後 `/xddp.04.specout {CR}` を再実行すると、スキルが自動で波ループを再開します。」 |
| `## Paused-at-limit Handling` 選択肢A 手順2 | 「`/xddp.04.specout {CR}` の再実行を案内する（状態は `in-progress` に書き戻されているため、再実行時にスキルが自動で Discovery を再起動する）。」 | 「`/xddp.04.specout {CR}` の再実行を案内する（状態は `in-progress` に書き戻されているため、再実行時にスキルが自動で波ループを再開する）。」 |

**理由:** 現エージェントは Agent ツールを持たないため、並列起動の主体は Agent ツールを保持する
オーケストレータ（SKILL）でなければならない。決定的処理（search / チャンク分割 / 統合検証 / commit-wave）は
すべて Bash 経由のスクリプト呼び出しのまま維持する。step b で全 repo のチャンクを合算するのは、
現行の「リポジトリ間並列」（`docs/specout-discovery-guide.md`「分離単位」表）を失わないためである。

**コンテキスト蓄積の緩和策（メインコンテキストの枯渇対策）:**
- `search` / `commit-wave` の stdout は**必要キーのみ**を読む（`paused`・`hits_file`・`chunks`・`state`・
  `next_frontier_count`。件数・metrics の詳細はファイルに残し、メインには載せない）。
- 波ループ内で `status` を呼ばない。波番号は `search --hits-dir` がスクリプト側で解決する。
  Step A 入口など `status` が必要な箇所では `status --brief`（§4.5(f)）を使う
  （現行の `cmd_status` は `print(json.dumps({"ok": True, **data}))` で bfs-state.json 全体
  ＝ `visited`・`confirmed_files`・`classified_locations` 等の単調増加フィールドを stdout に出すため、
  波ごとに呼ぶとコンテキスト蓄積の主因になる）。
- 波ごとの詳細（hits・classification・チャンク）は**すべてファイル**に置き、メインは**パスのみ**を保持する。
- Stage 1 の計測で「波数 × リポジトリ数」の実測分布を採取し、蓄積が許容量を超える見込みの場合は
  Stage 2 の設計を「repo ごとの wave driver を別サブエージェントに切る」構成へ見直す
  （その場合 wave driver には Agent ツールが必要となり案Y の検証が前提になる）。

> **補足:** 一時停止・再開の分岐は「現行はエージェント内のみ」ではなく、
> **エージェント内と SKILL Step A の両方**に存在する（SKILL 側は Discovery エージェント完了後の
> `status` 判定でも paused を処理している）。本変更でエージェント側の分岐が消え、SKILL 側に一本化される。

### 4.3 既存エージェントの再定義（xddp-specout-agent.md）

**変更前:** `MODE: "discovery" | "document"`。discovery は Step 1（Wave 0 構築）→ Step 2（BFS ループ全体）→ Step 3。

**変更後:** `MODE: "discovery-setup" | "document"`。

| 現行 discovery の責務 | 移設先 |
|---|---|
| Step 2 冒頭の「**開始**（bfs-state.json が存在しない場合）／**再開**（既に存在する場合）」分岐 | **SKILL**（§4.2 step 1 の起動条件へ移設）。`discovery-setup` は「state が存在しない repo」に対してのみ起動されるため、エージェント側の再入判定は不要になる（`discovery-setup` は state 不在を前提とした一本道になる） |
| Step 1: Wave 0 シンボル構築（CRS 識別子抽出・インスタンス属性パターン・サブクラス/実装クラス grep・re-export 検索・grep未対応パターンの事前記録） | `discovery-setup`（既存エージェントに残置。LLM の意味判定が必要なため） |
| discovery-log 初期化（**現行はエージェント「### Step 1: Wave 0 シンボルの構築」の項目6**：テンプレート `04_specout-discovery-log-template.md` から探索設定・grep未対応パターンセクションを記入）＋`init` 実行（**現行は Step 2「開始（bfs-state.json が存在しない場合）」ブロック**。両者は別ステップにある） | `discovery-setup`（一本道へ再編。state 不在が前提のため「開始」条件判定は不要）。**実行順を明示する: Step 1 項目1〜5（シンボル構築）→ 項目6（discovery-log 初期化）→ `init`（`--module-catalog` を含む全フラグを渡す）→ code-knowledge 参照。** モジュールカタログ優先度設定は独立した実行ステップではない（`init` に `--module-catalog` を渡すだけでよく、優先度算出は Wave 0 の `commit-wave` 時にスクリプトが行う）。 `cmd_init` の discovery-log ヘッダ生成は `if not log_path.exists():` ガード下にあるため、項目6 が先に走ればヘッダはテンプレート由来のものが採用され `init` 側は skip される（現行と同じ結果）。この順序を規定しないと実装者の解釈次第でヘッダの生成元が変わるため、仕様として固定する。なお両者の見出し `## grep未対応パターン（手動確認必要）` と3列構成は一致しており、§4.5(e) のセクション内挿入ヘルパはどちらの経路でも破綻しない |
| Wave 0 完了後: モジュールカタログ優先度設定 | 責務は不変（`init --module-catalog` に渡すのみ。スクリプトが実施）。**ただし §4.5(g) に伴い当該節の LOW 退避の説明文を S1 で改訂する**（§4.7.1 (3)・§3 参照） |
| Wave 0 完了後: code-knowledge 参照（constraints.md 読込・`_observation-memo.md`「## 既知制約との照合」生成） | `discovery-setup`（**`init` 実行の後段に置く**。`discovery-setup` の外へは移設しない。位置と no-op 性の詳細は下記「スコープ外として記録する既存欠陥」参照） |
| Step 2 a: `search` 実行 | **SKILL**（Bash） |
| Step 2 b: hits の意味判定（判定手順1〜4・伝播種別表） | **classifier エージェント**（逐語移設） |
| 判定中の Read による `enclosing_function` 特定 | **classifier**（`tools:` に Read が必要な理由） |
| grep未対応パターンの discovery-log への Edit 追記 | **classifier が返却 JSON で報告 → `commit-wave` が単一書き手として追記**（§4.5(e)） |
| Step 2 c: `commit-wave` 実行 | **SKILL**（Bash） |
| Step 2 の「**クラッシュ再開:**」ブロック（現行は「同じ `wave-{N}-hits.json` を使って classification を作り直し `commit-wave` を再実行する」＝ `search` を飛ばす経路） | **Stage 1 で「`search` から再開する」へ改訂**（改訂後の具体テキストは **§4.7.1 (1)**。既存 classification の再利用可否と、再利用波の計測上の扱い＝`classify_wall_ms_reused` を含む）→ Stage 2 で **SKILL**（§4.2 の波ループ）と `recovery-procedures.md` へ移設し、エージェントからは削除する。**残置してはならない**（§4.7 の経路統一が破れ、`classify_wall_ms` が汚染される） |
| Step 3: 確定ファイル一覧書き出し | 不変（スクリプトが自動実施） |
| Phase 2: Documentation | 不変 |

**スコープ外として記録する既存欠陥 — code-knowledge 参照が成果物へ到達しない:**

現行の「### Wave 0 完了後: code-knowledge 参照（MODE: discovery のみ）」は
`specout_bfs.py status` の `confirmed_files` から `confirmed_modules` を推定し、
`_observation-memo.md` に「## 既知制約との照合」セクションを生成する。しかし調査の結果、
**この機能は現行の実装では成果物（SPO）へ到達しない**ことが判明した。根拠は以下の4点である。

1. **生成物が削除される:** `MODE: document` の Step 0 が `_observation-memo.md` を
   「前回実行の残骸を引き継がないため」削除する。discovery フェーズで生成しても document 開始時に消える。
2. **SPO への転記手順が存在しない:** Step 10 の集約対象は Section 4.1（外部副作用）・4.2・5.6
   （非機能特性）・Section 9 転記に固定されており、「## 既知制約との照合」を読む手順がない。
   さらに Step 10 の後処理で `_observation-memo.md` 自体が削除される。
3. **制約メモの消費者が別コンテキストにある:** `KNOWN_CONSTRAINTS` の利用先として当該節が指定するのは
   「Phase 2 の各ファイル観察時（Step 2・3）」であるが、Phase 2 は `MODE: document` として
   **別 Task で起動される独立コンテキスト**である。したがって in-memory で保持された
   `KNOWN_CONSTRAINTS` は原理的に消費者へ届かない（唯一の受け渡し手段がファイル＝上記1で消える）。
4. **記載位置（副次的根拠）:** 当該節は `init` を実行する Step 2「開始」ブロックよりも**前**に
   記載されている（見出しは「Wave 0 完了後」だが、`init` の実行記述はその後方にある）。新規実行時に
   記載順どおりに実行されると `bfs-state.json` が未作成で `status` が成立しない。ただし姉妹節
   「Wave 0 完了後: モジュールカタログによる BFS 優先度設定」も同様に前方に置かれつつ実処理は
   `commit-wave` 側で行われるため、**記載順がそのまま実行順である保証はない**。この項目は
   「成立しない可能性がある」という位置づけに留め、上記1〜3（条件によらず成立する）を主たる根拠とする。

**本プランの方針: `discovery-setup` の外へは移設せず、`init` 実行の後段に置く。** 理由:
- **位置を `init` の後段に固定する理由:** `status` は state 不在時に
  「bfs-state.json が見つかりません（init を実行してください）」で異常終了する。
  現行の記載位置（`init` より前）をそのまま踏襲すると `discovery-setup` が毎回この異常終了を踏むため、
  相対位置は現行のままにせず `init` の後段へ置く。これは**実行順の明確化のみ**であり、
  移設（別フェーズ・別エージェントへの移動）ではない。
- **成果物観点で現行と等価:** 新設計の `discovery-setup` は `commit-wave` を実行しないため
  `confirmed_files` は常に空であり、`confirmed_modules` も空 → `KNOWN_CONSTRAINTS` も空となり、
  当該節は**無条件に no-op** となる。現行も上記1〜3により成果物へ到達しないため、
  **SPO・discovery-log・confirmed_files のいずれにも差は生じない**（§5 の等価性の主張が保たれる）。
  なお「中間ファイル `_observation-memo.md` が discovery 時点で生成されるか」という
  内部的な差は生じうるが、当該ファイルは document Step 0 で削除されるため成果物には現れない。
- `MODE: document` への移設は一見自然だが、**本プランの変更範囲では成立しない**:
  (a) `xddp.04.specout/SKILL.md` の `MODE: document` pass ブロックに `DOCS:` キーが無く
  （`DOCS:` を渡しているのは discovery 呼び出しのみ）、エージェントは「`DOCS` が未設定または空の場合は
  このセクションを全てスキップする」と自己規定しているため no-op が場所を変えて再発する。
  (b) 上記2のとおり SPO 転記手順の新設が必要になる。
  (c) Step 0 直後にメモを生成すると、Step 2 の「ファイルが存在しない場合にヘッダを作成する」条件と、
  Step 10 前処理の「`_observation-memo.md` 不在 ＝ 観察が一切行われなかった」判定の**両方を壊す**
  （既存機能のデグレード）。
- したがって本欠陥の是正は独立した変更であり、**Phase 3（並列化）のスコープ外**とする。
  **別プランとして起票すること**（本節がその記録である。CLAUDE.md「問題を見つけたら放置せず、
  必ず対処または明示的に記録する」）。
  → **2026-08-09 起票完了:**
  [PLAN-20260809-specout-code-knowledge-relay.md](PLAN-20260809-specout-code-knowledge-relay.md)
  （草案・承認待ち）。

**別プランへの申し送り（是正に必要な要件・4点）:**

| # | 要件 | 理由（対応する上記根拠） |
|---|---|---|
| 1 | **実行フェーズ自体の再設計** — `confirmed_modules` の推定には BFS 完了後の `confirmed_files` が必要であり、`commit-wave` を持たない `discovery-setup` に置く限り**どう直しても no-op のまま**である。「`discovery-setup` に残したまま SPO 転記だけ足す」案は成立しない | 根拠3・上記「成果物観点で現行と等価」 |
| 2 | **`DOCS` の受け渡し追加** — `xddp.04.specout/SKILL.md` の `MODE: document` pass ブロックに `DOCS:` キーが無く（渡しているのは discovery 呼び出しのみ）、エージェントは「`DOCS` が未設定または空の場合はこのセクションを全てスキップする」と自己規定している。実行フェーズを document へ移すなら必須 | (a) |
| 3 | **SPO テンプレート／Step 10 集約手順の拡張** — 「## 既知制約との照合」を読み SPO の該当セクションへ転記する手順と、転記先セクションの新設 | 根拠2 |
| 4 | **メモ不在シグナルの再設計** — Step 2 の「ファイルが存在しない場合にヘッダを作成する」条件と、Step 10 前処理の「`_observation-memo.md` 不在 ＝ 観察が一切行われなかった」判定は、いずれもファイル不在をシグナルとして使っている。早い段階でメモを生成する設計に変えるなら**両方の再設計が必要** | (c) |

**併せて是正する既存の矛盾（ボーイスカウトルール）— 判定手順2:**

変更前:
> 同一ファイルに複数ヒットがある場合、ファイルの Read は1回に留める。同一波内で複数の異なる
> ファイルへの Read が必要な場合は、Agent ツールの並列呼び出しで同時に読み込むと波の処理時間を
> 短縮できる。

変更後（classifier へ移設する際に修正）:
> 同一ファイルに複数ヒットがある場合、ファイルの Read は1回に留める。

**理由:** 現行 frontmatter の `tools:` は Read/Grep/Glob/Bash のみで Agent ツールを含まず、この記述は
実行不能な指示である。classifier も Agent ツールを持たないため、移設先でも同様に成立しない。

### 4.4 新規 classifier エージェント（骨子）

```markdown
---
name: xddp-specout-classifier-agent
description: Classifies one chunk of Discovery BFS search hits for XDDP specout
  (process step 4a). Reads a chunk file, judges each hit line's propagation type,
  and writes a classification JSON. Invoked in parallel, one instance per chunk.
tools:
  - Read
  - Grep
  - Write
---

### Inputs (provided by the caller)
- `CR_NUMBER`
- `REPO_NAME`
- `REPO_PATH`: 判定対象コードのルート（`enclosing_function` 特定の Read・引数伝播の定義検索に使用）
- `CRS_FILE`: `{CR_PATH}/03_change-requirements/CRS-{CR_NUMBER}.md`
  （`out-of-scope-discard` の判定に必要な変更スコープの文脈。現行は同一コンテキストが保持していた）
- `CHUNK_FILE`: `{OUTPUT_DIR}/wave-{N}-hits-chunk-{K}.json`
  （`hits` 部分集合 ＋ `known_symbols` ＋ 当該ヒットに対応する `commands` サブセット）
- `OUT_FILE`: `{OUTPUT_DIR}/wave-{N}-chunk-{K}-class.json`（このエージェントが Write する唯一のファイル）
- `EXCLUDE_PATTERNS`, `INCLUDE_EXTENSIONS`: 引数伝播の定義検索時の Grep 範囲
```

**出力スキーマ（`OUT_FILE`）:**
```json
{
  "chunk_id": "W3-K2",
  "classification": [ { "line_id": "W3-R7", "classification": "propagation-direct", "next_symbols": [],
                        "enclosing_function": "...", "is_external_api": false, "note": "..." } ],
  "unsupported_patterns": [ { "pattern": "リフレクション", "location": "src/a.py:42", "note": "..." } ]
}
```

> **時刻はスキーマに含めない（設計判断）:** classifier の `tools:` は Read/Grep/Write のみで `Bash` を持たず、
> LLM は時計を読めないため、classifier に開始・終了エポック秒を書かせる設計は成立しない
> （書かせても値は捏造になる）。実効並列度の観測は §4.5(d) のとおり**オーケストレータ側の
> バッチ計測**（`Bash` の `date` ＋ `--batch-count`）で行う。

`chunk_id` の形式は `W{wave}-K{index}`（`index` は0起点。ファイル名 `wave-{N}-hits-chunk-{K}.json` の `K` と一致）。

> **併せて是正する既存の不整合（ボーイスカウトルール）:** 現行 `xddp-specout-agent.md` の
> 判定結果スキーマ例は `"line_id": "W3-C1-L07"` だが、実装（`cmd_search` の `_next_line_id`）が
> 発番するのは `W{wave}-R{n}` 形式である。逐語移設の際にスキーマ例を実装形式へ是正する。

**設計判断の理由:**
- `tools:` に **Grep が必須** — 引数伝播判定は `func_name` の定義を `REPO_PATH` から検索して
  パラメータ名を特定する（現行の判定手順3）。
- `tools:` に **Write が必須** — 分類結果を戻り値テキストで返すと大量 JSON の切り詰め・整形崩れの
  リスクがあり、`merge_classification.py` による決定的検証にも適さない。ファイル書き出しに統一する。
  Write 先は `OUT_FILE` のみ（discovery-log・bfs-state.json は書かない＝単一書き手の維持）。
- `Bash` は付与しない（スクリプトを実行しないため。最小権限）。
- `description` はドメイン中立に保つ（親プラン指摘#9。Web/組み込み等を想起させる語を使わない）。
- SKILL の pass ブロック（§4.2）のキーと Inputs 節を1対1で一致させる（`refcheck.py` 検査B の照合対象）。

### 4.5 specout_bfs.py の変更（7点：S1 = (c)(d)(g) ／ S2 = (a)(b)(e)(f)）

**(a) `known_symbols` の出力〔S2〕** — §4.1 のとおり（素名正規化を含む）。

**(b) チャンク分割出力（`search --hits-dir DIR` ＋ `--chunk-size N`）〔S2〕**

変更前: `search` は `--hits-out {パス}` に1ファイルを書くのみ（呼び出し側が波番号を知っている前提）。
現行の `--hits-out` は `required=True` で宣言されている。

**既定値の層の区別（混同回避）:**

| 層 | 既定値 | 意味 |
|---|---|---|
| CLI 引数 `--chunk-size` | `0` | 未指定時は分割しない（＝チャンク1件）。スクリプト単体テスト・手動実行時の安全側の既定 |
| config キー `SPECOUT_CLASSIFY_CHUNK_SIZE`（§4.8） | `40` | SKILL が波ループで**常に明示的に `--chunk-size` へ渡す**値。運用上の実効既定 |

変更後:
- `--hits-dir DIR` を追加する。指定時は state の `current_wave` から `{DIR}/wave-{N}-hits.json` を
  スクリプト側で組み立てる。実パスは stdout の既存キー `hits_file` で返る。
- **`--hits-out` の `required=True` を解除**し、`--hits-out` と `--hits-dir` を**相互排他**にする
  （両方未指定 → `_err`、両方指定 → `_err`。いずれも明示エラーとし、暗黙の優先順位を作らない）。
- **常に**チャンクファイル `{hits_file の stem}-chunk-{K}.json` を出力し、
  stdout JSON に `chunks`（パス配列）と `chunk_count` を追加する。
- チャンクスキーマ（分割有無にかかわらず同一）:
  `{"chunk_id", "wave", "hits": [...], "known_symbols": {...全体と同一...}, "commands": [...当該ヒットが参照する command のサブセット...]}`
  （`chunk_id` = `W{wave}-K{index}`）
- **書き出し前に当該波の既存チャンクファイルを削除する**（`{DIR}/wave-{N}-hits-chunk-*.json`）。
  再 `search` でチャンク数が減った場合に旧ランのファイルが連番の末尾に残り、
  stale な結果が §4.7【S2】手順2 の再利用対象に混入することを防ぐ
  （classification 側の `wave-{N}-chunk-*-class.json` は §4.6 処理6 の line_id 照合で弾かれる）。
- **分割条件を満たさない場合（`--chunk-size 0` または `len(hits) ≤ N`）も `chunks` は必ず1件**
  （`chunk-0`）を返す。SKILL 側に分岐を作らないための統一契約。
- **分割軸: ファイル単位グルーピング。** 同一ファイルのヒットは同一チャンクに入れる
  （ファイルごとにヒットをまとめ、ファイル単位で貪欲にチャンクへ詰める）。
  1ファイルのヒット数が `--chunk-size` を超える場合は当該ファイル単独でチャンク化する。
  全 line_id はちょうど1チャンクに属する（重複・欠落なし）。

**理由:**
- チャンク分割は決定的処理であり LLM に委ねない（CLAUDE.md「決定的処理はスクリプト」）。
  分割境界の再現性が保証され、再開時に同じチャンク構成を再生成できる。
- `--hits-dir` を設けるのは、**`search` を実行する前に出力パスを確定できない**ためである。出力先は
  state の `current_wave` に依存するが、SKILL 側でそれを知るには毎波 `status`（現行は state 全体を
  stdout に出す）を呼ぶ必要があり、コンテキスト蓄積の主因になる（§4.2 の緩和策）。
  `search` 実行**後**であれば波番号は stdout の既存キー `"wave"` から得られるため、step c/d の
  `wave-{N}-class.json`・`wave-{N}-unsupported.json` の組み立てには支障がない
  （＝「SKILL 側が波番号を一切知らなくて済む」わけではなく、「search 前に知る必要がない」ことが本質）。
  なお step c/d の出力パスを `merge_classification.py`／`commit-wave` 側で `--hits` のパスから
  導出させれば、波番号をメインコンテキストから完全に排除することも可能である
  （Stage 2 実装時の選択肢として記録する。本プランの既定は stdout の `"wave"` を使う方式）。
- ファイル単位グルーピングにするのは、判定手順2「同一ファイルに複数ヒットがある場合、ファイルの
  Read は1回に留める」を並列化後も成立させるため。出現順の連続範囲で切ると同一ファイルが複数
  チャンクに分断され、複数 classifier が同じファイルを重複 Read してトークン増分が跳ね上がる
  （`cmd_search` の hits 生成順は HIGH 分（`all_emitted` を後段でまとめて append）→ MEDIUM スコープ順であり、
  ファイル単位でまとまっていない）。`enclosing_function` の表記ゆれ防止にもなる。
- `commands` サブセットを含めるのは、現行エージェントが「`{hits_file}` の内容（`commands` 配列・`hits` 配列）を
  読み込む」と規定されており、検索種別・パターン・スコープが判定文脈に含まれているため
  （不変条件1「判定入力が狭まらない」を無検証の削減で破らない）。

**(c) 分類開始時刻の記録とライフサイクル〔S1〕**

`cmd_search` の末尾（`data["wave_write_complete"] = False` の近傍）で、以下の**2キーを対で** state に記録する。

```python
data["classify_started_at"]   = time.time()   # 分類区間の開始時刻（エポック秒）
data["classify_started_wave"] = wave          # その時刻がどの波のものかを固定する
```

**ライフサイクル（本項が本仕様の一部・実装必須）:**

| 事象 | 挙動 |
|---|---|
| `cmd_search` 正常終了 | 上記2キーを**毎回上書き**する（同じ波を再 search した場合は最新の開始時刻で置き換わる＝最後の試行を計測する） |
| `cmd_search` が波数上限で早期 return（`_pause_for_wave_limit` 経由） | **2キーを書かない**（hits も生成されないため分類区間が存在しない）。加えて**既存の2キーを state から削除する**（古い波の値が残り続けることを防ぐ） |
| `cmd_commit_wave` | `classify_started_wave` が**今回コミットする `wave` と一致する場合のみ** `classify_wall_ms` を算出する。不一致・いずれかのキーが欠損の場合は `classify_wall_ms: null` とする |
| `cmd_commit_wave` 正常終了（算出の成否によらず） | **2キーを state から削除する**（消費後破棄。次波の `search` が再度書く） |
| `cmd_finish` / `cmd_re_discover` / `cmd_prune` / `cmd_set_state` | **2キーを state から削除する**（search を経ない状態遷移の後に古い開始時刻が残らないようにする） |
| `cmd_import` | 実装上は**自動的に消える**（`_default_state()` から state を再構築し、checkpoint.md に記載のあるラベルのみを復元する方式のため、2キーは復元対象に含まれない）。明示的な削除コードは不要だが、**「復元対象に加えないこと」を仕様として固定する** |
| `cmd_merge_frontier` / `cmd_record_module` | **削除しない**（いずれも波を進めず、進行中の波の frontier / module 記録を更新するだけであり、その波の分類区間は継続中とみなすのが正しいため。`classify_started_wave` は当該波のまま有効） |

**理由:**
- `search` と `commit-wave` は**別プロセス**であり、既存 `search_ms` が使う `time.monotonic()` は基準点が
  プロセス間で保証されない（Python の仕様上、差分が有効なのは同一プロセス内）。プロセスをまたぐ
  差分計測のため `time.time()` を用いる。
**用語の区別（プラン全体で統一する）:** 本プランには「波不一致」が2種類ある。
**α＝「開始時刻の波不一致」**（`classify_started_wave != wave`。state に古い開始時刻が残っている状態。
本項の検証対象で、結果は `classify_wall_ms: null`）と、
**β＝「hits の波不一致」**（`hits_payload["wave"] != data["current_wave"]`。渡された hits 自体が古い状態。
§4.5(g) の fail-loud **条件1** の検証対象で、結果は exit 非0。なお fail-loud には条件2・3 もあるが、
それらは波不一致ではないため β には含めない）である。
**β が成立する入力では `commit-wave` が異常終了するため metrics 行そのものが出力されず、α の `null` は観測できない。**
両者を同一視すると相互に矛盾するテストを書くことになるため、以降の記述・テスト・確認項目では常にどちらかを明示する。

- 波の一致検証（α。`classify_started_wave`）と消費後破棄が必要なのは、`cmd_search` が波数上限到達時に
  早期 return する経路（`cmd_search` 冒頭の `current_wave > max_wave_depth` 分岐）と、search を経ずに
  state を遷移させる経路（`finish` / `re-discover` 等）が存在し、そのままでは
  **別の波の開始時刻から差分が算出されて計測値が汚染される**ためである。Stage 1 の成果物は
  事実上この数値ひとつであり、§4.9 のゲート判定に直結するため、ライフサイクルを仕様として固定する。
- 2キーはいずれも**時間値と同じく metrics 専用**であり、state 判定（再開の決定性）には持ち込まない
  （欠損しても BFS の進行に一切影響しないこと＝欠損時 `null` フォールバックで足りることが要件）。

**防御の位置付け（テスト本数の根拠）:** 汚染防止の**一次防御は `commit-wave` の α（開始時刻）の波一致検証**であり、
`classify_started_wave != wave` なら `classify_wall_ms` は `null` になる。したがって
`finish` / `re-discover` / `prune` / `set-state` の4経路での明示削除は**二次防御**であり、
correctness（計測値の正しさ）は一次防御だけでも成立する。それでも仕様として固定するのは、
state ファイルに古い開始時刻が残ると**調査時に「その波の計測が生きている」と誤読される**ためである
（Stage 1 の成果物は事実上この数値ひとつであり、投資判断に直結する）。
この位置付けにより、4経路のテストは「二次防御の回帰検査」として本数を維持する。

**(d) metrics の追加（`cmd_commit_wave` の `metrics_line`）〔S1〕**

> `--chunk-count` / `--batch-count` / `--parallelism` の**CLI 引数追加そのものは Stage 1 に含める**
> （いずれも既定 1 で挙動不変。Stage 1 では常に既定値が入る）。実際に 1 以外の値が渡るのは Stage 2 以降である。

変更前:
```python
metrics_line = {
    ..., "search_ms": wave_metrics.get("search_ms", 0), ...
}
```
変更後: 以下のキーを追加する（件数は今後の増減で陳腐化するため書かない。§3 の S1 実装行のキー列挙と一致させること）。
- `classify_wall_ms`: `classify_started_wave == wave` の場合のみ
  `int((time.time() - data["classify_started_at"]) * 1000)`。
  **α＝開始時刻の波不一致**・`classify_started_at`／`classify_started_wave` のいずれかが state に無い場合は `null`
  （§4.5(c) のライフサイクル表に従う）。**さらに下記「再利用波の判定」が真の場合も `null` とする。**
  算出の成否によらず、算出直後に2キーを state から削除する。
- `classify_wall_ms_reused`: **再利用波の判定**（下記）の結果。`true` の波は §4.9 の集計から除外する。
  `classify_wall_ms` が `null`（**α＝開始時刻の波不一致**・キー欠損）で判定自体が成立しない場合は `null`
- `classify_wall_ms_suspect`: `classify_wall_ms` が閾値（**暫定 1,800,000ms ＝30分**。根拠は §4.9
  「残存する限界と機械的な安全弁」）を超える場合に `true`、閾値内なら `false`。
  **`classify_wall_ms` が `null` の場合は `false` ではなく `null` とする**
  （集計側で「値なし」と「閾値内」を区別できるようにするため）
- `chunk_count`: `--chunk-count`（既定 1）
- `batch_count`: `--batch-count`（既定 1）。**観測値**（SKILL が実際に起動したバッチ数。下記参照）
- `parallelism`: `--parallelism`（既定 1）。**これは SKILL が渡した設定値であり、
  オーケストレータが実際に何並列で Agent tool を起動したかという観測値ではない**
  （SKILL の並列起動は自然言語指示であり決定的に強制できないため、`SPECOUT_CLASSIFY_PARALLEL` を
  渡しても逐次起動されうる）。

**再利用波の判定（過小計測の防止・`classify_wall_ms_reused`）〔S1〕:**
§4.7 の再開手順は、既存の classification（Stage 1 では `wave-{N}-class.json`、Stage 2 では
チャンク `OUT_FILE` 群）を**再利用してよい**と規定している。再利用した波では、再 `search` から
`commit-wave` までの間に実際の分類が行われないため、`classify_wall_ms` はその波の分類所要時間ではなく
**数秒〜数十秒の過小値**になる。過小値は `paused` 除外にも `classify_wall_ms_suspect`（過大側のみ検出）にも
掛からず、中央値をそのまま押し下げて §4.9 のゲートを**偽陰性**（Stage 2 を不要と誤判定）へ振らせる。

- **判定方法〔S1〕（機械判定・LLM の自己申告に依存しない）:** `cmd_commit_wave` は `--classification` で
  受け取ったファイルの **mtime** を `data["classify_started_at"]` と比較し、
  **mtime < `classify_started_at` なら再利用とみなす**（`classify_wall_ms_reused: true`）。
  Stage 1 では `wave-{N}-class.json` を人／エージェントが直接再利用するため、
  正常系では classification は再 `search` の**後**に生成され mtime は必ず `classify_started_at` 以降となる。
  この判定は誤検出しない。
- **判定方法〔S2〕（確定・2026-08-09）:** Stage 2 の `--classification` は
  §4.2 step c のとおり `merge_classification.py` が**毎波その場で生成**するため、チャンク結果を全件再利用しても
  merge の実行時刻（＝再 `search` より後）が mtime になり、**上記 S1 方式では `reused` が常に `false` になる**
  （原理的に検出できない）。したがって S2 では `--classification` ファイル自身の OS mtime を使わず、
  以下の経路で「チャンクが実際に書かれた時刻」を伝達する（`--classification` の中身は現行どおり
  `commit-wave` の入力契約と同一のバイト配列のままとし、判定用の値は**別チャンネル**で渡す。
  配列の中に判定用キーを混ぜると `for c in classification:` の既存契約を壊すため）。
  1. `merge_classification.py`（§4.6 処理7）は収集した `chunk_mtimes` のうち mtime が取得できたものの
     **最小値**を `min_chunk_mtime`（エポック秒）として stdout JSON へ追加する
     （全チャンクの mtime が取得不能な場合は `min_chunk_mtime: null`）。
  2. SKILL（§4.2 step c の直後）は stdout の `min_chunk_mtime` を読み、非 `null` なら
     step d の `commit-wave` 呼び出しへ **`--chunk-mtime-min {値}`** として渡す
     （`null`／キー自体が無い場合は渡さない）。
  3. `cmd_commit_wave` に **`--chunk-mtime-min`（任意引数・既定 `None`・float）** を追加する。
     指定されていれば**その値**を、未指定なら**従来どおり `--classification` ファイルの OS mtime**
     （`_file_mtime`）を `classify_started_at` との比較に用いる。
  S1 の既存呼び出し（`--chunk-mtime-min` を渡さない）は一切変更なく現行のファイル mtime 判定のまま
  動作する（後方互換・退行なし）。この設計により「判定は決定的処理側で完結し LLM の自己申告に
  依存しない」という方針を維持したまま、S1／S2 いずれの呼び出し形式でも同一の `cmd_commit_wave`
  実装で両立する。
- 再利用と判定した波は `classify_wall_ms: null` / `classify_wall_ms_reused: true` とし、
  §4.9 の集計から除外する（除外波は §4.9「外れ値の扱い」の規定に従い**別掲**する）。
- mtime が取得できない場合（ファイル削除等の異常時）は `classify_wall_ms_reused: null` とし、
  `classify_wall_ms` は通常どおり算出する（計測専用であり correctness に関与しないため fail させない）。

> **`resumed` フラグは設けない（設計判断・重要）:** クラッシュ再開波を
> `wave_write_complete` から判別する方式は**実装不能**である。`cmd_search` は
> 正常系でも毎波必ず `data["wave_write_complete"] = False` を書いて `_write_state` する
> （`cmd_commit_wave` の既存処理 `if not data["wave_write_complete"]: _truncate_wave_section(...)` が
> この前提に依存している）。したがって `cmd_commit_wave` が読む値は通常波でも常に `False` であり、
> この方式のフラグは**全波 true** になって外れ値除外が全波除外に化ける。
> 代わりに §4.7 で**再開経路を「`search` から再開する」の1本に統一**し、
> 再開時に `classify_started_at` が必ず書き直されるようにすることで、
> **汚染の発生自体を設計で消す**（詳細は §4.7・§4.9）。

**実効並列度の観測（Stage 2 で必要・Stage 1 では不要）:** `parallelism` が設定値である以上、
「`parallelism: 4` かつ短縮なし」の結果が①並列化に効果がない／②そもそも並列起動されなかった、の
どちらなのかを metrics だけでは区別できず、Stage 2 の効果判定を誤らせる。
**Stage 2 では `batch_count`（観測値）を併記する**:
- SKILL は §4.2 step b で classifier を**バッチ単位**（1バッチ＝同時起動する最大
  `{SPECOUT_CLASSIFY_PARALLEL}` 件。バッチは repo 横断で組まれる）に分けて起動する。
- **`--batch-count` の定義（repo 単位に揃える）:** 当該 repo のチャンクが**1件以上含まれていたバッチの数**を
  repo ごとに数えて渡す。バッチ自体は repo 横断で組むが、metrics は repo ごとの `chunk_count` と
  分母を揃えるため repo 単位で数える（例: 2 repo × 各3チャンク・`parallelism=4` → 全体2バッチ。
  repo A のチャンクが両バッチに跨るなら repo A の `batch_count = 2`）。
- **判定（repo 単位で行う。下記の順に評価し、先に成立した分岐で確定する）:**
  1. **上界内なら「概ね設定どおりに並列起動されている」と判定する（第1優先）:**
     `batch_count ≤ ceil(chunk_count / parallelism) + 1`
     （repo 横断バッチの切れ目により最大1バッチ分ぶれるため `+1` を許容する）。
     **この上界は §4.2 step b の「repo 単位で連続充填する」規定を前提に成立する**
     （幅 `p` のバッチ列上で連続する `k` 件は高々 `ceil(k/p)+1` バッチに跨る）。
     交互充填では成立しないため、充填順序の規定は判定式の必須前提である。
  2. **上記を満たさず、かつ `batch_count == chunk_count` かつ `chunk_count > parallelism` なら
     「並列起動されていない」と判定する（1件ずつ逐次）。**
  3. いずれにも該当しない場合は「判定不能」とし、`wave-{N}-batches.json` を人が確認する。
  **優先順位を規定するのは、2つの分岐が数値上オーバーラップしうるためである**
  （例: `chunk_count = 2`・`parallelism = 4` の repo のチャンクがバッチ境界を跨ぐと `batch_count = 2` となり、
  上界 `ceil(2/4)+1 = 2` を満たす一方で `batch_count == chunk_count` も成立する。優先順位がないと、
  実際は並列起動しているケースを「逐次だった」と誤判定する偽陰性が生じる）。
  `chunk_count ≤ parallelism` の repo は分岐2 の対象外とし、`chunk_mtimes`（下記「`batch_count` の裏付け」）で
  補完的に確認する。
  この順序により「①並列化に効果がない」と「②そもそも並列起動されなかった」を metrics だけで区別できる。
- **記録先（監査用）:** `{CR_PATH}/04_specout/{repo}/wave-{N}-batches.json`（`{N}` は当該 repo の波番号。
  repo ごとに書くため repo 横断バッチでも `{N}` は一意に定まる）。スキーマ:
  `[{"batch_index": 0, "chunk_files": ["…-chunk-0-class.json", …], "started_at": 1786000000, "ended_at": 1786000042}, …]`
  （`started_at`/`ended_at` は SKILL が各バッチの起動直前・完了直後に Bash の `date +%s` で取得する。
  `Bash` を持つのはオーケストレータのみであり、classifier の権限は増やさない）。
  **消費者は人（事後監査）と §6 の確認項目**であり、これを読むスクリプトは新設しない
  （`batch_count` のみが metrics へ入り、機械判定はそちらで行う）。

**`batch_count` の裏付け（自己申告値であることへの対処）:** `batch_count` はオーケストレータ LLM の
自己申告値であり、「実際に並列起動したか」を測る指標の観測主体が測られる当人になっている。
逐次起動したのに辻褄合わせの値を報告する可能性を排除するため、`merge_classification.py` が
読み込む各チャンク `OUT_FILE` の **mtime** を収集し、完了時刻の分布（バッチ状にクラスタするか、
等間隔に散るか）を stdout の統計（`chunk_mtimes`）として出力する。スクリプト側で完結するため
classifier の権限は増えない。§6 でこの分布と `batch_count` の整合を確認項目とする。

この方式を採るのは、classifier が時計を読めない（`Bash` なし・LLM は現在時刻を取得できない）ため、
チャンク単位の実行区間を classifier 自身に記録させる設計が成立しないからである（§4.4 の注記）。

なお `classified`（= `len(hits)`。post-dedup/filter の実分類行数）は**既存キーとして既に記録済み**であり
追加は不要だが、§4.9 のゲート判定はこのキーを使う（`raw_hits` ではない）。

**理由:** 時間値は既存 `search_ms` と同じく **metrics 専用**とし state 判定には持ち込まない
（`cmd_commit_wave` の既存コメント「時間値（search_ms）は非決定のため metrics 専用とし state 判定には
持ち込まない（再開の決定性保持）」と同一方針）。
**名称を `classify_wall_ms` とするのは、この値が「search → commit-wave 間の壁時計」であり、
LLM の実行時間そのものではなく、その上界だからである**（チャンク起動待ち・`merge_classification.py` の
実行時間・paused 時の人の介在時間を含む）。§4.9 の投資判断はこの上界値で行う。

**(e) `commit-wave --unsupported-patterns FILE`〔S2〕**

**変更前（`cmd_commit_wave` の引数定義）:** `--unsupported-patterns` フラグは存在しない。

**変更後:**
```python
p_commit.add_argument("--unsupported-patterns")  # 新規・任意引数（既定 None）
```
JSON 配列を受け取り、discovery-log.md の「grep未対応パターン」セクションへ追記する
（重複はスクリプト側で除去）。ファイル未指定時は何もしない（既存呼び出しと完全に同一挙動＝後方互換）。

**追記先の構造と挿入方式（実装上の必須事項）:**
- 「grep未対応パターン」は discovery-log の**先頭ヘッダ部**に `init` が生成するセクションであり、
  見出しは `## grep未対応パターン（手動確認必要）`、テーブルは
  `| パターン種別 | 根拠（CRS/コードより） | 確認状況 |` の**3列**である。以降に Wave セクションが
  追記されていく構造のため、**このセクションはファイル末尾ではなく中間に位置する**。
- 既存ヘルパはいずれもそのままでは使えない。`_append_to_file` は EOF 追記であり、
  `_upsert_confirmed_files_section` は当該セクションを一旦削除して**末尾へ再構築**する方式である
  （確定ファイル一覧が末尾にあってよいため成立している）。grep未対応パターンに同じ方式を使うと
  ヘッダ部から末尾へセクションが移動してしまう。
  → **見出しを検索し、その直下のテーブル末尾（次の `## ` 見出しまたは `---` の手前）へ行を挿入する
  「セクション内挿入」ヘルパを新設する**。
- 列の対応（classifier 出力スキーマ `{pattern, location, note}` → 3列）:

  | テーブル列 | 値 |
  |---|---|
  | パターン種別 | `pattern` |
  | 根拠（CRS/コードより） | `location`（`{file}:{line}` 形式）＋ `note` が非空なら `（{note}）` を連結 |
  | 確認状況 | `⬜ 未確認`（固定。人が後から更新する） |

- 重複判定キーは `(pattern, location)` とする（§4.6 の `--unsupported-out` 側のマージキーと同一）。
  既にテーブルに存在する行は再挿入しない（`commit-wave` の再実行で行が増殖しないこと）。
- `_truncate_wave_section`（クラッシュ再開時に書きかけ Wave セクションを切り捨てる）は
  `## Wave {n}` 以降のみを対象とし、ヘッダ部の本セクションより後方に位置するため**干渉しない**。
  この不干渉は単体テストで固定する。

**理由:** 並列 classifier が discovery-log.md を各自 Edit すると書き込み競合が起きる。
書き手を `commit-wave`（Bash・単一）に集約する。

**(f) `status --brief`〔S2〕**

`--brief` 指定時は `{"ok", "state", "current_wave", "wave_write_complete", "remaining_frontier_count"}` のみを
出力する（無指定時は現行どおり state 全体）。

**`remaining_frontier_count` の算出定義（実装上の必須事項）:**
- 値は `len(data["frontier"]) + len(data.get("low_priority_frontier", []))` とする。
- **`commit-wave` の stdout キー `next_frontier_count` とは別物**であり、名前を意図的に変える。
  `cmd_commit_wave` の `next_frontier_count` は `len(next_frontier)`（＝ HIGH/MEDIUM 分のみ。
  `low_priority_frontier` を含まない）である。一方 `cmd_commit_wave` が `state` を `complete` にする条件は
  `if not next_frontier and not data.get("low_priority_frontier")` であり、**両方が空**であることを要求する。
  したがって `--brief` の「まだ探索が残っているか」の判定に `len(frontier)` だけを使うと、
  `low_priority_frontier` が残っている repo を SKILL 側が誤って完了扱いし ACTIVE_REPOS から外す事故が起きる。
  complete 判定と同じ集合（両者の合計）を返すことでこれを防ぐ。
- なお `bfs-state.json` に `next_frontier_count` という**フィールドは存在しない**
  （`_default_state()` のフロンティア関連キーは `frontier` と `low_priority_frontier` の2つ）。
  state 由来でないことが名前から分かるよう `remaining_frontier_count` を用いる。

**変更前（`cmd_status`）:**
```python
def cmd_status(args) -> None:
    data = _load_state(Path(args.path))
    print(json.dumps({"ok": True, **data}, ensure_ascii=False))
```

**変更後:** `args.brief` が真なら上記4キー＋`ok` のみを出力する分岐を追加する（既定は現行と同一）。

**理由:** 現行は `visited`・`confirmed_files`・`classified_locations` 等の単調増加フィールドを含む
state 全体を stdout に出す。波ループが SKILL 側へ移るとこれがメインコンテキストに蓄積するため、
判定に必要な最小キーのみを返す経路を用意する（§4.2 のコンテキスト蓄積緩和策）。

**(g) `cmd_search` の非破壊化 — frontier / low_priority_frontier の更新を `commit-wave` へ一元化〔S1〕**

§4.7「再 `search` の冪等性の担保」で述べた既存不具合の是正。**Phase 3 とは独立の既存欠陥だが、
§4.7 の経路統一の前提条件であり、かつ Stage 1 の基準線採取の正しさに直結するため Stage 1 に含める。**

**変更前（`cmd_search` の末尾）:**
```python
data["wave_write_complete"] = False
data["low_priority_frontier"] = low     # ← search が破壊的に書き換える（frontier は更新しない）
_write_state(state_path, data)
```

**変更後:**
- `cmd_search` は `low_priority_frontier` を**書き戻さない**（読み取って分割に使うだけ）。
  `frontier` を更新しないのは現行どおり。＝ `search` はフロンティア状態に対して**読み取り専用**になる。
- 分割結果は `hits_payload` に載せて `commit-wave` へ渡す:
  - `searched_frontier`（＝ `this_wave`）は**既存キーとして既に存在する**ためそのまま使う。
  - `deferred_low`（＝当波で LOW へ退避した結果の `low`）を**新規キーとして追加**する。
- `cmd_commit_wave` が `--hits` から `deferred_low` を読み、`data["low_priority_frontier"] = deferred_low` を
  適用する。**適用位置は「入力読み込み直後（`_truncate_wave_section` の近傍）」とし、
  discovery-log 生成部より前とする**（理由は下記「適用位置を早期に固定する理由」）。
  `deferred_low` キーが無い hits（旧形式）を受け取った場合は `low_priority_frontier` を**変更しない**
  （後方互換ではなく、キー欠損時に既存値を壊さないための安全側の既定）。
- **コミット妥当性の fail-loud を追加する（下記のうち条件1 が β＝「hits の波不一致」に当たる。
  条件2・3 は波不一致ではなく「既に確定済みの波への再コミット」の検出である）:** `cmd_commit_wave` は以下の**いずれか**が
  成立する場合、state も discovery-log も一切変更せず `_err` で異常終了する。
  1. `hits_payload["wave"] != data["current_wave"]`（渡された hits が現在の波と異なる）
  2. `data["state"] == "complete"`（既に BFS が完了している）
  3. `hits_payload["wave"] <= data.get("last_completed_wave", -1)` かつ `data["wave_write_complete"]`
     （正常終了済みの波の再コミット）

  **条件2 と条件3 は役割が異なる。**「最終波の穴」（下記）は**条件2・3 のいずれでも捕捉される**が、
  それぞれ**単独でしか効かない経路**を持つため、どちらも省いてはならない。

  | 条件 | 単独で成立する経路 | 塞ぐ事象 |
  |---|---|---|
  | 条件2（`state == "complete"`） | 当該波の `search` 実行**後**に `finish` を実行した state（`cmd_finish` は `data["state"] = "complete"` を書くのみで `wave_write_complete`・`last_completed_wave`・`current_wave` を**触らない**ため、`wave_write_complete: false` かつ `wave > last_completed_wave` のまま complete になる＝条件1・3 が不成立） | `wave_write_complete: false` のため `_truncate_wave_section` が呼ばれる。**当該波の書きかけ `## Wave w` セクションが discovery-log に既に存在する場合**（`commit-wave` がログ追記後・状態更新前にクラッシュし、その後 `finish` した state）は、その位置以降がすべて切り捨てられ、後から追記された「## 継続パス C（残存フロンティアをスコープ外として承認）」等の監査記録も失われる。**存在しない場合は `_truncate_wave_section` は早期 return し no-op となる**（`heading = f"## Wave {wave}"` を `text.find` で探し `idx == -1` なら return。`## Wave w` を書くのは `cmd_commit_wave` のみで `cmd_search` は書かない）。**切り捨てが起きない場合でも、当該波の classification が伝播を生む（`next_frontier` が非空）か `deferred_low` が非空であれば、`data["frontier"] = next_frontier` と `deferred_low` の適用によりスコープ外承認したフロンティアが復活する。** いずれも空の場合でも、`## 継続パス C` の後ろに Wave w セクションが追記され、`visited`・`confirmed_files`・`last_completed_wave` 等が上書きされる（**監査整合性の破壊**。なお二重追記は起きない — `cmd_commit_wave` はログ追記 → metrics.jsonl 追記 → 状態更新の順で処理するため、「`## Wave w` が存在しない＝切り捨てが起きない」分岐では metrics 行も未追記であり、再コミットの追記は log・metrics とも初回追記になる） |
  | 条件3（`wave <= last_completed_wave` かつ `wave_write_complete`） | `cmd_set_state`／手編集 checkpoint の `cmd_import` で `state` だけを `in-progress` へ戻した state（`state != "complete"` のため条件2 が不成立） | 確定済みの波の再コミットによる discovery-log・metrics.jsonl の二重追記 |

  この役割分担がないと、実装者がいずれかを「もう一方の重複」と判断して省く恐れがある。
  **「最終波の穴」とは以下を指す。**実コードの `cmd_commit_wave` は
  `if not next_frontier and not data.get("low_priority_frontier"): data["state"] = "complete"` の
  **else 側でのみ** `data["current_wave"] = wave + 1` を実行するため、**BFS を完了させる波では
  `current_wave` が進まない**。さらに `cmd_commit_wave` には `cmd_search` のような complete ガードがない。
  条件1 だけでは最終波の hits 再投入が素通りし、`wave_write_complete` が既に `True` のため
  `_truncate_wave_section` も走らず、**discovery-log の Wave セクションと metrics.jsonl の行が二重追記**される
  （2キーは前回コミットで削除済みのため `classify_wall_ms: null` の重複行になる）。
  `last_completed_wave` は `cmd_commit_wave` が正常終了時に書く**既存キー**であり、追加は不要。
  **検証位置は「`hits_payload` を読み込んだ直後・`_truncate_wave_section` の呼び出しより前」とする。**
  `_truncate_wave_section(log_path, wave)` は **hits 由来の `wave`** で discovery-log を
  `## Wave {wave}` の位置から破壊的に切り捨てるため、検証を後置すると
  （例: `current_wave = 5`・`wave_write_complete = false` の状態で誤って `wave-2-hits.json` を渡した場合）
  **Wave 2〜4 の確定済みログが復旧不能に失われてから**エラー終了する。
  ガードが守るはずの誤操作でガード導入前より被害が拡大するため、位置の規定は仕様の一部である。
  (g) 以前は `low_priority_frontier` を `search` 側が書いていたため古い波の hits を渡しても LOW フロンティアは
  壊れなかったが、(g) 適用後は `deferred_low` が LOW フロンティアを古い波の値で上書きし、
  **消費済みエントリの復活・現在の繰り越し分の消失**を招く（`cmd_commit_wave` は
  `wave = hits_payload["wave"]` をそのまま採用し `data["current_wave"] = wave + 1` も hits 由来のため、
  現状この不整合は検出されない）。§4.5(c) の `classify_started_wave` による波一致検証と防御の粒度を揃える。
- 結果として、同一 state に対して `search` を何回実行してもフロンティア状態は変化せず、
  `this_wave`・line_id・チャンク構成が**完全に一致**する。入れ替え（`this_wave, low = low, []`）が
  起きた波でも、`commit-wave` に到達するまで元の `frontier`・`low_priority_frontier` が保持されるため、
  繰り越し LOW エントリが失われない。

**理由:** state のフロンティア更新を `commit-wave`（単一書き手）に集約することは、
§4.7 冒頭の「`bfs-state.json` の書き手は `commit-wave`（Bash・単一）に集約したまま」という方針とも整合する。
`search` に残す state 書き込みは `wave_write_complete`・`backend_effective`・
`backend_fallback_logged`・`classify_started_at`／`classify_started_wave` のみとし、
いずれも再実行で同じ値に収束する（冪等）。`backend_fallback_logged` はバックエンド警告を discovery-log へ
1度だけ出すための **set-once フラグ**であり、再実行で値が変わらず警告の二重出力を防ぐ方向に働くため
**削除してはならない**。なお `_pause_for_wave_limit` 経由の `state`・`limit_reached_count` 更新は
一時停止経路であり、本列挙（正常系で `search` が残す書き込み）の対象外である。

**適用位置を早期に固定する理由（`cmd_commit_wave` の参照箇所は2つある）:**

`cmd_commit_wave` が `data["low_priority_frontier"]` を参照する箇所は、実コード照合の結果**2箇所**である。

| # | 参照箇所 | 位置 |
|---|---|---|
| (A) | complete 判定 `if not next_frontier and not data.get("low_priority_frontier")` | 状態更新ブロック内（`data["frontier"] = next_frontier` の近傍） |
| (B) | discovery-log の frontier 行生成 `log_lines.append("→ 空。新規発見なし。探索終了。" if not data.get("low_priority_frontier") else "→ Wave {wave+1} frontier: (MODULE_PRIORITY_LOW 分へ移行)")` | **状態更新ブロックより前**（この直後に `_append_to_file(log_path, …)` が走る） |

適用位置を「`data["frontier"] = next_frontier` と同じ箇所」にすると (A) は救われるが **(B) は救われず**、
(B) は `search` 前の繰り越し値で判定して discovery-log を実状態と食い違わせる。

- **(i) 誤って「探索終了」と書く:** 繰り越し LOW が空・当波で新たに LOW 退避が発生・`next_frontier` が空、
  というケースで「→ 空。新規発見なし。探索終了。」と記録される。実際は `deferred_low` が非空のため
  state は `in-progress` のまま次波へ進む＝**discovery-log と bfs-state.json が矛盾する**。
- **(ii) 誤って「LOW 分へ移行」と書く:** 入れ替えが起きた波（`deferred_low = []`）で `next_frontier` も空なら
  state は `complete` になるが、ログはまだ探索が続くかのように記録される。

discovery-log は SPO の一次根拠かつ人の監査対象であり、§5 は「生成される SPO・**discovery-log**・
confirmed_files は現行と等価」と明言している。**この行を検査するテスト・fixture は現存しない**ため
（`MODULE_PRIORITY_LOW 分へ移行` / `新規発見なし` は本体スクリプトにしか出現しない）、
`make test` でも検出されずそのまま出荷される。したがって **(A)(B) いずれよりも前に `deferred_low` を
適用する**ことを仕様として固定し、対応する単体テストと確認項目（§6 Stage 1）を追加する。

> **実装時の必須確認:** 上記 (A)(B) の**両方**が `deferred_low` 反映**後**の値で判定されることを確認すること。
> 早期適用による他への副作用は、実コード照合の範囲では見当たらない
> （`_pause_for_wave_limit`・`cmd_prune`・`cmd_merge_frontier`・`cmd_record_module` は
> `low_priority_frontier` を読み書きしない。`cmd_finish` の `residual` 算出は (g) により改善する）。

### 4.6 merge_classification.py（新規・S2）

**変更前:** ファイルは存在しない。

**変更後:** 新規ファイルとして追加する。呼び出し形式:
```
merge_classification.py --hits {wave-N-hits.json} \
                        --hits-chunks {wave-N-hits-chunk-0.json} {wave-N-hits-chunk-1.json} ... \
                        --chunks {wave-N-chunk-0-class.json} {wave-N-chunk-1-class.json} ... \
                        --out {wave-N-class.json} \
                        --unsupported-out {wave-N-unsupported.json}
```

**引数の意味（取り違え防止・§4.2 の `HITS_CHUNKS` / `CLASS_CHUNKS` と1対1）:**

| フラグ | 渡すもの | 生成元 |
|---|---|---|
| `--hits` | 波全体のヒット（`wave-{N}-hits.json`） | `search`（§4.5(b)） |
| `--hits-chunks` | **ヒットチャンク**群（`wave-{N}-hits-chunk-{K}.json`＝`HITS_CHUNKS`） | `search`（§4.5(b)）。処理6 のチャンク単位 line_id 照合に使う |
| `--chunks` | **classifier の出力**群（`wave-{N}-chunk-{K}-class.json`＝`CLASS_CHUNKS`） | classifier の `OUT_FILE`（§4.4） |

`--hits-chunks` を独立フラグとして受け取るのは、パスをスクリプト側で暗黙導出させないためである
（呼び出し側が明示することで `refcheck.py` 検査D のフラグ照合対象になり、取り違えが契約として残る）。

**処理:**
1. 各チャンク結果を読み、`classification` 配列を結合する。
2. `--hits` の line_id 集合と照合し、**欠落・重複**があれば `stderr` に一覧を出して `exit 1`。
3. `classification` 値が既定の列挙値でない行があれば `exit 1`（`commit-wave` に到達する前に捕捉）。
4. `unsupported_patterns` を全チャンク分マージ（同一 pattern + location は1件に集約）し `--unsupported-out` へ。
5. `--out` には **`--hits` の出現順**で整列した classification 配列を書く（`commit-wave` の現行入力形式と同一）。
6. **チャンク結果の再利用可否を判定する（§4.7【S2】手順2 の実行主体はここ）:** 各チャンク結果の `chunk_id` と、
   `--hits-chunks` で受け取った対応するヒットチャンク（`wave-{N}-hits-chunk-{K}.json`）の line_id 集合を照合し、
   **不一致（`--hits` に存在しない未知 line_id の混入を含む）なら当該チャンクを再投入対象として
   stderr に出力し `exit 1`** とする。これにより旧ランの stale なチャンク結果の取り込みを機械的に防ぐ。
   再利用可否の判定を SKILL（LLM）に委ねない（CLAUDE.md「決定的処理はスクリプト」）。
7. 各チャンク `OUT_FILE` の **mtime** を収集し、stdout JSON に `chunk_mtimes`
   （`[{"chunk_id", "mtime"}, …]` を mtime 昇順）として出力する。実効並列度の裏付け
   （`batch_count` が自己申告値であることへの対処。§4.5(d)）に使う。
   mtime が取得できないチャンクがあっても**エラーにしない**（計測専用であり correctness に関与しない）。
   **あわせて `chunk_mtimes` のうち mtime が取得できたものの最小値を `min_chunk_mtime`
   （エポック秒。1件も取得できなければ `null`）として同じ stdout JSON へ出力する**
   （§4.5(d)「判定方法〔S2〕」の再利用波検出＝`commit-wave --chunk-mtime-min` の入力元）。
8. **classifier が `OUT_FILE` を書かずに終了した場合の扱い:** `--hits-chunks` の各エントリに対応する
   `--chunks` のファイルが**存在しない**場合は、traceback で落とさず、欠落チャンクの `chunk_id` と
   期待パスの一覧を stderr へ出力して `exit 1` する。この一覧が §4.7【S2】手順2 の
   「**欠落しているチャンクのみ** classifier を再投入する」の特定根拠になる
   （欠落チャンクの特定は SKILL〔LLM〕ではなく merge 側〔決定的処理〕の責務である）。

**実装制約（`refcheck.py` 検査D を実効化するため・必須）:**
`merge_classification.py` は**サブコマンドを持たない**ため、検査D（`check_d_script_wiring`）の有効フラグ集合は
`sub_flags` ではなく `top()["flags"]` ＝ **`merge_classification.py --help` の全出力**に
`FLAG_RE = --[a-z][a-z0-9-]*` を適用して収集したものになる。したがって
`ArgumentParser(description=__doc__)` を用い、かつモジュール docstring に上記 usage 断片
（`--hits` / `--chunks` / `--out` / `--unsupported-out`）を書くと、**argparse が実際には定義していない
フラグまで有効扱いになり**、SKILL.md 側のフラグ誤記・引数契約ずれが violation にならない
（＝ `DETERMINISTIC_SCRIPTS` へ登録しても検査Dが空振りする）。
このため `merge_classification.py` には以下の**2つを両方**課す（いずれか一方を選ぶ2択ではない）。

1. **必須制約:** `ArgumentParser(description=__doc__)` を**用いない**
   （`description` を渡さないか、フラグ名を含まない短い説明文を直接渡す）。
   §6 整合性の検証手順はこの条件の充足を検査するため、**検証可能なのはこちらだけ**である。
2. **併記条件（二重化）:** モジュール docstring にフラグ名（`--…`）を列挙しない。
   1 が将来の編集で復活した場合にも保証が静かに失われないための予防であり、**1 の代替ではない**。
   ただし 2 のみを満たす実装では「docstring にのみ存在するフラグ」が原理的に存在せず
   §6 の検証手順そのものが構成できなくなるため、2 を理由に 1 を省いてはならない。

**理由:** `commit-wave` も line_id 一致を検証するが、その時点では「どのチャンクが失敗したか」が分からない。
前段で明示エラーにすることで、再投入すべきチャンクを特定できる。`--out` の形式を現行と同一に保つことで
`commit-wave` の入力契約は不変（＝並列化しても下流ロジックは無改修）。

### 4.7 状態一貫性・再開

- `bfs-state.json` の書き手は `commit-wave`（Bash・単一）に集約したまま。並列化するのは**分類のみ**。
- `discovery-log.md` の書き手も `commit-wave` に集約する（§4.5(e)）。classifier は自分の `OUT_FILE` のみ Write する。
- **途中失敗時の再開（経路は1本に統一する）:** `wave_write_complete=false` の波は、
  **必ず `search` から再開する**（hits を再利用して `search` を飛ばす経路は設けない）。
  この経路統一は **Stage 1 で成立させる**が、**再開手順の中身は Stage 1 と Stage 2 で異なる**
  （Stage 2 の手順はチャンク・`merge_classification.py` という **S2 成果物に依存する**ため、
  Stage 1 時点の `recovery-procedures.md` にそのまま書くと存在しないファイルを参照することになる）。
  したがって以下のとおり段階別に規定する。

  **【S1】Stage 1 の再開手順**（チャンク分割前。分類は単一コンテキストで1回）
  1. `search` を再実行する。`cmd_search` は `data["current_wave"]` を進めず、line_id 採番は
     呼び出しごとにリセットされるローカルカウンタ（`_next_line_id` の `line_n`）で `W{wave}-R{n}` を振る。
     **ただし現行の `cmd_search` は再実行が冪等ではない**（下記「再 `search` の冪等性の担保」）。
     §4.5(g) の是正を入れて初めて「同一 state・同一コード内容に対して同一の line_id が
     決定的に再生成される」が成立する。**§4.5(g) は本経路統一の前提条件であり Stage 1 に含める。**
  2. 既存の `wave-{N}-class.json` は、**line_id 集合が一致することを条件にそのまま再利用してよい**
     （一致しない場合は分類をやり直す）。**一致判定は `commit-wave` の既存スキーマ検証
     （`hits と classification の line_id が一致しません` で異常終了）として決定的に行われるため、
     再利用の可否を人／エージェントが目視照合する必要はない**（不一致ならコミットは必ず失敗する）。
     Stage 1 に `merge_classification.py` は存在しないが、判定主体がスクリプト側にある点は
     【S2】と同じである（CLAUDE.md「決定的処理はスクリプト」）。
     **ただし line_id 一致は再利用の必要条件であって十分条件ではない** — `_next_line_id` は
     `f"W{wave}-R{line_n}"` の**位置カウンタ**でありファイル・行番号・マッチ内容を反映しないため、
     中断中に対象コードが変更されヒット総数だけが同じになると、**line_id 集合は一致したまま各 id が
     別の行を指す**。この場合は再利用せず分類をやり直す（手順1 の「同一コード内容に対して」が前提条件である）。
     再利用した場合、`commit-wave` は §4.5(d)「再利用波の判定」
     （classification ファイルの mtime < `classify_started_at`）により
     `classify_wall_ms: null` / `classify_wall_ms_reused: true` とし、§4.9 の集計から除外する
     （**実際の分類が行われていない波を計測値として採らないため**）。
  3. `commit-wave` の既存クラッシュ再開（`_truncate_wave_section` による書きかけ Wave セクションの
     切り捨て）に接続する。

  **【S2】Stage 2 の再開手順**（チャンク並列分類の導入後）
  1. 【S1】手順1 と同一。加えて「同一のチャンク構成が決定的に再生成される」ことも要件になる。
  2. 既存のチャンク classification（`wave-N-chunk-*-class.json`）は、**line_id 集合が一致することを条件に
     そのまま再利用**し、欠落しているチャンクのみ classifier を再投入する。
     **一致判定の主体は `merge_classification.py`（決定的処理）であり、SKILL は判定しない**
     （CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」）。判定内容は §4.6 の処理6 に規定する。
     **どのチャンクが欠落しているか（classifier が `OUT_FILE` を書かずに終了した分）の特定も
     `merge_classification.py` の責務であり、§4.6 の処理8 が stderr へ一覧を出力する。**
     旧ランの stale なチャンクファイルが混入しないよう、`search` は書き出し前に当該波の既存チャンクを
     削除する（§4.5(b)）。**チャンクを1件でも再利用した波は、`merge_classification.py` が出力する
     `min_chunk_mtime` を経由して `commit-wave --chunk-mtime-min` へ渡り、`classify_wall_ms_reused: true`
     として §4.9 の集計から除外される**（§4.5(d)「判定方法〔S2〕」・確定済み。
     現行の `--classification` ファイル自身の mtime では Stage 2 の再利用を検出できないため、
     【S1】手順2 のファイル mtime 方式をそのまま適用するのではなく、この別チャンネル方式を用いる）。
  3. 【S1】手順3 と同一。

#### 4.7.1 Stage 1 の再開経路統一（Before/After）

**(1) `ClaudeCode/.claude/agents/xddp-specout-agent.md`「### Step 2: BFS ループ」の「クラッシュ再開:」ブロック〔S1〕**

変更前:
> **クラッシュ再開:** commit-wave 実行前にエージェントがクラッシュした場合、`status` を実行すると
> `wave_write_complete: false` が返る。この場合は同じ `wave-{N}-hits.json` を使って classification を
> 作り直し（既に作成済みならそのまま再利用）、`commit-wave` を再実行すればよい（discovery-log.md の
> 書きかけ Wave セクションはスクリプトが自動的に切り捨てて再構築する。二重記録は発生しない）。

変更後:
> **クラッシュ再開:** commit-wave 実行前にエージェントがクラッシュした場合、`status` を実行すると
> `wave_write_complete: false` が返る。この場合は**必ず `search` から再開する**（`search` を飛ばして
> `commit-wave` だけを再実行してはならない。分類区間の計測が中断中の待ち時間で汚染されるため）。
> `search` は `current_wave` を進めず、同一 state・同一コード内容に対して同一の line_id を決定的に
> 再生成する。既存の `wave-{N}-class.json` は **line_id 集合が一致する場合に限り再利用してよい**
> （一致しない場合は分類をやり直す）。再利用した波は `commit-wave` が自動的に
> `classify_wall_ms_reused: true` として記録し、計測の集計対象から外す（人が申告する必要はない）。
> discovery-log.md の書きかけ Wave セクションはスクリプトが自動的に切り捨てて再構築する。二重記録は発生しない。

**(2) `ClaudeCode/.claude/skills/xddp.04.specout/recovery-procedures.md`〔S1〕**

変更前: 再開経路に関する統一規定は**存在しない**（`## Re-discover Processing`・`## Paused-at-limit Handling`
はいずれも「Discovery エージェントを再起動する」までを規定し、波の途中失敗からの再開手順を持たない）。

変更後: 新規セクションを追加する。**スクリプト呼び出しは同ファイルの既存記法に合わせること**
（実行コマンド5件〔`re-discover` 1・`prune` 1・`finish` 3〕はいずれも
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py {sub} --path {CR_PATH}/04_specout/{repo}/bfs-state.json …` 形式である。
裸のコマンド・`{STATE}` のような当該ファイルで未使用のプレースホルダ・引数の省略を持ち込むと、
**実行できない再開手順が運用手順書に載る**）。
> ## Wave 途中失敗からの再開（経路統一）
>
> **Input:** `CR_PATH`, `repo`, `TODAY`
>
> `bfs-state.json` の `wave_write_complete` が `false` の波は、**必ず `search` から再開する**。
> `search` を飛ばして `commit-wave` を再実行する手順は用いない（分類区間の計測が中断中の待ち時間で
> 汚染されるため）。
>
> 1. 波番号 `{N}` を以下で確認する:
>    `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py status --path {CR_PATH}/04_specout/{repo}/bfs-state.json`
>    出力の `current_wave` が `{N}` である。そのうえで `search` を再実行する:
>    `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py search --path {CR_PATH}/04_specout/{repo}/bfs-state.json --hits-out {CR_PATH}/04_specout/{repo}/wave-{N}-hits.json`
>    `current_wave` は進まず、line_id は決定的に再生成される。
> 2. 既存の `wave-{N}-class.json` は **line_id 集合が一致する場合に限り再利用してよい**。
>    一致しない場合は分類をやり直す。**一致判定は `commit-wave` が自動で行う**
>    （不一致なら「hits と classification の line_id が一致しません」で異常終了する）ため、
>    人が2ファイルを目視照合する必要はない。
>    **ただし中断中に対象コードを変更した場合は再利用してはならない。** line_id は位置カウンタ
>    （`W{wave}-R{n}`）であり内容を反映しないため、ヒット総数が同じなら line_id 集合は一致したまま
>    各 id が別の行を指しうる。コード変更を挟んだ再開では既存 `wave-{N}-class.json` を削除し、
>    分類をやり直すこと。再利用した波は `commit-wave` が
>    `classify_wall_ms_reused: true` として記録し、計測の集計対象から外す。
> 3. 以下を実行する:
>    `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py commit-wave --path {CR_PATH}/04_specout/{repo}/bfs-state.json --hits {CR_PATH}/04_specout/{repo}/wave-{N}-hits.json --classification {CR_PATH}/04_specout/{repo}/wave-{N}-class.json --today {TODAY}`
>    discovery-log.md の書きかけ Wave セクションはスクリプトが自動的に切り捨てて再構築するため、
>    二重記録は発生しない。

> **注（上記 (2) のセクションに係る）:** **(2)** で追加するセクションは Stage 1 時点の手順であり、
> チャンク分割（`wave-{N}-hits-chunk-{K}.json`）と `merge_classification.py` は**まだ存在しない**ため参照しない。
> Stage 2 で並列化本体を実装する際に、**(2) のセクションを** §4.7【S2】の手順
> （チャンク単位の再利用・`merge_classification.py` による一致判定）へ差し替える
> （差し替え対象は (2) のみであり、下記 (3) は対象外）。
> **その差し替え時に、手順1 の `status`（state 全体を出力）を必ず解消すること。**
> Stage 1 時点では `--brief`（§4.5(f)）も `search --hits-dir`（§4.5(b)）も未実装であるため
> 全体出力の `status` を使うが、Stage 2 ではこれを `status --brief` へ置き換えるか、
> `search --hits-dir` により波番号の事前取得自体が不要になるため当該行を削除する。
> §6 Stage 2 の確認項目「`recovery-procedures.md` 側に state 全体を出す `status` 呼び出しが
> 残っていないこと」は、この差し替えと1対1で対応する。

**(3) `ClaudeCode/.claude/agents/xddp-specout-agent.md`「### Wave 0 完了後: モジュールカタログによる BFS 優先度設定」節〔S1〕**

§4.5(g) により LOW 退避の **state への反映タイミング**が `search` から `commit-wave` へ移るため、
当該節の説明が不正確になる（`search` 直後の `bfs-state.json`・`checkpoint.md` には退避が現れない）。
§4.7 の再開手順は人が state を確認する運用を前提とするため、退避漏れと誤認されないよう是正する。

変更前:
> `search` 実行時、MODULE_PRIORITY_LOW に属する frontier シンボルは自動的に
> `low_priority_frontier` へ退避され、HIGH/MEDIUM 分の frontier が尽きた波で自動的に繰り込まれる。

変更後:
> `search` 実行時、MODULE_PRIORITY_LOW に属する frontier シンボルは退避対象として判定され、
> hits の `deferred_low` に載って `commit-wave` が `low_priority_frontier` へ反映する
> （**`search` 直後の `bfs-state.json`・`checkpoint.md` にはまだ現れない**）。
> 退避されたシンボルは HIGH/MEDIUM 分の frontier が尽きた波で自動的に繰り込まれる。

**再 `search` の冪等性の担保（現行コードの既存不具合・是正必須）:**
現行の `cmd_search` は末尾で `data["low_priority_frontier"] = low` を書き込む一方、
`data["frontier"]` は**一切更新しない**（更新は `cmd_commit_wave` のみ）。
`module_priority_computed` が真の通常経路（Wave 1 以降）で、これが2つの非冪等を生む。

| # | 事象 | 影響 |
|---|---|---|
| (i) | `this_wave` が空になり `this_wave, low = low, []` の入れ替えが起きた波では、繰り越された LOW エントリが `this_wave` へ移されたうえで `low_priority_frontier = []` が書かれる。これらは `frontier` に存在しないため、`commit-wave` に到達せず再 `search` すると**frontier からも low からも消える** | **取りこぼし（重大）** — 親プランの不変条件「確定影響ファイルの取りこぼしゼロ」に直接抵触 |
| (ii) | 入れ替えが起きない波では `low.extend(new_low)` が再実行のたびに繰り返され、同一エントリが累積する | 後続波で同一シンボルを重複検索し、分類トークンと `raw_hits` を無駄に増やす |

この不具合は**現行コードに既に存在する**（Phase 3 とは独立の既存欠陥）が、現行の再開手順は
`xddp-specout-agent.md` の「クラッシュ再開:」ブロックが「`search` を飛ばして `commit-wave` を再実行」と
規定しているため踏まれにくかった。**本節はこれを「唯一の再開経路」に格上げするため、
潜在バグを常用経路に載せることになる。** したがって §4.5(g) の是正を Stage 1 に含め、
基準線（ゴールデン）採取より**前**に適用する（汚染された基準線を採ると Stage 2 の等価性検証が無意味になる）。

- **この統一の目的（計測の正しさ）:** 再開時に `search` が走ることで `classify_started_at` /
  `classify_started_wave` が必ず書き直され（§4.5(c)）、**中断中の人の待ち時間が
  `classify_wall_ms` に混入しない**。`search` を飛ばす再開経路を残すと、最初の `search` 時刻からの
  差分が計測されて Stage 2 着手ゲート（§4.9）を誤成立させるため、経路を1本に統一することが
  Stage 1 の計測品質の前提条件になる。`recovery-procedures.md` にも同じ規定を書く（§3 参照）。
- **マルチリポジトリの独立性（2つの側面を分けて規定する）:**
  - **状態の独立性:** repo ごとに `bfs-state.json`・波番号・discovery-log が独立しており、
    ある repo の再開処理が他 repo の状態に影響を与えることはない。
  - **失敗時の停止粒度:** §4.2 の step a（`search`）／step c（`merge_classification.py`）／
    step d（`commit-wave`）の**いずれの失敗も、失敗した repo のみを ACTIVE_REPOS から外す**
    （波ループ全体を止めない）。同じ波の他 repo はその波を最後まで完了する。
    - **step a 失敗:** 当該波は未コミットで state は前波の確定状態のまま。原因を除去すれば
      そのまま `search` から再開して安全であり、本節の再開手順を要しない。
    - **step c 失敗:** state は `wave_write_complete=false` のまま残るため、本節の再開手順
      （再 `search` ＋既存チャンク結果の再利用・欠落チャンクのみ再投入）にそのまま接続する。
    - **step d 失敗:** `commit-wave` は fail-loud（§4.5(g)）・スキーマ検証で異常終了する場合に
      state も discovery-log も変更しないため、state は `search` 直後（`wave_write_complete=false`）の
      まま残る。step c と同じく本節の再開手順に接続する。

    したがって「1 repo の失敗で他 repo の完了済み分類が捨てられる」
    ことはないが、**失敗 repo だけが波の進み方で遅れる**（波番号が repo 間でずれる）。
    これは元々「波番号は repo ごとに独立して進む」（§4.2 step e）設計であり問題にならない。

### 4.8 チャンクサイズ・並列度（設定キー・S2）

| キー | 既定値 | 効果 |
|---|---|---|
| `SPECOUT_CLASSIFY_CHUNK_SIZE` | `40` | 1チャンクに含めるヒット行数の目安（ファイル単位グルーピング後の貪欲詰め）。`0` で分割無効（＝常に単一チャンク）。波のヒット数がこの値以下なら分割しない |
| `SPECOUT_CLASSIFY_PARALLEL` | `4` | classifier の同時起動数上限（**全 ACTIVE_REPOS のチャンクを合算した値**）。超過分はバッチに分けて順次起動する |

既定値は「起動オーバーヘッドと分割効果の釣り合い」の初期値であり、**根拠のある実測値ではない**。
Stage 1 の実測（`classify_wall_ms` × `raw_hits` 分布）で見直す前提の暫定値として設定する。
配線は `SPECOUT_BACKEND` の前例（`xddp.config.md` テンプレート → `xddp.common`「## Load Config」の
Output 一覧・Process 手順2 → `xddp.04.specout/SKILL.md` の受領キー列挙行 → 各呼び出し）に合わせる。

### 4.9 実装順序（計測先行・2段階）

**Stage 1（本プランの承認対象）:**
0. **§4.5(g)（`cmd_search` の非破壊化）と §4.7 の再開経路統一（`xddp-specout-agent.md`「クラッシュ再開:」
   ブロック・`recovery-procedures.md`）を実装・デプロイする。**これらは計測値と基準線の正しさの前提条件であり、
   手順1・2 より**前**に完了させる（この手順があるため Stage 1 は「計測のみ」ではない。§5 参照）。
1. §4.5(c)(d) の計測を実装・デプロイし、実 CR の波あたり `classify_wall_ms`・`classified`・
   `raw_hits`・波数 × リポジトリ数の分布を metrics.jsonl で採取する
   （`classified` はゲート判定用、`raw_hits` は Phase 1/2 の削減率を併せて把握するための参考値）。
2. **不変条件1 の基準線（ゴールデン）を、BFS 構造が変わらない Stage 1 のうちに採取する。
   採取は §4.5(g)（`cmd_search` の非破壊化）の適用**後**に行うこと**（是正前に採取すると、
   繰り越し LOW の消失を含んだ基準線になり Stage 2 の等価性検証が無意味になる）。
   現行アーキ（単一コンテキスト分類）で smoke シードおよび実 CR を実行し、
   `discovery-log.md` の確定影響ファイル一覧と `bfs-state.json` の `frontier`（次波 frontier）を
   保存する。Stage 2 の等価性検証はこの基準線と比較する（§6 参照）。
3. **案Y（Agent/Task ツールを持つサブエージェント）の最小スパイクを実施し、結果を記録する。**
   §2 で案Y を「前例なし・実現可否未検証」として不採用にした一方、§4.2 のコンテキスト蓄積緩和策の
   最終手段（repo ごとの wave driver を別サブエージェントに切る構成）は**案Y の実現可否に依存**している。
   すなわち**案X の唯一の退避先が未検証の案Y**という構造になっており、Stage 2 でコンテキスト枯渇が
   判明してから退避先の実現可否を調べ始めると手戻りが最大化する。
   **実施手順（この範囲を超えないこと）:**
   1. `ClaudeCode/.claude/agents/_spike-agent-tool.md` を作成する。
      frontmatter は **`name: _spike-agent-tool`（ファイル名 stem と一致させること。
      `refcheck.py` の `check_agent_name_frontmatter` が agents ディレクトリの全 `*.md` について
      `name:` と stem の不一致を error 判定するため、一致させないとスパイク中に `make test` が赤になる）**、
      `tools:` は Agent と Read のみ。本文は「子エージェントを1つ起動し、その戻り値をそのまま返す」だけ。
   2. `bash ClaudeCode/setup.sh` で `~/.claude/` へ配備する。
   3. Agent tool で `_spike-agent-tool` を1回起動し、**子エージェントが起動できたか**を確認する。
      子には**成果物を書き換えない引数**で呼べるエージェントを使う
      （例: `xddp-reviewer` は `tools:` に Write を含むため、`OUTPUT_FILE` を渡さず
      「このファイルを読んで1行で要約せよ」とだけ指示する。既存の CR・成果物には一切触れない）。
   4. 結果（可否・エラーメッセージ）を**本手順3の直下に追記**する（§7「## 7. レビュー」は
      AI レビュー結果へのリンク欄であり、スパイク結果の記録先ではない）。
   5. **後始末:** `ClaudeCode/.claude/agents/_spike-agent-tool.md` と `~/.claude/agents/_spike-agent-tool.md` を
      削除する（コミットしない）。`make test` が緑であることを確認する。

   **スパイク結果（2026-08-08 実施・記録）:**

   | 項目 | 結果 |
   |---|---|
   | ネストしたサブエージェント起動の可否 | **可能**。`tools: *` を持つ `general-purpose` エージェントから子エージェント（`xddp-reviewer`）を1回起動し、子の戻り値がそのまま親経由で返ることを確認した（子はファイルを書かない引数で呼び出し、既存 CR・成果物には触れていない） |
   | `_spike-agent-tool`（`tools:` に Agent を明示列挙した専用定義）での検証 | **本セッションでは実施不可**。定義ファイルを作成し `setup.sh` で `~/.claude/agents/` へ配備したうえで Agent tool から起動したところ `Agent type '_spike-agent-tool' not found`（利用可能一覧は起動時の登録分のみ）となった。**エージェント定義の登録はセッション開始時に解決される**ため、新規追加した定義は新しいセッションを開始しないと見えない |
   | 未検証のまま残る点 | frontmatter の `tools:` に `Agent` を**明示列挙**した場合に当該ツールが実際に付与されるか。上記のとおり検証には別セッションが必要 |

   **結論:** ネストしたサブエージェント起動そのものはハーネス上**技術的に可能**であり、案X の退避先
   （repo ごとの wave driver を別サブエージェントに切る構成）は原理的に成立しうる。ただし
   「`tools:` への明示列挙で Agent ツールを付与できるか」は未確定であり、Stage 2 でこの退避先を
   採る場合は着手前に別セッションでの再スパイクを要する。
   §4.2 のコンテキスト蓄積緩和策は「推奨」のまま据え置く（実現不可と判明した場合の「必須」格上げには当たらない）。

   既存の挙動を一切変えず低コストで実施できる。
   - 実現可能と判明 → §2 の比較表と Stage 2 の設計選択肢を事実に基づいて更新する
   - 実現不可能と判明 → §4.2 のコンテキスト蓄積緩和策を「推奨」から**「必須」に格上げ**し、
     許容量を超える見込みなら Stage 2 に着手しない判断材料とする

**2段階構成の根拠（「切り戻し不能」ではない）:** 移設対象は `SKILL.md`・`agents/*.md`・`scripts/*.py` という
**git 管理下の定義ファイル**であり、`git revert` で復元できる。CLAUDE.md「後方互換性ポリシー」も
「既存 CR・成果物が新しいフォーマットに追従できない場合は再実行・再生成を求めることを許容する」と
明記している。実際に切り戻せないのは**移設後に開始した進行中 CR の途中状態のみ**であり、
これはポリシー上「再実行を求めてよい」範囲に収まる。
したがって本プランを2段階に分ける根拠は「切り戻し不能」ではなく、
**費用対効果が未実測であること**（CLAUDE.md「推測ではなく計測に基づいて最適化」）に一本化する。

**Stage 2 着手ゲート（数値基準）:** 以下を**いずれも**満たす場合にのみ §4.1〜§4.8 の本体を実装する。
満たさない場合は本プランを保留し、Stage 1 の計測と基準線のみを成果として残す。

- `classify_wall_ms` が **60,000ms（1分）以上**の波が、**有効波の 20% 以上**を占める
  （**比率の分母は「除外後の有効波」とする**。**下記「外れ値の扱い」に列挙した除外波は分子・分母の
  双方から除く**——カテゴリを個別に再列挙せず、常に当該箇所を唯一の定義とする
  〔カテゴリが増減するたび複数箇所を直す必要をなくすため。§4.5(d) で metrics のキー件数表記を
  撤廃したのと同じ考え方〕。除外前の全波を分母に採ると、除外が多い実行ほど分子だけが減って自動的に
  ゲート不成立＝**偽陰性**へ振れるため）。
  **有効波が 3 波未満の場合はゲート判定を行わない**（統計的に意味を持たないため、採取のやり直しか
  人の判断とする）
- その該当波の **`classified`**（post-dedup/filter の実分類行数）の中央値が
  `SPECOUT_CLASSIFY_CHUNK_SIZE` の既定値（40）の **2倍以上**
  （＝チャンク分割で実際に2並列以上になる規模）

**ゲート指標に `classified` を用いる理由（`raw_hits` ではない）:** `raw_hits` は dedup・保守的フィルタ・
noise-collapse を**適用する前**の生ヒット数であり（`_process_command` の冒頭でインクリメントされ、
除外処理はその後に走る）、チャンク分割の対象になるのは post-filter の `hits`（= metrics の `classified`）
である。Phase 1/2 のヒット削減が効いている環境ほど両者は大きく乖離するため、`raw_hits` で判定すると
**「生ヒットは多いが分類対象は 40 未満（分割しても常に単一チャンク）」の案件で誤ってゲートが成立し、
切り戻し不能なループ移設に着手する**判断ミスを招く。`raw_hits` は削減率の把握用に併記するに留める。

**外れ値の扱い:** `classify_wall_ms` は人の介在時間を含む上界値であるため（§4.5(d)）、
以下の波を集計から除外し、代表値には平均ではなく**中央値**を用いる。
- `paused`（paused-at-limit / 2nd）を挟んだ波
- `classify_wall_ms_suspect: true` の波（規定外の手動操作による汚染の疑い。下記「残存する限界」参照）
- `classify_wall_ms_reused: true` の波（既存 classification を再利用した再開波。実際の分類が行われて
  おらず**過小**計測となるため。判定方法は §4.5(d)「再利用波の判定」）
- **`classify_wall_ms` が `null` の波（計測不成立）** — α＝開始時刻の波不一致・キー欠損・再利用判定成立の
  いずれかで値が得られなかった波。値がない以上、分子にも分母にも算入できない

**除外波は捨てずに別掲する（必須）:** 除外は分布を非対称に歪めうる。とくに `suspect` 除外は
**最も長い波＝並列化の必要性を最も強く示す証拠**を母数からも分子からも落とす方向に働く。
したがってゲート判定の提示時には、**除外した波数と、その各波の `classify_wall_ms`・`classified`・
除外理由（上記に列挙した各カテゴリ。`paused` / `suspect` / `reused` / `classify_wall_ms: null`＝計測不成立）を
一覧で承認者へ添付する**。
**各波の除外理由は1つに定める**（優先順位: `paused` ＞ `reused` ＞ `suspect` ＞ `classify_wall_ms: null`）。
カテゴリは定義上オーバーラップするため（`reused` の波は §4.5(d) の規定により必ず `classify_wall_ms: null`
にも該当する）、一意化しないと二重計上が起きる。**除外波数は波の実数で数え、カテゴリ別内訳の合計と
一致させること**（承認者が受け取る唯一のゲート根拠資料であり、二重計上は除外の妥当性検証を誤らせる）。承認者は除外の妥当性を
自分で検証できる状態でゲート判定を受け取ること。

**クラッシュ再開波の扱い（過大側は設計で解決・過小側はフラグで除外する）:**

- **過大側（人の待ち時間の混入）— 設計で解決する:** §4.7 のとおり再開経路を「`search` から再開する」の
  1本に統一するため、再開時には `classify_started_at` が必ず書き直され
  （§4.5(c) の「`cmd_search` 正常終了 → 2キーを毎回上書き」）、中断中の人の待ち時間は
  `classify_wall_ms` に混入しない。
- **過小側（既存 classification の再利用）— フラグで除外する:** 経路統一だけでは解決しない。
  §4.7 の再開手順は既存 classification／チャンク結果の再利用を明示的に許容しており、
  §4.5(g) により再 `search` が完全に冪等になる（＝ line_id が一致する）ため、
  **再開時の再利用はむしろ常に成立する**。再利用した波の `classify_wall_ms` は
  「再 `search` → 既存結果をそのまま commit」までの数秒〜数十秒となり、その波の実際の分類所要時間を失う。
  この過小値は `paused` 除外にも `classify_wall_ms_suspect`（過大側のみ検出）にも掛からず、
  中央値を押し下げてゲートを**偽陰性**（Stage 2 を不要と誤判定）へ振らせる。
  したがって §4.5(d)「再利用波の判定」（classification ファイルの mtime < `classify_started_at`）で
  機械判定し、`classify_wall_ms_reused: true` の波を集計から除外する（除外波は別掲する）。
- なお `wave_write_complete` から再開波を導出する方式は**実装不能**である（§4.5(d) の注記を参照）。
  再利用の検出に mtime 比較を用いるのはこのためである。
この経路統一は `xddp-specout-agent.md` の「クラッシュ再開:」ブロックと `recovery-procedures.md` の
両方に対して **Stage 1 で**適用する（§3 の S1 行。Stage 1 では BFS ループがまだエージェント内にあるため、
そこを直さない限り経路統一は成立しない）。

**残存する限界と機械的な安全弁:** 規定外の手動操作（`search` を飛ばして classification を作り直し、
その波の**最初の** `commit-wave` としてコミットする等）を行った波は、2キーが残存し波も一致するため
`classify_wall_ms` に人の待ち時間が丸ごと混入する（この場合 `null` にはならない。
なお「一度正常終了した `commit-wave` を再度手動実行した場合」は、§4.5(g) の fail-loud により
**exit 非0 となって metrics 行そのものが生成されない**（`null` にはならない）。
**最終波（BFS を完了させた波）も含めてこれが成立するのは、fail-loud の条件に
「`state == "complete"`」と「`wave <= last_completed_wave` かつ `wave_write_complete`」を加えているためである**
（最終波では `current_wave` が進まないため、fail-loud の条件1（β）だけでは捕捉できない。§4.5(g) 参照）。
α＝開始時刻の波不一致による `null` は、`commit-wave`／`finish`／`prune`／`set-state` が2キーを削除し
`merge-frontier`／`record-module` は波を進めないため、**state を直接編集しない限り実運用では再現しない**）。これを機械的に検出するため、
**`cmd_commit_wave` は `classify_wall_ms` が閾値を超える場合に
`classify_wall_ms_suspect: true` を metrics へ併記する〔S1〕**（閾値内なら `false`、
`classify_wall_ms` が `null` なら `null`。§4.5(d)）。
§4.9 のゲート判定では `classify_wall_ms_suspect: true` の波を集計から除外し（ただし上記「除外波は捨てずに
別掲する」に従い一覧を添付する）、さらに `classify_wall_ms` 上位3波を discovery-log の Wave セクションと
突き合わせて**人が目視確認**する。

> **閾値 1,800,000ms（30分）は暫定値であり、根拠のある実測値ではない**（§4.8 の既定値と同じ位置づけ）。
> 現行の閾値は「規定外の手動操作による汚染」と「正当に非常に遅い波」を区別できないため、
> **Stage 1 の実測分布が得られた時点で見直す**。見直しの選択肢として、固定閾値ではなく
> **相対基準（例: 全波の `classify_wall_ms` 中央値の N 倍）**への切り替えを併記しておく
> （分布判明後に仕様変更なしで調整できるようにするため）。いずれの基準を採る場合も、
> 除外波の別掲は必須とする。

**トークン増分の予測上限（承認者への提示物）:** Stage 1 で採取した `classified` 分布から
Stage 2 の `chunk_count` 分布を予測し、`chunk_count × (分類ルール + CRS のトークン量)` として
**工程04 の単価増分の予測上限**を算出して承認者へ提示する（現行の基準値は
`tools/harness/smoke_config.md`「## 工程別実行モデル」の工程04 実測 `~0.55 $/起動`）。
定量基準がないと §6 の「増分が §2 の見積り（中）の範囲」がどんな結果でも合格になってしまうため、
**Stage 2 着手ゲートの判定時にこの予測上限を必ず添えること**。合否閾値は §6 に定める。

#### 4.9.1 トークン増分のパラメトリック予測モデル（2026-08-08 算出）

`chunk_count` 分布は Stage 1 の実測を待つが、**`classified` を変数とした上限式と感度表は先に確定できる**。
実測値が出た時点で下表に当てはめるだけでゲート判定の提示物が完成する。

**(a) 静的部分の実測（文字数は実測、トークン数は下記換算の推定値）**

| 項目 | 実測文字数 | 推定トークン |
|---|---|---|
| 移設対象の分類ルール（`xddp-specout-agent.md`「b. hits の意味判定」＋「伝播種別の判定ルール」＋「grep未対応パターンへの対処」） | 9,088 | **≈ 2,950** |
| CRS（smoke シード `CR-2026-970`） | 1,277 | ≈ 620 |
| CRS（小規模実 CR 相当 `CR-2026-900`） | 3,420 | ≈ 1,843 |
| CRS（大規模実 CR 相当 `CR-2026-950`） | 19,422 | ≈ 13,163 |
| `known_symbols`（visited∪frontier 200シンボル想定・**未実測の仮定値**） | — | ≈ 800 |

> **トークン換算の前提（推定であり実測ではない）:** 日本語文字＝1トークン、ASCII＝4文字/トークンの近似で
> 算出した。`/v1/messages/count_tokens` による実測ではない（本セッションでは API 認証が未設定）。
> **Stage 2 再承認時には `count_tokens` で再計測すること**（換算誤差は ±30% 程度を見込む）。

**(b) チャンク数の上界（分割方式によらず成立する順に）**

| # | 上界 | 成立条件 |
|---|---|---|
| 1 | `chunk_count ≤ f`（当波の異なるファイル数） | **常に成立**。§4.5(b) は「1ファイルのヒット数が `--chunk-size` を超える場合は当該ファイル単独でチャンク化する」＝ファイルグループを分割しないため、各チャンクは必ず1グループ以上を含む |
| 2 | `chunk_count ≈ ceil(n / C)`（`n` = `classified`、`C` = `SPECOUT_CLASSIFY_CHUNK_SIZE`） | ファイル粒度が `C` に比べ十分小さい場合の実用推定 |
| 3 | `chunk_count ≤ max(1, ceil(2n / C))` | 貪欲詰めの最悪ケース（first-fit のビン数上界）。安全側を採るならこちら |

**(c) 増分式（2026-08-09 改訂: 固定ブートストラップ項を追加）**

現行は「repo ごとに specout エージェントを1回起動し、分類ルール＋CRS を**1回だけ**読む」構成のため、
複製コストの基準線は 1 セット分である。Stage 2 では**チャンクごとに新規サブエージェントが1体立つ**ため、
`T_dup`（移設される分類ルール・CRS・シンボル集合）だけでなく、**サブエージェント1体ごとに必ず載る
固定ブートストラップ**（エージェント定義本体・`CLAUDE.md`・ツール定義）も `chunk_count` 倍に複製される。
この項はモデルの当初版（2026-08-08 算出）には含まれておらず、
[PLAN-20260806-specout-phase3-stage1-measurement.md](PLAN-20260806-specout-phase3-stage1-measurement.md) §5.5
の実測で判明した欠落である。

```
T_dup   = T_rules + T_CRS + T_known              （1チャンクあたりの複製入力トークン。§4.9.1(a)）
T_boot  = 固定ブートストラップ（classifier エージェント定義＋CLAUDE.md＋ツール定義。
          実測 ≈33,000〜49,000。汎用エージェントでの計測値であり、
          軽量な classifier 専用定義〔§4.4〕では減る見込みだが未実測）
ΔTokens = Σ_waves [ chunk_count × T_boot + (chunk_count − 1) × T_dup ]   （キャッシュ無・上限値）
Δ$      = ΔTokens × 入力単価
```

**プロンプトキャッシュを考慮した式（有効性を実測で確認済み。measurement §5.5・§5.6）:**
兄弟サブエージェント間でプレフィクスがバイト同一であれば、波の各バッチで1体目が書き込み（1.25×）、
残りは読み出し（0.1×）で済む（波をまたいだキャッシュ再利用は含めない安全側の式。実際にはウォーム
アップ後は波をまたいでもヒットするため、下式は上限値である）。

```
ΔTokens_cached = Σ_waves [ T_boot × 1.25 + (chunk_count − 1) × T_boot × 0.1
                          + T_dup  × 1.25 + (chunk_count − 1) × T_dup  × 0.1 ]
```

**この式が成立する前提条件（§4.2 step b の設計要件と1対1対応）:** チャンク固有情報
（`CHUNK_FILE`・`OUT_FILE`・`chunk_id`）をプロンプト末尾に置き、先頭側をバイト単位で全チャンク同一に
保つこと。崩れるとキャッシュ無の式（上式）に戻る。

**(d) 感度表（`C = 40`・大規模実 CR 想定 `T_dup ≈ 16,913`・Sonnet 5 標準入力単価 $3.00/MTok）**

| 波数 W | 波あたり `classified` | 波あたり chunk | ΔTokens | Δ$（標準） | 工程04 実測 $0.55 比 |
|---|---|---|---|---|---|
| 3 | 80 | 2 | 84,565 | $0.254 | **+46%** |
| 3 | 160 | 4 | 186,043 | $0.558 | +102% |
| 3 | 320 | 8 | 388,999 | $1.167 | +212% |
| 5 | 80 | 2 | 152,217 | $0.457 | +83% |
| 5 | 160 | 4 | 321,347 | $0.964 | +175% |
| 5 | 320 | 8 | 659,607 | $1.979 | +360% |
| 10 | 160 | 4 | 659,607 | $1.979 | +360% |
| 10 | 320 | 8 | 1,336,127 | $4.008 | +729% |

> 単価は Claude Sonnet 5 の標準入力 $3.00/MTok。2026-08-31 までの導入価格 $2.00/MTok なら上記の 2/3。
> smoke ランのモデルは `tools/harness/smoke_config.md`「## 工程別実行モデル」により Sonnet 単一。

> **上表は `T_boot`（固定ブートストラップ）を含まない（2026-08-09 判明の欠落。§4.9.1(c) 参照）。**
> `T_boot` を含めた場合の効果は、実測（[stage1-measurement.md](PLAN-20260806-specout-phase3-stage1-measurement.md) §5.5・§5.6）で
> 得た CR-2026-990（自然波3波・Σ`chunk_count`=9・`T_boot` 実測 33,288）の実例で確認できる:
>
> | 条件 | ΔTokens | Δ$（$3.00/MTok） | §6 閾値 $0.55 |
> |---|---|---|---|
> | `T_dup` のみ（上表の式。§4.9.1(c) 旧版） | 43,776 | $0.131 | 収まる |
> | `T_dup + T_boot`・キャッシュ無（9体が各自書き込み） | 299,592 | $0.90 | **超過** |
> | `T_dup + T_boot`・キャッシュ共有あり（§4.2 step b の設計要件を満たす場合） | 68,240 | $0.20 | 収まる |
>
> **`T_boot` を無視すると増分を実態の約 1/7 に過小評価する。** 一方、§4.2 step b の設計要件
> （プレフィクスのバイト同一性・コールドスタート緩和）が満たされれば `T_boot` はキャッシュ共有により
> 実質無害化される。したがって Stage 2 再承認時の閾値判定は、**この設計要件が実装されていることを
> 前提条件として明示したうえで**行うこと（要件が満たされない実装では上表・(e) いずれの閾値内論も成立しない）。

**(e) 結論と、Stage 2 再承認への申し送り（重要）**

**§6 Stage 2 のトークン閾値「現行実測 `~0.55` の2倍以内」は、`chunk_count ≥ 2` の波が
数波以上ある現実的なケースでは、プロンプトキャッシュが効かない限り超過する。**
上表で 2倍以内（Δ$ ≤ $0.55）に収まるのは `W=3 / n=80`（+46%）だけである。

一方、**複製される内容の大部分（分類ルール ＋ CRS ＝ `T_dup` の約 95%）は全チャンクで
バイト単位に同一**であり、プロンプトキャッシュが効けば書き込み1回（1.25×）＋以降は読み出し（0.1×）
となる。同条件で試算すると：

| ケース | キャッシュ無 | キャッシュ有 | 削減率 |
|---|---|---|---|
| W=5 / n=160 | 321,347 tok ／ $0.964 | 65,956 tok ／ **$0.198** | −79% |
| W=5 / n=320 | 659,607 tok ／ $1.979 | 114,182 tok ／ **$0.343** | −83% |

いずれもキャッシュ有なら現行実測 $0.55 を下回る。したがって：

- **費用対効果の分岐点は「並列化そのもの」ではなく「classifier サブエージェントの
  安定プレフィクス（分類ルール＋CRS＋固定ブートストラップ）にプロンプトキャッシュが効くか」である。**
  さらに実測（stage1-measurement.md §5.5）により、**分岐点はそれよりも手前の
  「並列起動された兄弟サブエージェント間でキャッシュが共有されるか」にある**ことが判明した。
- **Stage 2 再承認の必須確認事項（2026-08-09 更新: 実測で判明した事項を反映）:**
  (1) ~~サブエージェント起動時に system プロンプト側のプロンプトキャッシュが有効かを実測で確認する~~
  → **完了**（stage1-measurement.md §5.5。単体 cache_read 率 96.2%）。
  (2) ~~兄弟サブエージェント間でキャッシュが共有されるか~~ → **完了**（同 §5.6。共有される。
  ただしコールドスタート時に約1〜2.5秒の競合窓あり）。
  (3) **設計要件として反映済み（本改訂・§4.2 step b）:** チャンク投入順を固定してプレフィクスを
  バイト一致させること、および最初のバッチはチャンク0を単独起動して競合窓を回避すること。
  **Stage 2 実装時にこの要件どおりに実装されているかの確認が引き続き必要**（§6 の該当チェック項目）。
  (4) `T_rules`・`T_CRS`・`T_boot` を `count_tokens` で実測し直し、(a)(c)(d) の各表を差し替える
  （本セッションでは API 認証が未設定のため未実施。文字数からの推定値のまま）。
  (5) ~~CRS を Read ツール経由で読む場合のキャッシュ適用可否~~ → **実測完了（2026-08-09。
  stage1-measurement.md §5.7）:** キャッシュ対象に**なりうる**（同時起動した兄弟の一方は CRS 読み込み分まで
  含めて完全ヒットした）が、固定ブートストラップ部分ほど確実ではなく、**確率的**である
  （同時起動したもう一方はヒットせず新規に書き込んだ。Read 呼び出し自体をモデルが生成するため、
  指示文が同一でもバイト完全一致が保証されない）。**Stage 2 実装時の推奨:** 確実性を優先するなら
  CRS 本文を classifier の起動プロンプト（オーケストレータが組み立てる静的文字列）へ直接埋め込み、
  モデル自身のツール呼び出し生成を経由させない設計に変更する。埋め込みとの費用対効果比較
  （プロンプト構築の複雑化・CRS 肥大時の起動プロンプト肥大とのトレードオフ）は Stage 2 実装時に行う。
- **`known_symbols`（≈800 トークンの仮定値）だけは波ごとに変わるためキャッシュが効かない。**
  visited が肥大する長い CR ではこの項が支配的になりうるので、Stage 1 の実測で
  `len(visited)` の分布も併せて採取しておくと精度が上がる。

**基準線採取の注意（判定集合の非対称性）:** §4.1 で採用した素名正規化は
`paramName[MEDIUM:{path}]` のスコープ限定を落とすため、判定集合は現行より**広がる**方向へ非対称に働く。
したがって Stage 2 の合否は「基準線に対して確定影響ファイル集合が**縮小しないこと**」で判定し、
拡大した場合は差分を人が確認して妥当性を判断する（漏れは増やさないが探索肥大の可能性があるため）。

**Stage 2 再承認時の必須補完事項（暗黙の先送りにしない・2026-08-09 更新: 対応済み分を反映）:**

- ~~§4.5(b)（チャンク分割出力）・§4.5(e)（`--unsupported-patterns` 追記）・§4.6（`merge_classification.py`）の
  Before/After 補完~~ → **完了**（本改訂で (b) は元より保持済みと確認、(e)・§4.6 に
  `plans/_template.md` §3 の書式に合わせた「変更前:」/「変更後:」枠を追加した）。
- ~~Stage 2 の再利用波検出方式（§4.5(d)「判定方法〔S2〕」）の確定と §6 への配線~~ → **完了**
  （`merge_classification.py` が出力する `min_chunk_mtime` を `commit-wave --chunk-mtime-min` へ
  中継する方式で確定し、§4.2 step c/d・§4.6 処理7・§6「Stage 2 決定的層」チェック項目に配線済み）。
- ~~§4.9.1 の増分モデルへの固定ブートストラップ項の反映~~ → **完了**（§4.9.1(c) に `T_boot` を追加し、
  (d) にキャッシュ有無別の実測当てはめ、(e) に必須確認事項の更新を反映した）。
- ~~プレフィクスのバイト同一性・コールドスタート緩和の設計要件化~~ → **完了**（§4.2 step b に追加し、
  §6「Stage 2 意味層」に対応する確認項目を追加した）。
- ~~引き続き未了（Stage 2 再承認までに必要）~~ **→ 2026-08-09 更新: 3点とも解消（うち1点は人の判断による受容）。**
  1. ~~`T_rules`・`T_CRS`・`T_boot` の `count_tokens` による実測~~ → **2026-08-09 人が判断し受容（実測は依然未実施）。**
     `ANTHROPIC_API_KEY` 未設定のため `count_tokens` 実測は本セッションでも実施できず
     （`CLAUDE_CODE_OAUTH_TOKEN` は CLI 専用スコープのため生 API 呼び出しへの流用は不可）、
     人は「文字数ベース推定値（±30%誤差見込み）のまま Stage 2 再承認へ進める」ことを選択した。
     したがって §4.9.1(a)(c)(d) の表は**推定値のまま**であり実測値への差し替えは行っていない。
     **Stage 2 実装時、実測と推定が乖離した場合（特にキャッシュ無効時の増分が閾値を超える場合）は
     `SPECOUT_CLASSIFY_CHUNK_SIZE` の引き上げ等で調整するリスクを人は許容済み**（§6 の
     「トークン増分が定量閾値内」チェック項目は `make smoke-full PHASE=04` の実測 $/起動で最終判定するため、
     このリスクは Stage 2 実装完了時点の実測ゲートで捕捉される）。
  2. ~~CRS が Read ツール経由でもキャッシュ対象になるかの検証~~ → **完了**（§4.9.1(e)(5)。
     stage1-measurement.md §5.7。対象になりうるが確率的。埋め込み設計への変更は Stage 2 実装時に検討）。
  3. ~~`phase04-multi` シードの生成~~ → **完了（2026-08-09）。**
     `test-fixtures/scratch-workspace-min/seeds/phase04-multi/`（CR-2026-991・svc-a/svc-b それぞれに
     UR1本・SP1本の極小構成。既存 `960`/`961` と同粒度）として手動最小化フィクスチャを作成し、
     `smoke_full.stage_workspace()` で実際にステージング（`ws/svc-a`・`ws/svc-b` が自己完結で展開され、
     `multi/` 同伴コピーが発生しないこと）を検証済み。`make test` 緑（詳細は下記「Stage 2 着手の外部依存」）。

**Stage 2 着手の外部依存（本プランの成果物ではない）:** §6 意味層のマルチリポジトリ検証に必要な
`test-fixtures/scratch-workspace-min/seeds/phase04-multi/` は、
`seeds/README.md` のレイアウト定義・`tools/harness/smoke_config.md` の工程別シード対応表・
`smoke_full.py` の `MULTI_PHASES`（`04`・`11`）に織り込み済みであり、当初は**校正ラン側で生成される
成果物**と位置付けていたが、Stage 2 意味層検証の前提条件として**校正ラン完了を待たず 2026-08-09 に
先行生成した**（`*-single` シードと `phase04-multi` は生成済み。**`phase11-multi` のみ依然未生成**）。
本プランはこの `phase04-multi` シード自体を成果物として追加するものではなく（既存の校正ラン方針・
`seeds/README.md` の位置付けは変更しない）、Stage 2 着手の前提条件（依存）が満たされた状態として扱う。

**理由:** 親プラン §8 備考「Phase 1/2 の計測結果を見てから着手判断」を具体化したもの。
CLAUDE.md「推測ではなく計測に基づいて最適化」に従い、費用対効果を事実で裏付けてから構造変更に入る。
Stage 1 は BFS ループの構造を変えず、変更は「metrics の追記」「既存の取りこぼし不具合の是正（§4.5(g)）」
「再開経路の統一」に限られるため、単独でデプロイしても安全である
（**ただし「挙動不変」ではない** — §5 参照。§4.5(g) は失われていたエントリが失われなくなる方向の変化であり、
Stage 1 の基準線はこの是正**後**に採取する）。

---

## 5. 影響範囲

- **影響するスキル・コマンド:** `/xddp.04.specout`（工程4a Discovery）。Stage 2 は SKILL とエージェント定義の
  構造変更を伴う。**Stage 1 は「metrics 追記のみで挙動不変」ではない** — 計測追加（§4.5(c)(d)）に加えて、
  (1) §4.5(g) の `cmd_search` 非破壊化（既存不具合の是正。フロンティア更新が `commit-wave` へ一元化される）、
  (2) `xddp-specout-agent.md`「クラッシュ再開:」ブロックと `recovery-procedures.md` の再開経路統一
  を含む。いずれも**正しい計測と正しい基準線を得るための前提条件**であり、Stage 1 に含めないと
  Stage 2 の投資判断そのものが成り立たない。(1) は取りこぼし不具合の是正であり、
  挙動変化の方向は「失われていたエントリが失われなくなる」＝改善側である。
- **影響する工程:** 工程4a のみ。生成される SPO・discovery-log・confirmed_files は**現行と等価**
  （分類の判定入力は §4.1 で狭まらないことを保証し、集約は `commit-wave` 一括のまま）。
  code-knowledge 参照（`_observation-memo.md`「## 既知制約との照合」）は `discovery-setup` の外へ
  **移設せず `init` の後段に置く**。当該節は現行実装でも成果物へ到達せず、新設計でも
  （`discovery-setup` に `commit-wave` が無く `confirmed_files` が常に空のため）無条件 no-op となるため、
  **成果物観点では現行と等価**である（中間ファイルの生成有無という内部差は document Step 0 の削除により
  成果物に現れない）。この既存欠陥の是正は本プランのスコープ外として §4.3 に記録し、
  申し送り4点を添えて**別プランで対応**する。
- **影響するエージェント:** `xddp-specout-agent`（モード再定義）、`xddp-specout-classifier-agent`（新規）。
  他の工程のエージェントには影響しない。
- **マルチリポジトリ:** 現行の「リポジトリごとに独立 Agent コンテキストで並列」という分離モデルが変わる。
  §4.2 step b で全 repo のチャンクを合算して並列投入することでリポジトリ間の並列度は維持するが、
  コンテキストの分離は失われる（メインコンテキストが全 repo の波ループを保持する）。
  `docs/specout-discovery-guide.md`「分離単位」表の更新が必要。
- **ハーネス:** `tools/harness/refcheck.py` は**検査B は改修不要**（`check_b_subagents` が
  `agents_dir / "{name}.md"` を自動解決するため）。ただし**検査Bが有効に働くには pass ブロックの
  書式要件（§4.2）を満たす必要がある**。一方**検査D（`check_d_script_wiring`）は改修が必要**であり、
  モジュール定数 `DETERMINISTIC_SCRIPTS` に `merge_classification.py` を追加しない限り、
  SKILL からの呼び出しフラグ誤記が `make test` でサイレントに素通りする（§3 参照）。
  **登録は必要条件にすぎず**、`merge_classification.py` がサブコマンドを持たない以上
  有効フラグ集合は `--help` 全出力由来となるため、§4.6 の実装制約
  （`ArgumentParser(description=__doc__)` を用いない）を併せて満たすことが検査D 実効化の条件である。
  `tools/harness/smoke_config.md` は「工程別実行モデル」表の工程04 実測コストと、そこから導出される
  グローバル `SMOKE_TOKEN_BUDGET` の再算定が必要（並列サブエージェント分の消費増。工程別の予算上限という
  設定項目は存在せず、`smoke_full.py` も一律の `DEFAULT_PHASE_EST_USD` ＋グローバル予算で判定する）。
  `make test` には `test_merge_classification.py` が追加される。
  `seeds/phase04-multi/` は本プランの成果物ではないが、Stage 2 着手の前提条件として
  2026-08-09 に先行生成済み（§4.9「Stage 2 着手の外部依存」）。
- **後方互換性:** 不要（ポリシー）。ただし discovery のループ手順が変わるため、
  途中状態の bfs-state.json は再実行で追従する場合がある。
- **本プランから切り離した既存不備（README の件数・一覧表）:** `README.md` のディレクトリ構成図は
  エージェント「15種」・スキル「16種」と記載されているが実数はエージェント16件・
  `skills/*/SKILL.md` 24件であり、「## サブエージェント一覧」表も10件のみで
  chd-sync / close-knowledge / close-promote / design-sync / specs-mod / specs-uc の**6件が未掲載**である。
  これは本プランの目的（波内 classification の並列化）と無関係な既存不備であり、
  最も承認ハードルの高い Stage 2 に紐付けると **Stage 2 保留時に一緒に塩漬けになる**。
  したがって本プランの README 変更は「classifier 1件の一覧表追記＋工程4a 説明の更新」に限定し、
  **件数是正と未掲載6件の追記はドキュメント修正のみの独立変更として先行実施する**
  （CLAUDE.md「問題を見つけたら放置せず、必ず対処または明示的に記録する」）。
- **デグレードリスク（実装者への申し送り）:**
  - **繰り越し LOW フロンティアの消失（Stage 1・不変条件に直結）:** §4.5(g) の是正
    （`cmd_search` の非破壊化）を入れずに §4.7 の「`search` から再開」を運用すると、
    入れ替えが起きた波の繰り越し LOW エントリが frontier からも low からも消え、
    **確定影響ファイルの取りこぼしが発生する**（既存不具合を常用経路に載せることになる）。
    §4.5(g) は基準線採取より**前**に適用すること。
  - **Phase 2B の LOW 退避回帰検査の喪失（Stage 1）:** §4.5(g) により
    `test_2b_search_defers_unlisted_module_as_low_and_keeps_it`・`test_search_defers_low_priority_module` の
    2件が必ず失敗する。**「壊れたテスト」として削除すると Phase 2B（module-priority による LOW 退避）の
    保証が失われる。** 検査対象を `search` 直後の state から hits の `deferred_low` へ移して維持すること
    （§3 の S1 テスト行）。§6 の「`make test` が緑」だけでは正しい更新と削除を区別できない。
  - **fail-loud テストの偽陰性（一般則・Stage 1）:** 複数条件を持つ fail-loud（§4.5(g) の条件1〜3）は、
    条件どうしが同一 state で同時に成立しうる。**各条件のテストは「その条件が単独で成立する state」を
    前提に組むこと。**「エラーになること」だけを確認するテストは、他条件が先に成立していれば
    当該条件の実装を丸ごと落としても緑になり、ガードの欠落を検出できない
    （同型の見落としが本プランのレビューで3回連続で発生している）。単独成立経路は §4.5(g) の
    役割分担表に整理済みであり、テスト前提（§3 の S1 テスト行 (4)(5)(6)）と §6 Stage 1 の確認項目は
    その表と1対1で対応させること。
    **さらに各アサーションについて、「当該ガードを外した実装で実際に失敗すること」を確認すること**
    （ミューテーション観点）。主アサーション（exit 非0）が有効でも、副次アサーションは前提 state の
    組み方しだいでガードの有無と無関係に成立しうる（例: `_truncate_wave_section` は対象見出しが
    無ければ早期 return し、伝播ゼロの classification では frontier 復活そのものが起こらない）。
  - **discovery-log と bfs-state.json の不整合（Stage 1）:** `deferred_low` の適用位置を
    discovery-log 生成部より後にすると、frontier 行が実状態と食い違う（§4.5(g)「適用位置を早期に固定する理由」）。
    この行を検査するテストは現存しないため、§3 の S1 テスト行に追加した単体テストで固定すること。
  - **計測値の汚染（Stage 1 固有・投資判断に直結）:** `classify_started_at`／`classify_started_wave` の
    **α＝開始時刻の波不一致**・消費後破棄漏れは、別の波の開始時刻から差分を算出して
    `classify_wall_ms` を汚染する。
    また、`xddp-specout-agent.md` の「クラッシュ再開:」ブロックを Stage 1 で改訂しないと、
    `search` を飛ばす再開が規定として残り、人の待ち時間が丸ごと混入する（`null` にはならない）。
    さらに**過小側**の汚染として、再開時に既存 classification を再利用した波は実際の分類が行われず
    `classify_wall_ms` が数秒〜数十秒に落ちる。`classify_wall_ms_suspect` は過大側しか見ないため、
    §4.5(d)「再利用波の判定」（mtime 比較）による `classify_wall_ms_reused` の除外が必須である
    （欠くとゲートが**偽陰性**へ振れる）。
    ゲート指標に `raw_hits`（フィルタ前）を使うと分類対象規模を過大評価する。
    §4.5(c) のライフサイクル表・§4.9 の指標定義・§3 の S1 行を厳守すること。
  - **判定入力の縮小（最大リスク）:** `known_symbols` の素名正規化漏れ・チャンクへの複製漏れ・
    `CRS_FILE` 未配布は、frontier 伝播の縮小（探索漏れ）または `out-of-scope-discard` の緩和（探索肥大）に
    直結する。チャンクファイルに `known_symbols` が素名で全件複製されることを単体テストで固定する。
  - **オーケストレータのコンテキスト蓄積:** 移設後はメインコンテキストに
    「最大 `MAX_WAVE_DEPTH`（既定10）波 × リポジトリ数」分の波ループ履歴が蓄積する。
    枯渇すると工程4a 全体が停止し、以降の工程指示も失われる。§4.2 の緩和策を必ず実装し、
    Stage 1 で実測分布を採取して許容量を超える見込みなら Stage 2 の設計を見直す
    （定義ファイル自体は git revert で戻せるが、**退避先の設計（wave driver のサブエージェント化）は
    案Y の実現可否に依存する**ため、§4.9 Stage 1 手順3 のスパイク結果を着手前に得ておくこと）。
  - チャンク境界での **line_id 欠落・重複**は `commit-wave` のスキーマ検証でも弾かれるが、
    `merge_classification.py` で先に検出し明示エラーにする。
  - **責務移設先での実行可能性:** 移設する手順は、移設先の時点で必要な入力（呼び出し元が渡すキー・
    確定済みの状態ファイル・生成順序の前提）を得られるかを個別に確認すること。code-knowledge 参照は
    この検討の結果、移設先が成立しないため**移設対象から除外**した（§4.3）。同種の判断を
    Wave 0 構築・判定ルール移設の各項目についても実施すること。
  - 分類ルールを classifier エージェントへ移設する際の**判定基準のドリフト**（現行 specout エージェントと
    差異が出ると分類結果が変わる）。移設は逐語的に行い、移設前後の差分を人がレビューする
    （判定手順2 の Agent ツール記述削除のみ意図的な差分）。
  - **書き込み競合:** 状態更新・discovery-log 追記を誤って classifier 側に持たせると競合する。
    **書き手は `commit-wave` 単一**を厳守（classifier の Write 先は `OUT_FILE` のみ）。
  - **トークン増分:** チャンク数 × (分類ルール + CRS + 重複 Read) の増加。ファイル単位グルーピング
    （§4.5(b)）で重複 Read を抑えるが、増分は smoke-full で実測して §2 の見積りを検証する。
  - SKILL 側のループ複雑化による一時停止/再開の回帰。`make smoke-full PHASE=04` と recovery 手順で検証。
  - **refcheck 検査B の warning:** SKILL が classifier へ渡すキーが定義本文に現れないと warning が出る。
    Inputs 節に全キーを宣言する（§4.4）。

---

## 6. 確認項目

**Stage 1（計測）**
- [x] `make test` が緑（`classify_wall_ms` のテストを含む）
- [x] metrics.jsonl に `classify_wall_ms`・`chunk_count`・`batch_count`・`parallelism` が記録され、
      `classify_started_at`／`classify_started_wave` の**欠損時**に `classify_wall_ms: null` で落ちない
- [x] **`classify_started_wave` が今回の `wave` と一致しない場合に `classify_wall_ms: null` になる**
- [x] **`commit-wave` 完了後に `classify_started_at`・`classify_started_wave` が state から削除される**
      （消費後破棄。次波の `search` が再度書く）
- [x] **波数上限による `search` の早期 return で2キーが書かれず、既存の2キーが削除される**
- [x] **`finish`・`re-discover`・`prune`・`set-state` の各経路で2キーが削除される**
      （search を経ない状態遷移の後に古い開始時刻が残らない）。`import` は復元対象に2キーを含めない。
      `merge-frontier`・`record-module` は**削除せず**当該波の値を保持する
- [x] 時間値が state 判定に混入しない（再開の決定性保持。既存 `search_ms` と同方針）。
      2キーが欠損しても BFS の進行に影響しないこと
- [ ] 実 CR で波あたり `classify_wall_ms`・**`classified`**・`raw_hits`・波数 × リポジトリ数の分布を
      採取できる（ゲート判定は `classified`、`raw_hits` は削減率の参考値）
- [ ] **不変条件1 の基準線を現行アーキ（単一コンテキスト分類の Stage 1 時点）で採取・保存する**
      （確定影響ファイル一覧と次波 frontier。Stage 2 の比較基準となるため Stage 1 のうちに必須。
      **§4.5(g) の適用後に採取すること**）
- [x] **`chunk_count`・`batch_count`・`parallelism` が Stage 1 では常に既定値 `1` で記録され、既存挙動が変わらない**
- [x] **§4.5(g) の冪等性是正:** 同一 state に対して `search` を2回連続実行しても `low_priority_frontier` が
      変化せず、`this_wave`・line_id・チャンク構成が完全一致する（`this_wave` が空になり
      `this_wave, low = low, []` の入れ替えが起きる波を**必ずテストケースに含める**＝繰り越し LOW の消失回帰検査）
- [x] **`commit-wave` が hits の `deferred_low` を `low_priority_frontier` へ適用する**（キー欠損時は既存値を変更しない）。
      complete 判定（`not next_frontier and not low_priority_frontier`）が適用後の値で行われる
- [x] **再開経路が `search` から始まる**ことで `classify_started_at` が書き直され、中断中の待ち時間が
      `classify_wall_ms` に混入しない。**`xddp-specout-agent.md` の「クラッシュ再開:」ブロックと
      `recovery-procedures.md` の両方が Stage 1 時点で §4.7.1 (1)(2) の After テキストどおりに改訂されている**。
      **あわせて `xddp-specout-agent.md`「### Wave 0 完了後: モジュールカタログによる BFS 優先度設定」節の
      LOW 退避の説明が §4.7.1 (3) の After テキストどおりに改訂されている**（§4.5(g) に伴う陳腐化の是正）。
      **`recovery-procedures.md` の記述が S2 成果物（チャンクファイル・`merge_classification.py`）を
      参照していない**（Stage 1 時点で存在しないため）
- [x] **`classify_wall_ms_suspect`** が閾値（暫定 1,800,000ms）超過で `true`・閾値内で `false`・
      **`classify_wall_ms` が `null` の波では `null`** になり、§4.9 の集計除外に使える
- [x] **`classify_wall_ms_reused`（§4.5(d) 再利用波の判定）:** classification ファイルの mtime が
      `classify_started_at` より**古い**場合に `true` かつ `classify_wall_ms: null` になり、通常波では `false`。
      mtime が取得できない場合は `null` となり `commit-wave` は失敗しない
- [ ] **除外波の別掲（§4.9）:** ゲート判定の提示物に、除外した波数と各波の
      `classify_wall_ms`・`classified`・除外理由（§4.9「外れ値の扱い」に列挙した全カテゴリ＝
      paused / suspect / reused / `classify_wall_ms: null`）の一覧が添付される。
      **各波の除外理由が1つに一意化され（優先順位: paused ＞ reused ＞ suspect ＞ null）、
      カテゴリ別内訳の合計が除外波数（波の実数）と一致する**
- [x] **discovery-log の frontier 行が実状態と一致する（§4.5(g) の適用位置）:**
      `next_frontier` が空・`deferred_low` が非空の波で「→ 空。新規発見なし。探索終了。」と**書かれない**。
      入れ替えが起きた波（`deferred_low` が空）で「(MODULE_PRIORITY_LOW 分へ移行)」と**書かれず** complete と整合する
- [x] **波一致の fail-loud（β＝hits の波不一致。§4.5(g) 条件1）:** `hits_payload["wave"]` が
      `data["current_wave"]` と一致しない hits を渡すと `commit-wave` が exit 非0 になり、
      **state（`frontier`・`low_priority_frontier` を含む）も discovery-log も変更されない**。
      **検査は「`wave_write_complete: false` かつ切り捨て対象の `## Wave {n}` が discovery-log に存在する」
      state を前提に行い**、exit 非0 後に当該 Wave セクションが残存していることを確認する
      （この前提がないと `_truncate_wave_section` 自体が呼ばれず、ガードの位置を検査できない）
- [x] **`finish` 後の再コミットがブロックされる（§4.5(g) 条件2）:** **`state == "complete"` かつ
      `wave == current_wave > last_completed_wave` かつ `wave_write_complete: false`**（＝当該波の `search` 後に
      `finish` を実行した state）に当該波の hits を再投入すると **exit 非0 になる**
      （この前提でないと条件3 が先に成立し、条件2 の実装欠落を検出できない）。
      **副次アサーション（切り捨て不発生・frontier 非復活）を置く場合は、①discovery-log に当該波の
      書きかけ `## Wave {n}` が存在し「## 継続パス C」がその後ろにあること
      （`## Wave {n}` は `search` では書かれず `commit-wave` のみが書くため、log fixture として直接用意するか
      `commit-wave` のログ追記直後のクラッシュを模して作る。§4.5(g) 役割分担表 条件2 行を参照）、
      ②classification の `next_symbols` が非空（または `deferred_low` が非空）であることを満たす**
      （満たさないと条件2 の有無にかかわらず成立し、空振りする）
- [x] **最終波の二重追記が起きない:** 最終波コミット後の state に同じ hits を再投入しても discovery-log の
      Wave セクションと metrics.jsonl の行が二重追記されない（条件2・3 の**いずれか**が効いていれば成立する
      挙動テストであり、個々の条件の検査ではない）
- [x] **完了済み波の再コミットがブロックされる（§4.5(g) 条件3）:** **`state != "complete"`
      （`set-state` 相当で `in-progress` へ戻した状態）かつ `wave == current_wave == last_completed_wave`
      かつ `wave_write_complete: true`** の state に当該波の hits を再投入すると exit 非0 になる
      （この前提でないと条件1・2 が先に成立し、条件3 の実装欠落を検出できない）
- [x] **既存2テストが削除されずに更新されている:**
      `test_2b_search_defers_unlisted_module_as_low_and_keeps_it`・`test_search_defers_low_priority_module` の
      検査対象が hits の `deferred_low` へ移り、Phase 2B の LOW 退避保証が維持されている
- [ ] Stage 2 着手ゲート（§4.9 の数値基準）を採取データで判定できる
      （**指標は `classified`**・§4.9「外れ値の扱い」の**全カテゴリ**の除外〔paused / suspect / reused /
      `classify_wall_ms: null`〕・中央値集計・上位3波の目視確認）。
      **比率の分母が「除外後の有効波」であり、有効波が 3 波未満なら判定を行わないことが守られている**
- [x] **案Y の最小スパイク（§4.9 手順3）を実施し、結果（Agent/Task 保持エージェントから子エージェントを
      起動できるか）を記録した**。実現可能なら §2 比較表を更新、不可能なら §4.2 緩和策を「必須」に格上げ
- [x] **トークン増分の予測上限（§4.9）を算出し、承認者へ提示できる**（パラメトリック版を §4.9.1 に作成済み。`classified` 実測値の当てはめのみ残る）
      （`chunk_count` 予測分布 × (分類ルール + CRS) を工程04 実測 `~0.55 $/起動` と対比。**プロンプトキャッシュの有無が分岐点**という §4.9.1 (e) の結論を必ず添えること）

**Stage 2 決定的層（`make test` / 0トークン）**
- [ ] `make test` が緑（`refcheck` ＋ `test_merge_classification.py` ＋ 既存 unittest）
- [ ] `search --hits-dir DIR` が state の `current_wave` から `wave-{N}-hits.json` を組み立て、
      実パスを stdout の `hits_file` で返す。**`--hits-out` / `--hits-dir` の両方未指定・両方指定が
      いずれも明示エラーになる**（`--hits-out` の `required=True` 解除に伴う退行防止）
- [ ] `status --brief` が `ok`/`state`/`current_wave`/`wave_write_complete`/`remaining_frontier_count` のみを
      返し、無指定時は現行どおり state 全体を返す。**`remaining_frontier_count` が
      `len(frontier) + len(low_priority_frontier)`**（＝`commit-wave` の complete 判定と同じ集合）であり、
      `low_priority_frontier` のみが残る状態で `0` にならない
- [ ] **`xddp.04.specout/SKILL.md` の Step A 入口の `status` 呼び出しが `status --brief` に置き換わっている**
      （`--brief` を実装したのに呼び出し側が変わらない取りこぼしの防止。`recovery-procedures.md` 側に
      state 全体を出す `status` 呼び出しが残っていないことも確認する — **Stage 1 が §4.7.1 (2) 手順1 で
      持ち込んだ全体出力 `status` が対象であり、§3 の S2 `recovery-procedures.md` 行の差し替え規定
      〔`status --brief` への置換、または `search --hits-dir` 化による当該行の削除〕と1対1で対応する**）
- [ ] `search` が**常に `chunks` を1件以上**返す（`--chunk-size 0` / `len(hits) ≤ N` の場合も
      `chunk-0` が1件返り、その内容がチャンクスキーマである）
- [ ] チャンク分割が全 line_id をちょうど1チャンクに配分する（欠落・重複ゼロ）
- [ ] **同一ファイルのヒットが同一チャンクに入る**（1ファイルのヒット数が `--chunk-size` を
      超える場合のみ当該ファイル単独チャンク）
- [ ] 各チャンクに `known_symbols` が**全件同一内容で複製**され、`visited`・`searched_frontier` の
      MEDIUM エントリ（`paramName[MEDIUM:path]`）が**素名**で含まれる
- [ ] 各チャンクに当該ヒットが参照する `commands` サブセットが含まれる
- [ ] `merge_classification.py` が line_id の**欠落・重複・未知 classification 値**を検出し
      `exit 1` ＋ stderr に該当 line_id を出力する
- [ ] `merge_classification.py` が**チャンク単位の line_id 集合照合**を行い、stale なチャンク結果
      （`--hits` に存在しない未知 line_id を含む・`chunk_id` と対応しない）を検出して `exit 1` する（§4.6 処理6）
- [ ] **`--hits-chunks` と `--chunks` の取り違えが起きていない:** SKILL.md の step c 呼び出しで
      `--hits-chunks` に `HITS_CHUNKS`（`wave-{N}-hits-chunk-{K}.json`）、`--chunks` に `CLASS_CHUNKS`
      （`wave-{N}-chunk-{K}-class.json`）が渡っている。**取り違えてもフラグ名は一致するため
      `refcheck.py` 検査Dでは検出できない**（`--chunks` にヒットチャンクを渡すと classification が
      1件も読まれないことを単体テストで固定する）
- [ ] `merge_classification.py` が `--chunks` の**不在ファイル**に対し traceback ではなく
      欠落 `chunk_id`／期待パス一覧を stderr へ出力して `exit 1` する（§4.6 処理8。
      §4.7【S2】手順2 の「欠落チャンクのみ再投入」の特定根拠になる）
- [ ] `search` が書き出し前に当該波の既存チャンクファイル（`wave-{N}-hits-chunk-*.json`）を削除し、
      チャンク数が減る再 `search` でも旧ランのファイルが残らない（§4.5(b)）
- [ ] `merge_classification.py` の `--out` が `--hits` の出現順に整列され、
      同一入力に対する `commit-wave` の出力（確定影響ファイル集合・`next_frontier`・ケースA分岐）が
      分割なし実行と**バイト等価**（fixture 固定）
- [ ] `commit-wave --unsupported-patterns` が discovery-log の「grep未対応パターン」テーブルへ
      **ヘッダ部のセクション内に**（末尾ではなく）重複なく追記し、`{pattern, location, note}` が
      3列（パターン種別／根拠／確認状況）へ規定どおり対応付く。`commit-wave` 再実行で行が増殖しない
- [ ] `_truncate_wave_section`（クラッシュ再開時の Wave セクション切り捨て）が
      「grep未対応パターン」セクションを破壊しない

**Stage 2 意味層（`make smoke-full PHASE=04`・校正ラン後）**

> **前提条件（これを満たさない検証は空振りする）:** 検証ランでは seed の `xddp.config.md` に
> 小さい `SPECOUT_CLASSIFY_CHUNK_SIZE`（例 `5`）を設定し、**metrics.jsonl に `chunk_count ≥ 2` の波が
> 存在すること**を先に確認してから以下の各項目を判定する。シードのヒット数が既定値 `40` 以下だと
> §4.5(b) の統一契約により常に単一チャンクとなり、不変条件1 の検証・「分割なし vs 並列分割」の一致・
> トークン増分の閾値が**すべて自動的に合格してしまう**（何も検証していない状態になる）。
> トークン閾値の比較も、**分割が実際に発生したラン**の実測値で行うこと。
- [ ] **不変条件1 の検証（最重要）:** Stage 1 で採取した**現行アーキの基準線**に対して、
      並列分割実行の**確定影響ファイル集合が縮小しない**（拡大した場合は差分を人が確認）。
      `next_frontier` の差分も同様に確認する。
      ※「分割なし実行 vs 並列分割実行」の比較は**どちらも移設後**であり不変条件1 を検査できないため、
      比較対象は必ず Stage 1 の基準線とすること
- [ ] **非決定性の分離（上項の実施条件）:** 基準線・検証実行のいずれも LLM 分類を含むため、
      1対1比較では「チャンク分割による判定入力の縮小」と「LLM のゆらぎ」を区別できない。
      以下の手順で実施する:
      1. **基準線は同一シードで 3 回実行し、確定影響ファイル集合の和集合（∪）と積集合（∩）を保存する**
         （Stage 1 のうちに採取。∪ と ∩ の差が LLM ゆらぎの実測幅であり、この幅自体も記録する）
      2. 並列分割実行も同一シードで 3 回実行し、その**和集合**を比較対象とする
      3. 合否判定: 並列側の和集合が**基準線の積集合（∩）を包含する**こと（＝ゆらぎの影響を受けない
         コア集合を1件も落としていないこと）。これを満たさない場合は不合格とし、
         落ちたファイルごとに `known_symbols`・`CRS_FILE` の配布漏れを実装レベルで追跡する
      4. 並列側が基準線の和集合を超えて拡大した場合は、**拡大分の各ファイルについて
         「なぜ影響ありと判定されたか」を人が確認**し、探索肥大（§4.9 の非対称性）か
         正当な検出かを判断する。判断者は本プランの承認者とする
- [ ] 分割なし実行（`--chunk-size 0`）と並列分割実行で確定影響ファイル集合・`next_frontier` が一致する
      （チャンク分割そのものの回帰検査。上項の代替ではない）
- [ ] **マルチリポジトリシード**（`test-fixtures/scratch-workspace-min/seeds/phase04-multi/`。
      `smoke_config.md` の工程別シード対応表・`smoke_full.py` の `MULTI_PHASES` に既定義。
      **2026-08-09 に手動最小化フィクスチャとして生成済み**〔CR-2026-991・svc-a/svc-b 各1UR〕。
      §4.9「Stage 2 着手の外部依存」参照）で、
      リポジトリ間の並列度が維持され、repo ごとの state・波番号が独立して進む
      （本チェック自体は Stage 2 実装後の意味層検証であり、シード生成のみでは満たされない）
- [ ] 一時停止（paused-at-limit / 2nd）・再開・`status` 判定が SKILL 移設後も正しく動作する
      （recovery-procedures.md の改訂内容と整合）
- [ ] **`discovery-setup` は `bfs-state.json` が存在しない repo でのみ起動され、存在する repo では
      スキップされて波ループへ直行する**（`init` の「既に存在します」エラーで停止しない）
- [ ] **code-knowledge 参照が `discovery-setup` 内の `init` 実行の後段に置かれ**、`status` の
      state 不在エラー（「bfs-state.json が見つかりません」）で停止しない
- [ ] **code-knowledge 参照が成果物観点で現行と等価**（`MODE: document` の Step 0／Step 10 における
      `_observation-memo.md` の削除・「観察なし」判定に変化がなく、SPO・discovery-log・confirmed_files に差が出ない）。
      §4.3 に記録した既存欠陥は本プランでは是正せず、申し送り4点とともに別プランで対応する旨が §4.3 に明記されていること
- [ ] 途中失敗からの再開が**必ず `search` から始まり**、同一 line_id・同一チャンク構成が決定的に再生成される。
      既存チャンク結果は line_id 集合の一致を条件に再利用され、欠落チャンクのみ再投入される（§4.7）
- [ ] **Stage 2 の再利用検出方式（§4.5(d)「判定方法〔S2〕」で確定したもの）が実装・配線され、
      チャンクを再利用した波で `classify_wall_ms_reused: true` になる**（S1 の `--classification` mtime 方式は
      Stage 2 では常に `false` になるため、確定方式の実装確認が必要）
- [ ] `classify_wall_ms` の実測で並列化前後の壁時計短縮が確認できる
      （**`classify_wall_ms_reused: true` の波と `classify_wall_ms` が `null` の波を除外したうえで**判定する。
      再開が挟まったランの過小値が混ざると「短縮した」という**偽陽性**になる）
- [ ] **実効並列度が観測できる:** `chunk_count ≥ 2` の波で `batch_count ≤ ceil(chunk_count / parallelism) + 1`
      であること（repo 単位。§4.5(d) の**判定分岐1＝第1優先**）。これを満たさず、かつ
      `batch_count == chunk_count` かつ `chunk_count > parallelism` の場合は「並列化の効果がない」ではなく
      「並列起動されていない」と判定して原因を追う（分岐2）。`chunk_count ≤ parallelism` の repo は
      分岐2 の対象外とし `chunk_mtimes` で補完確認する（分岐のオーバーラップによる偽陰性を避ける）
- [ ] **`batch_count` の自己申告が裏付けられる:** `merge_classification.py` が出力する `chunk_mtimes` の
      完了時刻分布が `batch_count` と整合する（バッチ状にクラスタしており、等間隔に散っていない）
- [ ] `wave-{N}-batches.json` が repo ごとに規定スキーマ（`batch_index`/`chunk_files`/`started_at`/`ended_at`）で
      記録され、事後監査できる
- [ ] **プレフィクスのバイト同一性が実装で保証されている（§4.2 step b・§4.9.1(c) の前提条件）:**
      同一波内の全 classifier 起動プロンプトについて、チャンク固有情報（`CHUNK_FILE`・`OUT_FILE`・`chunk_id`）を
      除いた先頭部分がバイト単位で一致する。波の最初のバッチはチャンク0を単独起動してキャッシュ書き込みを
      完了させてから残りを起動する（またはバッチ内起動のタイミングを2〜3秒ずらす）実装になっている
- [ ] **キャッシュ共有が実測で確認できる（§4.9.1(d)(e) の閾値内論の前提）:** `chunk_count ≥ 2` の波で、
      2体目以降の classifier 起動の `usage.cache_read_input_tokens` が1体目の `cache_creation_input_tokens` と
      同等の値を示す（＝プレフィクスが再利用されている）。確認できない場合、
      §4.9.1(d) の「キャッシュ有」列の閾値内論は成立しないため、
      `SPECOUT_CLASSIFY_CHUNK_SIZE` の引き上げ等で再検討するか Stage 2 を保留する
- [ ] **トークン増分が定量閾値内:** `make smoke-full PHASE=04` の実測 $/起動が、
      §4.9 で承認者へ提示した**予測上限以内**であり、かつ現行実測（`smoke_config.md` 工程04 `~0.55`）の
      **2倍以内**である（超過時は `SPECOUT_CLASSIFY_CHUNK_SIZE` の引き上げで再測定するか、Stage 2 を保留する）
- [ ] オーケストレータのコンテキストが最長シード CR で枯渇しない

**整合性**
- [ ] 新規 `xddp-specout-classifier-agent` の `tools:` が `Read/Grep/Write` に限定され、
      `description` がドメイン中立（親プラン指摘#9）
- [ ] SKILL の pass ブロック（8キー）と classifier の Inputs 節が1対1で一致（`refcheck.py` 検査B が緑）
- [ ] `SPECOUT_CLASSIFY_CHUNK_SIZE` / `SPECOUT_CLASSIFY_PARALLEL` の配線が
      config テンプレート → `xddp.common`「## Load Config」→ `xddp.04.specout/SKILL.md` 受領キー列挙 →
      各呼び出しで一貫（前例: `SPECOUT_BACKEND`）
- [ ] `SPECOUT_CLASSIFY_CHUNK_SIZE: 0` で分割が完全に無効化され、現行と同一の単一分類に戻る（退路の担保）
- [ ] SKILL.md の classifier pass ブロックが**「説明行はフェンス外・キーはフェンス内」の書式**で
      転記され、`refcheck.py` 検査Bの「pass ブロックが定型でなく契約照合をスキップ」warning が出ない
      （＝契約照合が実際に走っている）
- [ ] **結線検査が実際に走っている:** `refcheck.py` の `DETERMINISTIC_SCRIPTS` に
      `merge_classification.py` が登録され、SKILL.md 側の呼び出しに**argparse・docstring のいずれにも
      存在しないフラグ**を混ぜると検査Dが violation を出す（登録漏れだとサイレントに素通りする）
- [ ] **§4.6 の必須制約1（`ArgumentParser(description=__doc__)` を用いない）が守られている:**
      docstring に一時的にフラグ表記を1つ加え、そのフラグ（argparse には未定義）を SKILL.md の
      呼び出しへ混ぜても検査Dが violation を出す。制約1 が破られていると当該フラグが
      `top()["flags"]` へ混入して violation が出ず、**docstring と argparse の乖離という
      最も起きやすいズレを検出できなくなる**（検証後、一時的に加えた docstring 行と呼び出しは元に戻す）
- [ ] CLAUDE.md・README.md（classifier 1件の一覧表追記・工程4a 説明）・
      `docs/specout-discovery-guide.md`・ADR-0010・**`docs/adr/README.md` の索引行**・
      `tools/harness/smoke_config.md` の整合
- [ ] 特定ドメイン（Web・業務・組み込み）への偏りがないか（CLAUDE.md「適用ドメインの中立性」）

---

## 7. レビュー

AIレビュー結果: [plans/review/PLAN-20260806-specout-phase3-parallel-classification-review.md](review/PLAN-20260806-specout-phase3-parallel-classification-review.md)

---

## 8. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | tsuna44 |
| 承認日 | 2026-08-08（Stage 1） / **2026-08-09（Stage 2）** |
| 備考（Stage 2） | **Stage 2（並列化本体・§4.1〜§4.8。SKILL.md 波ループ移設・`xddp-specout-classifier-agent` 新設・`merge_classification.py` 追加・ADR-0010 起票を含む）を承認する。** 前提の必須補完事項（§4.9 末尾）は全項目解消済み（`count_tokens` 実測のみ、人が文字数ベース推定値〔±30%誤差見込み〕を明示的に受容し実測なしで承認）。承認の前提となったリスク: §6「トークン増分が定量閾値内」チェックが `make smoke-full PHASE=04` の実測 $/起動で最終判定するため、推定と実測の乖離はその時点で捕捉し `SPECOUT_CLASSIFY_CHUNK_SIZE` 引き上げ等で対処すること。 |
| 備考（Stage 1） | 親: PLAN-20260804（Phase 0/1 実装完了）＋ Phase 2 個別プラン実装完了。目的=レイテンシ短縮（トークン削減ではない）。設計案は**案X で確定**（案Y は Agent/Task 保持エージェントの前例なしにより不採用）。**本承認は Stage 1 の実装承認**（§4.5(c)(d) の計測追加＋ライフサイクル仕様、§4.5(g) の `cmd_search` 非破壊化＝**既存の取りこぼし不具合の是正**、および `xddp-specout-agent.md`・`recovery-procedures.md` の再開経路統一。**「挙動不変」ではない**点に注意）であり、**Stage 2（並列化本体・§4.1〜§4.8）は Stage 1 の実測結果を添えて別途承認を要する**（根拠は「切り戻し不能」ではなく**費用対効果が未実測**であること。定義ファイル自体は git revert 可能で、追従しないのは移設後に開始した進行中 CR の途中状態のみ＝後方互換性ポリシー上は再実行を求めてよい。§4.9 参照）。Stage 2 再承認時は §4.9 末尾「必須補完事項」を満たすこと（2026-08-09 時点: §4.5(b)(e)・§4.6 の Before/After、§4.5(d) 再利用波検出方式の確定、§4.9.1 固定ブートストラップ項の反映、プレフィクスのバイト同一性の設計要件化、CRS キャッシュ経路の検証、`phase04-multi` シード生成、**`T_rules`/`T_CRS`/`T_boot` の `count_tokens` 実測（`ANTHROPIC_API_KEY` 未設定のため実測は未実施のまま、文字数ベース推定値〔±30%誤差見込み〕を人が受容し Stage 2 再承認へ進めることを選択・2026-08-09）はすべて解消済み**。**必須補完事項はこれで全項目解消であり、Stage 2 の実装着手には本表に Stage 2 の承認日・備考を追記する人の正式承認が必要**）。ゲート指標は **`classified`**（`raw_hits` ではない）。Stage 1 には**案Y の最小スパイク**（§4.9 手順3）と**トークン増分の予測上限の算出**（§4.9）を含む。**未了の申し送り（いずれも本プランのスコープ外・埋没に注意）: (1) code-knowledge 参照が成果物へ到達しない既存欠陥（§4.3・申し送り4点）の別プラン起票（起票までは §4.3 が唯一の記録）、(2) README の件数是正・サブエージェント一覧の未掲載6件追記（§5。Stage 2 と切り離してドキュメント修正のみで先行実施する）** |

---

## 9. 次セッションへの申し送り（2026-08-08 時点）

> **現在地:** Stage 1 のコード・ドキュメント実装は完了・`~/.claude/` へデプロイ済み・`make test` 緑。
> 残るは**計測の実採取**のみ。実 CR が存在しないため、**手書き CRS ＋ 実サイズ母体で工程4a だけを
> 単独実行する**方針（下記 B 案）を人が選択した。順序は **B（採取）→ ゲート判定 → 必要なら A / Stage 2**。
>
> **更新（2026-08-08）: B案の1ラン目を実施しゲート判定まで完了した。結果は
> [PLAN-20260806-specout-phase3-stage1-measurement.md](PLAN-20260806-specout-phase3-stage1-measurement.md)。
> ゲートは成立。あわせて §9.3 がゲート成立時の前提条件として課していた §4.9.1 (e) の
> プロンプトキャッシュ実測も完了し、条件は充足された**（兄弟サブエージェント間でキャッシュは共有される。
> ただしコールドスタート時に約1〜2.5秒の競合窓あり）。**基準線は人の判断により1回で確定。**
> 計測ワークスペースは `/Users/tsuna/Documents/src/git-work/specout-measure`（本リポジトリ外・条件は
> 同ディレクトリの `RUN-CONDITIONS.md` に固定記録）。
>
> **更新（2026-08-09）: 上記の「残作業」（§4.9「Stage 2 再承認時の必須補完事項」の記載と、
> 計測で判明した2点の反映）に対応した。** §4.9.1(c) に固定ブートストラップ項 `T_boot` を追加し
> (d)(e) を更新、§4.2 step b・§4.4 にプレフィクスのバイト同一性・コールドスタート対策を設計要件として
> 明記、§4.5(d)「判定方法〔S2〕」（`min_chunk_mtime` 経由）を確定し §4.2/§4.6/§6 へ配線、
> §4.5(e)・§4.6 に Before/After 枠を追加。詳細は §4.9 末尾「Stage 2 再承認時の必須補完事項」を参照。
> ~~**残る未了: (1) `T_rules`/`T_CRS`/`T_boot` の `count_tokens` 実測のみ**（API 認証未設定のため未実施）。
> これが埋まり次第、人による Stage 2 再承認の申請が可能になる。~~ → **2026-08-09 人が判断し受容。**
> 継続セッションでも `ANTHROPIC_API_KEY` 未設定のため実測は不可のままであり、人は「文字数ベース推定値
> （±30%誤差見込み）を受容し実測なしで Stage 2 再承認へ進める」ことを明示的に選択した。
> `count_tokens` による再計測はもはや Stage 2 再承認の前提条件ではない（実測ゲートは §6 の
> `make smoke-full PHASE=04` 実測 $/起動チェックへ委ねる）。
> ~~(2) CRS が Read ツール経由でもキャッシュ対象になるかの検証~~ → **2026-08-09 完了**
> （stage1-measurement.md §5.7・§4.9.1(e)(5)。対象になりうるが確率的。埋め込み設計は Stage 2 実装時に検討）。
> ~~(3) `phase04-multi` シードの生成~~ → **2026-08-09 完了**（CR-2026-991・手動最小化フィクスチャ。
> 詳細は §4.9「Stage 2 着手の外部依存」）。
>
> **Stage 2 再承認の必須補完事項はすべて解消した。残るアクションは人による Stage 2 の正式承認（§8）のみ。**

### 9.1 B案の実行手順（計測データの採取）

**認証は不要**（`CLAUDE_CODE_OAUTH_TOKEN` が要るのは隔離 HOME で動く `make smoke-full` のみ。
本手順は通常セッションで `/xddp.04.specout` を実行するだけ）。

1. **計測用ワークスペースを作る**（本リポジトリの成果物を汚さない場所に置く）
   - `xddp.config.md` を `xddp.01.init/templates/xddp.config.md` から作成し、
     **`REPOS:` を実サイズのリポジトリへ向ける**（例: XddpSettings 自身、または他の作業ディレクトリの
     リポジトリ）。`DEVELOPMENT_MODE: change` であること（`new` だと工程4a がスキップされる）。
   - `/xddp.01.init {CR番号} {タイトル}` を実行して CR ワークスペース（`progress.md` 等）を作る。
   - **`{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.md` を手書きする。**
     工程4a が読むのはこのファイルであり、工程2・3 を通す必要はない。
     Wave 0 シンボルが母体コードから実際に引けるよう、**実在する関数名・クラス名を SP に含めること**
     （ここが空振りすると波が伸びず計測にならない）。書式は `artifact_lint.py --doc-type CRS` に通せば確認できる。
2. **`/xddp.04.specout {CR}` を実行する。** 波ごとの metrics が
   `{CR_PATH}/04_specout/{repo}/metrics.jsonl` に1行ずつ追記される。
3. **基準線（§4.9 手順2・§6 の不変条件1 用）は同一条件で3回**実行し、
   `discovery-log.md` の確定影響ファイル一覧と `bfs-state.json` の `frontier` を毎回別ディレクトリへ保存して
   **和集合（∪）と積集合（∩）**を出す（∪と∩の差が LLM ゆらぎの実測幅。これも記録する）。

### 9.2 採取後のゲート判定（§4.9）

`metrics.jsonl` を集計する。**除外**するのは以下の波（§4.9「外れ値の扱い」。除外理由は
`paused` ＞ `reused` ＞ `suspect` ＞ `null` の優先順で1つに一意化し、除外波数は実数で数える）:

- `paused`（paused-at-limit / 2nd）を挟んだ波
- `classify_wall_ms_reused: true` の波
- `classify_wall_ms_suspect: true` の波
- `classify_wall_ms` が `null` の波

**判定（両方満たす場合のみ Stage 2 へ）:**
- `classify_wall_ms ≥ 60,000` の波が**除外後の有効波の 20% 以上**（有効波が3波未満なら判定しない）
- その該当波の **`classified` の中央値が 80 以上**（＝既定チャンクサイズ40の2倍）

提示物には**除外波の一覧（波数・`classify_wall_ms`・`classified`・除外理由）**と、
§4.9.1 の感度表に実測 `classified` を当てはめたトークン増分予測を必ず添える。

### 9.3 判定結果ごとの次アクション

| 判定 | 次アクション |
|---|---|
| ゲート成立 | §4.9「Stage 2 再承認時の必須補完事項」（§4.5(b)(e)・§4.6 の Before/After、Stage 2 の再利用波検出方式の確定）を書いて再承認 → Stage 2。**その前に §4.9.1 (e) のプロンプトキャッシュ有効性を実測すること** |
| ゲート不成立 | 本プランを保留し、Stage 1 の計測と基準線を成果として残す（§4.9 の規定どおり） |
| 判定不能（有効波 < 3） | 母体をより大きなリポジトリに替えて再採取するか、人の判断で A 案（ゲート非依存の決定的層のみ実装）へ進む |

### 9.4 A案（ゲート非依存・0トークンで検証できる範囲）

ゲート判定を待たずに実装できる Stage 2 の部分集合。**いずれも既定値で挙動不変・`make test` で検証可能**。
着手する場合も CLAUDE.md「変更前の計画・合意」に従い、§4.9 の必須補完事項（Before/After）を先に書いて再承認する。

- `specout_bfs.py`: (a) `known_symbols` 出力 / (b) チャンク分割出力（`--hits-dir`・`--chunk-size`）/
  (e) `commit-wave --unsupported-patterns` / (f) `status --brief`
- 新規 `merge_classification.py` ＋ `tests/test_merge_classification.py`
- `tools/harness/refcheck.py` の `DETERMINISTIC_SCRIPTS` へ `merge_classification.py` を追加

**含めない**（構造変更・ゲート依存）: SKILL.md の波ループ移設、`xddp-specout-agent.md` の MODE 再定義、
classifier エージェント新設、`recovery-procedures.md` の S2 差し替え、docs/ADR/README/smoke_config の更新。

（A案は Stage 2 本体が別途承認・実装完了したため、実質的に不要になった。§10 参照）

---

## 10. Stage 2 実装完了記録（2026-08-09）

§8 の Stage 2 承認を受け、§3〜§4 の全 S2 変更を実装した。

**実装したファイル（§3 S2 行と1対1）:**
- `ClaudeCode/.claude/skills/xddp.04.specout/scripts/specout_bfs.py`: (a) `known_symbols` の素名正規化配布、
  (b) `search --hits-dir`/`--chunk-size` によるファイル単位グルーピング・チャンク分割出力（stale チャンクの
  事前削除を含む）、(e) `commit-wave --unsupported-patterns` によるセクション内挿入ヘルパ
  （`_append_unsupported_patterns`）、(f) `status --brief`。あわせて §4.5(d)「判定方法〔S2〕」の
  `commit-wave --chunk-mtime-min` を追加し、モジュール docstring の Usage・LLM プロトコル節を更新した。
- `ClaudeCode/.claude/skills/xddp.04.specout/scripts/tests/test_specout_bfs.py`: 上記の単体テストを21件追加
  （既存99件 → 120件。うち1件は既存のスキップ）。
- （新規）`ClaudeCode/.claude/skills/xddp.04.specout/scripts/merge_classification.py` ＋
  `tests/test_merge_classification.py`（15件）。§4.6 の実装制約（`ArgumentParser(description=__doc__)`
  不使用・docstring にフラグ非列挙）を満たす。
- `tools/harness/refcheck.py`: `DETERMINISTIC_SCRIPTS` に `merge_classification.py` を追加。
- `ClaudeCode/.claude/skills/xddp.04.specout/SKILL.md`: 「## Step A」の波ループをオーケストレータ側へ
  再設計（Setup: discovery-setup ＋ 波ループ a〜e）。CR Resolution 受領キー列挙行に
  `SPECOUT_CLASSIFY_CHUNK_SIZE`/`SPECOUT_CLASSIFY_PARALLEL` を追記。状態テーブル・`status --brief` 化を
  §4.2 のとおり改訂。
- `ClaudeCode/.claude/agents/xddp-specout-agent.md`: `MODE: discovery-setup` へ再定義。Step 2「BFS ループ」・
  Step 3・伝播種別判定ルール表・grep未対応パターン表を classifier エージェントへ逐語移設し、
  「Step 2: Wave 0 探索の開始（init 実行）」へ置き換えた。
- （新規）`ClaudeCode/.claude/agents/xddp-specout-classifier-agent.md`: `tools: Read/Grep/Write`。
  判定手順・伝播種別ルール・grep未対応パターン対処を逐語移設し、`known_symbols` ベースの判定基準・
  `unsupported_patterns` 出力（discovery-log 非直接編集）を明記。
- `ClaudeCode/.claude/skills/xddp.04.specout/recovery-procedures.md`: 「Discovery エージェントを
  呼び出す／再起動する」前提の文言を「SKILL 側の波ループを再開する」に改訂。「## Wave 途中失敗からの
  再開（経路統一）」を §4.7【S2】のチャンク単位再利用手順（`merge_classification.py` による判定）へ
  差し替え、Stage 1 が持ち込んだ全体出力 `status` 呼び出しは `search --hits-dir` により削除した。
- `ClaudeCode/.claude/skills/xddp.common/SKILL.md`（「## Load Config」）: `SPECOUT_CLASSIFY_CHUNK_SIZE`
  （既定 `40`）・`SPECOUT_CLASSIFY_PARALLEL`（既定 `4`）を Output 一覧・Process 手順2・
  CR Resolution の2箇所へ配線（`SPECOUT_BACKEND` の前例に準拠）。
- `ClaudeCode/.claude/skills/xddp.01.init/templates/xddp.config.md`: 上記2キーを `SPECOUT_HIT_FILTER`
  の隣接位置に追加。
- `docs/specout-discovery-guide.md`: 「分離単位」表を discovery-setup／波ループ／classification の
  3層構成へ更新。
- （新規）`docs/adr/ADR-0010-specout-parallel-classification.md` ＋ `docs/adr/README.md` の索引行。
- `CLAUDE.md`: ファイル構成テーブル（`merge_classification.py` の役割）、
  「xddp.config.md の位置付け」節に新設定キー2種の説明を追加。
- `README.md`: 「## サブエージェント一覧」表に `xddp-specout-classifier-agent` を追記し
  `xddp-specout-agent` の役割説明を更新、スクリプト一覧テーブルに `merge_classification.py` を追加し
  `specout_bfs.py` の説明を更新（README 全体の件数是正・未掲載6件の追記は §5 のとおり本プランのスコープ外
  として据え置いた）。
- `tools/harness/smoke_config.md`: 工程04の実測 $/起動が並列 classifier 導入**前**の値である旨を
  ⚠️ 注記した。**実測の更新自体は未実施**（本セッションは API 認証未設定のため `make smoke-full` を
  実行できない。次回校正ラン時に工程04を再実測し、本値と `SMOKE_TOKEN_BUDGET` を確定すること）。

**検証:** `make test`（`refcheck` ＋ 全 unittest）が緑（specout のユニットテストは 86 → 132 件、
新規 `test_merge_classification.py` の15件を含む）。`bash ClaudeCode/setup.sh` で `~/.claude/` へ
デプロイ済み（デプロイ後の diff で内容一致を確認）。

**未実施（本プランのスコープ外として明示的に据え置き）:**
1. **`make smoke-full PHASE=04` による意味層検証**（§6「Stage 2 意味層」の全項目）。
   `CLAUDE_CODE_OAUTH_TOKEN`／`ANTHROPIC_API_KEY` のいずれも本セッションには設定されておらず、
   隔離 HOME 実行を要する `smoke-full` を起動できない。次回、認証が利用可能なセッションで
   `SPECOUT_CLASSIFY_CHUNK_SIZE` を小さく設定したシードを用いて実施すること（§6 の前提条件を参照）。
2. **不変条件1（基準線に対する確定影響ファイル集合の非縮小）の実 CR での検証**、および
   プロンプトキャッシュ有効性（プレフィクスのバイト同一性・コールドスタート対策）の実装後再実測。
   いずれも意味層検証の一部であり、上記1と同時に実施する。
3. `tools/harness/smoke_config.md` の工程04実測値・`SMOKE_TOKEN_BUDGET` の再算定（上記参照）。
4. ~~README.md の件数是正・未掲載6サブエージェントの追記~~ → **2026-08-09 完了**
   （§5・§8 承認欄の申し送り。エージェント数「15種」→17種・スキル数「16種」→24種に是正し、
   「## サブエージェント一覧」表に未掲載6件（`xddp-chd-sync-agent`・`xddp-close-knowledge-agent`・
   `xddp-close-promote-agent`・`xddp-design-sync-agent`・`xddp-specs-mod-agent`・`xddp-specs-uc-agent`）
   ＋本プランで新設した `xddp-specout-classifier-agent` を追記。現行の全17エージェントと1対1で一致することを確認済み）。
5. ~~code-knowledge 参照が成果物へ到達しない既存欠陥（§4.3・申し送り4点）の別プラン起票~~ →
   **2026-08-09 起票完了:** [PLAN-20260809-specout-code-knowledge-relay.md](PLAN-20260809-specout-code-knowledge-relay.md)
   （草案・承認待ち。実装は当該プランの承認後に別途実施する）。

上記1・2（意味層検証）が完了するまで、Stage 2 は**決定的層のみ検証済み**の状態である。
実 CR での効果測定（壁時計短縮の実測・トークン増分の実測確認）は次回のトークン予算が確保できる
セッションで実施すること。
