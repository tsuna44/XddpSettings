# PLAN-20260725-p2-test-harness

作成日: 2026-07-25
ステータス: **実装完了（L1〜L3）／L4〜L5 も有効化済み（2026-07-26・軽量 advisory・子プラン PLAN-20260726-smoke-full-runner-enablement B〜D 完了。goldens 02〜11・`SMOKE_TOKEN_BUDGET`=30・Sonnet 単一・close は手動検証）**

### 実装状況（2026-07-25）

**L1〜L3（0トークン層・完了）:**
- `tools/harness/refcheck.py`（検査A/B/C/D）・`run_all.py`（`make test` 実体）・`Makefile`・
  `pre-commit.sample` を実装。`make test` が緑（全 unittest 6 スイート ＋ refcheck）で約2秒。
- `refcheck` を現行リポジトリに実行 → **エラー0・警告10**。検査A（`apply` 175箇所）・
  検査D（スクリプト結線）は完全にクリーン。警告の内訳と棚卸し結果:
  - 検査B: 5件＝`### Inputs` 節を持たない3エージェント（`xddp-reviewer`・`xddp-chd-sync-agent`・
    `xddp-design-sync-agent`）の契約照合スキップ通知（plan 3.1 の想定どおり best-effort）、
    1件＝`xddp-verifier-agent` の非定型 pass ブロックのスキップ、3件＝caller 注入タスクキー
    （`CLASSIFICATION_TASK`・`ALTERNATIVES_TASK`・`PAST_CROSS_DESIGN_DIR`。エージェントが名前で
    参照しない正当な設計）。いずれも真の違反ではない。
  - 検査C: 1件＝`{SPECOUT_MAX_WAVE_DEPTH}`（テンプレート内の設定例示。人が確認する候補として残す）。
- **過検出の解消（Section 5 の棚卸し）:** 初回実行で 128 error を検出したが、うち大半は
  (1) エージェント入力宣言のカンマ区切り複数キー記法（`` - `A`, `B`, `C` ``）のパース漏れ、
  (2) 多モードエージェント（spec-writer の create/update/update-design）・条件付き入力に対する
  「必須キー欠落」検査の構造的偽陽性（73件）だった。前者はパーサ修正で解消。後者は
  plan 3.1「確実な誤りのみ error／過検出で運用を破綻させない」に従い、**必須キー欠落方向の
  検査を静的リントから外し L4/L5 full-run スモークに委譲**、契約キー照合は「エージェント本文の
  どこにも現れないキーを渡す」場合のみ warning とした。検査B の error は「エージェント定義不在」
  「name フロントマター不一致」の高信頼2種に限定。検査C はドメイン例示除外リスト
  （`{DB}`・`{GPIO}` 等）で過検出を抑止。
- ハーネス自身の unittest（`test_refcheck.py` 15件・`test_smoke_full.py` 17件）＋異常系
  フィクスチャ（`tests/fixtures/badrepo`）で検査A/B/C/D の検出ロジックを固定。
- **確認項目5実施（2026-07-25）で発見・修正:** 共通確認項目「`openpyxl` 不在環境でも skip 扱いで
  `make test` が緑になる」を検証したところ、`test_crs_md2excel.py`・`test_excel_dump.py` が
  `openpyxl` を無条件 import しており、不在時に import エラーで `make test` が**赤になる**不具合を
  発見。両ファイルに `try/except ImportError` ＋ `@unittest.skipIf(openpyxl is None, ...)` ガードを
  追加して修正し、openpyxl 有無どちらでも `make test` が緑（不在時は `skipped=2`）になることを
  シャドウモジュールで実機確認済み。

**L4〜L5（LLM 層・2026-07-26 有効化済み／軽量 advisory）:**
- `smoke_full.py`（予算ガード `BudgetTracker`・構造性質抽出・ゴールデン照合・`--phase` 解決・
  config ロードの純ロジック）と `smoke_config.md`（確定値）を実装。純ロジックは unittest 済み（0トークン）。
- **L4〜L5 は子プラン `PLAN-20260726-smoke-full-runner-enablement` の A〜D で有効化完了（2026-07-26）。**
  実 LLM 起動経路（`_invoke_phase`＝実コマンド名・CR引数・`--dangerously-skip-permissions`・母体 `--add-dir`）、
  工程別入口シード（`seeds/phaseNN-single/`＝**人手オーサリング**。自動ハーベストは XDDP の人間参加型ゲートと
  衝突するため）、ゴールデン（`golden/phase02〜11-single.json` の**9件**）、`SMOKE_TOKEN_BUDGET`=30（C 実測確定）
  を確定。**モデルは Sonnet 単一の advisory 運用**（厳密な偽失敗率 N 回校正はコスト＋サブスクのセッション上限で
  行わず）。`close` は成果物 glob が CR 全体で実出力を見ないため advisory 対象外（手動検証＝exit 8）。
  `make smoke-full PHASE=NN`（NN∈02〜11）が実走可能。認証は隔離 HOME で
  `CLAUDE_CODE_OAUTH_TOKEN`／`ANTHROPIC_API_KEY`（未設定は exit 5）、起動失敗（セッション上限等）は exit 9。
- **オーケストレーションループ（隔離ステージング→工程起動→予算ガード→構造アサート→後片付け）は
  子プラン `PLAN-20260726-smoke-full-runner-enablement` で実装済み**（0トークン・モック unittest 済み。
  設計は本プラン Section 3.2「実行モデル」）。旧「校正完了後に有効化（return 4）」ゲートは撤去し、
  実効予算ゲート（`SMOKE_TOKEN_BUDGET`／`SMOKE_CALIBRATE_BUDGET`／`--budget` のいずれか>0 を要求。
  exit 6）＋ゴールデン未確定 assert の停止（exit 8）へ置換した。残るシード・ゴールデン・工程別モデル・
  `SMOKE_TOKEN_BUDGET` の確定は同子プランの B/C/D で実施する。
- **前提スパイク（3.5 step 0）を2026-07-25に実施（総コスト約$0.19）。** ①②③は想定どおり確認。
  ④で `_invoke_phase` の隔離HOME方式（`env={"HOME": 一時dir}`）が**認証を引き継げず失敗する**
  ことを発見（詳細は3.5 step 0実施結果・確認項目参照）。frontmatter `model:` 注入自体はプロジェクト
  スコープ配置で有効性を確認済み。**校正ラン本体（1.以降）に進む前に、認証伝搬の是正
  （API キー認証の採用 or 認証ファイルの選択的引き継ぎ or プロジェクトスコープ配置への設計変更）
  を別途プラン化する必要がある。**

ステータス（旧）: **承認済み**（L1〜L3 実装着手）

---

## 1. 背景・目的

`docs/xddp-ai-devtool-analysis-2026-07.md` の第2優先提案 **P2「ツール自体のテストハーネス（参照整合リント＋ゴールデンスモーク）」**（同レポート「### P2」節、`docs/...analysis...:214-217`）に対応する。

同レポートの指摘（W2 系・`docs/...analysis...:129-131`）:

- `test-fixtures/` と手動チェックリスト（`docs/xddp-tool-verification-checklist.md`）はあるが、**CI・自動スモーク・ゴールデンテストが存在しない**。
- 自然言語プログラム（スキル・エージェント定義）はコンパイラも型検査もないため、**参照整合性**（`apply` 対象見出しの存在・エージェント引数契約・テンプレートプレースホルダー）は唯一機械検証が容易な部分であり、数十行のスクリプトで静的リントできる。

P1（PLAN-20260714）で決定的処理が Python スクリプト群（`xddp_progress.py`・`xddp_gate_snapshot.py`・`specout_bfs.py`・`specout_verify_counts.py`・`chd_sp_coverage.py`・`artifact_lint.py`）へ移設され、各スクリプトには `scripts/tests/test_*.py`（unittest）が同梱された。本プランはその布石（P1 非対象節「本プランの各スクリプトには unittest を同梱し、P2 の布石とする」）を回収し、**リポジトリ全体を一括検証する開発時ハーネス**を新設する。

### 本プランが対象とする守備レイヤー（L1〜L5 / コスト2グループ）

品質確保を「守る対象レイヤー」で L1〜L5 の**5層**に分解し、それを**コストの異なる2グループ**で守る（この「2グループ構成」が本プランの骨格）。L1〜L3 は 0 トークン（既定の `make test`）、L4〜L5 のみ LLM を使う予算ガード付き別ターゲット（`make smoke-full`）に隔離する。

