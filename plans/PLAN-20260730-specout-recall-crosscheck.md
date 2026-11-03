# PLAN-20260730-specout-recall-crosscheck

作成日: 2026-07-30
ステータス: **承認待ち**
> 保留: PLAN-20261103-contract-audit の A2 の開始から統合の終わりまで実装しない（同プランの 3.2.4）。その後も、同プランで A3 の指摘を割り当てたすべての修正プランの実装の後（割り当てた修正プランが無ければ、A3 の指摘の扱いを「段階3 の割り当て」に記録した後）に、同プランの 3.3 のとおり書き換え、AI レビューをやり直してから承認・実装に進む。

> **目的:** Discovery BFS の**検索漏れ（偽陰性）を機械的にクロスチェックする層**を新設する。
> 既存 [PLAN-20260730-p5-specout-backend-abstraction.md](PLAN-20260730-p5-specout-backend-abstraction.md)
> は参照解決の**バックエンド差し替え**（主眼は偽陽性剪定）であり、本プランは別レイヤ＝
> **BFS とバイアスの異なる独立オラクルによる漏れ候補列挙＋事後 recall 実測**を扱う。両者は独立に実装可能。

---

## 1. 背景・目的

### 1.1 現状の事実（実地調査・2026-07-30）

行番号はドリフトするため関数名・セクション名で示す。

- **参照解決はテキスト検索のみ。** `specout_bfs.py` の `_run_rg_patternfile`（rg 経路）/
  `_run_grep_batch`（grep 経路）が語境界付きパターン `\bSYM\b`（`escape_symbol` でエスケープ）を
  実行する。型情報・スコープ情報は一切使わない。
- **Phase 3 検証スイープは同一エンジンでの再 grep。** `xddp-specout-agent.md`「## Phase 3: 検証スイープ
  （Phase 2 の末尾）」は discovery-log の全シンボルを同じ grep で再検索し、SPO 記録済みファイルと
  突き合わせる。したがって**帳簿ミス（記録漏れ）は検出できるが、手法起因の漏れ（grep が原理的に
  見えないもの）は構造的に検出できない**。同セクションの「【検証スイープの限界】」も
  「ファイル単位の漏れを検出。伝播パスの正しさは保証しない」と限界を宣言している。
- **grep 未対応14パターンは検索されない。** `xddp-specout-agent.md`「### grep未対応パターンへの対処」表
  （リフレクション・動的ディスパッチ・インタフェース型依存・ジェネリクス/型エイリアス・
  モジュール再エクスポート・エイリアス・マクロ展開・設定/DI経由・Go 暗黙実装・デコレータ・
  イベント駆動・遅延インポート・デストラクチャリング）は「discovery-log に記録して人手確認を促す」だけで、
  検索は行われない。
- **除外領域の波及は可視化されない。** `_build_exclude_include_grep` / `_build_exclude_include_rg` が
  `SPECOUT_EXCLUDE_PATTERNS`（既定で `tests/`・`fixtures/`・`vendor/` 等）と
  `SPECOUT_INCLUDE_EXTENSIONS` を無条件に適用する。除外側にヒットがあっても件数すら残らない。
- **既存の独立チェックは帳簿系のみ。** `specout_verify_counts.py` は discovery-log の件数一致検証であり、
  recall（漏れの有無）とは無関係。
- **確定集合は機械可読で存在する。** `bfs-state.json` の `confirmed_files`（`_upsert_confirmed_files_section`
  が discovery-log へ描画する元データ）に `{path: {wave, confidence}}` が入っている。オラクルの残差計算に
  そのまま使える。

**結論:** 現状「漏れがないこと」を検査する独立オラクルが 1 つも無い（同一手法の再実行のみ）。

### 1.2 ツール制約（実測・2026-07-30、本開発機）

