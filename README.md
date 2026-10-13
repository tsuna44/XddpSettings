# XDDP for Claude Code

Claude Code で XDDP（eXtreme Design-Driven Process）を運用するためのスキル・テンプレート・エージェント定義集です。

## セットアップ

```bash
# 1. リポジトリを取得
git clone <this-repo> xddp

# 2. .claude を ~/.claude に反映
bash xddp/ClaudeCode/setup.sh
```

これで Claude Code 上で XDDP スラッシュコマンドが使えるようになります。

> **実行要件:** Python 3 が必要です。決定的処理スクリプトの大半は標準ライブラリのみで動作しますが、
> `/xddp-md2excel`（CRS→Excel変換。CRS更新のたびに自動実行される）・`/xddp-excel2md`
> （Excel→Markdown変換）は `openpyxl` を追加で必要とします。Excel が使えない環境では、代わりに
> 標準ライブラリのみで動作する `/xddp-crs-view`（HTML ビューア／CLI ツリー）が使えます。
> `python3 -c "import openpyxl"` がエラーになる場合、`pip install openpyxl` するか、venv を作成して
> `xddp.config.md` の `MD2EXCEL_PYTHON_BIN` にそのインタプリタパスを指定してください
> （詳細は `xddp.config.md` の「## 5. 実行環境設定」参照）。
> Windows は WSL または Git Bash 経由（POSIX 互換シェル・`grep`/`rg`・`~` 展開が利用可能な環境）を
> 前提とします。ネイティブの cmd/PowerShell 単体には対応していません。

> **任意: 波紋調査のスライス判定（tree-sitter）**  
> `/xddp-04-specout` の波紋調査は、C / C++ / Python のヒットを LLM を使わずに判定します。tree-sitter があれば
> 関数内の静的スライス（スライス判定）、無ければ標準ライブラリのみの規則判定（ヒット行を含む関数を追う）で動きます
> （どちらでも動作し、波数上限・1波の予算は同じ値です）。スライス判定を使う場合は次を実行してください。
> ```bash
> pip install -r ~/.claude/skills/xddp-04-specout/scripts/requirements-slice.txt
> ```
> 既定の `python3` に入れられない場合は venv に入れ、`xddp.config.md` の `SPECOUT_SLICE_PYTHON_BIN` に
> そのインタプリタパスを指定してください（`SPECOUT_SLICE: off` で常に規則判定にもできます）。

> **既存の ~/.claude に設定がある場合**  
> `setup.sh` は既存ファイルをスキップします（上書きしません）。  
> 強制上書きしたい場合は手動でコピーしてください。
> ```bash
> cp -r ~/.claude ~/.claude.bak
> cp -r xddp/ClaudeCode/.claude/* ~/.claude/
> ```

## 使い方

対象プロジェクトのディレクトリで Claude Code を起動し、スラッシュコマンドを実行します。

### 標準フロー

CR番号とタイトルを指定して実行します（要求書ファイルがまだない場合は省略可）。

```
/xddp-01-init REQ-2026-001 "モジュール間送信データへの付帯情報追加" path/to/要求書.md
/xddp-02-analysis REQ-2026-001
/xddp-03-req REQ-2026-001
/xddp-04-specout REQ-2026-001
/xddp-05-arch REQ-2026-001
/xddp-06-design REQ-2026-001
/xddp-07-code REQ-2026-001
/xddp-08-verify REQ-2026-001
/xddp-09-test REQ-2026-001
/xddp-10-test-run REQ-2026-001
/xddp-11-specs REQ-2026-001
/xddp-close REQ-2026-001
```

> 要求書ファイル（3番目の引数）は省略できます。省略した場合、`REQ-{CR}.md` はテンプレートに文書番号・タイトル・作成日を自動記入した状態で配置されるので、内容を編集してから次のコマンドに進んでください。引数を一切指定しない場合は、CR番号・タイトル・要求書ファイルパスをAIが対話的に質問します。

各コマンドは AI が成果物を生成→自動レビュー→人レビューゲートの順で進みます。人レビューゲート表示時には、
確信度が低い箇所トップN・前工程からの差分サマリー・推奨レビュー順序と目安時間をまとめた
レビューブリーフ（`.review-brief.md`）が自動生成され、案内文にインライン要約されます。

### 母体調査（CR 非依存）

CR を回さずに母体コードの処理内容を調べる。

```bash
/xddp-survey repo-A module src/auth      # モジュール単位で調査
/xddp-survey repo-A topic g_device_state # 識別子を起点にモジュール横断で調査
/xddp-survey repo-A promote              # 既存の調査結果を昇格のみ実行
```

調査後、結果をどう扱うかを選択する。

| 選択 | 動作 |
|---|---|
| 調査のみ | `{XDDP_DIR}/survey/` に残す。baseline は変更しない |
| knowledge へ昇格 | `baseline_docs/{repo}/knowledge/code-knowledge/` へ登録する |
| specs へ昇格 | モジュール仕様書として `baseline_docs/{repo}/specs/` へ登録する（module スコープのみ） |

CR を1本も回していない母体は `latest-specs/` が空であり、工程4a（スペックアウト）が
参照する `BASELINE_SPECS_DIR` に何も無い状態から始まる。`/xddp-survey` で先に仕様を起こしておくと、
以後の CR の調査精度が上がる。

### 進捗確認

```
/xddp-status REQ-2026-001
```

### ツール自体（スキル・エージェント）を修正したときの動作確認

修正箇所に応じた確認手順は [docs/xddp-tool-verification-checklist.md](docs/xddp-tool-verification-checklist.md) を参照。

#### 開発時テストハーネス（make）

`tools/harness/` はツール自身（`ClaudeCode/.claude/` 配下のスキル・エージェント）を検証する
開発時メタツール。守備範囲を「0トークン層（L1〜L3）」と「LLM 層（L4/L5）」の2グループに分ける。
**環境構築（`claude` CLI・認証・第三者エンドポイント設定）から終了コード一覧・トラブルシューティングまでの詳細手順は [tools/README.md](tools/README.md) にまとめてあるので、初めて実行する場合はそちらを参照してください。**

| コマンド | 内容 | LLM トークン |
|---|---|---|
| `make test` | L1〜L3 一括（全 unittest ＋ `refcheck`）。数秒・git pre-commit 実用圏 | **0** |
| `make lint` | `refcheck` のみ（検査A: `apply` 見出し／B: `subagent_type`・引数契約／C: テンプレートプレースホルダー／D: スクリプト↔スキル結線／E: xddp-reviewer チェックリスト遅延ロード契約／F: 設計根拠・変更履歴記述の混入／G: xddp-common/procedures/ とインデックスの整合） | 0 |
| `make unit` | 全 unittest のみ | 0 |
| `make smoke-harvest [PHASE=NN]` | ブートストラップ: シード起こし（no-assert。初回校正の入口。B） | 予算上限内 |
| `make smoke-full PHASE=NN` | L4/L5 full-run スモーク（隔離HOMEでスキルを実起動・予算ガード付き）。触った1工程のみ | 予算上限内 |
| `make smoke-full-all` | 全通し（init→close。稀。既知の制限あり。詳細は [tools/README.md](tools/README.md) 3.5節） | 予算上限内 |
| `make smoke-calibrate [PHASE=NN] [MODEL=haiku]` | 校正ラン（偽失敗率・トークン実測） | 予算上限内 |

- **実行要件:** `python3`（標準ライブラリのみ）・GNU make。`smoke-full*`／`smoke-calibrate` のみ `claude` CLI と非対話認証用の環境変数が必要（隔離HOME実行のため必須。`make test` は影響を受けない）。認証方法（Anthropic 公式／第三者エンドポイント）・第三者エンドポイント利用時のゴールデン分離・予算と計測の扱いは [tools/README.md](tools/README.md)「2. 事前準備」を参照。
- **git pre-commit フック雛形:** `tools/harness/pre-commit.sample` を `.git/hooks/pre-commit` にコピーして `chmod +x` すると、`ClaudeCode/.claude/` 変更コミット時に `make test`（0トークン層のみ）が自動で走る。full-run（L4/L5）はフックに載せない。
- **L4/L5 は校正済み・有効化済み（2026-07-26・軽量 advisory）。** `make smoke-full PHASE=NN`（NN∈`02`〜`11`）が `SMOKE_TOKEN_BUDGET`=30（C 実測確定）で実走し、工程の主成果物の構造性質を `test-fixtures/golden/phaseNN-single.json` と照合する（違反は人が解釈する **advisory チェック**）。子プラン PLAN-20260726-smoke-full-runner-enablement 参照。
- **校正の実施結果（B→C→D、概要）:** 工程別入口シードは人手オーサリングで確定（B。`--all --harvest` は XDDP の人間参加型ゲートと衝突し自動連鎖でシードを起こせないため）→各シードに `--update-golden` を実走しゴールデンを確定（C。02〜11 の9件）→モデルは Sonnet 単一・`SMOKE_TOKEN_BUDGET` は C 実測から確定し厳密な偽失敗率測定は行わない軽量 advisory 運用とする（D。`close` は成果物 glob の制約により advisory 対象外＝手動検証）。複数工程のゴールデンをまとめて確定する手順・終了コード一覧は [tools/README.md](tools/README.md) を参照。

### スペックアウト（波紋検索）の詳細仕様

Discovery BFS の検索対象決定方法・判定先（スライス判定・規則判定・LLM 分類）・波数上限と打ち切り記録・中断耐性・コンテキスト管理の詳細は [docs/specout-discovery-guide.md](docs/specout-discovery-guide.md) を参照。

### 人が成果物を直接編集した後に AI レビューしたい場合

```
/xddp-review REQ-2026-001 <ドキュメント種別>
```

| ドキュメント種別 | 対象ファイル |
|---|---|
| `analysis` | `02_analysis/ANA-{CR}.md` |
| `req` | `03_change-requirements/CRS-{CR}.md` |
| `specout` | `04_specout/SPO-{CR}.md` |
| `arch` | `05_architecture/DSN-{CR}.md` |
| `design` | `06_design/CHD-{CR}.md`（インデックス。実体はUR別内容ファイルへの選択を促される） |
| `test` | `09_test-spec/TSP-{CR}.md` |
| `spec` | `latest-specs/` 配下の指定ファイル（対象ファイルを引数で直接指定。省略時は確認される） |

