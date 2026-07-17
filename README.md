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
/xddp.01.init REQ-2026-001 "モジュール間送信データへの付帯情報追加" path/to/要求書.md
/xddp.02.analysis REQ-2026-001
/xddp.03.req REQ-2026-001
/xddp.04.specout REQ-2026-001
/xddp.05.arch REQ-2026-001
/xddp.06.design REQ-2026-001
/xddp.07.code REQ-2026-001
/xddp.08.verify REQ-2026-001
/xddp.09.test REQ-2026-001
/xddp.10.test-run REQ-2026-001
/xddp.11.specs REQ-2026-001
/xddp.close REQ-2026-001
```

> 要求書ファイル（3番目の引数）は省略できます。省略した場合、`REQ-{CR}.md` はテンプレートに文書番号・タイトル・作成日を自動記入した状態で配置されるので、内容を編集してから次のコマンドに進んでください。引数を一切指定しない場合は、CR番号・タイトル・要求書ファイルパスをAIが対話的に質問します。

各コマンドは AI が成果物を生成→自動レビュー→人レビューゲートの順で進みます。

### 進捗確認

```
/xddp.status REQ-2026-001
```

### ツール自体（スキル・エージェント）を修正したときの動作確認

修正箇所に応じた確認手順は [docs/xddp-tool-verification-checklist.md](docs/xddp-tool-verification-checklist.md) を参照。

### スペックアウト（波紋検索）の詳細仕様

Discovery BFS の検索対象決定方法・中断耐性・コンテキスト管理の詳細は [docs/specout-discovery-guide.md](docs/specout-discovery-guide.md) を参照。

### 人が成果物を直接編集した後に AI レビューしたい場合

```
/xddp.review REQ-2026-001 <ドキュメント種別>
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
/xddp.review REQ-2026-001 design
```

レビュー結果は `{CR}/review/` に出力されます。  
指摘事項を反映する場合は `/xddp.revise` を使います（`spec` は対象外です。`latest-specs/` 配下の
ファイルを直接編集してください）。

### レビュー指摘を成果物に反映したい場合

```
/xddp.revise REQ-2026-001 <ドキュメント種別> [ID,ID,...]
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
修正後に再度レビューする場合は `/xddp.review` を実行してください。

### フェーズ一覧