| ツール | 状態 | 判断 |
|---|---|---|
| `grep` | あり（POSIX 必須。BSD/GNU 双方で `-r -n -E --exclude-dir` を既存コードが使用中） | **採用** |
| `git` | あり。既に `xddp.close`・`xddp.sync-design`・`xddp.feedback`・`xddp.fill-rulebook`・`xddp-design-sync-agent`・`xddp-chd-sync-agent` の 6 ファイルが依存 | **採用**（新規依存ではない） |
| `python3`（標準ライブラリのみ） | あり。全決定的スクリプトの既存前提 | **採用** |
| `rg` | この機にはあるが Linux/mac/WSL の標準搭載ではない | 既存どおり「あれば使う」。新規要件にしない |
| `global` / `gtags` | **未インストール**。標準搭載ではない | **不採用** |
| `ast-grep` / `sg` | **未インストール**。標準搭載ではない | **不採用** |
| `ctags` | `/usr/bin/ctags` は BSD ctags（`--version` が `illegal option`）。universal-ctags ではない | **不採用**（P5 段階2 の推奨は本制約と衝突する。§6 に記録） |

`global`（GNU GLOBAL）を仮に導入しても、得られるのは主に索引速度と定義/参照の区別＝**偽陽性の削減**で
あり、§1.1 の 14 パターン（偽陰性）は解決しない。また C 系以外の参照索引はプラグインパーサ依存で精度は
**確認していない**。よって本プランでは採用しない。

### 1.3 目的

`grep` ＋ `git` ＋ `python3` 標準ライブラリのみで、

1. **BFS とバイアスの異なる 3 オラクル**を実行し、確定集合に含まれない残差を「漏れ候補」として機械列挙する
2. 候補が解消（追加ドキュメント化 or 根拠付き承認）されるまで**工程 4a を完了させないゲート**にする
3. 工程 7 の実装差分を正解データとして**事後 recall を機械実測**し、オラクルの有効性と閾値の根拠を蓄積する

オラクルは recall を**証明しない**（証明には正解データが必要）。本プランの主張は「見えない漏れを、
列挙された候補＋事後実測値に変換する」ことに限る。

---

## 2. スコープ

### 2.1 対象（本プランで確定）

| ID | オラクル/機構 | 手段 | 捕まえる漏れの種類 |
|---|---|---|---|
| **C** | 除外領域の逆検査 | 確定 HIGH シンボルを除外パターン・拡張子フィルタ**無効**で再 grep | テスト・fixture・vendor 側の改修漏れ、設定/リソースファイル（拡張子外）の漏れ |
| **B** | git 共変更（logical coupling） | `git log --name-only` の共起集計 | 設定・リソース・i18n・ビルド・DI 配線など**静的解析で原理的に見えない**波及 |
| **D** | 識別子の名前変異・文字列リテラル | シンボル名から機械生成した表記変異を grep | DI キー・設定キー・イベント名・リフレクション文字列 |
| **G** | 工程 4a 完了ゲート | 候補 0 件または全件根拠付き承認まで工程 4b へ進めない | — |
| **F** | 事後 recall 実測 | `git diff --name-only {baseline_commit}..HEAD` × `confirmed_files` | 実際に起きた漏れの**実測値**とオラクル別の的中実績 |

### 2.2 非対象

- **import/include グラフ閉包オラクル（A）。** re-export・エイリアス漏れに最も効くが、言語別 import
  パターン表とモジュール名解決の設計が必要で規模が大きい。**別プランへ分離**（F の実測で「re-export 系の
  漏れが実際に起きている」ことを確認してから投資判断する）。
- **参照解決バックエンドの変更**（P5 の担当領域）。本プランは既存の rg/grep 経路をそのまま呼ぶ。
- **grep 未対応14パターンの記録機構の変更。** 動的系はどのオラクルでも残るため現行維持。
- **LLM の classification 契約・`commit-wave` の帳簿ロジック。** 一切触らない。
- **設定キーの追加。** オラクルの閾値は当面スクリプト内定数とし、F の実測後に別プランで調整する
  （設定過多の回避。§6 に未検証仮定として記録）。
- 後方互換性の保証（CLAUDE.md 後方互換性ポリシー）。ただし `bfs-state.json` の**前方互換読み込み**
  （新フィールド欠落時に既定値で動作）は受入条件とする。