例：

```
/xddp-review REQ-2026-001 design
```

レビュー結果は `{CR}/review/` に出力されます。  
指摘事項を反映する場合は `/xddp-revise` を使います（`spec` は対象外です。`latest-specs/` 配下の
ファイルを直接編集してください）。

### レビュー指摘を成果物に反映したい場合

```
/xddp-revise REQ-2026-001 <ドキュメント種別> [ID,ID,...]
```

レビューファイルが存在する場合、未対応（⬜）の指摘を自動で読み込み一覧表示します。
ID を指定すると該当番号の指摘のみを対象にします。省略すると全ての未対応指摘が対象になります。

レビューファイルが存在しない場合は Claude から「修正箇所を教えてください」と問われるので、
リスト形式で指摘を入力してください。

```
- セクション3.2: 用語を「変更要求」→「変更要求仕様」に統一
- 表1: トレーサビリティ列が抜けている
```

修正後はレビュー記録ファイルの対応状況が ✅ 対応済 に更新され、ドキュメントのバージョンが +0.1 されます。  
修正後に再度レビューする場合は `/xddp-review` を実行してください。

### フェーズ一覧

| コマンド | 引数 | 内容 | 生成する主な成果物 |
|---|---|---|---|
| `/xddp-01-init` | `CR番号 タイトル [要求書.md] [--profile {full\|quick}]` | CRワークスペースを初期化し、成果物フォルダ・`progress.md`・テンプレートから生成した要求書（`REQ-{CR}.md`）を作成する。要求書ファイルを指定した場合は参照コピーする（`--profile` は位置非依存。省略時は `xddp.config.md` の `CR_PROFILE`（未設定時 `full`）を使用する） | `{CR}/`, `{CR}/progress.md`, `{CR}/01_requirements/REQ-{CR}.md`, `xddp.config.md`, `project-rulebook.md` |
| `/xddp-02-analysis` | `[CR番号]` | 要求書を読み込み、UR/SR/SP 分類・曖昧点・実現可能性を含む要求分析メモ（ANA）を生成。AI レビューループ後に人レビューゲートで停止する（`quick`: 工程3と統合し軽量 ANA＋CRS を生成、CRS へ1ラウンドのAIレビューのみ実施。人レビューゲートは設けないが、project-rulebook 追記候補の確認は `quick` でも行う） | `ANA-{CR}.md`, `CRS-{CR}.md`（`quick` の場合のみ） |
| `/xddp-03-req` | `[CR番号]` | ANA を元に USDM 形式の変更要求仕様書（CRS）を作成。AI レビューループ後に人レビューゲートで停止する（`DEVELOPMENT_MODE: new` の場合、SP は Before/After ではなく単一の仕様記述になる。`quick`: 工程2に統合されスキップ） | `CRS-{CR}.md` |
| `/xddp-04-specout` | `[CR番号] [エントリポイント...]` | 母体コードを調査し、変更影響範囲を特定するスペックアウト文書（SPO）を生成。CRS にフィードバックする。母体調査の本体は下調べで、波紋調査はその周りを機械的に確認する追加の調査。初回実行（初回の波紋調査 `ripple/initial/` も `work/no-ripple.json` も無い repo）は ① 下調べ（Step A-Prelim。`xddp-specout-prelim-agent` が CRS から関係する処理を推論して母体を読み、`SPO-{CR}.md`・`modules/` を波紋調査に依存する節を除いて書き、根拠付きのシード候補を出す。完了しなかった repo は波紋調査・SPO の仕上げへ進まずに停止し、再実行で下調べからやり直す）→ ② シード候補表の作成（discovery-setup）→ ③ シード確認（Step A-Seed。`seed-preview` でヒット数を試算した候補表と repo ごとの波紋調査の要否〔既定は行う〕を提示し、人が採用・除外・追加を確定する。「`{repo}`: 波紋調査なし」と指示した repo は波紋調査を行わず、下調べ資料で工程4a を完了する〔印 `work/no-ripple.json` を書く。影響範囲は下調べで読んだ範囲に限られる〕。「中断する」を選ぶと波紋調査を始めずに ⏸ 中断で終了し、再実行で Step A-Seed から再開する。`SPECOUT_SEED_GATE: false` なら提示のみで全 repo の波紋調査へ進む〔採用0件・全件ヒット過多または予算超過の repo がある場合は確認する〕）→ ④ 波紋調査（波紋調査を行う repo のみ。波紋調査は1回＝1フォルダ `ripple/{調査}/` の独立した記録で、`ripple/runs.json` に名前・由来・シード・採用の有無を記録する。工程4a は初回の調査 `initial` を `run-add`・`init` で作って波ループ〔共通プロシージャ「## Ripple Wave Loop」〕で調べ、完了したら調査ごとの出力〔方式検討エージェント向けの上限つきの要約 `ripple-digest.md`・人向けの全量・検証スイープ・伝播グラフ〕を作って採用する。C / C++ / Python のヒットは LLM を使わずにスライス判定〔tree-sitter〕または規則判定で判定し、それ以外の言語のヒットだけを classifier が LLM 分類する。1波のヒット予算〔`SPECOUT_WAVE_HIT_BUDGET`〕・LLM 分類の上限〔`SPECOUT_LLM_HIT_BUDGET`〕を超えた分は優先順位の低いシンボルから打ち切り、波数上限〔`SPECOUT_MAX_WAVE_DEPTH`。既定6波〕に達したら一時停止せず、残りを discovery-log の「## 打ち切り記録」に残して自動完了する。上限を上げて再実行すると打ち切ったところから続ける）→ ⑤ SPO の仕上げ（Step A-Document。共通プロシージャ「## Specout Finish」。SPO の波紋調査の欄は採用した調査の合算で作る。スクリプトが採用した調査の合算を機能〔モジュール〕単位に要約し〔`ripple-summary`。人向けの全量 `ripple-summary.md` は上限なしで、LLM には渡さない〕、シードが直接参照するのに下調べの資料に無いファイルがあれば `xddp-specout-prelim-agent` を追加下調べ〔`PRELIM_MODE: additional`。repo ごとに1回。対象は repo ごとの累計で `SPECOUT_MAX_AFFECTED_FILES` 件まで。超えた分と資料にできなかった分は SPO §5.0 の ⚠️ と §9 で知らせる〕で起動して資料を書かせる。`assemble-spo` が SPO のスクリプトが書く欄〔§5.0 の波紋調査の要約は最大30行。§5.2・§5.5 は資料のあるモジュールのファイルだけ〕・資料のある各モジュール資料の「波紋調査の結果」節〔最大30行〕・版の確定を書き、`xddp-specout-document-agent` を1回起動して SPO の LLM が書く欄〔§2〜§4・§5.3・§5.4・§5.6・§5.7・§7〕と funcmap を書き、検証スイープ〔`verify-sweep`〕と伝播グラフ〔モジュール単位〕・関数単位の階層表〔`ripple-trace`。LLM には渡さない〕は調査ごとに作り、採用した各調査の検証スイープの未記録ヒット・未実施は SPO §9 に記録する。シードの直接参照ファイル数が `SPECOUT_MAX_AFFECTED_FILES` を超えたら CR の分割を推奨する警告を出す〔処理は止めない〕。配置は成長型で、資料のある〔台帳の〕ファイル数が閾値を超えた単位だけを分割へ移し、波紋調査で届いただけで資料の無いモジュールは `modules/` に作らない。採用した調査が0件の repo は下調べの資料だけで SPO を仕上げる〔`work/no-ripple.json` の有無で「波紋調査を行っていない」「採用した波紋調査が無い」を書き分ける〕）→ ⑥ SPO の AI レビュー（機械検査 `artifact_lint.py --doc-type SPO` の結果と、LLM は影響範囲の十分性〔L1〕・設計への申し送り〔L2〕の2項目だけ）の順に進む。再実行では、モジュール資料（人の修正を含む）・文書化済みファイル台帳・累積観察メモを保持し、SPO のスクリプトが書く欄とモジュール資料の「波紋調査の結果」は毎回作り直し、SPO の LLM が書く欄と funcmap は入力（台帳・波紋調査の要約・CRS・エントリポイント）が変わったか前回の document agent が成功していない場合だけ書き直す（`work/no-ripple.json` の repo は再実行でも SPO の仕上げだけを行う）。クロスリポジトリ伝播は、消費 repo に新しい調査 `cross-{提供 repo}-{n}` を作って採用する。工程4a の後にシンボルを足して調べる・調査を採用・取り消す・取り除く場合は `/xddp-investigate` を使う。設計根拠は [ADR-0023](docs/adr/ADR-0023-specout-two-layer-output.md)・[ADR-0025](docs/adr/ADR-0025-specout-ripple-runs.md)。下調べの調査範囲は `quick` でも full と同一（`quick`: 探索深さは full と同じ。SPO 文書の記載量とシーケンス図の粒度を簡略化・SPOレビュー1ラウンド。完了時にプロファイル適合性を双方向で案内） | `SPO-{CR}.md`, `SPO-{CR}-funcmap.md`, `04_specout/{repo}/ripple/runs.json`（調査の記録。スクリプトだけが書く）, `04_specout/{repo}/ripple/{調査}/`（調査ごとの `discovery-log.md`・`ripple-digest.md`〔LLM 向けの要約〕・`ripple-summary.md`〔全量。人向け〕・`ripple-graph.md`・`ripple-tree.md`〔伝播の経路。人向け〕・`work/`〔`bfs-state.json`（真実）＋`bfs-state.md`（自動生成ビュー）、per-wave metrics の `metrics.jsonl`、波ごとの一時ファイル `waves/wave-{N}-*.json`、`verify-sweep.json`・`ripple-summary.json` 等〕。取り除いた調査は `ripple/_removed/` に退避）, `04_specout/{repo}/ripple-summary.md`（採用した調査の合算の全量。人向け）, `CRS-{CR}.md`（更新）。中間ファイルは `04_specout/{repo}/work/`（下調べ索引 `prelim-index.md`（存在＝下調べ完了の印）・累積観察メモ `observation-memo.md`・文書化済みファイル台帳 `documented-files.md`・シード候補表 `seed-candidates.md`（Step A-Seed で人が採否を編集しうる）・`seed-unsupported.json`・`module-assignments.json`・初回の波紋調査を作らない印 `no-ripple.json`・波紋調査の要約 `ripple-summary.json`（採用した調査の合算）・追加下調べが関係なしと判断したファイルの記録 `prelim-gap-reviewed.md`・SPO の仕上げの記録 `specout-finish.json`・採用・取り消しの前に退避した SPO `spo-backup/`・document agent の入力の指紋 `assemble-inputs.json`・document agent に渡すエントリポイントの累積 `doc-entry-points.json`（以前の指定を外すときは人が編集する）・統合パスの追加下調べの下書き `module-drafts/`（SPO へ差し込んだ後に削除）等。下書き以外は削除せず残す。人は候補表以外を通常参照しない）と `04_specout/cross/work/`（`cross-propagation-targets.json`／`cross-propagation-log.json`。マルチリポジトリ・共有インタフェース検出時のみ）に出力 |
| `/xddp-05-arch` | `[CR番号] [--detail \| --from-step-c]` | 実装方式を複数案比較し、推奨方式を決定する実装方式検討メモ（DSN）を生成。AI レビューループ後に人レビューゲートで停止する。方式検討エージェントが、案で変える既存の識別子の広がりを確かめる波紋調査を申告した場合は、人の許可を得て案ごとの調査（`arch-{案}`。SPO には入れない）を行い、エージェントが要約 `ripple-digest.md` を DSN の影響範囲・QCD に反映する（Step A-ripple。1ラウンド）。Step C で採用案の最新の調査を採用し（前に採用していた別の案の調査は取り消す）、採用が変わった repo の SPO を仕上げ直してから CRS へフィードバックする。Step C の SPO の仕上げで止まった場合は `--from-step-c` で Step C から再開する。`--detail` を指定すると、既存の全案（approach-*.md）に構造体関連図・主処理シーケンス図を統一粒度で追記する（`quick`: per-repo の方式比較をスキップ。マルチリポジトリで cross SPO がある場合は cross DSN のみ生成する） | `DSN-{CR}.md` |
| `/xddp-06-design` | `[CR番号]` | DSN を元にBefore/After設計（インタフェース定義・図、実装コードは書かない）の変更設計書（CHD）を作成。AI レビューループ後に人レビューゲートで停止する（`DEVELOPMENT_MODE: new` の場合、Before設計は「新規実装のため対象外」表記になる。`quick`: DSN 不在で単一設計案・CHD 簡略化・レビュー1ラウンド） | `CHD-{CR}.md`（インデックス）＋ `CHD-{CR}-{UR-ID}[-{N}].md`（UR別内容ファイル）, `CRS-{CR}.md`（フィードバック更新） |
| `/xddp-07-code` | `[CR番号]` | CHD に基づいてソースコードを変更し、静的検証（設計適合・コード品質・セキュリティ、および `VERIFY_LINT_COMMAND`/`VERIFY_BUILD_COMMAND`/`VERIFY_TYPECHECK_COMMAND` 設定時は lint/build/型検査コマンドの実行）を実施する（`VCS_TYPE: git`（既定 `auto`）の場合、開始時に作業ブランチ `{VCS_BRANCH_PREFIX}{CR}` を自動作成/切替し、完了時に自動コミットする） | 実装ファイル群, `TOOLRUN-{CR}-{repo}.md`（`VERIFY_*_COMMAND` 設定時のみ） |
| `/xddp-08-verify` | `[CR番号]` | xddp-07-code の自動検証と同一内容の静的検証（設計適合・コード品質・セキュリティ、および設定時は lint/build/型検査コマンドの実行）を人が任意のタイミングで手動実行する（`xddp-07-code` と同じ作業ブランチ切替を行う。失敗しても検証は続行する） | `VERIFY-{CR}.md`, `TOOLRUN-{CR}-{repo}.md`（`VERIFY_*_COMMAND` 設定時のみ） |
| `/xddp-09-test` | `[CR番号]` | テスト仕様書（TSP）を生成し、AI レビューループ後に人レビューゲートで停止する（テスト実行は `/xddp-10-test-run` で行う。`DEVELOPMENT_MODE: new` の場合、回帰テストは新規コンポーネント間の依存整合性テストに置き換わる） | `TSP-{CR}.md` |
| `/xddp-10-test-run` | `[CR番号]` | レビュー確定済み TSP に基づきテストを実行し、不具合修正→TM/CRS フィードバックを実施する（全テストパス時に自動コミットする） | `TRS-{CR}-{NN}.md`（NN=実施回数） |
| `/xddp-11-specs` | `[CR番号]` | CR で変更された仕様を `latest-specs/` に反映・生成する。Kruchten 4+1 ビューモデルに基づいた多階層ディレクトリ構造（system/use-cases, {repo}/overview, {repo}/{module}, cross/interfaces 等）を生成・更新する。AI レビュー（バッチ単位）後に人レビューゲートで停止し、人が `latest-specs/` を直接編集した場合（`CHANGED` 検知）はバッチ単位で最終レビューを1回実施する | `latest-specs/` 配下の各仕様書（spec.md・state-machine.md・structure.md・sequences/・overview/・system/use-cases/ 等） |
| `/xddp-close` | `[CR番号]` | 工程の気づきをバックログへ集約し、知見ログを更新して CR を完了する（クローズ前に未コミット変更を最終コミットする。成果物昇格・AI_INDEX.md更新は `promote.py`（決定的処理）が担当し、project-rulebook upsert・code-knowledge 昇格等の知識命名判断のみエージェント（`xddp-close-knowledge-agent`）が担当する） | `improvement-backlog.md`（更新）, `lessons-learned.md`（更新） |
| `/xddp-abort` | `[CR番号] [, 中止理由]` | 完了見込みのない CR を理由付きで中止し、VCS 後片付けを案内する（再開しない前提） | `progress.md`（`## CR 中止` セクション追記） |
| `/xddp-investigate` | `[CR番号] (ripple [--name 名前] [--adopt] シンボル... \| adopt --name 名前 \| unadopt --name 名前 \| remove --name 名前 \| list \| finish \| document 対象... [--focus 観点] \| suggest) [--repo リポジトリ]` | CR の母体調査に波紋調査を足す・採用する・取り消す・取り除く（工程4a の後でも、工程5以降でも実行できる。下調べの完了後から使える）。`ripple` は新しい調査 `ripple/{名前}/` を作り（`--adopt` で完了後に採用）、`adopt`・`unadopt` で SPO の波紋調査の欄に入れる・外し、`remove` は調査を `ripple/_removed/` に退避する。工程4a の完了後に採用が変わると、SPO を退避してから仕上げ直し（AI レビューは行わない）、工程5の状態に応じて CRS への反映を案内する（工程5が未着手なら工程5で、進行中なら DSN の更新を経て Step C で、それ以外は人に確認して `xddp-spec-writer-agent` で更新する）。採用・取り消しを決めるのは人で、LLM は根拠を添えて提案するだけ。`document` は人の依頼でファイル・ディレクトリ・モジュールを調べて資料にする（依頼調査。例: `/xddp-investigate CR-2026-001 document src/net --focus エラー時の後始末の流れ`。`suggest` は資料の無いモジュールの候補をスクリプトが示す。依頼するかは人が決める）。下調べのエージェントが母体コードを読んで資料を書き、台帳の工程は `依頼調査`（追加下調べの累計の上限には数えない）。CRS との関係を確かめられなくても資料にし、台帳に `確認できず`・SPO §8 に注記を書く。除外パターン（テストコード等）に一致する対象も、人が名指しすれば調べる。資料のあるファイルは「すでに資料として記述しています。追記が必要ですか？」と尋ね、「必要」なら追記の節（`### 2.7 追加調査（依頼調査）`、統合パスは `### 2.A.10`）に足す（既存の記述は変えず、スクリプト `doc-append-check` が検査して満たさなければ元に戻す）。設計根拠は [ADR-0026](docs/adr/ADR-0026-specout-requested-docs.md) | `04_specout/{repo}/ripple/{名前}/`・`ripple/runs.json`、（採用・取り消し時）`SPO-{CR}.md` 等の更新、（依頼調査）モジュール資料・台帳・観察メモ・依頼調査の記録 `work/doc-request-log.md` |
| `/xddp-status` | `[CR番号]` | CR の現在フェーズと全成果物の状態を一覧表示する | —（参照のみ） |
| `/xddp-set-profile` | `CR番号 {full\|quick} [理由]` | CR_PROFILE を明示的に切り替える。工程4（スペックアウト）完了時のプロファイル適合性チェック（quick↔full 双方向の案内）で使用を促されるほか、任意のタイミングで実行できる（既に完了・スキップ済みの工程には遡及しない。未着手の工程から新しいプロファイルが適用される） | —（`progress.md` の更新のみ: ヘッダの `CR_PROFILE`、プロファイル変更で不整合になる工程の状態・成果物列、「次に実行すべきコマンド」欄、`## 備考・メモ` へのプロファイル変更履歴） |
| `/xddp-review` | `[CR番号] analysis\|req\|specout\|arch\|design\|test\|spec [対象ファイル]` | 人が直接編集した成果物に対して単体 AI レビューを実施する（`spec` は latest-specs 配下のファイルを対象） | `{成果物}/review/*.md` |
| `/xddp-revise` | `[CR番号] analysis\|req\|specout\|arch\|design\|test [repo名] [ID,ID,...]` | 人のレビュー指摘を成果物に反映する | 対象成果物（更新） |
| `/xddp-plan-review` | `[プランファイルパス]` | プランのAIエキスパートレビューと修正を、Criticalと残指摘事項（🟡/🔵）がなくなるまで繰り返す | `plans/review/{PLAN_NAME}-review.md` |
| `/xddp-excel2md` | `[CR番号] [Excelファイル]` | 人が編集した USDM 形式 Excel の変更要求仕様書を Markdown（CRS）に変換する | `CRS-{CR}.md` |
| `/xddp-md2excel` | `[CR番号]` | CRS Markdown から USDM 形式 Excel を生成する | `CRS-{CR}.xlsx` |
| `/xddp-crs-view` | `[CR番号] [--format html\|tree] [--status "..."]` | CRS を階層的に閲覧できる HTML ビューア（既定）または CLI ツリーを生成する。Excel が使えない環境向け。HTML はステータス絞り込み・全文検索・レビュー指摘のコメント入力に対応し、`.md` 書き出しで `/xddp-revise` に連携できる | `CRS-{CR}-view.html`（`--format html`）／標準出力（`--format tree`） |
| `/xddp-fill-rulebook` | `[repo名 / cross]` | `project-rulebook.md` の未記入セクションをコード調査でドラフト生成し、人が確認後に書き込む（完了時デスクトップ通知）。シングルリポジトリ時は共通 `project-rulebook.md` のみ対象（`{repo}` / `cross` 指定はエラー） | `project-rulebook.md` または `project-rulebook-{repo}.md`（更新） |
| `/xddp-codemap` | `[repo名 \| all]` | モジュールカタログを生成・更新する。モジュール構成・主要シンボル・依存グラフを baseline_docs に保存し、specout の BFS 優先度制御に活用する | `baseline_docs/{repo}/module-catalog.md` |
| `/xddp-survey` | `[repo名] [module {モジュール名}... \| topic {シード}... \| promote]` | CR 非依存で母体コードを調査し「現状仕様」を文書化する。調査後に (a) 調査のみ (b) knowledge へ昇格 (c) specs へ昇格 を人が選択する。CR を1本も回していない母体から仕様書を起こす場合に使用する | `{XDDP_DIR}/survey/{repo}/**/SURVEY-*.md`、および昇格を選んだ場合は `baseline_docs/{repo}/knowledge/code-knowledge/` 配下または `baseline_docs/{repo}/specs/{module}/` |
| `/xddp-update-knowledge` | `[repo名] [constraint\|flow\|callgraph\|lesson\|note\|glossary\|structure]` | CR 非依存で baseline_docs/ の knowledge ディレクトリに知識を登録・更新する。対話形式と引数形式に対応。`glossary` はプロジェクト共通（`{DOCS}/glossary.md`）・リポジトリ固有（`{repo}/knowledge/glossary.md`）・クロス（`cross/knowledge/glossary.md`、`IS_MULTI` の場合のみ）のいずれかのスコープを選択して用語を登録する。`structure` はモジュール間の構造体依存関係と落とし穴・注意点を `_structures/` へ登録する | `baseline_docs/{repo}/knowledge/` 配下の各ファイル、または `baseline_docs/glossary.md`／`baseline_docs/cross/knowledge/glossary.md`（`glossary` 種別の場合） |
| `/xddp-sync-design` | `[CR番号] [変更サマリ（省略可）]` | コードから DSN を再生成してリビジョンとして記録し、AI レビュー→人承認を実施する | `DSN-{CR}-rev{N}.md`、`DSN-{CR}-rev{N}-review.md` |
| `/xddp-feedback` | `[CR番号] arch\|design\|test\|code [repo名]` | arch/design/test 成果物の現在の内容（人が直接編集した内容、または `/xddp-sync-design` 適用後の最新DSNリビジョンを含む）の未反映分を抽出し、人の確認後に CRS（design/code の場合は TM も）へ反映する。`code` の場合はコード差分から該当CHDバッチファイルを先に同期する | `CRS-{CR}.md`（更新）、design/code の場合は `TM-{CR}.md`（更新）、code の場合はさらに対象CHDバッチファイル（直接更新） |