| 層 | 守る対象 | 手段 | LLM トークン | 入口 |
|---|---|---|---|---|
| L1 静的参照整合 | `apply` 見出し・`subagent_type`・プレースホルダー | refcheck（純 Python） | **0** | `make test` |
| L2 スクリプト単体正しさ | 各 `.py` のロジック | 既存 `scripts/tests/`（P1 導入済） | **0** | `make test` |
| L3 スクリプト↔スキル結線 | スキルが正しいサブコマンド／フラグで呼ぶか | refcheck 拡張（純 Python） | **0** | `make test` |
| L4 スキル制御フロー挙動 | どの分岐でどの手順が走るか | full-run スモーク（フェーズ単位・LLM） | **予算上限内** | `make smoke-full` |
| L5 成果物の意味的健全性 | 成果物が構造的に妥当に生成されるか | full-run スモーク（同上・構造アサート） | **予算上限内** | `make smoke-full` |

- L1〜L3（`make test`）は git pre-commit で常用する **0 トークン・数秒**の防御線。
- L4〜L5（`make smoke-full`）は **既定でフェーズ単位**（変更した1工程のみ LLM 起動）。全11工程通しは `make smoke-full-all` として稀に実行。
- 既存の分散 unittest（`ClaudeCode/.claude/skills/**/scripts/tests/`）と L1・L3 を **単一エントリポイント（`make test`）** から一括実行する。
- **段階導入:** L1〜L3（0 トークン・全前提が検証済み・低リスク）と L4〜L5（LLM・3.5 step 0 の未検証 API 前提に依存・高コスト）はリスク／コスト特性が異なる。本プランは単一プランとして管理するが、**承認・導入は 2 グループ単位で段階的に行える** — L1〜L3 を先行して承認・常用開始し、L4〜L5 は校正ラン（3.5）完了後に有効化してよい（確実性の高い静的リント層の価値を早期回収する）。

### 目標

| 指標 | 現状 | 目標 |
|---|---|---|
| ツール修正時の参照切れ検出（L1） | 手動チェックリスト＋人の目視 | `refcheck` が機械検出（`apply`/agent/placeholder） |
| スクリプト↔スキル結線の検出（L3） | 検出手段なし | `refcheck` がサブコマンド・フラグ不整合を機械検出 |
| 帳簿スクリプトの回帰検出（L2） | 各 `scripts/tests/` を個別に手動実行 | 単一コマンドで全 unittest を実行 |
| スキル挙動・成果物健全性（L4/L5） | 手動 LLM 検証のみ | フェーズ単位 full-run スモークで自動検証 |
| **`make test` の LLM トークン消費** | （存在しない） | **0 トークン**（L1〜L3） |
| **`make smoke-full` のトークン消費** | （存在しない） | **予算上限で構造的にキャップ**（校正ランで実測 → 上限確定） |
| L1〜L3 の実行時間 | — | 数秒（git pre-commit 実用圏） |
| 実行の入口 | 個別 `python3 -m unittest discover` | `make test`/`make lint`/`make smoke-full[-all]` |

### トークン戦略（本プランの中核）

レポート P2 のゴールデンスモークは「主要スキルを流し（run major skills）」と記す。これを額面どおり全パイプラインで LLM 実行すると1回で数十万〜数百万トークンに達し、5時間割り当て枠を圧迫する。ユーザー要件「L4/L5 も自動化するが、リーズナブルなトークンで・5時間枠を溶かさない」を満たすため、以下を設計原則とする。

- **既定の `make test` は 0 トークン（L1〜L3）。** LLM を使う検証は `make smoke-full` に隔離し、pre-commit には含めない。
- **フェーズ単位実行を既定**とする。`scratch-workspace-min` に各工程の中間状態（progress.md・前工程までの成果物、および前工程が状態ファイルを生成する場合は `bfs-state.json` 等）を**事前シード**し、`make smoke-full PHASE=NN` で**変更した1工程だけ**を起動する。全通しは `smoke-full-all`（稀）。
- **ハード・トークン予算ガード（必須）:** full-run は各工程を `claude -p --output-format json` のヘッドレスで起動し、返却 `usage`/`total_cost_usd` を積算。累積が設定上限を超えたら**即中断・赤で報告**。「気づいたら枠を消費」を構造的に排除する。
- **コスト削減レバー:** ①サブエージェント実行モデル（既定 **Sonnet**。工程により Haiku 可 — 下記モデル方針。`smoke_config.md`〔ハーネスレベル〕が保持し、適用機構は 3.2「サブエージェントのモデル適用機構」参照）②`REVIEW_MAX_ROUNDS=1`（レビューループがトークン倍増の主因。スキルが読むシードの `xddp.config.md` で設定）③極小フィクスチャ（UR1本・SP1本・母体3ファイル）④アサートは**構造性質のみ**（必須セクション・フロントマター・TM 整合・progress の ✅ 到達）で意味の良し悪しは判定しない。
- **モデル方針（品質確保＝シグナル信頼性の下限）:** スモークの検証対象は「ツール」であり、成立条件は「ツールが正しければ緑・壊れていれば赤」。弱いモデルは、XDDP スキルの長大・多段な指示を取りこぼして**ツールが正しくても構造アサートに落ちる＝偽の赤（flaky fail）**を起こしやすく、これはシグナルを"オオカミ少年"化させて品質確保を無効化する最悪の失敗様式。したがってモデルは憶測で固定せず、校正ラン（3.5）で**既知の正しいツリーに対する工程×モデルの偽失敗率**を実測し、**偽失敗率がほぼ0になる最安モデルを工程ごとに採用**する（例: 単純工程は Haiku、specout BFS・TM生成・SPカバレッジ等の複雑工程は Sonnet のハイブリッド）。実測前の暫定既定は安全側の Sonnet とする。
- **予算上限は推測せず校正ランで実測して確定する**（3.5 参照。ユーザー CLAUDE.md「推測ではなく計測に基づいて最適化」に準拠）。
- ゴールデン期待値は**構造性質**（見出し集合・ID 集合・件数・状態値）で表現し、LLM 出力依存の散文は byte 一致で固定しない。フィクスチャ肥大（＝人が読むトークン）も抑える。

### 非対象（スコープ外）

- **CI サービス（GitHub Actions 等）の構築**。本リポジトリには `.github/` が存在せず、レポート P2 も「git hooks か手動の `make test` でよい」とする。本プランは `make test`/`make smoke-full` と任意導入の git pre-commit フック雛形の提供に留め、特定 CI サービスへの結線はしない。
- **full-run スモークの pre-commit 常用**。LLM を使う L4/L5 は明示コマンドでのオンデマンド実行とし、自動フックに載せない（トークン枠保護）。
- **既存スキル/エージェント定義の意味的リファクタリング**。refcheck が既存の参照切れを検出した場合の**修正**は、検出（本プランの成果物）とは切り離し、検出結果を見てから別途対応する（本プランは「検出器の新設」が目的。既存違反の是正は確認項目で洗い出すが、修正自体は最小限に留め、大規模なものは別プラン化する）。
- **ネイティブ Windows（cmd/PowerShell 単体）対応**。P1 と同じく WSL / Git Bash（POSIX 互換シェル）を前提とする。

---

## 2. 変更対象ファイル

### 配置方針

ハーネスは**ツール自身を検証する開発時メタツール**であり、`setup.sh` によるデプロイ対象（`~/.claude/`）に含めてはならない。`docs/adr/`・`plans/`・`test-fixtures/` と同様、`ClaudeCode/.claude/` の**外**（リポジトリルート直下 `tools/harness/`）に置く。`setup.sh` のコピー処理は `ClaudeCode/.claude/` 配下のみを走査するため、デプロイ側の変更は不要。