---

## 3. 変更対象ファイル

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `ClaudeCode/.claude/skills/xddp.04.specout/scripts/specout_crosscheck.py` | **追加** | オラクル C/B/D の実行本体。サブコマンド `run` / `approve` / `status`。標準ライブラリのみ。`grep`・`git` は `subprocess` 経由 |
| `ClaudeCode/.claude/skills/xddp.04.specout/scripts/tests/test_specout_crosscheck.py` | **追加** | `subprocess`（grep/git）をモックした unittest。**0トークン** |
| `ClaudeCode/.claude/skills/xddp.common/scripts/xddp_recall_report.py` | **追加** | F（事後 recall 実測）。`bfs-state.json` ＋ `crosscheck.json` ＋ `git diff` のみを読む。`xddp.close` から呼ぶため全スキル共通側に置く（CLAUDE.md のスクリプト配置規約に従う。他スキルの scripts/ を跨いで呼ぶ先例は無い＝`chd_sp_coverage.py` は自スキル内からのみ呼ばれている） |
| `ClaudeCode/.claude/skills/xddp.common/scripts/tests/test_xddp_recall_report.py` | **追加** | 同上。`git` をモックした unittest。**0トークン** |
| `ClaudeCode/.claude/skills/xddp.04.specout/scripts/specout_bfs.py` | 修正 | `_default_state` に `baseline_commit`（既定 `""`）を追加。`cmd_init` で `git -C {repo_path} rev-parse HEAD` を記録（非 git / git 不在時は空文字＋警告を discovery-log へ記録＝無音縮退の禁止）。**参照解決・帳簿ロジックは変更しない** |
| `ClaudeCode/.claude/skills/xddp.04.specout/SKILL.md` | 修正 | 「## Step A-Document」と「## Step A2: SPO Review Loop」の間に **`## Step A-CrossCheck`** を新設。`specout_crosscheck.py run` の Bash 呼び出し（`PY=$(command -v python3 \|\| command -v python)` 規約踏襲）＋候補提示＋承認ゲート＋`approve` 記録。progress.md の DETAIL_STEP 更新を既存 `## Progress Update` 適用で行う |
| `ClaudeCode/.claude/agents/xddp-specout-agent.md` | 修正（最小） | 「## Phase 3: 検証スイープ（Phase 2 の末尾）」の【検証スイープの限界】に「手法起因の漏れはスキル側 `Step A-CrossCheck` の独立オラクルが扱う」1 文を追記。**参照解決手順・14パターン表は変更しない** |
| `ClaudeCode/.claude/skills/xddp.close/SKILL.md` | 修正 | 「## Step C-Pre: All Repos Git Status Check」の後に **`## Step C-Recall`** を新設し `xddp_recall_report.py` を実行。「## Step A: Collect Insight/Proposal Memos」の収集対象に `recall-report.md` を追加 |
| `tools/harness/refcheck.py` | 修正 | `DETERMINISTIC_SCRIPTS` に `specout_crosscheck.py`・`xddp_recall_report.py` を追加（検査D の SKILL→スクリプト結線・フラグ照合対象にする） |
| `tools/harness/tests/test_refcheck.py` | 修正 | `refcheck.py` の注記「変更時は test_refcheck.py の該当ケースも更新すること」に従い該当ケースを更新 |
| `CLAUDE.md` | 修正 | ファイル構成テーブルの `xddp.04.specout/scripts/`・`xddp.common/scripts/` の説明へ新スクリプトを追記 |
| `README.md` | 修正 | 工程4の説明・スクリプト一覧に該当箇所があれば追記 |
| `docs/adr/`（新規1ファイル） | 追加 | 「検索漏れは参照解決の精度向上ではなく独立オラクル＋事後実測で扱う」設計判断。ツール制約（標準搭載のみ）と `global`/ctags 不採用理由を記録 |