### 決定的処理スクリプト

帳簿管理・件数照合・機械検査など決定的に処理できる部分は Python スクリプトに実装し、LLM は意味判定
（言語知識を要する分類・レビュー）に専念する（詳細は `CLAUDE.md`「開発ルール」参照）。

| スクリプト | 役割 | 呼び出し元 |
|---|---|---|
| `xddp-common/scripts/xddp_progress.py` | `progress.md` の状態・詳細ステップ・成果物リンク・備考⚠️行を更新する | 全フェーズスキルの「## Progress Update」等 |
| `xddp-common/scripts/xddp_gate_snapshot.py` | CR フォルダのファイル群のスナップショット取得・差分判定（Human Review Gate の `CHANGED` 機械判定）。`--extra-file`（複数指定可）で `{CR_PATH}` 外側の個別ファイル（`latest-specs/` 等）も走査対象に追加できる | 「## Human Review Gate」、`/xddp-11-specs` Step GATE（インライン呼び出し。`--extra-file` で `latest-specs/` 配下の直接編集も検知） |
| `xddp-common/scripts/artifact_lint.py` | フロントマター必須キー検査（SPEC のみ）・Mermaid 基本構文検査・Markdown テーブル列数検査・SPO 機械検査（`--doc-type SPO` のみ：funcmap の SP 網羅・直接呼び出し元数・`確認要` 残存・影響種別の一致〔F1〜F4。cross/ は対象外。採用した波紋調査が無い SPO（同じディレクトリの `ripple/runs.json` に `"adopted": true` の調査が無い。ファイルが無い・読めない場合を含む）は F4 の対象外〕と §4.1・§4.2・§5.5〜§5.7 の存在・記入〔S1〜S5〕。`reviewer` へ `LINT_RESULTS` の `spo` カテゴリとして渡す）・CRS 構造チェック（`--doc-type CRS` のみ：理由必須・ID一意・仕様グループ配下SP存在・グループ名 `＜＞` 表記・「等」等の曖昧表現・SP本文重複・否定表現候補・分割軸の列挙値・要求3階層の兆候・H7見出し不在（L12）・CRプレフィクス欠落ID検出（L13 fail-loud） = L1〜L13。ID形式は形式B（CR名前空間先頭。例 `CR-2026-970-UR-001`／`CR-2026-970-SP-001-001.010`）。見出し体系は USDM Canonical（カテゴリ=H3 ＜＞・UR=H4・要求グループ=H5 ＜＞・SR=H6・仕様グループ=太字行・SP=リスト項目）。error/warning を区別）・ANA §0 degraded mode 注記チェック（`--doc-type ANA` のみ：§0テーブルの出典ファイルに `latest-specs/` 由来の参照があれば注記の有無を検査。A1） | 「## Invoke Reviewer」（`subagent_type=xddp-reviewer` の唯一の入口） |
| `xddp-common/scripts/xddp_review_brief.py` | Human Review Gate 向けレビューブリーフ生成（不確信度マーカー集約・前工程からの差分・推奨レビュー順序と目安時間）。`baseline`（工程開始時スナップショット）／`generate`（ブリーフ本体生成、`--extra-file` で `{CR_PATH}` 外側の個別ファイルもマーカー検出・ランキング対象に追加可能。差分集計は対象外）の2サブコマンド。`{工程}/{repo}/work/` 配下の中間ファイルと CR 直下の計測ファイル（`.phase-metrics-*.json`・`metrics.jsonl`）はレビュー対象外として除外し、work 配下は差分件数のみ表示する | 「## Snapshot Phase Baseline」「## Human Review Gate」、`/xddp-11-specs` Step 0・Step GATE（インライン呼び出し） |
| `xddp-common/scripts/xddp_metrics.py` | 工程別テレメトリ CLI（`phase-start`／`record`）。`## Snapshot Phase Baseline`〜`## Progress Update`（完了時）間の壁時計所要時間と、`## Review Loop` のレビューラウンド数・収束可否、`## Invoke Reviewer` 呼び出し1回あたりの `reviewer_call` イベント（`--reference-file` から算出する `reference_bytes`／`reference_file_count`／`reference_unmeasured_count`）を `{CR_PATH}/metrics.jsonl` へ1行1イベントで追記する | 「## Snapshot Phase Baseline」「## Review Loop」「## Invoke Reviewer」「## Progress Update」 |
| `xddp-04-specout/scripts/specout_bfs.py` | Discovery BFS 帳簿エンジン（visited/frontier管理・参照解決の実行・コマンドID採番・HIGH/MEDIUM交差ルール・同名MEDIUM異スコープのケースA/B/C分岐・高ノイズシンボル判定・モジュール優先度制御・discovery-log.md/状態ファイル書き出し。LLMはhitsの意味判定のみ担当する）。エントリ表記 `symbol[FILE:filepath]`（static・無名名前空間・そのファイルで定義したマクロ等、そのファイルの中でしか参照できない名前。そのファイルの中だけを検索する種別 `FILE` のコマンドで、`[MEDIUM:…]` とは別のエントリ〔確信度 HIGH・交差ルール・ケースA/B/C の対象外〕）・エントリ表記 `symbol[CLASS:ClassName]`（C++ のメソッド・メンバー変数。C++ として解析するファイルだけを素の名前で検索し、判定でクラスを絞る。同じ素の名前のエントリの検索は1回にまとめ、ヒット行をエントリごとに複製する。種別 `CLASS`、確信度 HIGH・交差ルール・ケースA/B/C の対象外。要約と種類の表は `summary_key`〔`[CLASS:…]` はエントリ文字列、それ以外は素名〕を鍵にする。人が候補表・`/xddp-investigate` でシードに指定できる。設計根拠は [docs/adr/ADR-0022-specout-cpp-class-identity.md](docs/adr/ADR-0022-specout-cpp-class-identity.md)）・同一性の印（state の `entry_identity`〔`resolved`／`name-only`〕・`confirmed_files` の `identity`・ヒット表と確定ファイル一覧の「同一性」列・材料の `同一性:`・`status --brief` の `name_only_file_count`。`init --entry-identity`。設計根拠は [docs/adr/ADR-0021-specout-symbol-identity.md](docs/adr/ADR-0021-specout-symbol-identity.md)）。参照解決は差し替え可能な Backend（`SPECOUT_BACKEND`＝`auto`/`index`/`grep`/`rg`、静的種別は段階2以降）として抽象化されており、既定 `auto` は `index`（起動のたびにリポジトリ全体の識別子と `root.field` の索引を作り、辞書の参照で検索する。索引で引けない形のシンボルは rg・無ければ grep に委譲する。`grep`/`rg` を明示すると索引を使わず、`root.field` も `root.field` / `root->field` に一致するパターンで検索する）。除外パターン（`SPECOUT_EXCLUDE_PATTERNS`）は、バックエンドによらず同じ意味（名前のディレクトリ／ルートからのパスのディレクトリ／glob の3種の書き方）で適用する。保守的ヒットフィルタ（`SPECOUT_HIT_FILTER`＝`conservative`/`off`。行コメント除外は拡張子で言語別解決）＋分類済みロケーションdedup＋per-wave metrics（metrics.jsonl）でトークン・時間を削減し、除外行は discovery-log の「## フィルタ除外一覧」に監査記録する。高ノイズ HIGH シンボル（`SPECOUT_MAX_FILES_PER_MODULE` 超過）は、LLM 分類に回るヒットにだけ、`search` 時点で代表サブセットのみ分類する前倒し縮退（noise-collapse）を適用し（高ノイズによる波及停止も同様）、全ファイルは confirmed_files へ網羅する（代表行以外は判定しないため `false-positive` だけのファイルも含む。次波への伝播抑止の等価性は fixture で保証。[ADR-0009](docs/adr/ADR-0009-specout-hit-reduction.md)）。`module-catalog.md` 不在時は Wave 0 の確定ファイルから近傍ディレクトリ（深度1）を HIGH とする簡易 module-priority を構築する。波内 classification のチャンク並列化（`SPECOUT_CLASSIFY_CHUNK_SIZE`/`SPECOUT_CLASSIFY_PARALLEL`）に対応し、`search` は `known_symbols` の素名正規化配布・判定先ごとのチャンク分割出力（`--hits-dir`/`--chunk-size`。C / C++ / Python のヒットはスライス用チャンク `wave-{N}-hits-chunk-S.json`〔常に1件。`specout_slice.py classify` が判定する〕、それ以外の言語のヒットだけを LLM 用チャンク〔0件可〕に分ける）を行い、`commit-wave` は `--unsupported-patterns` による grep未対応パターンの一元追記と再利用波検出（`--chunk-mtime-min`）を担う。`status --brief` はオーケストレータのコンテキスト蓄積対策として最小キーのみを返す（[ADR-0010](docs/adr/ADR-0010-specout-parallel-classification.md)。`max_wave_depth`・`truncated_wave_limit_count`・`slice_engine`・`seed_direct_file_count`・`seed_budget_truncated_count` を含む）。`search` は dedup・フィルタの後に1波のヒット予算（`SPECOUT_WAVE_HIT_BUDGET`）と LLM 分類の上限（`SPECOUT_LLM_HIT_BUDGET`）を適用し、超えた分を関数シンボル→値シンボル、各々ヒットの少ない順に予算に収まるシンボルを採って残りを打ち切る（`commit-wave` が discovery-log の「## 打ち切り記録」に理由 `hit-budget`／`llm-budget` で記録し、件数一致検証では「フィルタ除外」に数える）。探索の起点の波（`wave_origin`）から数えた波数が `SPECOUT_MAX_WAVE_DEPTH` に達したら、一時停止せず残りのシンボルを打ち切り記録（理由 `wave-limit`）に残して `complete` にする。`extend` は状態によらず波数上限を引き上げ、`wave-limit` で打ち切ったシンボルを frontier に戻す（上限を上げて再実行したときに SKILL が呼ぶ）。`switch-engine` は探索の途中で tree-sitter を使えなくなり人が選んだときに、判定エンジンを規則判定へ切り替える。state の `seed_summary_pending`（シード要約の取り込みが済んでいないシード）が空でなければ、`search` は検索せずに終了コード 6 で止まる（SKILL が `specout_slice.py seed-summary` の結果を `merge-frontier --summaries-file`〔シードが書くグローバルがあれば `--as-seed-globals` も〕で取り込んでから再実行する）。`commit-wave` は、スライス判定で visited 済みの関数シンボルの要約（戻り値・副作用・出力引数）が広がった場合に、そのシンボルを次の波で再訪し（discovery-log の「## 要約の拡大による再訪（Wave N）」）、シードの直接参照ファイル数（`seed_direct_files`。Step C5 の規模の判定と、Step A-Document の CR 分割の警告・追加下調べの対象に使う）とファイル別のシードのヒット行数（`seed_direct_hits`。伝播しない判定を除く。追加下調べの対象を採る順に使い、`import` で初期化する）を記録する。discovery-log の種別・派生元・判定の値は英語のコード（`propagation-direct`・`seed(X)`・`hit-budget` 等）で書き、日本語の説明は冒頭の「## 凡例」にまとめる。`ripple-summary` は波紋調査の結果を機能（モジュール）単位に要約し、人向けの全量 `ripple-summary.md`（全モジュールの表・調査の打ち切り・下調べに無いシードの直接参照・grep 未対応パターン・モジュールごとのファイル一覧。上限なし。LLM には渡さない）と、`assemble-spo` の入力 `work/ripple-summary.json` を書く。`prelim_gap_files`（シードの直接参照のうち台帳にも追加下調べの判断の記録 `work/prelim-gap-reviewed.md` にも無いファイル。理由 `over-limit`／`not-written`）を返し、どのモジュールにも属さない確定ファイルがあれば終了コード 1 で止まる。`ripple-trace` は discovery-log と `work/ripple-summary.json` から、人向けのモジュール単位の伝播グラフ `ripple-graph.md`（Mermaid。描くモジュールは60個・辺は400本まで、全量は表。実線＝送り手の行と受け手の行がともに resolved の伝播を含む）と関数単位の階層表 `ripple-tree.md`（各関数1回・他の派生元つき）を書く（LLM には渡さない。設計根拠は [ADR-0024](docs/adr/ADR-0024-specout-ripple-trace.md)）。`verify-sweep` は検証スイープ（全シンボルの再検索と、波紋調査の帳簿〔確定ファイル・判定で関係なしとしたファイル〕との突き合わせ。資料にしたかは問わない）を行い、未記録ヒットがあれば終了コード 7（`specout_verify_counts.py` の件数不一致〔終了コード 3〕とは別）で終了する（SKILL は止めずに SPO §9 に記録する）。`assemble-spo` は、`--layout-only --only seed-direct --max-files N` で台帳と追加下調べの対象による成長型の配置判定・統合→分割の移し替えを行って追加下調べの書き先（`file_outputs`）を返し、指定なしでは台帳のファイルだけで配置を判定して（資料の無いモジュールに `modules/` を作らない）、統合パスの追加下調べの下書きの差し込み、資料のある各モジュール資料の「波紋調査の結果」節（最大30行）、SPO サマリーのスクリプトが書く欄（§1・§1.x 調査の打ち切り・§5.0 波紋調査の要約〔最大30行〕・§5.1・§5.2・§5.5 のテスト可能性・§8・§9）、SPO とモジュール資料の版の確定を書き、`metrics.jsonl` に `specout_doc_summary` を追記する。`assemble-spo`・`doc-targets`・`ripple-summary`・`funcmap-counts` は `--repo-dir` で採用した調査の合算を使う（採用した調査が0件の repo は台帳だけから組み立てる）。調査の記録 `ripple/runs.json` は `run-add`／`run-adopt`／`run-unadopt`／`run-remove`（`ripple/_removed/` へ退避）／`run-list` が扱い、`finish-record`／`finish-needed` が SPO の仕上げの完了と採用した調査の集合を記録・照合し、`ripple-digest` が調査1つの上限つきの要約（方式検討エージェント向け）を書く（[ADR-0025](docs/adr/ADR-0025-specout-ripple-runs.md)）。document agent に渡す ENTRY_POINTS（`doc_entry_points`。今回の指定・`work/doc-entry-points.json` の累積・クロスリポジトリ伝播のシンボルの和集合）と入力の指紋（`inputs_fingerprint`・`inputs_changed`）を返す。`commit-assemble-inputs` は document agent の成功の後に指紋を `work/assemble-inputs.json` に保存する（入力が変わらない再実行では document agent を起動しない。指紋は依頼調査の記録 `work/doc-request-log.md` も含む）。依頼調査（`/xddp-investigate document`・`suggest`）は、`doc-request`（対象のファイル・ディレクトリ・モジュール名を資料にするファイルへ展開し、モジュール単位のバッチを決める。`--append-file` で資料のあるファイルへの追記。`pattern_overridden`・`concerns`〔名前の一致のみ・追加下調べが関係なしと判断〕を返す。`module-assignments.json` は書かない）・`doc-suggest`（資料の無いモジュールの候補）・`assemble-spo --layout-only --only requested --files-file`（書き先の決定）・`doc-append-check`（`snapshot`／`verify`／`restore`／`discard`。追記が決まった節と変更履歴の表だけに入ったかを検査し、満たさなければ元に戻して exit 3）・`doc-request-record`（依頼調査の記録 `work/doc-request-log.md`）が担う。`assemble-spo --exclude` は台帳の工程 `依頼調査` の行のうち除外パターンに一致するファイル（`pattern_override_files`）を §5.5・影響の一覧から外し、統合パスの下書きは抜き出し元の節の SHA-256 を `work/module-drafts/.source-sha256.json` に記録して、抜き出しの後に §2.A… が変わっていれば差し込み・移し替えを止める（exit 1）。`finish-needed` は台帳・依頼調査の記録の変化も検知する（`reason_code` `docs-changed`）。`doc-targets --auto-assign` は、どのモジュールにも属さないファイルを親ディレクトリへ機械的に割り当てる（SPO の仕上げのみ。設計根拠は [ADR-0020](docs/adr/ADR-0020-specout-doc-digest-and-review.md)。2層の出力・追加下調べ・波紋調査なしの経路は [ADR-0023](docs/adr/ADR-0023-specout-two-layer-output.md)）。`search` は投入シンボル（Wave 0 は初期シンボル全件、Wave 1 以降は `--entry-point-symbols` で渡された人由来のシンボルのみ）のうち母体にヒットしなかったものを検出し、discovery-log の「## 未ヒット投入シンボル（Wave N）」へ波ごとに冪等に記録する（非ブロッキング。生ヒット0件とフィルタ後0件を区別する）・ヒット過多の投入シンボル検出（未ヒット検出と同じ対象集合のうち、ヒットしたファイル数が `SPECOUT_MAX_FILES_PER_MODULE` を超えた〔多数のファイルにヒットした。LLM 分類に回るヒットは代表行に縮退される〕シンボルを discovery-log の「## ヒット過多の投入シンボル（Wave N）」へ波ごとに upsert し、`search` の stdout へ`noisy_seed_symbols`／`all_seeds_noisy` として返す。非ブロッキング）・予算で打ち切った投入シンボル検出（1波の予算に収まらず丸ごと打ち切った投入シンボルを discovery-log の「## 予算で打ち切った投入シンボル（Wave N）」へ upsert し、stdout へ `budget_truncated_seed_symbols`／`all_seeds_budget_truncated` として返す。非ブロッキング）・投入シンボルが0件（1波もコミットしていない状態で frontier が空）のときは `search` が終了コード 4 で終了。`write-seed-candidates` は discovery-setup が渡した由来別のシンボルと根拠の JSON（`work/seed-input.json`）からシード候補表（`work/seed-candidates.md`）を決定的に書く（採否は常に ☑。同一シンボルは `ENTRY_POINTS ＞ CRS SP項目 ＞ 下調べ ＞ 母体コードから補完 ＞ 継承展開` で1行に畳む。`--append` は人が編集済みの既存行を変えずに足りない行だけを追記し、採否 ☐ の ENTRY_POINTS を返す。同じ入力の `unsupported_patterns` から grep 未対応パターンの記録（`work/seed-unsupported.json`。`--unsupported-out`）も書く（`location` の全角 `（` 以降は `note` へ分け、`(pattern, location)` で重複を除いて注記を連結する。`--append` は既存の要素を変えずに足りない要素だけを追加する。書き出しは検証をすべて済ませた後で、exit 1 ではどちらのファイルも変更しない））。`seed-preview` はシード候補表（`work/seed-candidates.md`）の採用シンボルを `search` と同じバックエンド・フィルタで試算し、「ヒット（ファイル数）」「警告」（未ヒット／フィルタ後0件／ヒット過多／予算超過）列を書き換え、`--wave-hit-budget` 指定時は採用シンボルの合計ヒット数の注記行（予算超過なら分割実行の案内。`--slice-engine slice` ならシードが書くグローバルを試算に含まない旨も）を候補の表の直前に書く（状態ファイルは作らない。`--ledger` 指定時は台帳の工程 `下調べ` の行からモジュール数・ファイル数を数え、台帳の整合も検査する）。`init --seed-candidates` は候補表の採用行から初期シンボルと `entry_point_symbols` を作り、由来テーブル「## 投入シンボルの由来」の全9行を候補表から決定的に書く（`--symbols`／`--entry-point-symbols` とは排他）。`init --unsupported-patterns` は discovery-setup が見つけた grep 未対応パターン（`work/seed-unsupported.json`）を記録する。`doc-targets` は `bfs-state.json` と文書化済みファイル台帳（`work/documented-files.md`。工程は `下調べ`／`追加下調べ`／`依頼調査`）の集合演算で、台帳に無い確定ファイル（`doc_targets`。`--only seed-direct --max-files N --gap-reviewed …` では追加下調べの対象＝シードの直接参照のうち台帳にも判断の記録にも無いファイルを、repo ごとの累計の上限 N の残りまで同一性 `resolved` → シードのヒット行数の多い順 → パスの順に採り、残りを `over_limit_files` に返す）・下調べ済みの確定ファイル・確定しなかった下調べ済みファイル・モジュールの割り当て（台帳のモジュールディレクトリへのディレクトリ境界での最長前方一致）・モジュール別ファイル数・現在の配置を返し、累積観察メモ（`work/observation-memo.md`）から孤立行を除去する（台帳・観察メモの不整合は exit 1、`work/module-assignments.json` の不正は exit 5）。`prelim-metrics` は下調べの効果測定値（`prelim_summary`。下調べが文書化したファイル数・シード候補の採否・人の追加/除外数・波紋調査だけが見つけたファイル数等）を初回の波紋調査完了時に1回だけ `metrics.jsonl` へ追記する（予算超過の採用数 `adopted_over_budget_count`・採用シンボルの合計ヒット数 `adopted_total_hits` を含む）。 | `/xddp-04-specout` Step A（Step A-Seed・波ループ）, `/xddp-04-specout` Step A-Document（SPO の仕上げ）, `/xddp-04-specout` Step A2, `/xddp-investigate`, `/xddp-05-arch`（Step A-ripple・Step C）, `xddp-common/procedures/`（ripple-*・specout-finish） |
| `xddp-04-specout/scripts/merge_classification.py` | チャンク並列 classification の検証・結合（line_id 欠落/重複/未知値検出・チャンク単位の line_id 集合照合による stale チャンク検出・grep未対応パターンの重複集約・チャンク mtime 収集による実効並列度の裏付けと再利用波検出）。並列起動された classifier サブエージェントの出力を `commit-wave` の入力契約と同一の単一配列へ結合する（[ADR-0010](docs/adr/ADR-0010-specout-parallel-classification.md)） | `/xddp-04-specout` Step A, `xddp-common/procedures/`（ripple-*） |
| `xddp-04-specout/scripts/specout_verify_counts.py` | discovery-log.md の件数一致検証（生=記録+dedup除外+フィルタ除外+noise-collapse除外で突合。「フィルタ除外」には保守的フィルタに加え、1波の予算〔`hit-budget`／`llm-budget`〕で除いた件数を含む。判定の値は英語のコード〔`✅ excluded(…)`／`⚠️ mismatch(…)`／`➖ discarded(case-a)`〕。specout_bfs.py導入後も独立回帰チェックとして併用。`commit-wave` の自己検証がメモリ上のデータを見るのに対し、本スクリプトは書き出されたログのテキストを見るため、ログ書き出し自体の欠陥を検出できる。`--wave all` で全波一括検証、`--strict` で不一致時 exit 3） | `/xddp-04-specout` Step A, `xddp-common/procedures/`（ripple-*） |
| `xddp-04-specout/scripts/specout_slice.py` | 波紋調査のヒット判定エンジン（`probe`／`seed-summary`／`classify`）。`search` が書いたスライス用チャンク（C / C++ / Python のヒット）を LLM を使わずに判定する。判定エンジンは `bfs-state.json` の `slice_engine`（`init` が保存）で決まり、`slice`＝tree-sitter による関数内の静的スライス（影響が関数の外へ出る経路を求め、呼び出し元・グローバル変数の読み手・関数の外の値〔マクロ名・初期化した変数名・代入先〕を次の波のシンボルにする）、`rule`＝標準ライブラリのみ（コメント・文字列・goto のラベル名・プロトタイプ宣言の引数名を偽陽性とし、それ以外はヒット行を含む関数を次の波のシンボルにする）。`seed-summary` はシード関数の副作用の要約と、シードが書くグローバルを求める。リンケージによる名前の解決〔static・`extern`・ヘッダ。書き込み先は書き込んだ関数のファイルから見える宣言で解決し、内部リンケージは `name[FILE:path]`、見える宣言の無い名前は呼び出し元へ伝播する〕・呼び出し先の要約は呼び出し元のファイルから呼べる定義だけで作る・変数のシンボルのヒット側の除外〔`member-name`・`shadowed-local`・`param-name`・`other-static`・`other-class`。`false-positive` にする〕・同一性の印〔classification の `identity`・`next_symbol_kinds`・`name_only_symbols`〕・C++ のクラス単位の同一性〔メソッド・メンバー変数を `name[CLASS:X]` で送り〔メンバー変数はヒットした関数の中の直接の書き込みからだけ。`this` を省いたメソッドの呼び出しも呼び出し元の `out(this)` にする〕、ヒットの受け手のクラスを修飾・`this`・宣言の型〔型の別名を解決〕から決める。兄弟・無関係のクラス・リポジトリの外の型〔`std::` 等〕の受け手と、メソッドのエントリの変数・引数の名前の出現は `other-class`、基底クラスの virtual は動的ディスパッチとして関係あり、決められなければ `name-only`。呼び出し先の要約はクラスごと。設計根拠は [docs/adr/ADR-0022-specout-cpp-class-identity.md](docs/adr/ADR-0022-specout-cpp-class-identity.md)〕。関数ポインタ経由の呼び出し・デストラクタ・演算子オーバーロードは grep 未対応パターンとして返す。C/C++ の前処理（判定エンジンが `slice` のとき、リポジトリのオブジェクト形式のマクロのうち、宣言を飾るマクロ・名前空間マクロを同じ行の中で置き換える。プリプロセッサ指令の行・コメント・文字列の中は対象外。マクロの表は `specout_macros.py` が作り、置き換えた数は `init` が state の `preprocess` と discovery-log の「## 探索設定」に書く。置き換えたマクロ自体へのヒットは `file-scope`〔`neutralized-macro`〕。文のループマクロの書き換えは引数が1行に収まるものに限り、コンストラクタ等を書き換えない）。構文解析の誤りで言語の予約語が含む関数・次の波のシンボルになった箇所は送らず、grep 未対応パターン `parse-artifact` として返す。tree-sitter は任意（`requirements-slice.txt`。`SPECOUT_SLICE_PYTHON_BIN` の Python で実行）。終了コード 0=成功／1=実行時エラー／2=使用法エラー／5=判定エンジンが使えない（state が `slice` なのに tree-sitter を import できない）。書き込むのは `--out` のファイルだけ（設計根拠は [ADR-0019](docs/adr/ADR-0019-specout-static-slicer.md)） | `/xddp-04-specout` Step 0.55・Step A-Seed・波ループ（a のシード要約の取り込み・b-0）, `xddp-common/procedures/`（ripple-*） |
| `xddp-04-specout/scripts/specout_log_values.py` | discovery-log に書く英語の値（伝播種別・派生元・実行コマンドの種別・件数一致検証の判定・同名 MEDIUM 重複ログのケースと処置・打ち切り記録の理由）の定数と、件数一致検証の判定の文字列を作る書式関数だけを持つモジュール（サブコマンドなし・標準ライブラリのみ。件数の照合は各スクリプトが別々に行う） | `specout_bfs.py`, `specout_verify_counts.py`（import） |
| `xddp-04-specout/scripts/specout_macros.py` | C/C++ のマクロの事前走査と種類の判定（オブジェクト形式のマクロのうち、すべての定義が宣言を飾るマクロ〔`inline`・`__attribute__((…))` 等だけ〕または名前空間マクロ〔`namespace X {` / `}` だけ。同じ側・同じ段数〕に当たるもの、および空の定義を持つ構造を開く側・閉じる側の組〔`export {`／`}`・`try`／`catch (…) {…}` 等。両方の空の定義・空でない定義がそれぞれ同じファイルの同じ条件コンパイルの枝にあるもの。両方を空にする〕）・置き換え（同じ行の中だけ。プリプロセッサ指令の行・コメント・文字列の中は対象外）・字句の走査・C/C++ の拡張子と言語の対応（`C_CXX_EXT_LANG`・`c_cxx_lang`）だけを持つモジュール（サブコマンドなし・標準ライブラリのみ） | `specout_slice.py`, `specout_bfs.py`（import） |
| `xddp-06-design/scripts/chd_sp_coverage.py` | CRS×CHD のトレーサビリティマトリクス SP カバレッジ照合（欠落 SP-ID 検出） | `/xddp-06-design` Step A2 |
| `xddp-common/scripts/crs_ur_scope.py` | CRS Markdown から指定 UR の見出しサブツリー＋概要＋TM該当行を抽出（AIレビュー時に CRS 全文の代わりに渡し、レビュアーへの入力サイズを UR 単位に絞り込む） | `/xddp-06-design` Step B, `/xddp-feedback` Step 1-code-d |
| `xddp-md2excel/scripts/crs_md2excel.py` | CRS Markdown → USDM 形式 Excel 変換（`openpyxl` 依存。`MD2EXCEL_PYTHON_BIN` 参照） | `/xddp-md2excel`, 「## Regenerate CRS Excel」 |
| `xddp-excel2md/scripts/excel_dump.py` | Excel の全セルをタブ区切りテキストとして標準出力にダンプ（`openpyxl` 依存。`MD2EXCEL_PYTHON_BIN` 参照） | `/xddp-excel2md` |
| `xddp-crs-view/scripts/crs_view.py` | CRS Markdown を HTML ビューア／CLI ツリーへレンダリング（`crs_model.py` を共有利用。標準ライブラリのみで動作し `openpyxl` 不要） | `/xddp-crs-view` |
| `xddp-common/scripts/xddp_vcs.py` | VCS 抽象層（detect / branch / commit / revert / status）。VCS 種別ごとの関数群＋ディスパッチ構成 | `/xddp-07-code` Step -1、`/xddp-08-verify` Step -1、「## VCS Commit If Dirty」、`/xddp-close` Step C-Pre |
| `xddp-close/scripts/promote.py` | latest-specs→DOCS_DIR の成果物昇格コピー・削除伝播検出・AI_INDEX.md 全7セクション upsert・lessons-learned/CRS/TSP/TRS/project-rulebook/improvement-backlog の昇格・cross破壊的変更検出 | `/xddp-close` Step C2〜C7 |
| `xddp-common/scripts/xddp_verify_tools.py` | `VERIFY_LINT_COMMAND`/`VERIFY_BUILD_COMMAND`/`VERIFY_TYPECHECK_COMMAND` で指定された lint/build/型検査コマンドを REPO を cwd として実行し、終了コード（0=全PASS／1=いずれか非0終了・タイムアウト含む／2=使用法エラー・内部例外）で PASS/FAIL を機械的に判定して結果レポート（Markdown）を生成する。タイムアウト時はプロセスグループ全体を強制終了する（[ADR-0015](docs/adr/ADR-0015-verify-real-tool-execution.md)） | 「## Run Verification Tools」（`/xddp-07-code` Step B, `/xddp-08-verify` Step A, `/xddp-10-test-run` b-1） |