### 新規（ハーネス本体）

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `tools/harness/refcheck.py` | 追加 | 参照整合リント（L1・L3、トークン0）。①`apply "## X"` 参照先見出しの存在検証 ②`subagent_type=` とエージェント定義・引数契約照合 ③テンプレートプレースホルダー整合 ④**スキルのスクリプト呼び出し行がサブコマンド・フラグに解決するか**（L3）。JSON＋人可読サマリ出力、違反で exit 非0 |
| `tools/harness/run_all.py` | 追加 | 集約ランナー（`make test` の実体）。①`ClaudeCode/.claude/skills/**/scripts/tests/` と `tools/harness/tests/` の全 unittest discover ②`refcheck.py` を実行。いずれか失敗で非0。**LLM 不使用（トークン0）** |
| `tools/harness/smoke_full.py` | 追加 | L4/L5 full-run スモーク（LLM 使用・予算ガード付き）。事前シード済みフィクスチャに対し `claude -p --output-format json` で工程を起動し、`usage` を積算して上限超過で中断。生成成果物の構造性質を `test-fixtures/golden/` と照合。`--phase NN`（既定・単一工程）/`--all`（全通し）/`--calibrate`（校正）/`--update-golden` を持つ |
| `tools/harness/smoke_config.md` | 追加 | full-run 専用の**ハーネスレベル** config（**工程別実行モデル**・`SMOKE_TOKEN_BUDGET`・工程別シード対応表。`smoke_full.py` が読む）。校正ラン結果（工程別モデル・上限）を反映して確定。`REVIEW_MAX_ROUNDS=1`（スキルが読む設定）は本ファイルには持たせず、各シードの `xddp.config.md` で担保する（役割分担は 3.2 参照） |
| `tools/harness/tests/test_refcheck.py` | 追加 | refcheck 自体の unittest（正例・違反例フィクスチャで検査A〜D の検出ロジックを検証） |
| `tools/harness/tests/test_smoke_full.py` | 追加 | smoke_full の**純ロジック**（構造性質抽出・予算積算・上限判定）の unittest。LLM は起動せずモック応答で検証（トークン0） |
| `tools/harness/tests/fixtures/` | 追加 | refcheck 用の小さな合成スキル/エージェント（参照切れ・引数不一致・未置換プレースホルダー・不正フラグを含む異常系サンプル） |
| `tools/harness/pre-commit.sample` | 追加 | `make test`（0トークン層のみ）を回す git フック雛形。手動導入。full-run は含めない |
| `Makefile` | 追加 | `make test`（=run_all・0トークン）/ `make lint`（=refcheck）/ `make unit`（unittest のみ）/ `make smoke-full PHASE=NN`（単一工程）/ `make smoke-full-all`（全通し）/ `make smoke-calibrate`（校正） |
| `test-fixtures/golden/` | 追加 | full-run スモークの構造性質ゴールデン（JSON。見出し集合・ID 集合・件数・状態値。散文は固定しない） |

### 修正（フィクスチャ・ドキュメント）

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `test-fixtures/scratch-workspace-min/seeds/`（工程別シード・新設サブツリー） | 修正（追加） | full-run スモークをフェーズ単位で起動するため、各工程の**入口状態**（前工程までの成果物・progress.md、および前工程が状態ファイルを生成する場合は `bfs-state.json` 等。工程04入口のように specout 未実行で状態ファイルが未生成の工程では含まれない）を事前シードとして格納。配置レイアウト・`--phase` 解決規則・規模見積り・既存 `multi/CR-2026-960`・`single/CR-2026-961`（フィードバック検証用。据え置き）との関係は 3.2「工程別シードの配置」で定義する。シード自体も校正ランの生成物から起こす（人が最小化して確定） |
| `test-fixtures/scratch-workspace-min/README.md` | 修正 | スモークの入力フィクスチャ・工程別シードの用途・再生成手順を追記 |
| `test-fixtures/README.md` | 修正 | `golden/` とシードの追加を一覧へ追記 |
| `docs/xddp-tool-verification-checklist.md` | 修正 | 各項目に「機械検証（`make test`＝L1〜L3）」「full-run 自動（`make smoke-full`＝L4/L5）」「手動 LLM 検証が必要」のタグを付し、自動化済み項目を人手手順から外す |
| `README.md` | 修正 | 「開発・テスト」節に `make test`（0トークン層）/ `make smoke-full`（LLM・予算ガード）/ refcheck の説明と実行要件（python3・GNU make・`claude` CLI）を追記 |
| `CLAUDE.md` | 修正 | ファイル構成表に `tools/harness/` を追記。「開発ルール」に「`ClaudeCode/.claude/` を変更したら最低限 `make test`（0トークン）を実行し緑を確認。挙動に関わる変更時は該当工程を `make smoke-full PHASE=NN` で検証」を追記 |

### 変更不要（確認済み）

- `ClaudeCode/setup.sh`: コピー処理は `ClaudeCode/.claude/` 配下のみ走査。`tools/harness/` はデプロイ対象外のため変更不要。
- P1 で追加された各 `scripts/*.py` 本体: 本プランは既存スクリプトを**呼び出す**のみで改変しない。

---

## 3. 変更内容

### 共通設計方針（ハーネス全体）

1. **Python 3 標準ライブラリのみ**（P1 の共通方針と同じ。外部依存を持たせない。`openpyxl` 依存の `crs_md2excel.py` はスモークの必須経路から外し、`openpyxl` 不在時はスキップ扱いにする）。
2. **入出力契約**: 各チェッカーは `--json` で機械可読結果（`{"ok": bool, "violations": [...]}`）を stdout に、既定では人可読サマリを出力。違反時 exit code 非0。
3. **LLM 使用は smoke_full のみ**: refcheck・run_all（＝`make test`）は `claude`・スキル・サブエージェントを一切起動しない（トークン0）。LLM を使うのは `smoke_full.py` だけで、必ず予算ガード配下で動く。
4. **クロスプラットフォーム**: ファイル I/O は `encoding="utf-8"`、パス操作は `pathlib.Path`。P1 スクリプト呼び出しは `PY=$(command -v python3 || command -v python)` 相当をハーネス内でも解決（`sys.executable` を利用）。
5. **検証対象は `ClaudeCode/.claude/` のソース**（`~/.claude/` のデプロイ済みコピーではなく、リポジトリ内の編集元）。ただし full-run スモークは実行時にスキルを `~/.claude/` から読むため、**隔離した一時 HOME へ `setup.sh` でデプロイしてから**起動し、実利用者の `~/.claude/` を汚染しない（3.4 参照）。リポジトリルートを基準にパス解決する。

---

### 3.1. `refcheck.py`（参照整合リント）

`ClaudeCode/.claude/skills/**/*.md` と `ClaudeCode/.claude/agents/*.md` を走査し、以下4種の参照整合を機械検証する（すべて純 Python・トークン0）。実測（2026-07-25 時点）で `apply "## X"` は 25 ファイル・175 箇所、`subagent_type=` は 16 種のエージェント、スクリプト呼び出しは `script.py subcommand --flag` 定型で 6 スクリプト・約28箇所。

#### 検査A: `apply "## X"` 参照先見出しの存在

`apply` は原則として同一行の `` Read `<file>` `` とセットで現れる（例: `` Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with ... ``）。

- 各 `apply "## HEADING"` について、直近に指定された Read 対象ファイル（`~/.claude/...` を `ClaudeCode/.claude/...` に読み替え）に見出し `## HEADING` が実在するか検証する。
- Read 対象がその行に無く自ファイル内の見出しを指す場合は、同一ファイル内に `## HEADING` があるか検証する。
- 見出しは Markdown の `^##+ ` 行から抽出。末尾の補足（`（up to REVIEW_MAX_ROUNDS.CRS rounds）` 等の可変サフィックス）を許容するため、**前方一致でなく「見出しテキストの正規化後一致」**を採る（正規化ルールは実装時に既存 apply 実測値から確定し、`test_refcheck.py` で固定する）。
- 違反例: `apply "## Progress Updat"`（タイポ）、リネームされた見出しへの旧参照。

#### 検査B: `subagent_type=` とエージェント定義・引数契約の照合

- 各 `subagent_type=xddp-XXX` について `ClaudeCode/.claude/agents/xddp-XXX.md` が実在するか検証（frontmatter の `name:` とファイル名の一致も確認）。
- **引数契約照合（best-effort）**: 呼び出し側の `subagent_type=... and pass:` 直後のフェンスブロック（`NAME: value` 行）で渡すキー集合と、エージェント定義の `### Inputs (provided by the caller)` 節が宣言する必須キー集合を突き合わせる。
  - エージェントが**必須**と宣言するキーが呼び出し側で渡されていない → 違反。
  - 呼び出し側が渡すキーがエージェント定義に**存在しない**（誤記・廃止キー）→ 違反。
  - **条件付きキー**（呼び出し側の `（... の場合のみ追加）` プレフィックス付き行、エージェント側の `### Optional Input` / `(optional)` 宣言）は「任意」として欠落を許容する。
  - パース不能な非定型記法は「警告（warning）」に留め、exit code を汚さない（過検出で運用が破綻しないよう、確実な誤りのみ error にする）。契約書式の網羅性は `test_refcheck.py` の異常系フィクスチャで担保する。
  - **カバレッジは部分的（best-effort であることの明示）:** 突き合わせ対象の `### Inputs (provided by the caller)` 見出しは実測（2026-07-25）で **16 エージェント中 13** にのみ存在し、残り3（`xddp-chd-sync-agent`・`xddp-design-sync-agent`・`xddp-reviewer`）は非定型のため warning 降格となる。検査Bは「宣言が定型な13エージェントの契約 error 検出」を保証範囲とし、残り3は warning 扱いであることを設計として明記する（全数の厳密照合は目標にしない）。

#### 検査C: テンプレートプレースホルダーの整合