**変更不要（確認済み）:** `specout_verify_counts.py`（件数整合の独立チェックで参照解決非依存）、
`commit-wave` の帳簿ロジック、`wave-{N}-class.json` スキーマ、`xddp.01.init/templates/xddp.config.md`
（設定キー追加なし）、他工程スキル。

**設計上の注記:** `refcheck.py` の検査D は `discover_skill_md`（`skills/**/*.md`）のみを走査対象とし、
`agents/*.md` の script 呼び出しは結線照合されない。したがってクロスチェックの起動は
**エージェント本文ではなく SKILL.md 側に置く**（静的検査の網に入れるため）。

---

## 4. 変更内容（設計）

> 実装は承認後。本節は関数名・セクション名アンカーで設計を確定する。

### 4.1. 共通の入出力契約

- **入力:** `bfs-state.json`（`repo_path`・`confirmed_files`・`visited`・`exclude_patterns`・
  `include_extensions`・`symbol_module`・`high_noise_symbols`）
- **出力（機械可読）:** `{CR_PATH}/04_specout/{repo}/crosscheck.json`
  ```
  { "generated": "<TODAY>", "oracles": { "<oracle-id>": { "status": "ok|skipped",
    "skip_reason": "...", "candidates": [ {"path": ..., "oracle": ..., "evidence": {...}} ] } },
    "approved": [ {"path":..., "reason":..., "approved_on":...} ] }
  ```
- **出力（人可読）:** discovery-log.md の新セクション `## クロスチェック結果`（`_append_to_file` /
  `_upsert_*` と同じ「毎回セクション全体を再構築」方式で冪等に更新する）
- **確定集合との差分:** すべてのオラクルは `confirmed_files` のキー集合に含まれるパスを候補から除外する。
  XDDP 成果物ディレクトリ（`{XDDP_DIR}/` 配下）も除外する。
- **縮退時の挙動:** 前提（git 履歴・grep 実行可否）が満たされない場合は当該オラクルを
  `status: skipped` ＋ `skip_reason` で記録し、discovery-log にも警告を残す（**無音縮退の禁止**）。
  他オラクルは継続する。

### 4.2. オラクル C — 除外領域の逆検査（`--oracle excluded-scope`）

1. `confirmed_files` のうち確信度 HIGH のシンボル群（`visited` の平文シンボル＝MEDIUM スコープ付き
   `symbol[MEDIUM:path]` を除いたもの）を対象にする。
2. `_build_exclude_include_*` 相当の除外・拡張子オプションを**付けずに**同じ複合パターンで再検索する。
   検索手段は既存と同一（`rg` があれば rg、無ければ `grep -rn -E`）。
3. ヒットを 2 系統に分類して集計する。
   - **除外ディレクトリ系:** パスが `exclude_patterns` のいずれかに該当
   - **拡張子外系:** `include_extensions` が非空で、拡張子が含まれない（設定・リソース・ビルド定義等）
4. ディレクトリ単位に集約し、`{ディレクトリ, 系統, ヒット件数, 代表ファイル最大3件, 該当シンボル}` を候補にする。

ノイズ対策: ファイル一覧を全列挙せずディレクトリ集約＋代表 3 件に留める（人の判定コストを一定に保つ）。

### 4.3. オラクル B — git 共変更（`--oracle co-change`）

1. `git -C {repo_path} log --no-merges --pretty=format:%H -- {confirmed_files のパス群}`
   → 確定ファイルを触ったコミット SHA 集合（既定上限 500 コミット）。
2. 各 SHA について `git -C {repo_path} show --name-only --pretty=format: {sha}` でファイル一覧を取得。
   **ファイル数が閾値（既定 50）を超えるコミットは一括整形・リネーム等と見なして除外**する。
3. python3 標準ライブラリで集計する。
   - `support` = そのファイルが確定ファイルと同一コミットに現れた回数
   - `confidence` = `support` ÷ （確定ファイルを触ったコミット総数）
4. 既定閾値 `support ≥ 3` かつ `confidence ≥ 0.3` を満たし、`confirmed_files` に無いものを候補にする。
   候補は `confidence` 降順・上限 20 件。