### SPO（スペックアウト文書）のセクション構成

`/xddp-04-specout` が生成するサマリー SPO（`SPO-{CR}.md`）は以下のセクション構成を持つ。

| セクション | 内容 | 必須条件 |
|---|---|---|
| Section 2 | 全体アーキテクチャ図（影響モジュール間の依存図） | 常時 |
| Section 3 | モジュール間シーケンス図 | Wave 0 シンボルがモジュール間呼び出しに関与する場合（SPECOUT_SEQUENCE_LEVELS 設定に関わらず）。⚠️ 判定は Wave 0 直接ファイルの親ディレクトリのみを参照するヒューリスティックのため、Wave 1 以降を経由するモジュール間呼び出しは検出されない場合がある |
| Section 4.1 | 外部副作用一覧（DB書き込み・外部API・イベント発行等） | 常時。副作用なし場合は「副作用なし」と明記 |
| Section 4.2 | データフロー図（DFD） | Section 4.1 に副作用ありエントリが 1 件以上ある場合。外部エンティティ（入力源）→プロセス→データストア/外部システムの全体フローを記載。入力源が未観察の場合は「外部呼び出し元（詳細未調査）」を明示 |
| Section 4.3 | データモデル（エンティティ関連図・データ構造定義） | `SPECOUT_DIAGRAM_LEVEL = full` の場合のみ生成。複数モジュール SPO のデータモデルをマージして統合記録。`latest-specs/overview/data-model.md` の生成元となる |
| Section 4.4 | データアクセスマトリクス（CRUDマトリクス・Read/Writeマトリクス） | `SPECOUT_DIAGRAM_LEVEL = full` の場合のみ生成。複数モジュールのアクセス操作を行単位でマージして統合記録。`latest-specs/overview/crud.md` の生成元となる |
| Section 5.1〜5.4 | 影響分析（直接影響・間接影響・影響なし・エラーパス） | 常時 |
| Section 5.5 | テスト可能性（プロダクションコードの構造の観察。テストコードは調べない。依頼調査で名指ししたテストコード等も載せない） | 常時。DI可能/密結合/シングルトン/未確認 から選択（複数混在はスラッシュ列挙） |
| Section 5.6 | 非機能特性・実装制約の観察（パフォーマンス感度・並行性・後方互換性等） | 常時。観察なし場合は「観察なし」と明記 |
| Section 5.7 | 既知制約（code-knowledge）との照合 | DOCS が設定され、確定ファイルが属するモジュールに constraints.md が存在する場合のみ生成。それ以外は「対象外」と明記 |
| Section 6 | 機能ソースコード対応表（`SPO-{CR}-funcmap.md` へのリンク） | 常時。表本体は `SPO-{CR}-funcmap.md` に独立して格納。シグネチャ概略・直接呼び出し元数・影響種別を含む（アーキテクト方式比較用） |
| Section 7〜9 | CRS フィードバック候補・モジュールファイルリンク・気づきメモ | 常時 |