- テンプレート（`ClaudeCode/.claude/skills/**/templates/*.md`）中の `{PLACEHOLDER}`（`^\{[A-Z][A-Z0-9_]*\}$` 形の独立トークン）を抽出。
- テンプレート**内で自明に例示目的のもの**（`{DB}`・`{GPIO}` 等のドメイン例示）と、**スキルが実行時に置換すべき制御プレースホルダー**を区別する必要がある。両者を機械のみで判別するのは困難なため、本検査は次の2点に限定する（過検出回避）:
  - (C1) スキル本文が「置換する」と明記して渡すプレースホルダー名の集合と、対応テンプレートが実際に持つプレースホルダー集合の**双方向差分**（スキルは置換予定だがテンプレートに無い＝デッドキー／テンプレートにあるがどのスキルも触れない＝置換漏れ候補）。
  - (C2) 生成後の成果物に `{[A-Z_]+}` 形の未置換トークンが残っていないかの検査は、full-run スモーク（3.2）の構造アサートで実施する（実際に生成した成果物に対して行う方が確実なため。refcheck では静的な C1 のみ）。
- C1 の対象プレースホルダー一覧・例示除外リストは実装時にテンプレート実測から確定し、`test_refcheck.py` に固定する。判定に迷うものは warning とする。

#### 検査D: スクリプト↔スキル結線（L3）

スキルが決定的スクリプトを呼ぶ Bash 行（例: `` xddp_progress.py update --cr-path {CR_PATH} --step {STEP_NUM} ... ``）を静的に解析し、呼び出しが**実在するサブコマンド・実在するフラグに解決するか**を検証する。P1 で結線先スクリプトはすべて argparse 定義を持つため機械照合できる（`excel_dump.py`・`crs_md2excel.py` は argparse 非使用のため対象外＝スキップ）。