5. `{path, support, confidence, 代表コミットSHA 3件}` を evidence として記録する。

前提不成立時の `skip_reason`: 「非 git リポジトリ」「`git` コマンド不在」「対象コミット数 < 3（履歴不足）」。
リネーム追跡（`--follow`）は使わない（複数パス指定と併用できず、結果が不安定なため）。

### 4.4. オラクル D — 名前変異・文字列リテラル（`--oracle name-variants`）

Wave 0 シンボル（`_discovery_log_header` の「初期シンボル」に相当するもの＝`cmd_init` の `--symbols`）と
確定 HIGH シンボルを入力に、**決定的規則**で表記変異を生成する。

| 変異種別 | 規則 | 既定 |
|---|---|---|
| ケース変異 | camelCase/PascalCase ⇄ snake_case / kebab-case / SCREAMING_SNAKE_CASE の相互変換 | 有効 |
| 引用符付き完全一致 | `"SYM"` / `'SYM'`（区切り文字を含む DI キー・イベント名・設定キーを狙う） | 有効 |
| 語境界なし後方一致 | `SYM` を語境界なしで検索（マクロのトークン結合 `PREFIX##SYM` 等） | **無効（opt-in）** |

- 生成結果から元表記と重複するもの、`visited` に既に含まれる名前、長さ 3 文字以下のものを除外する
  （短い識別子は偽陽性が支配的になるため）。
- ヒットのうち `confirmed_files` に無いファイルを候補にし、**変異種別を kind として分離**して報告する
  （確信度が異なるため一括提示しない）。候補上限は変異種別ごとに 20 件。

ドメイン中立性: 生成規則は識別子の表記法のみに依存し、言語・ドメイン（Web / 業務 / 組み込み / 制御 /
科学技術計算）に依存しない。

### 4.5. ゲート G — `Step A-CrossCheck`（`xddp.04.specout/SKILL.md`）

1. Document フェーズ完了後、各 `{repo}` について `specout_crosscheck.py run` を実行する。
2. 候補 0 件（かつ全オラクルが `status: ok`）→ そのまま `## Step A2: SPO Review Loop` へ進む。
3. 候補 1 件以上、またはいずれかのオラクルが `skipped` → 人へ提示する。
   > ⚠️ {repo} のクロスチェックで漏れ候補 {N} 件を検出しました（オラクル別内訳: …）。
   > 各候補について「追加ドキュメント化」または「影響なし（根拠）」を指定してください。
   > スキップされたオラクル: {skip_reason}
4. 人の判断を待つ。追加ドキュメント化が選ばれた場合は Document フェーズを該当ファイルに対して再実施する。
   「影響なし」が選ばれた場合は `specout_crosscheck.py approve --path ... --reason "..."` で
   `crosscheck.json` と discovery-log に根拠を機械記録する（`--reason` 未指定・空はエラー＝
   `cmd_prune` の理由必須と同じ規約）。
5. 全候補が解消するまで工程 4b（`## Step B: Update CRS with Specout Findings`）へ進まない。
   既存の Phase 3 未記録ヒットゲート（`xddp-specout-agent.md`「## Phase 3」5 項）と同型の運用にする。

### 4.6. F — 事後 recall 実測（`xddp_recall_report.py`、`xddp.close/SKILL.md` の `Step C-Recall`）

1. `cmd_init` 時点で `bfs-state.json` に `baseline_commit`（`git rev-parse HEAD`）を記録しておく（§3）。
2. close 時に `git -C {repo_path} diff --name-only {baseline_commit}..HEAD` で実装差分ファイル集合を得る。
   XDDP 成果物ディレクトリ配下と `bfs-state.json` の `exclude_patterns` 該当分は集計対象外にする。