各モジュール SPO（`modules/{module-name}-spo.md`）の Section 4 は `SPECOUT_DIAGRAM_LEVEL` 設定に従うが、
Wave 0 シンボルを含む HIGH 確信度モジュールは設定に関わらず以下を強制生成する:

| フラグ | 強制生成セクション |
|---|---|
| HAS_VAR_CHANGE（変数・フィールド変更） | Section 4.3（データ構造） |
| HAS_STRUCT_CHANGE（クラス・型変更） | Section 4.2（クラス図） |
| HAS_FUNC_CHANGE（関数・メソッド変更） | Section 4.5（モジュール内シーケンス図） |

## サブエージェント一覧

各フェーズのスキルから自動的に呼び出されます。直接呼び出す必要はありません。

| エージェント | 役割 |
|---|---|
| `xddp-analyst-agent` | 要求分析メモ（ANA）生成（工程2） |
| `xddp-spec-writer-agent` | 変更要求仕様書（CRS）作成・更新（工程3・4b）。arch/design/test成果物からのフィードバック反映（工程5・6b、`xddp-feedback`）も担う |
| `xddp-specout-prelim-agent` | スペックアウトの下調べ（工程4a Step A-Prelim）。CRS から変更対象の振る舞いを実装する母体コードを推論して読み、SPO サマリー・モジュール別ファイル（波紋調査に依存する節を除く）と根拠付きの Wave 0 シード候補（`work/prelim-index.md`）を書く。`work/bfs-state.json` が無い repo でのみ discovery-setup の前に起動される。SPO の仕上げ（Step A-Document）では `PRELIM_MODE: additional` で repo ごとに1回起動され、シードが直接参照するのに下調べの資料に無いファイルを読んで資料に追記する（追加下調べ。関係しないファイルは `work/prelim-gap-reviewed.md` に記録する） |
| `xddp-specout-agent` | スペックアウトの discovery-setup（工程4a）。下調べのシード候補・CRS のコード表記・ENTRY_POINTS から Wave 0 のシード候補表（`work/seed-candidates.md`）を作る。`init`（BFS state 初期化）と波ループ本体は `xddp-04-specout/SKILL.md` が実行する |
| `xddp-specout-document-agent` | スペックアウトの SPO の仕上げ（工程4a Step A-Document）。repo ごとに1回起動され、ソースを読まず、SPO サマリー（§5.0 等のスクリプトが書いた欄を含む）・資料のあるモジュールの資料・funcmap の機械算出値から、SPO サマリーの LLM が書く欄（§2〜§4・§5.3・§5.4・§5.6・§5.7・§7）と funcmap を書く。モジュール資料は書かない（下調べ・追加下調べが書く）。入力が前回の成功時と変わらない再実行では起動されない。文書化手順は `xddp-04-specout/module-documentation.md` を下調べエージェントと共有する |
| `xddp-specout-classifier-agent` | Discovery BFS の1チャンク分のヒット行を意味判定（工程4a）。受け取るのは関数の範囲を決定的に取れない言語（C / C++ / Python 以外）のヒットだけで、C / C++ / Python のヒットは `specout_slice.py` が LLM を使わずに判定する。波ごとに `xddp-04-specout/SKILL.md` が並列起動する（LLM 分類に回るヒットが無い波では起動しない） |
| `xddp-architect-agent` | 実装方式検討・アーキテクチャメモ（DSN）作成（工程5） |
| `xddp-design-sync-agent` | コードと既存 DSN を読み、DSN を再生成してリビジョンファイルを出力する（`xddp-sync-design`、工程対象外・随時実行） |
| `xddp-designer-agent` | 変更設計書（CHD）作成（工程6a） |
| `xddp-chd-sync-agent` | コードと既存 CHD（該当バッチファイル）を読み、そのSP範囲の CHD 内容を現在のコード実装に合わせて直接更新する（`xddp-feedback` DOC_TYPE=code、工程対象外・随時実行） |
| `xddp-coder-agent` | CHDに基づくコーディング（工程7） |
| `xddp-verifier-agent` | コーディング後の静的検証・コードレビュー（工程8）。設計適合性・コード品質・セキュリティ・バグリスクを検証する |
| `xddp-test-writer-agent` | テスト仕様書（TSP）生成（工程9） |
| `xddp-test-runner-agent` | テスト実行・不具合修正（工程10a〜10c） |
| `xddp-specs-mod-agent` | SPO + CHD からモジュール別最新仕様書を生成・更新する（工程11 Step MOD） |
| `xddp-specs-uc-agent` | CRS UR からユースケース（`system/use-cases/`）を生成・更新する（工程11 Step UC） |
| `xddp-close-knowledge-agent` | project-rulebook upsert と code-knowledge 昇格を担当する（`xddp-close` Step C3.5・C3.6） |
| `xddp-reviewer` | 任意成果物の単体AIレビュー |