- スキル本文から `` <script>.py <subcommand> [--flag ...] `` 形の呼び出し行を抽出。
- 対象スクリプトを **`--help` 相当のイントロスペクション**（`argparse` のサブパーサ・オプション一覧を取得する薄いヘルパ、または対象スクリプトを `import` してパーサ定義を読む）で解析し、宣言済みサブコマンド集合・各サブコマンドのフラグ集合を得る。
  - 呼び出しサブコマンドが未定義 → 違反（例: `specout_bfs.py commit-wav`）。
  - 呼び出しフラグが当該サブコマンドに未定義 → 違反（例: `--pathh`・廃止フラグ）。
  - 必須フラグの欠落は、可変展開（`[--artifact-link ...]` の任意表記や複数行継続 `\`）を伴うため **warning に留める**（過検出回避。確実な「未定義サブコマンド／未定義フラグ」のみ error）。
- 抽出パターン（バッククォート内・複数行 `\` 継続・`PY=$(...) && "$PY" script ...` 展開）の網羅性は `test_refcheck.py` の異常系フィクスチャで固定する。
- **イントロスペクション方式の前提:** `--help` サブプロセス方式（対象スクリプトを別プロセスで起動しヘルプ出力を解析）と `import` 方式（パーサ定義を直接読む）の2案があるが、`import` 方式は対象スクリプトがパーサを `main()` 内でのみ構築する場合に露出しないため成立しない。P1 の6スクリプトのパーサ構築形態を実装時に確認し、`main()` 内構築のものは `--help` サブプロセス方式を採る（または対象スクリプト側にパーサファクトリを露出させることを前提とする旨を注記する）。既定は移植性の高い `--help` サブプロセス方式とする。

**理由（検査D）:** L3 は「自然言語プログラムのコンパイラ不在」の中核で、スキルがスクリプトを誤サブコマンド／誤フラグで呼ぶ結線バグは現状どの層でも検出できない。full-run スモークを回さずとも（＝0トークンで）この結線バグの大半を静的に潰せるため、費用対効果が高い。

**理由（refcheck 全体）:** 自然言語プログラムで唯一機械検証可能な参照整合を、修正のたびに人が目視する現状を機械化する。特に検査A（`apply` 175 箇所）は見出しリネーム時の切れを高頻度で作り込みやすく、検査D（結線）と合わせて 0 トークンで防げる事故の範囲を最大化する。

---

### 3.2. `smoke_full.py`（L4/L5 full-run スモーク・予算ガード付き）

スキルのオーケストレーション（L4）と成果物の構造的健全性（L5）を、**実際に LLM でスキルを起動して**検証する。トークンは予算ガードで構造的にキャップする。

#### 実行モデル

1. **隔離環境の準備**: 一時ディレクトリ（scratchpad）に `HOME` を切り、`ClaudeCode/setup.sh` でスキルをそこへデプロイ（実利用者の `~/.claude/` を汚さない）。`test-fixtures/scratch-workspace-min` の該当**工程シード**を作業コピーする（single 版シードは参照母体 `multi/svc-a`・`svc-b` を相対レイアウトを保って同伴コピーする — 3.2「隔離コピー時の母体解決規則」参照）。**認証:** 隔離 HOME では OAuth/セッション認証を引き継げないため非対話認証用の環境変数を用いる。`CLAUDE_CODE_OAUTH_TOKEN`（`claude setup-token` で発行・Pro/Max契約消費で追加課金なし）を優先し、未設定時は `ANTHROPIC_API_KEY`（API従量課金）にフォールバックする（PLAN-20260725-smoke-full-api-key-auth で是正済み。3.5 step 0 実測で HOME 差し替えのみでは "Not logged in" になることを確認）。
2. **工程起動**: `claude -p --output-format json`（ヘッドレス）で対象工程のスラッシュコマンド相当を1回起動する。既定は `--phase NN`（単一工程）。`--all` は init→close を順に通す。
   - トークン削減レバーの適用経路（**設定の役割分担**）: **工程別実行モデル**（既定 Sonnet）は `smoke_config.md`（ハーネスレベル。`smoke_full.py` が読み `--model`／frontmatter 注入で適用）で、`REVIEW_MAX_ROUNDS=1` は各シードの `xddp.config.md`（**スキルが実際に読む設定ファイル**）で適用する。`smoke_config.md` はスキルからは読まれないため、スキル挙動を変える設定（`REVIEW_MAX_ROUNDS` 等）は smoke_config.md に置かずシード側 `xddp.config.md` に置く。

##### サブエージェントのモデル適用機構

工程別モデル（Haiku/Sonnet）を、**母体のエージェント定義（`ClaudeCode/.claude/agents/*.md`）を一切改変せず**に適用する。現状どのエージェントにも `model:` フロントマターは無い（実測: `grep "^model:" agents/*.md` → 0 件）ため、以下の二段で適用する。

1. **ベースライン**: `claude -p --model {MODEL}` で主モデルを指定する。`model:` フロントマターを持たないサブエージェントは主モデルを継承するため、工程全体を単一モデルで回す場合はこれだけで足りる。
2. **エージェント別上書き（必要時）**: `smoke_config.md` の工程別モデル表がエージェント単位でモデルを分ける場合、`smoke_full.py` は **隔離 HOME にデプロイされたコピー**（`{一時HOME}/.claude/agents/*.md`）にのみ `model:` フロントマターを注入する。母体リポジトリの `agents/*.md` は読み取りのみで書き換えない。したがって「本プランはスキル/エージェント定義を改変しない」（Section 2 配置方針・Section 4）と矛盾しない。
3. この機構が期待どおり効く（注入モデルで実行される・母体が汚れない）ことは校正ラン（3.5）と確認項目（Section 5）で検証する。`--model` 継承・frontmatter 注入いずれの API 挙動も未検証仮定を含むため、3.5 step 0 のスパイクで先に確認する。
3. **予算積算とガード**: 各起動の応答 JSON から `usage`（input/output/cache トークン）と `total_cost_usd` を取得し累積。**工程開始前に「残予算 < 想定単価」なら起動せず中断**、起動後に累積が上限超過でも**以降を中断**して赤報告。上限は `smoke_config.md` の `SMOKE_TOKEN_BUDGET`（校正で確定、3.5）。
4. **構造アサート**: 生成成果物を `test-fixtures/golden/` の**構造性質**（下表）と照合。散文の内容一致は見ない。
5. **後片付け**: 一時 HOME・作業コピーを破棄。

#### 工程別に検証する構造性質（例。全11工程分を実装時に確定）

| 工程 | 主な起動スキル | アサートする構造性質（L5） | 検証する挙動（L4） |
|---|---|---|---|
| 02 | xddp.02.analysis | ANA に必須セクション（要求レベル分類・ギャップ等）が存在／UR 行数 ≥ 入力 UR 数 | analyst 起動 → レビューループ1回 → progress step2=✅ |
| 03 | xddp.03.req | CRS に SP-ID が採番され Section 4 に登録／Excel 生成（openpyxl 有時） | spec-writer 起動 → progress step3=✅ |
| 04 | xddp.04.specout | discovery-log の件数一致・`bfs-state.json` の state=complete／CRS 更新反映 | specout(discovery→document) → BFS 帳簿スクリプト結線が実起動 |
| 05 | xddp.05.arch | DSN に方式比較セクション存在／arch 成果物にコード片が無い | architect 起動 → CRS フィードバック |
| 06 | xddp.06.design | CHD の TM で全 SP-ID がカバー（`chd_sp_coverage` が missing 空）／Mermaid 構文健全 | designer 起動 → SPカバレッジ自動検証が実起動 |
| 07 | xddp.07.code | 変更が CHD 範囲内／静的検証レポート生成 | coder→verifier 連携 |
| 09 | xddp.09.test | TSP に CHD 確認項目由来のテストケース存在 | test-writer 起動 |
| 10 | xddp.10.test-run | テスト結果記録・TM 更新／カバレッジ判定分岐 | test-runner 起動 |
| 11 | xddp.11.specs | latest-specs 生成・フロントマター必須キー充足（`artifact_lint` 合格）／`{[A-Z_]+}` 未置換トークンが無い | specs-uc/mod 連携・ゲート |
| close | xddp.close | lessons-learned 更新・成果物昇格 | promote 連携 |

- **工程01（init）は本表に載せず `--all` 専用**とする。init はワークスペース自体（`xddp.config.md`・`project-rulebook` 群）を生成する工程で「前工程シード」から起こせないため、フェーズ単位（`--phase 01`）の対象外。`--all` 経路でのみ構造性質（config・rulebook 群が生成され必須キーを充足）を確認する。この意図的除外を明示して網羅性判断を容易にする。
- **フェーズ単位が既定**のため、各工程シードは「前工程まで完了した最小状態」を持つ。工程 NN のスモークは工程 NN のみ課金される。
- IS_MULTI の挙動差は、コストの高い全通しではなく **04/11 など cross 生成が絡む工程のシードを multi 版で用意**して局所的に確認する（全工程を multi で通さない）。
- `crs_md2excel.py`（`openpyxl` 依存）は不在時 skip。

#### 工程別シードの配置（フィクスチャレイアウト）

**配置レイアウト**（既存の `multi/CR-2026-960`・`single/CR-2026-961` は据え置き、`seeds/` を**新設サブツリー**として追加）:

```
test-fixtures/scratch-workspace-min/
├── multi/    CR-2026-960/   … （既存・フィードバック検証用。据え置き）
├── single/   CR-2026-961/   … （既存・フィードバック検証用。据え置き）
└── seeds/                       ← 新設。工程別入口状態のスナップショット
    ├── phase02-single/          # 各ディレクトリが完結したワークスペースルート
    │   ├── xddp.config.md        #  （xddp.config.md + xddp/CR-.../ の入口状態一式）
    │   └── xddp/CR-2026-9SS/…    #  工程01完了・工程02未着手の状態
    ├── phase03-single/ … phase11-single/, phaseClose-single/
    └── phase04-multi/, phase11-multi/   # cross 生成が絡む工程のみ multi 版
```

**`--phase` からの解決規則:** `smoke_full.py --phase NN` は `seeds/phaseNN-single/`（既定）を一時ディレクトリへ複製して起動する。cross 検証時は `--multi` フラグで `seeds/phaseNN-multi/` を使う（multi 版が存在する工程＝04/11 のみ受理、他工程で `--multi` 指定はエラー）。`smoke_config.md` の工程別シード対応表に「工程→シードディレクトリ名」を明示し、解決を config 駆動にする。

**規模見積り:** single 版 = 工程02〜11＋close の約10状態、multi 版 = cross 絡みの2状態（04/11）で計**約12スナップショット**。各スナップショットは UR1本・SP1本の極小構成（既存 960/961 と同粒度）で、大半は前工程までの成果物 md（数百行規模）。

**母体ソースの参照（実測に基づく訂正）:** 母体ソースは `multi/svc-a/src/`・`multi/svc-b/src/`（`mod_a.py`・`mod_a2.py`・`mod_b.py` の3ファイル）に**のみ**存在する。既存 `single/CR-2026-961` は独自 `src/` を持たず、`single/xddp.config.md` の `REPOS: svc-a: ../multi/svc-a`（相対パス）で `multi/` 側の母体を参照している。したがって single 版シードも同様に **`multi/svc-a` を相対参照する config を持たせ、母体ソースを二重に持たない**（既存フィクスチャの設計を踏襲）。single の specout（工程04）は `multi/svc-a/src/mod_a2.py`（single 専用の対象ファイル）を参照する。フィクスチャ肥大を避けるため、シードは校正ランの生成物から起こし**人が最小化して確定**する（不要な散文・重複セクションを削る）。

**隔離コピー時の母体解決規則（`../multi` の temp 内解決・ステージ後レイアウトを正準とする）:** single 版シードの config が参照する `../multi/svc-a` は参照先母体がワークスペースルートの**外**にあるため、シード部分木をそのまま temp へ置くだけでは解決できない。ここで重要なのは、**シードの `REPOS:` 相対パスは「フィクスチャ上の格納位置（`seeds/phaseNN-single/`）」ではなく「ステージ後の temp レイアウト」を基準に書く**という点である（格納位置基準で `../multi` と書くと depth が合わず `seeds/multi/` を指してしまう。格納位置での解決可能性は要件としない）。`smoke_full.py` の隔離コピー（実行モデル step 1）は、ステージ先で以下の**固定レイアウト**を組み立てる:

```
{temp}/
├── ws/        ← seeds/phaseNN-single/ の中身を展開（＝ワークスペースルート。xddp.config.md を持つ）
└── multi/     ← multi/svc-a・multi/svc-b の src/ を同伴コピー（母体）
```

`ws/xddp.config.md` の `REPOS: svc-a: ../multi/svc-a` はこの `{temp}/ws/` を基準に `{temp}/multi/svc-a` へ解決する（既存 961 が `single/`（ルート）から `../multi/` を見るのと同じ depth=1 関係を、ステージ時に再現する）。母体はフィクスチャ上は単一ソースのまま（`multi/` にのみ実体）で実行時に temp へ複製されるだけなので「母体ソースを二重に持たない」方針と矛盾しない。したがって「各 `seeds/phaseNN-single/` は完結したワークスペースルート」という記述は**ステージ後に `{temp}/ws/` として展開したときにワークスペースルートとして完結する**ことを指し、参照母体は隔離コピー時に `{temp}/multi/` として同伴される。multi 版シード（`seeds/phaseNN-multi/`）は母体を内包する自己完結ワークスペースのため同伴コピーは不要。この解決が実際に効く（single specout が `mod_a2.py` へ到達する）ことは Section 5 の隔離完走確認で検証する。

#### ゴールデンの表現（保守コスト最小化）

- ゴールデンは**構造性質の JSON**（見出し集合・ID 集合・件数・状態値・lint 合否）とし、LLM 生成の散文は byte 固定しない（実行ごとに変わるため）。
- 日付・絶対パス・トークン数等の環境/実行依存フィールドは正規化してから照合。
- ゴールデン更新は `python3 tools/harness/smoke_full.py --phase NN --update-golden`（LLM を1回起動して構造性質を再収集。レビューで diff を人が確認）。

**理由:** L4/L5 はスキルを実起動しないと検証できない。フェーズ単位＋Sonnet＋`REVIEW_MAX_ROUNDS=1`＋極小フィクスチャ＋構造のみアサートでトークンを抑え、予算ガードで**上限を構造的に保証**することで「リーズナブルなトークン・5時間枠を溶かさない」を満たす。

---

### 3.3. `run_all.py` と `Makefile`（エントリポイント）

`run_all.py`（=`make test`、**0トークン**）は次を順に実行し、いずれか失敗で exit 非0・失敗内訳を要約表示する。**LLM は起動しない。**

1. **unit**: `ClaudeCode/.claude/skills/**/scripts/tests/` を横断して `unittest` discover（各スクリプト同梱テスト）＋ `tools/harness/tests/`。
2. **lint**: `refcheck.py`（検査A/B/C/D）。

**入出力契約（`run_all.py`）:** 引数 `--only {unit,lint}`（省略時は unit→lint の両方を実行）で片方のみを実行できる（`make unit` が使用）。`--json` で機械可読サマリ（`{"ok": bool, "unit": {...}, "lint": {...}}`）を stdout に出力。いずれかのステップ失敗で exit code 非0。

`Makefile`:

```make
.PHONY: test lint unit smoke-full smoke-full-all smoke-calibrate
test:            ; python3 tools/harness/run_all.py          # 0トークン（L1〜L3）
lint:            ; python3 tools/harness/refcheck.py
unit:            ; python3 tools/harness/run_all.py --only unit
smoke-full:      ; python3 tools/harness/smoke_full.py --phase $(PHASE)   # LLM・予算ガード
smoke-full-all:  ; python3 tools/harness/smoke_full.py --all
smoke-calibrate: ; python3 tools/harness/smoke_full.py --calibrate $(if $(PHASE),--phase $(PHASE)) $(if $(MODEL),--model $(MODEL))  # 工程/モデルを絞ったバッチ分割校正
```

（実インタプリタ解決は各スクリプト先頭で `command -v python3 || command -v python` 相当を行う。Makefile の `python3` は Git Bash 環境向けにコメントで代替を併記。`smoke-full*` は `claude` CLI を要求し、未導入時は明示エラーで停止。）

**`PHASE` の受理値:** `make smoke-full PHASE=NN` の `PHASE`（＝`smoke_full.py --phase`）は**数値工程ラベルと非数値ラベルの両方**を受け付ける。受理値は工程シードに対応する `02`・`03`・`04`・`05`・`06`・`07`・`09`・`10`・`11`・`close`（工程08はxddp.07に統合、工程01は `--all` 専用のため `--phase` 対象外＝3.2 参照）。未定義ラベル指定時は受理値一覧を表示して明示エラーで停止する。`smoke_config.md` の工程別シード対応表が正準の受理値一覧となる。`make smoke-calibrate` も同じ受理値の `PHASE=`（任意）と `MODEL=`（任意・`haiku`/`sonnet` 等）を受け、3.5 step 2 のバッチ分割校正（工程・モデルを絞った起動）を `make` 経由で実行できる（いずれも省略時は全工程・全モデルの校正）。

**任意導入の git フック雛形**（`tools/harness/pre-commit.sample`）は **`make test`（0トークン層）のみ**を回す。full-run は自動フックに載せない。

**理由:** 常用の防御線（L1〜L3）は 0 トークン・数秒で pre-commit 適合。LLM を使う L4/L5 は明示コマンドのオンデマンド実行に隔離し、トークン枠を保護する。

---

### 3.4. full-run スモークの隔離実行（トークン枠・環境汚染の保護）

- **隔離 HOME**: `HOME` を一時ディレクトリに差し替えて `setup.sh` デプロイ → 実利用者の `~/.claude/` を変更しない。認証は `CLAUDE_CODE_OAUTH_TOKEN`（優先・Pro/Max契約消費で追加課金なし）または `ANTHROPIC_API_KEY`（フォールバック）による非対話認証（PLAN-20260725-smoke-full-api-key-auth 参照）。
- **予算ガードの二重化**: ①`smoke_config.md` の `SMOKE_TOKEN_BUDGET`（累積上限）②工程数上限（`--all` の暴走防止）。いずれか到達で中断・赤報告。
- **失敗時の可観測性**: 中断時は「どの工程まで実行し累積いくら消費したか」を JSON で残す（次回校正の材料）。
- **`claude` 未導入・認証未了**: 検出して「full-run スモークは `claude` CLI が必要」と案内し停止（`make test` は影響を受けない）。

---

### 3.5. 校正ラン（トークン上限を推測せず実測で確定）

**実装の最初のステップ**として校正ランを行い、①工程別モデル ②`SMOKE_TOKEN_BUDGET` を実測から決める（推測で数値を置かない）。

0. **前提スパイク（校正の前・最小コストで load-bearing 仮定を検証）:** 予算ガード・モデル適用の全体が依存する未検証仮定を、1〜2回の最小起動で先に確認する。① `claude -p --output-format json` が対象スラッシュコマンド（工程スキル）を起動できるか ② 返却 JSON に `usage`（input/output/cache）と `total_cost_usd` が含まれるか ③ **サブエージェント消費が親の `usage` に積算されるか**（積算されない場合は予算ガードの積算方式を修正する必要がある）④ 3.2 のモデル適用機構（`--model` 継承・隔離HOMEへの `model:` 注入）が実際に効くか。いずれかが想定と異なれば、校正・予算ガード設計を先に是正してから 1. 以降へ進む。結果は 4. の記録に残す。

   **実施結果（2026-07-25・簡易スパイク。総コスト約 $0.19・3起動）:**
   - ①②confirmed: `claude -p --output-format json --model haiku "..."` は正常応答し、返却 JSON に `usage`（`input_tokens`/`output_tokens`/`cache_creation_input_tokens`/`cache_read_input_tokens`）と `total_cost_usd` が含まれる。**加えて未記載だった `modelUsage`（モデル名キーごとの内訳: inputTokens/outputTokens/costUSD 等）が返却される**ことを確認（3.の予算ガード実装で `total_cost_usd` を積算すれば十分だが、`modelUsage` は工程別モデル実測の裏付けに使える）。
   - ③confirmed: Task ツールでサブエージェントを1回起動させたところ、`num_turns`・`output_tokens`・`total_cost_usd` が単純呼び出し比で明確に増加。さらに④の検証（後述）で親と異なるモデルのサブエージェントを起動させたところ `modelUsage` に親・子それぞれのモデルキーが個別に現れ、`total_cost_usd` がその合算になることを確認 — **サブエージェント消費は単一の `claude -p` 応答の `usage`/`total_cost_usd` に積算される**ことが確定的に確認できた。
   - ④**部分的に想定と異なる（要是正）**: モデル適用機構そのもの（エージェント定義 frontmatter の `model:` 注入）は有効だが、**プランが前提とする「隔離 HOME（`env={"HOME": 一時dir}`）」経由では認証が通らない**ことを発見した。
     - 検証A（frontmatter注入の有効性）: プロジェクトスコープの `.claude/agents/spike-test-agent.md`（`model: haiku` frontmatter）を作業ディレクトリ直下に配置し、親を `--model sonnet` で起動 → Task ツールで `subagent_type=spike-test-agent` を呼び出すと、`modelUsage` に `claude-sonnet-5`（親）と `claude-haiku-4-5-20251001`（該当サブエージェント）の**2エントリが個別に**現れ、応答も該当サブエージェントの出力どおりだった。**frontmatter `model:` 注入によるサブエージェント別モデル上書き自体は機能する**ことを確認。
     - 検証B（隔離HOME・現行設計の再現）: `smoke_full.py:_invoke_phase`（`env = {"HOME": str(home)}`）と同じ形で `HOME` を一時ディレクトリに差し替えて起動すると、`"result":"Not logged in · Please run /login"` で失敗した（このマシンの認証情報は実 `HOME`（`~/.claude/`）配下にあり `ANTHROPIC_API_KEY` 環境変数も未設定のため、`HOME` を丸ごと差し替えると認証が失われる）。
     - **含意:** 3.2/3.4 の「一時ディレクトリに `HOME` を切り替えて `setup.sh` デプロイ」という設計は、**認証情報の引き継ぎ手段を追加しない限り実行時に必ず失敗する**。是正案（要検討・本スパイクでは選定しない）: (a) `ANTHROPIC_API_KEY` 等 API キー認証を harness の前提要件にする、(b) 実 `HOME` の認証関連ファイルを隔離 HOME へ選択的にコピー/シンボリックリンクする、(c) `HOME` を丸ごと差し替えず実 `HOME` を維持したまま**プロジェクトスコープの `.claude/skills`・`.claude/agents`**（一時ワークスペース直下）に検証対象スキルを配置する方式へ設計変更する（検証Aと同じ方式。認証情報に触れず済む）。**校正ラン（1.以降）に進む前に、この認証伝搬の是正を別途プラン化・実装する必要がある。**
1. **ゴールデンのブートストラップ（鶏卵回避の順序固定）:** 偽失敗率測定は「生成物 vs ゴールデン照合」で判定するため、測定前にゴールデンが必要になる。順序を **(a) 既知の正しいツリーに対し各工程を1回起動 → `--update-golden` で構造性質を収集 → 人が diff を確認してゴールデンを確定 → (b) 確定ゴールデンに対して偽失敗率を N 回測定** に固定する。(a) を飛ばして (b) を実行しない。
2. **偽失敗率の測定（モデル選定・標本設計）:** 確定ゴールデンに対し、各工程を Haiku と Sonnet で **N 回** `smoke_full.py --calibrate` 起動し、構造アサートの**偽失敗率**（正しいツリーなのに赤になった割合）とトークンを工程×モデルで記録。**N は「採用したい偽失敗率の上側信頼限界」から rule of three で決める**（推測の固定値を置かない）: 0 失敗が n 回続いたときの真の失敗率の 95% 上側信頼限界は約 `3/n`。既定は**上側 95% 限界 ≤ 15% を要求して N=20**（0/20 → 約15%）、cross 生成など重い工程や信頼性を特に要する工程は**上側 ≤ 10% を要求して N=30**（0/30 → 約10%）とする。**採用は「N 回すべて緑（0 失敗）」を必須**とし、1回でも偽失敗が出たモデルはその工程で不採用（0 許容）。旧記載の N=5 は 0/5 の上側限界が約45%と緩く、中核主張「シグナル信頼性の下限担保」を裏付けられないため採らない。
   - 校正自体のトークン（N × 工程数 × モデル数）は一度きりだが無視できないため、校正ラン全体も予算ガード配下（`--calibrate` にも `SMOKE_TOKEN_BUDGET` を適用）で回し、消費を 4. に記録する。
   - **校正総コストの概算と分割:** 起動回数は概算 N(20〜30) × 約10工程 × 2モデル ＝ **約400〜600 起動**に達し、これを一度に流すと保護対象の5時間枠を校正自体が食い潰しうる。したがって校正は**工程単位（またはモデル単位）でバッチ分割**して複数セッションに分けて実施し、各バッチ後に累積コストを 4. の記録へ追記して残枠を確認しながら進める（`--calibrate` は工程・モデルを絞って起動できるようにする）。まず単純工程1件を Haiku/Sonnet で試走して1起動あたり実コストを把握し、全体所要を見積もってからバッチ計画を確定する。
3. **工程別モデルの確定:** 上記基準（N 回 0 失敗）を満たす**最安モデル**を工程ごとに採用（単純工程は Haiku、複雑工程は Sonnet）。基準を満たすモデルが Sonnet でも得られない工程は「その工程は L4/L5 自動対象外＝手動検証」に落とす（信頼できない緑/赤を作らない）。
4. **予算上限の確定:** 採用モデルでの実測 `usage`/`total_cost_usd` を基に、工程別上限＝実測 × 安全係数（例 1.5）、全通し上限＝各工程上限の総和。
5. 記録（スパイク結果・偽失敗率表〔工程×モデル×N〕・トークン実測表・採用モデル・確定 N）を `plans/review/PLAN-20260725-p2-test-harness-review.md`（またはプラン付録）に残し、確定値を `smoke_config.md` に書き込む。
6. 以降 `smoke-full` はこの上限を超えないことがガードで保証され、各工程は校正で信頼性を確認したモデルで動く。
7. **スキル変更後の再校正（運用）:** 初回校正後にスキル挙動を変える変更を入れた場合、**該当工程の構造性質（見出し集合・ID 集合・件数・状態値）に影響する変更**を再校正のトリガーとする（コメント修正等の構造性質に影響しない変更では不要）。トリガー該当時は当該工程のみ `--update-golden` でゴールデンを再確定し（diff は人が確認）、採用モデルの偽失敗率が劣化していないかを当該工程のみ再測定する（全工程の一括再校正は不要）。継続コストは 2. の「1起動あたり実コスト × N」で見積もる。

**理由:** 「Haiku で品質確保できるか」は憶測で決めず、シグナル信頼性の下限（偽失敗率）とトークンの両方を実測して工程ごとに最適化する。ユーザー要件「リーズナブルなトークン・5時間枠を溶かさない」と品質確保（信頼できるシグナル）を同時に、事実で担保する（CLAUDE.md「推測ではなく計測に基づいて最適化」）。

---

### 3.6. ドキュメント更新

既存ファイルへの追記は**見出し名アンカー＋挿入する実文**で確定する（行番号は使わない＝CLAUDE.md 行番号参照禁止に準拠。実装時に見出し直下へ挿入）。

#### README.md（アンカー: `### ツール自体（スキル・エージェント）を修正したときの動作確認` の直後に新規サブセクションを追加）