3. 突き合わせ結果を `{CR_PATH}/04_specout/{repo}/recall-report.md` に出力する。
   - **実漏れ (miss):** 実装で変更されたが `confirmed_files` に無いファイル
   - **過剰検出 (over):** `confirmed_files` にあるが実装で変更されなかったファイル（参考値。設計判断で
     結果的に変更不要となる場合を含むため、精度指標として扱わない旨を明記する）
   - **recall = |confirmed ∩ changed| ÷ |changed|**
4. **各 miss について `crosscheck.json` を照合し、どのオラクルが候補として挙げていたかを記録する。**
   これによりオラクル別の的中実績（＝閾値調整の実測根拠）が CR ごとに蓄積される。
5. `xddp.close`「## Step A」の収集対象に `recall-report.md` を追加し、知見ログ（lessons-learned）へ
   流れるようにする。

`baseline_commit` が空（非 git 等）または欠落（旧 `bfs-state.json`）の場合は
「実測不可（理由）」を出力して正常終了する（工程を止めない）。

---

## 5. 影響範囲

- **影響するスキル・コマンド:** `xddp.04.specout`（新 Step A-CrossCheck ＝**工程 4a の完了条件が厳格化する**）、
  `xddp.close`（新 Step C-Recall。レポート出力のみでゲートにしない）。
- **影響する工程:** 工程 4a（ゲート追加）、CR クローズ（レポート追加）。成果物文法（SPO・CRS・
  discovery-log の既存セクション）は不変で、discovery-log に新セクションが 1 つ増える。
- **後方互換性:** 保証しない（CLAUDE.md ポリシー）。ただし `bfs-state.json` に `baseline_commit` が
  欠落した既存状態ファイルを読んでも既定値で動作すること（前方互換読み込み）は受入条件。
- **デプロイ:** `ClaudeCode/.claude/` 配下の変更のため `setup.sh` の対象。`tools/harness/` は
  デプロイ対象外（開発時メタツール）。
- **外部依存:** `grep`・`git`・`python3` 標準ライブラリのみ。**新規外部バイナリなし**。`rg` は
  あれば使う（既存どおり）。
- **ドメイン中立性（CLAUDE.md 必須）:** 3 オラクルはいずれも言語・ドメイン非依存
  （C は除外パス集計、B は git 履歴、D は識別子表記法）。言語別パーサ・import パターン表を
  持ち込まないため、Web / 業務 / 組み込み / 制御 / 科学技術計算のいずれでも同一に成立する。
- **トークン/コスト:** 実装・テストは 0 トークン（決定的スクリプト＋モック unittest）。
  実行時は候補提示分のコンテキストが増える（上限設計で抑制。§4.2〜4.4 の候補上限）。
  ゲートにより工程 4a の停止回数は増える＝**人の判断コストは意図的に増やす**（漏れの見落としと
  トレードオフした設計判断であり、ADR に記録する）。

---

## 6. リスクと未検証仮定