## プロジェクト固有ファイル

`/xddp-01-init` 実行時に対象プロジェクトのルートに生成されるファイルです。

| ファイル / ディレクトリ | 生成タイミング | 説明 |
|---|---|---|
| `{CR}/` | `/xddp-01-init` | CRワークスペース。`01_requirements/` 〜 `10_test-results/`・`review/` の工程別フォルダを含む。 |
| `{CR}/progress.md` | `/xddp-01-init` | 各工程の進捗・状態・次コマンドを記録する進捗管理ファイル。各スキルが自動更新する。 |
| `project-rulebook.md` | `/xddp-01-init` | プロジェクト固有の命名規約・アーキテクチャ決定・既存パターン・ドメイン制約（1.6）を記録するAI参照ファイル。工程2（要求分析）・工程4（specout）開始前に記入することで工程2・5・6の成果物品質が上がる。なくても動作するが、記入推奨。マルチリポジトリの場合は「1.5 リポジトリ構成」セクションも記入する。 |
| `xddp.config.md` | `/xddp-01-init` | specout粒度・波紋調査前のシード確認の有無（`SPECOUT_SEED_GATE`。既定 `true`＝人が候補表と repo ごとの波紋調査の要否を確定するまで待つ。`false` は確認せず全 repo で波紋調査を行う）・波紋調査の波数上限（`SPECOUT_MAX_WAVE_DEPTH`。既定 `6`＝探索の起点の波から数えて6波。上限に達したら打ち切り記録を残して自動完了し、上げて再実行すると続きから探索する）・1波のヒット予算と LLM 分類の上限（`SPECOUT_WAVE_HIT_BUDGET`。既定 `10000`／`SPECOUT_LLM_HIT_BUDGET`。既定 `160`）・変更の中心として扱うファイル数の目安（`SPECOUT_MAX_AFFECTED_FILES`。既定 `20`。シードの直接参照ファイル数がこれを超えたら CR の分割を推奨する警告を出し、追加下調べも repo ごとの累計でこの件数まで）・判定エンジン（`SPECOUT_SLICE`＝`auto`/`off`・`SPECOUT_SLICE_IGNORE_CALLS`・`SPECOUT_SLICE_H_AS`・`SPECOUT_SLICE_PYTHON_BIN`）・参照解決バックエンド（`SPECOUT_BACKEND`。既定 `auto`＝識別子索引 `index`）・AIレビュー最大回数・テストフレームワーク・テストケース粒度・カバレッジ閾値などの設定ファイル。マルチリポジトリ構成の場合は `REPOS:` セクションにリポジトリ名とパスを定義する。 |
| `latest-specs/` | `/xddp-01-init` | `/xddp-11-specs` で生成された最新仕様書の格納先（ドラフト領域）。Kruchten 4+1 ビューモデルに基づいた多階層ディレクトリ構造（下記参照）。初回 specout 時は空でよい。 |
| `latest-specs/{repo}/{module}/` | `/xddp-11-specs` | モジュール機能仕様（spec.md・state-machine.md・structure.md・sequences/）。Logical View に対応。 |
| `latest-specs/{repo}/overview/` | `/xddp-11-specs` | リポジトリ全体ビュー（architecture.md・data-model.md・crud.md・dfd.md・sequences/）。Development View / Process View に対応。 |
| `latest-specs/cross/interfaces/{if}/` | `/xddp-11-specs` | クロスリポジトリインタフェース仕様（spec.md・schema.md）。マルチリポジトリのみ生成。 |
| `latest-specs/cross/sequences/` | `/xddp-11-specs` | クロスリポジトリシーケンス図。Process View（クロス）に対応。 |
| `latest-specs/system/use-cases/{uc}/` | `/xddp-11-specs` | ユースケース記述（description.md・sequences/）。Use Case View (+1) に対応。CRS に UR がある場合に生成。 |
| `docs/specs/` | `/xddp-close` | 人レビュー済みの承認済み仕様書の格納先。`latest-specs/` から昇格されたファイルが置かれる。 |
| `improvement-backlog.md` | `/xddp-close` | 改善バックログ。各工程の「気づき・提案メモ」のうち今回対応しなかったものを `IDEA-NNN` エントリとして蓄積する。 |
| `lessons-learned.md` | `/xddp-close` | 知見ログ。CR全体を通じて得た教訓を `LL-NNN` エントリとして記録し、次のCR以降に活かす。 |