- **Before:** 「ツール自体を修正したときの動作確認」節は手動フィクスチャ手順のみを記載（`make` ターゲットの記載なし）。
- **After（挿入する実文の骨子）:** 新規サブセクション `#### 開発時テストハーネス（make）` を追加し、以下を記載する。
  - `make test`（L1〜L3・**0トークン**・数秒。git pre-commit 実用圏。`refcheck` ＋全 unittest）
  - `make lint` / `make unit`（片方のみ）
  - `make smoke-full PHASE=NN`（L4/L5・**LLM 使用・予算ガード付き**。触った1工程のみ起動）/ `make smoke-full-all`（稀）/ `make smoke-calibrate`
  - 実行要件: `python3`（標準ライブラリのみ）・GNU make・`smoke-full*` のみ `claude` CLI が必要
  - `tools/harness/pre-commit.sample` の導入方法（`make test` のみを回す。full-run は含めない）

#### CLAUDE.md（アンカー2箇所）

- **アンカー1: `## ファイル構成` テーブル**
  - **Before:** テーブルは `ClaudeCode/.claude/**`・`docs/`・`docs/adr/` 等を列挙（`tools/harness/` 行なし）。
  - **After:** 行を1つ追加 — `| tools/harness/ | ツール自身を検証する開発時メタツール（refcheck＝L1/L3 静的参照整合、run_all＝make test 実体、smoke_full＝L4/L5 full-run スモーク）。setup.sh のデプロイ対象（~/.claude/）には含めない |`