| 項目 | リスク | 緩和 |
|---|---|---|
| **閾値が未検証** | B の `support ≥ 3 / confidence ≥ 0.3`、C/D の候補上限は根拠のない初期値。ノイズ過多で運用されなくなる | 既定を保守的に置き、**F の実測（オラクル別的中実績）で校正**する前提を ADR とスクリプト docstring に明記。調整は別プラン |
| **D（名前変異）のノイズ** | ケース変異・引用符一致は偽陽性が出やすい | 変異種別ごとに kind 分離・上限 20 件・3 文字以下を除外。語境界なし後方一致は既定無効（opt-in） |
| **モノレポでの B の誤検出** | 大規模モノレポでは無関係ファイルが共起しやすい | 巨大コミット（既定 50 ファイル超）除外＋`confidence` 閾値。それでも残る場合は F の実績で閾値調整 |
| **並行 CR による F の汚染** | `baseline_commit`..HEAD に他 CR のコミットが混入し、miss/over が過大になる | recall は**参考値**である旨をレポート冒頭に明記。並行 CR 運用は既知（`xddp.close`「## Step C0: Pre-close Sync (Parallel-CR Support)」が既に前提としている） |
| **git 履歴が浅い / 非 git** | B・F が成立しない | `status: skipped` ＋ `skip_reason` を記録して継続（無音縮退の禁止）。他オラクルは動く |
| **BSD grep と GNU grep の差異** | 除外オプション等で挙動差が出る | 既存 `_build_exclude_include_grep` が使っている手段（`-r -n -E`・`--exclude-dir`）に限定し、新しいオプションを導入しない |
| **ゲートが厳しすぎて工程が停滞** | 候補が多い CR で工程 4a が進まない | 承認は根拠 1 行で通る設計＋候補上限で提示量を一定に保つ。F の実測で「候補ゼロ件率」を観測し、必要なら別プランで `report-only` 設定を追加検討（本プランでは設定を追加しない） |
| **P5 段階2 推奨との齟齬** | P5 §4.4 は段階2 に universal-ctags を推奨するが、標準搭載ではない（実測：本機の `/usr/bin/ctags` は BSD ctags） | 本プランは P5 と独立レイヤであり衝突しない。P5 段階2 の候補選定は「標準搭載ツール制約」を踏まえて同プラン側で再評価すべき旨を ADR に記録 |
| **オラクルは recall を証明しない** | 「クロスチェック済み＝漏れなし」と誤解される | discovery-log・SPO・recall-report に「オラクルは候補を列挙するもので、漏れの不在を証明しない」を明記（Phase 3 の【検証スイープの限界】と同じ書式） |

---

## 7. 確認項目

**実装（0トークン）**
- [ ] `make test`（L1〜L3）が緑（新規 2 スクリプトの unittest 追加後も既存 BFS 帳簿テストに回帰なし）
- [ ] `refcheck`（L1/L3）が緑（`DETERMINISTIC_SCRIPTS` 追加後の SKILL→スクリプト結線・フラグ照合）
- [ ] `subprocess`（grep / git）をモックし、テストが外部コマンド・ネットワークに依存しない
- [ ] 候補 0 件時にゲートが素通りし、工程 4b へ進む
- [ ] `git` 不在 / 非 git / 履歴不足で B・F が `skipped` ＋ `skip_reason` を記録し、他オラクルは継続する（無音縮退の禁止）
- [ ] `approve --reason` が空・未指定でエラーになる（`cmd_prune` の理由必須と同一規約）
- [ ] `crosscheck.json` と discovery-log の `## クロスチェック結果` が再実行で冪等（重複追記なし）
- [ ] `baseline_commit` 欠落の旧 `bfs-state.json` を読んでも既定値で動作し、F は「実測不可（理由）」で正常終了
- [ ] F が miss ごとに「どのオラクルが挙げていたか」を出力する

**挙動確認（トークン消費あり）**
- [ ] スキル挙動に関わる変更のため `make smoke-full PHASE=04`（隔離HOME・予算ガード）で
      Step A-CrossCheck が起動し、候補提示→承認→工程 4b へ進む経路が通る

**共通**
- [ ] CLAUDE.md（ファイル構成テーブル）・README.md の記述と整合
- [ ] 特定ドメイン（Web・業務・組み込み・制御・科学技術計算）への偏りがないか（CLAUDE.md「適用ドメインの中立性」）
- [ ] 実行時指示と設計根拠の分離：設計判断・不採用ツールの理由は `docs/adr/` へ、スキル本文には参照 1 行
- [ ] 相互参照に行番号を使っていない（CLAUDE.md「相互参照のルール」）

---

## 8. レビュー

AIレビュー結果: [plans/review/PLAN-20260730-specout-recall-crosscheck-review.md](review/PLAN-20260730-specout-recall-crosscheck-review.md)

`/xddp.plan-review` で Critical（🔴）・残指摘（🟡/🔵）がゼロになるまで実施予定。

---

## 9. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | |
| 承認日 | |
| 備考 | スコープは人の選択により確定（オラクル C+B+D ＋ 事後 recall 実測 F、結果は工程4a のゲートとする。import 閉包オラクル A は別プランへ分離）。承認前に `ClaudeCode/.claude/` は編集しない（CLAUDE.md 必須手順） |