### VCS設定

`xddp.config.md`「## 6. バージョン管理設定」で以下のキーを指定できます。

| キー | デフォルト | 説明 |
|---|---|---|
| `VCS_TYPE` | `auto` | バージョン管理システム（`auto`/`git`/`none`。Git 以外の VCS を使う場合は `none` を指定する） |
| `VCS_BRANCH_PREFIX` | `feature/` | 自動生成ブランチ名の接頭辞（Git のみ） |
| `VCS_BASE_BRANCH` | `auto` | 新規作業ブランチの起点 ref（`auto`=リモート既定ブランチ／`main`／`master`の順で解決。Git のみ） |
| `VCS_AUTO_BRANCH` | `true` | 工程7開始時に作業ブランチを自動作成するか（Git のみ） |
| `VCS_COMMIT_ON_STEP` | `7,10` | 自動コミットする工程番号（カンマ区切り。`none` で無効。Git のみ） |

## マルチリポジトリ対応

複数リポジトリにまたがる変更要求（マイクロサービス構成など）に対応しています。

### セットアップ

**1. `xddp.config.md` の設定**

```yaml
REPOS:
  api: ../tasksaas-api
  worker: ../tasksaas-worker
  notify: ../tasksaas-notify
  shared: ../tasksaas-shared
```