| コマンド | 引数 | 内容 | 生成する主な成果物 |
|---|---|---|---|
| `/xddp.01.init` | `CR番号 タイトル [要求書.md]` | CRワークスペースを初期化し、成果物フォルダ・`progress.md`・テンプレートから生成した要求書（`REQ-{CR}.md`）を作成する。要求書ファイルを指定した場合は参照コピーする | `{CR}/`, `{CR}/progress.md`, `{CR}/01_requirements/REQ-{CR}.md`, `xddp.config.md`, `project-rulebook.md` |
| `/xddp.02.analysis` | `[CR番号]` | 要求書を読み込み、UR/SR/SP 分類・曖昧点・実現可能性を含む要求分析メモ（ANA）を生成。AI レビューループ後に人レビューゲートで停止する | `ANA-{CR}.md` |
| `/xddp.03.req` | `[CR番号]` | ANA を元に USDM 形式の変更要求仕様書（CRS）を作成。AI レビューループ後に人レビューゲートで停止する | `CRS-{CR}.md` |
| `/xddp.04.specout` | `[CR番号] [エントリポイント...]` | 母体コードを調査し、変更影響範囲を特定するスペックアウト文書（SPO）を生成。CRS にフィードバックする | `SPO-{CR}.md`, `SPO-{CR}-funcmap.md`, `04_specout/{repo}/discovery-log.md`, `04_specout/{repo}/checkpoint.md`, `CRS-{CR}.md`（更新） |
| `/xddp.05.arch` | `[CR番号] [--detail]` | 実装方式を複数案比較し、推奨方式を決定する実装方式検討メモ（DSN）を生成。AI レビューループ後に人レビューゲートで停止する。`--detail` を指定すると、既存の全案（approach-*.md）に構造体関連図・主処理シーケンス図を統一粒度で追記する | `DSN-{CR}.md` |
| `/xddp.06.design` | `[CR番号]` | DSN を元にBefore/After設計（インタフェース定義・図、実装コードは書かない）の変更設計書（CHD）を作成。AI レビューループ後に人レビューゲートで停止する | `CHD-{CR}.md`（インデックス）＋ `CHD-{CR}-{UR-ID}[-{N}].md`（UR別内容ファイル）, `CRS-{CR}.md`（フィードバック更新） |
| `/xddp.07.code` | `[CR番号]` | CHD に基づいてソースコードを変更し、静的検証（差分・命名・型）を実施する | 実装ファイル群 |
| `/xddp.08.verify` | `[CR番号]` | xddp.07.code の自動検証と同一内容の静的検証を人が任意のタイミングで手動実行する | `VERIFY-{CR}.md` |
| `/xddp.09.test` | `[CR番号]` | テスト仕様書（TSP）を生成し、AI レビューループ後に人レビューゲートで停止する（テスト実行は `/xddp.10.test-run` で行う） | `TSP-{CR}.md` |
| `/xddp.10.test-run` | `[CR番号]` | レビュー確定済み TSP に基づきテストを実行し、不具合修正→TM/CRS フィードバックを実施する | `TRS-{CR}-{NN}.md`（NN=実施回数） |
| `/xddp.11.specs` | `[CR番号]` | CR で変更された仕様を `latest-specs/` に反映・生成する。Kruchten 4+1 ビューモデルに基づいた多階層ディレクトリ構造（system/use-cases, {repo}/overview, {repo}/{module}, cross/interfaces 等）を生成・更新する | `latest-specs/` 配下の各仕様書（spec.md・state-machine.md・structure.md・sequences/・overview/・system/use-cases/ 等） |
| `/xddp.close` | `[CR番号]` | 工程の気づきをバックログへ集約し、知見ログを更新して CR を完了する | `improvement-backlog.md`（更新）, `lessons-learned.md`（更新） |
| `/xddp.status` | `[CR番号]` | CR の現在フェーズと全成果物の状態を一覧表示する | —（参照のみ） |
| `/xddp.review` | `[CR番号] analysis\|req\|specout\|arch\|design\|test\|spec [対象ファイル]` | 人が直接編集した成果物に対して単体 AI レビューを実施する（`spec` は latest-specs 配下のファイルを対象） | `{成果物}/review/*.md` |
| `/xddp.revise` | `[CR番号] analysis\|req\|specout\|arch\|design\|test [repo名] [ID,ID,...]` | 人のレビュー指摘を成果物に反映する | 対象成果物（更新） |
| `/xddp.plan-review` | `[プランファイルパス]` | プランのAIエキスパートレビューと修正を、Criticalと残指摘事項（🟡/🔵）がなくなるまで繰り返す | `plans/review/{PLAN_NAME}-review.md` |
| `/xddp.excel2md` | `[CR番号] [Excelファイル]` | 人が編集した USDM 形式 Excel の変更要求仕様書を Markdown（CRS）に変換する | `CRS-{CR}.md` |
| `/xddp.md2excel` | `[CR番号]` | CRS Markdown から USDM 形式 Excel を生成する | `CRS-{CR}.xlsx` |
| `/xddp.fill-rulebook` | `[repo名 / cross]` | `project-rulebook.md` の未記入セクションをコード調査でドラフト生成し、人が確認後に書き込む（完了時デスクトップ通知）。シングルリポジトリ時は共通 `project-rulebook.md` のみ対象（`{repo}` / `cross` 指定はエラー） | `project-rulebook.md` または `project-rulebook-{repo}.md`（更新） |
| `/xddp.codemap` | `[repo名 \| all]` | モジュールカタログを生成・更新する。モジュール構成・主要シンボル・依存グラフを baseline_docs に保存し、specout の BFS 優先度制御に活用する | `baseline_docs/{repo}/module-catalog.md` |
| `/xddp.update-knowledge` | `[repo名] [constraint\|flow\|callgraph\|lesson\|note]` | CR 非依存で baseline_docs/ の knowledge ディレクトリに知識を登録・更新する。対話形式と引数形式に対応 | `baseline_docs/{repo}/knowledge/` 配下の各ファイル |
| `/xddp.sync-design` | `[CR番号] [変更サマリ（省略可）]` | コードから DSN を再生成してリビジョンとして記録し、AI レビュー→人承認を実施する | `DSN-{CR}-rev{N}.md`、`DSN-{CR}-rev{N}-review.md` |
| `/xddp.feedback` | `[CR番号] arch\|design\|test\|code [repo名]` | arch/design/test 成果物の現在の内容（人が直接編集した内容、または `/xddp.sync-design` 適用後の最新DSNリビジョンを含む）の未反映分を抽出し、人の確認後に CRS（design/code の場合は TM も）へ反映する。`code` の場合はコード差分から該当CHDバッチファイルを先に同期する | `CRS-{CR}.md`（更新）、design/code の場合は `TM-{CR}.md`（更新）、code の場合はさらに対象CHDバッチファイル（直接更新） |