- **アンカー2: `## 開発ルール`（新規サブセクション `### ツール修正後のハーネス実行（必須）` を追加）**
  - **Before:** 「実装後の関連ドキュメント更新（必須）」等はあるが、ハーネス実行の義務付けはない。
  - **After（挿入する実文）:** 「`ClaudeCode/.claude/` 配下を変更したら最低限 `make test`（0トークン）を実行し緑を確認する。スキルの分岐・手順など**挙動に関わる変更**の場合は、該当工程を `make smoke-full PHASE=NN`（隔離HOME・予算ガード）で検証してからプランのステータスを『実装完了』にする。」

#### docs/xddp-tool-verification-checklist.md（アンカー: `## 2. 部分実行チェックリスト（変更箇所別）` の各項目）

- **Before:** 各項目が手動確認手順のみ（機械検証・自動化の区別なし）。
- **After:** 各項目に検証手段タグを付す — 「機械検証（`make test`＝L1〜L3）」「full-run 自動（`make smoke-full`＝L4/L5）」「手動 LLM 検証が必要」の3種のいずれか。`make test`/`make smoke-full` で自動化済みの項目は人手手順の常時実施リストから外し、「ハーネスが緑なら省略可」と明記する。

---

## 4. 影響範囲

- **影響するスキル・コマンド**: なし（本プランはスキル/エージェント定義を改変しない。refcheck は読み取り専用、full-run スモークは隔離 HOME で実行）。ただし refcheck が既存の参照切れ・結線バグを検出した場合、その是正は別途対応（非対象節参照）。
- **影響する工程**: なし（開発時ツールであり XDDP プロセス実行時には介在しない）。full-run スモークは XDDP 工程を「テスト対象」として起動するが、本番ワークスペースには触れない。
- **デプロイ（`setup.sh`）**: 影響なし（`tools/harness/` はデプロイ対象外）。full-run スモークは `setup.sh` を隔離 HOME に対して**利用**するのみ。
- **トークン/コスト**: `make test` は 0 トークン。`make smoke-full` のみ LLM を消費するが、予算ガードと校正済み上限（3.5）で構造的にキャップされ、既定のフェーズ単位実行で「触った1工程分」に限定される。
- **後方互換性**: 考慮不要（CLAUDE.md 後方互換性ポリシー）。ハーネスは新規追加であり既存フローを変えない。
- **ドメイン中立性**: ハーネスは言語・ドメイン非依存の構造検証のみを行う。プレースホルダー例示（`{GPIO}`・`{DB}` 等）を error 判定しない設計（3.1 検査C）により、特定ドメインを前提としない。フィクスチャの母体コードもドメイン中立な最小合成コードとする。

---

## 5. 確認項目

**L1〜L3（0トークン層）**
- [x] `make test` が緑で通り、`make lint`・`make unit` 単体も動作する（いずれも LLM 非起動を確認）— **2026-07-26 実機確認。`make test` exit 0（全 unittest 6スイート ＋ refcheck errors=0/warnings=10）・約2.0秒。`make lint`・`make unit` 単独も exit 0。`refcheck.py`・`run_all.py` に `claude` 起動はなく（`subprocess` は unittest discover と 検査D の `--help` イントロスペクションのみ）LLM 非起動を確認**
- [x] `refcheck` を現行リポジトリに実行し、検出された既存違反を棚卸し（真の違反か過検出かを分類。過検出は正規化ルール/除外リストで解消、真の違反は別チケット化）— **errors=0・warnings=10。内訳は上部「実装状況」の棚卸し記載どおり（検査B: caller注入タスクキー3＋非定型契約6、検査C: `{SPECOUT_MAX_WAVE_DEPTH}` 1）で、いずれも真の違反ではないことを確認済み**
- [x] 異常系フィクスチャ（`tools/harness/tests/fixtures/`）で refcheck が期待どおり違反を検出する（検査A/B/C/D 各1件以上。特に検査D＝誤サブコマンド・誤フラグ）— **2026-07-26 実機確認。`fixtures/badrepo`（合成スキル/エージェント）に対し `test_refcheck.py` 15件が緑。検査A（欠落見出し）・B（エージェント不在／name不一致／未知キー）・C（未言及プレースホルダー警告／ドメイン例示除外）・D（未定義サブコマンド `test_undefined_subcommand_is_error`／未定義フラグ `test_undefined_flag_is_error`）を各1件以上検出**
- [x] `make test` の実行時間が数秒オーダー（git フック実用圏）に収まる — **2026-07-26 計測。`time make test` ＝ 約2.0秒（total）**