パスは `xddp.config.md` からの相対パスまたは絶対パスで指定します。
リポジトリ名（左辺）は CHD・SPO の `リポジトリ:` フィールドや変更対象ファイル一覧で使用される識別子になります。

テストフレームワークをリポジトリごとに個別指定することもできます：

```yaml
TEST_FRAMEWORK_REPOS:
  api: pytest
  worker: pytest
  notify: pytest
  shared: pytest
```

**2. `project-rulebook.md` の設定**

「1.5 リポジトリ構成」セクションにリポジトリ一覧・依存関係・共有インタフェースを記入します。
`xddp.config.md` の `REPOS:` のリポジトリ名と一致させてください。

### 動作

| フェーズ | マルチリポジトリ時の動作 |
|---|---|
| `/xddp-04-specout` | 各リポジトリの波紋調査（Discovery BFS）は独立に実行される。全リポジトリの調査完了後、`Step A-cross` が共有インタフェース（他リポジトリへ提供される関数・変数等）を意味判定し `cross/SPO-{CR}-cross.md` に記録する。`SPECOUT_CROSS_PROPAGATE`（既定: 有効）が有効な場合、識別された共有インタフェースについて `Step A-cross-propagate` が消費リポジトリ側に1ラウンドのみ新しい波紋調査（`cross-{提供 repo}-{n}`）を作って採用する（`cross/work/cross-propagation-targets.json`／`cross-propagation-log.json` を介して機械的に対象を管理。再実行をまたいでも連鎖的な追跡（A→B→C→…）はしない） |
| `/xddp-07-code` | CHD の各 Before/After ブロックの `リポジトリ:` フィールドを読み取り、実際のリポジトリパスを解決してコードを適用する |

---

## ファイル構成

```
ClaudeCode/
├── setup.sh               ← セットアップスクリプト
└── .claude/               ← ~/.claude にコピーされる（CLAUDE.md を除く）
    ├── settings.json      ← グローバル設定
    ├── agents/            ← サブエージェント定義（20種）
    └── skills/            ← フェーズ実行ロジック＋スラッシュコマンド（28種。うち `xddp-common` は user-invocable: false）
        ├── xddp-templates/ ← XDDP成果物ひな形・スキル作成ひな形（SKILL.mdなし）
        ├── xddp-rules/     ← XDDP規約・ルール文書（SKILL.mdなし）
        ├── xddp-md2excel/
        │   └── scripts/    ← crs_md2excel.py（xddp-md2excel専用）
        └── xddp-crs-view/
            └── scripts/    ← crs_view.py（xddp-crs-view専用）
docs/
├── REQ-2026-001_要求書.md   ← このリポジトリ自体の要求書
└── adr/                    ← XddpSettings自身の設計判断記録（ADR）。setup.shの非デプロイ対象
```