### SPO（スペックアウト文書）のセクション構成

`/xddp.04.specout` が生成するサマリー SPO（`SPO-{CR}.md`）は以下のセクション構成を持つ。

| セクション | 内容 | 必須条件 |
|---|---|---|
| Section 2 | 全体アーキテクチャ図（影響モジュール間の依存図） | 常時 |
| Section 3 | モジュール間シーケンス図 | Wave 0 シンボルがモジュール間呼び出しに関与する場合（SPECOUT_SEQUENCE_LEVELS 設定に関わらず）。⚠️ 判定は Wave 0 直接ファイルの親ディレクトリのみを参照するヒューリスティックのため、Wave 1 以降を経由するモジュール間呼び出しは検出されない場合がある |
| Section 4.1 | 外部副作用一覧（DB書き込み・外部API・イベント発行等） | 常時。副作用なし場合は「副作用なし」と明記 |
| Section 4.2 | データフロー図（DFD） | Section 4.1 に副作用ありエントリが 1 件以上ある場合。外部エンティティ（入力源）→プロセス→データストア/外部システムの全体フローを記載。入力源が未観察の場合は「外部呼び出し元（詳細未調査）」を明示 |
| Section 4.3 | データモデル（エンティティ関連図・データ構造定義） | `SPECOUT_DIAGRAM_LEVEL = full` の場合のみ生成。複数モジュール SPO のデータモデルをマージして統合記録。`latest-specs/overview/data-model.md` の生成元となる |
| Section 4.4 | データアクセスマトリクス（CRUDマトリクス・Read/Writeマトリクス） | `SPECOUT_DIAGRAM_LEVEL = full` の場合のみ生成。複数モジュールのアクセス操作を行単位でマージして統合記録。`latest-specs/overview/crud.md` の生成元となる |
| Section 5.1〜5.4 | 影響分析（直接影響・間接影響・影響なし・エラーパス） | 常時 |
| Section 5.5 | 既存テスト状況（テスト有無 + テスト可能性） | 常時。テスト可能性は DI可能/密結合/シングルトン/未確認 から選択（複数混在はスラッシュ列挙） |
| Section 5.6 | 非機能特性・実装制約の観察（パフォーマンス感度・並行性・後方互換性等） | 常時。観察なし場合は「観察なし」と明記 |
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
| `xddp-spec-writer-agent` | 変更要求仕様書（CRS）作成・更新（工程3・4b）。arch/design/test成果物からのフィードバック反映（工程5・6b、`xddp.feedback`）も担う |
| `xddp-specout-agent` | 母体コード調査・スペックアウト（工程4a） |
| `xddp-architect-agent` | 実装方式検討・アーキテクチャメモ（DSN）作成（工程5） |
| `xddp-designer-agent` | 変更設計書（CHD）作成（工程6a） |
| `xddp-coder-agent` | CHDに基づくコーディング（工程7） |
| `xddp-verifier-agent` | コーディング後の静的検証・コードレビュー（工程8）。設計適合性・コード品質・セキュリティ・バグリスクを検証する |
| `xddp-test-writer-agent` | テスト仕様書（TSP）生成（工程9） |
| `xddp-test-runner-agent` | テスト実行・不具合修正（工程10a〜10c） |
| `xddp-reviewer` | 任意成果物の単体AIレビュー |

## プロジェクト固有ファイル