**L4/L5（full-run スモーク）**

> **【2026-07-26 有効化・子プラン `PLAN-20260726-smoke-full-runner-enablement` B〜D 完了】**
> 下記のうち: **モデル適用（428）** は Sonnet 単一 advisory 運用で確定（母体 agents 無改変・隔離コピーのみ）。
> **偽失敗率 N 回校正（429）** は $2/工程＋サブスクのセッション上限（1窓 ~6工程）により**実行不能と判明し
> 「軽量 advisory」へ再設計**（厳密 N 測定は行わず・`SMOKE_TOKEN_BUDGET`=30 を C 実測で確定）。
> **手動退避（430）** は `close`（成果物 glob が CR 全体で実出力を見ない）を advisory 対象外＝手動検証として実施。
> **ブートストラップ順序（431）** は seeds を**人手オーサリング**（自動ハーベストは人間参加型ゲートと衝突）→
> C（`--update-golden`）で goldens 02〜11 を確定。**隔離 HOME 完走・`~/.claude` 無改変（432）** は C 実走で確認
> （実利用者 HOME を差し替え・setup.sh は隔離 HOME のみ）。**残: 予算ガード end-to-end 実演（433）・スキル挙動
> 回帰検出（434）** は advisory 有効化後の任意フォロー。詳細・実測値は子プラン §9。
- [x] **前提スパイク（3.5 step 0）を校正の前に実施**し、`claude -p --output-format json` がスラッシュコマンドを起動できること・返却 JSON に `usage`／`total_cost_usd` が含まれること・**サブエージェント消費が親 usage に積算されること**を確認（想定と異なれば予算ガード設計を先に是正）— **2026-07-25 実施。①②③は確認どおり。④で「隔離HOME方式は認証が通らない」を発見（詳細は3.5 step 0 実施結果）。予算ガードの積算方式（`total_cost_usd` を単純合算）自体は想定どおりで是正不要。是正が要るのは HOME 隔離の認証伝搬のみ**
- [ ] **サブエージェントのモデル適用機構（3.2）が母体エージェント定義を改変せず効く**ことを確認（`--model` 継承／隔離HOMEへの `model:` 注入で意図したモデルが使われ、リポジトリの `agents/*.md` が変更されないこと）— frontmatter注入自体はプロジェクトスコープ配置で有効性を確認済み（3.5 step 0 検証A）。**隔離HOME経由での認証は `CLAUDE_CODE_OAUTH_TOKEN` 優先（`ANTHROPIC_API_KEY` フォールバック）採用で是正済み（PLAN-20260725-smoke-full-api-key-auth）**。うち **認証成立とデプロイ済み user-scope スキルのランタイム解決は 2026-07-26 実機確認済み**（隔離HOME+`CLAUDE_CODE_OAUTH_TOKEN` で `is_error=false`・`~/.claude/skills/xddp.status/SKILL.md` が `claude -p` 単発で `AVAILABLE:yes`。再現手順: `tools/harness/verify_isolated_auth.sh`。詳細は PLAN-20260725-smoke-full-api-key-auth Section 5）。**残: モデル適用機構そのものの実測**（隔離HOME経由で `--model` 継承／`model:` 注入により意図したモデルが `modelUsage` に現れることの確認）は校正ラン着手時に実施する
- [ ] 校正ラン（3.5）を実施し、工程×モデルの**偽失敗率**とトークンを実測 → **標本数 N を rule of three 基準（上側95%限界 ≤15%→N=20／重要工程 ≤10%→N=30・0失敗必須）で確定**し、工程別モデル（Haiku/Sonnet）と `SMOKE_TOKEN_BUDGET` を確定してプランに記録
- [ ] 基準（N 回 0 失敗）を満たすモデルが Sonnet でも得られない工程は「手動検証」へ退避し、信頼できない自動判定を作らないことを確認
- [ ] ゴールデンのブートストラップ順序（3.5 step 1: 確定 → 測定）が守られ、鶏卵問題が起きないことを確認
- [ ] `make smoke-full PHASE=NN` が隔離 HOME で完走し、実利用者の `~/.claude/` を変更しないことを確認
- [ ] 予算ガードが機能する（上限を意図的に低く設定すると途中中断・赤報告になる）ことを確認 — **ガード純ロジックは unittest 済み（`test_smoke_full.py`: `test_raises_when_over_budget`＝超過で `BudgetExceeded`／`test_can_start_respects_remaining_budget`＝残予算不足で起動拒否／`test_can_start_respects_max_phases`＝工程数上限）。オーケストレーションループ（`run_phase`／`main`）は子プラン PLAN-20260726-smoke-full-runner-enablement A で実装済みで、モック `_invoke_phase` を用いた予算超過中断（exit 7）・残予算不足（budget_skip）は unittest 済み（`TestRunPhase`・`TestMainExitCodes`）。旧「校正完了後に有効化（return 4）」ゲートは撤去し実効予算ゲート（exit 6）へ置換済み。実消費を積算した「途中中断・赤報告」の end-to-end 実演は同子プランの B/C/D（校正ラン）で実施する（残）**
- [ ] full-run スモークがスキル挙動回帰を検出する（例: あるスキルの `apply` 参照や結線を壊すと該当工程が赤になる）ことを1件確認
- [x] `claude` 未導入環境で `make smoke-full` が明示エラーで停止し、`make test` は影響を受けないことを確認 — **2026-07-26 実機確認。`claude` を PATH から外して `smoke_full.py --phase 02` を起動すると `❌ full-run スモークは \`claude\` CLI を必要とします（未導入/認証未了）` を出力し exit 3 で停止。同条件で `make test` は exit 0（`run_all.py` は `claude` 非依存）。認証未設定時も別途 exit 5 で明示停止する経路あり（`_resolve_auth_env`）**

**共通**
- [x] `openpyxl` 不在環境でも skip 扱いで `make test` が緑になる — **2026-07-26 実機確認。`openpyxl` 不在を模したシャドウモジュールを `PYTHONPATH` 先頭に置いて `test_crs_md2excel.py`・`test_excel_dump.py` を実行すると両者 `OK (skipped=2)`。両ファイルの `try/except ImportError` ＋ `@unittest.skipIf(openpyxl is None, ...)` ガードで担保**
- [x] CLAUDE.md・README.md・verification-checklist の記述と整合 — **2026-07-26 確認。CLAUDE.md: `## ファイル構成` に `tools/harness/` 行＋`### ツール修正後のハーネス実行（必須）` 節あり。README.md: `#### 開発時テストハーネス（make）` 節に test/lint/unit/smoke-full の表・実行要件・pre-commit 雛形・隔離認証確認を記載。verification-checklist: 「機械検証（`make test`＝L1〜L3）／full-run 自動（`make smoke-full`）／手動 LLM 検証」の3タグ体系を導入。3ファイルとも `make` ターゲット名・トークン特性で一貫**
- [x] 特定ドメインへの偏りがないか（CLAUDE.md「適用ドメインの中立性」参照）— **2026-07-26 確認。ハーネスは言語・ドメイン非依存の構造検証のみ。検査C は `DOMAIN_EXAMPLE_PLACEHOLDERS`（`DB`・`GPIO`・`UART` 等）を error 判定から除外（`test_domain_examples_excluded` で固定）。ハーネス .py 本体に Web/RDB 等のドメイン固有語なし（`rest` はローカル変数）**

---

## 6. レビュー

AIレビュー結果: [plans/review/PLAN-20260725-p2-test-harness-review.md](review/PLAN-20260725-p2-test-harness-review.md)

`/xddp.plan-review` で Critical（🔴）・残指摘（🟡/🔵）がゼロになるまで実施予定。

---

## 7. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | tsuna44 |
| 承認日 | 2026-07-25 |
| 備考 | AIレビュー8回 ✅合格（🔴0）。L1〜L3（0トークン層）を先行実装。L4/L5（smoke_full）はコード骨格＋純ロジックのみ実装し、校正ラン（3.5・トークン消費／`claude` CLI 要）は運用者が別途実施する |