`/xddp.01.init` 実行時に対象プロジェクトのルートに生成されるファイルです。

| ファイル / ディレクトリ | 生成タイミング | 説明 |
|---|---|---|
| `{CR}/` | `/xddp.01.init` | CRワークスペース。`01_requirements/` 〜 `10_test-results/`・`review/` の工程別フォルダを含む。 |
| `{CR}/progress.md` | `/xddp.01.init` | 各工程の進捗・状態・次コマンドを記録する進捗管理ファイル。各スキルが自動更新する。 |
| `project-rulebook.md` | `/xddp.01.init` | プロジェクト固有の命名規約・アーキテクチャ決定・既存パターンを記録するAI参照ファイル。工程4（specout）開始前に記入することで工程5・6の成果物品質が上がる。なくても動作するが、記入推奨。マルチリポジトリの場合は「1.5 リポジトリ構成」セクションも記入する。 |
| `xddp.config.md` | `/xddp.01.init` | specout粒度・AIレビュー最大回数・テストフレームワーク・テストケース粒度・カバレッジ閾値などの設定ファイル。マルチリポジトリ構成の場合は `REPOS:` セクションにリポジトリ名とパスを定義する。 |
| `latest-specs/` | `/xddp.01.init` | `/xddp.11.specs` で生成された最新仕様書の格納先（ドラフト領域）。Kruchten 4+1 ビューモデルに基づいた多階層ディレクトリ構造（下記参照）。初回 specout 時は空でよい。 |
| `latest-specs/{repo}/{module}/` | `/xddp.11.specs` | モジュール機能仕様（spec.md・state-machine.md・structure.md・sequences/）。Logical View に対応。 |
| `latest-specs/{repo}/overview/` | `/xddp.11.specs` | リポジトリ全体ビュー（architecture.md・data-model.md・crud.md・dfd.md・sequences/）。Development View / Process View に対応。 |
| `latest-specs/cross/interfaces/{if}/` | `/xddp.11.specs` | クロスリポジトリインタフェース仕様（spec.md・schema.md）。マルチリポジトリのみ生成。 |
| `latest-specs/cross/sequences/` | `/xddp.11.specs` | クロスリポジトリシーケンス図。Process View（クロス）に対応。 |
| `latest-specs/system/use-cases/{uc}/` | `/xddp.11.specs` | ユースケース記述（description.md・sequences/）。Use Case View (+1) に対応。CRS に UR がある場合に生成。 |
| `docs/specs/` | `/xddp.close` | 人レビュー済みの承認済み仕様書の格納先。`latest-specs/` から昇格されたファイルが置かれる。 |
| `improvement-backlog.md` | `/xddp.close` | 改善バックログ。各工程の「気づき・提案メモ」のうち今回対応しなかったものを `IDEA-NNN` エントリとして蓄積する。 |
| `lessons-learned.md` | `/xddp.close` | 知見ログ。CR全体を通じて得た教訓を `LL-NNN` エントリとして記録し、次のCR以降に活かす。 |

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
| `/xddp.04.specout` | エントリポイントから波及調査を開始し、他リポジトリへの呼び出しを検出したら `REPOS_MAP` を参照して調査を延長する |
| `/xddp.07.code` | CHD の各 Before/After ブロックの `リポジトリ:` フィールドを読み取り、実際のリポジトリパスを解決してコードを適用する |

---

## ファイル構成

```
ClaudeCode/
├── setup.sh               ← セットアップスクリプト
└── .claude/               ← ~/.claude にコピーされる（CLAUDE.md を除く）
    ├── settings.json      ← グローバル設定
    ├── agents/            ← サブエージェント定義（15種）
    └── skills/            ← フェーズ実行ロジック＋スラッシュコマンド（16種）
        ├── xddp.templates/ ← XDDP成果物ひな形・スキル作成ひな形（SKILL.mdなし）
        ├── xddp.rules/     ← XDDP規約・ルール文書（SKILL.mdなし）
        └── xddp.md2excel/
            └── scripts/    ← crs_md2excel.py（xddp.md2excel専用）
docs/
└── REQ-2026-001_要求書.md   ← このリポジトリ自体の要求書
```
