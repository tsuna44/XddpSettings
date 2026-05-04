# 知識階層構造 レビューメモ

作成日: 2026-04-30  
ステータス: **設計確定中**（実装前確認待ち）

---

## 1. 運用したい全体像（確認済み）

### ワークスペース構造

```
workspace/                    ← VSCode ワークスペースルート
├── repo-A/                   ← 開発リポジトリ（xddp.config.md を置く）
├── repo-B/                   ← 開発リポジトリ
├── docs/                     ← 中央知識ハブ ★ここを育てる（GitHub管理）
└── xddp/
    └── CR-xxx/               ← XDDPの成果物（CR単位）
```

### 役割の分離（2026-04-30 確認）

| フォルダ | 役割 | 備考 |
|---|---|---|
| `repo-A/`, `repo-B/` | 実際のソースコード | 開発リポジトリ（最大10） |
| `docs/` | 中央知識ハブ | 承認済み仕様書・知見を集約。GitHub管理 |
| `xddp/CR-xxx/` | XDDPの作業成果物 | CRS・SPO・CHD等。ワークスペースレベルで共有 |
| XddpSettings | XDDPツール・スキル・設定 | 別リポジトリ。docs/ は知識ハブではない |

### 目的
- `docs/` を GitHub で管理し、新規開発を始めるときに **clone → AI に事前注入** する
- xddp.close 実行時に最新仕様書・知見が `docs/` に蓄積・更新される
- 知識のポータビリティを高め、リポジトリをまたいだ文脈の継続性を確保する
- 開発リポジトリ: 最大10以内、プロジェクトは開発内容により異なる

---

## 2. 現在の docs/ 構造

```
docs/
├── AI_INDEX.md                       ← ルートインデックス
├── ai-knowledge-system-design.md     ← 知識システム設計書
├── xddp-process-dfd.md               ← XDDPプロセスDFD
├── xddp-ai-era-assessment.md         ← AI時代のXDDP適合性評価
├── REQ-2026-001_要求書.md             ← 要求書サンプル
├── cc-sdd-vs-xddp-comparison.md      ← ツール比較
├── four-tools-comparison.md          ← ツール比較
├── github-spec-kit-vs-xddp-comparison.md
├── openspec-vs-xddp-comparison.md
├── shared/
│   ├── AI_INDEX.md
│   └── glossary.md                   ← 共通用語集（中身は空）
└── projects/
    └── _template/                    ← テンプレートのみ（実プロジェクト: 0件）
        ├── AI_INDEX.md
        ├── inter-repo/
        │   ├── repo-map.md
        │   └── dependency-graph.md
        └── repos/
            └── _template/
                ├── AI_INDEX.md
                └── knowledge/
                    ├── lessons-learned.md
                    └── patterns.md
```

---

## 3. 現状と理想のギャップ

| # | ギャップ | 詳細 | 影響 |
|---|---|---|---|
| G-1 | **実プロジェクトが未登録** | `docs/projects/` に実際の開発リポジトリ・プロジェクトが1件も登録されていない | 知識ハブとして機能していない |
| G-2 | **知識流入フローが未定義** | 各リポジトリで `xddp.close` を実行しても知見・仕様書は各リポジトリ内に留まる。XddpSettings/docs/ への集約ルールがない | CRの成果が中央に蓄積されない |
| G-3 | **shared/ が育っていない** | glossary.md の器はあるが中身が空。patterns.md もない | 横断知識が蓄積されない |
| G-4 | **docs/ 内に方法論ドキュメントが混在** | XDDP比較・評価文書などが docs/ 直下に散在し、「知識ハブ」なのか「ツール説明書」なのかが曖昧 | AI注入時にノイズになる可能性 |
| G-5 | **AI注入の入り口が未整備** | clone 後にどのファイルをどう AI に注入するかの手順が定義されていない | 開発開始時の運用が不明確 |

---

## 4. 中央知識ハブ docs/ の構造（設計案）

latest-specs と同じ体系 + lessons-learned を基本とする。

```
docs/                             ← 中央知識ハブルート
├── AI_INDEX.md                   ← AI注入の起点（ナビゲーションインデックス）
├── shared/                       ← 全リポジトリ横断の共通知識
│   ├── glossary.md               ← 共通用語集
│   ├── lessons-learned.md        ← 横断的な知見・教訓
│   ├── design/                   ← 設計時の注意点・ポイント・パターン
│   │   ├── notes.md              ← 設計時の注意点・ハマりポイント集
│   │   └── patterns.md           ← 再利用可能な設計パターン
│   ├── test/                     ← テストパターン
│   │   ├── patterns.md           ← 再利用可能なテストパターン・定型ケース
│   │   └── anti-patterns.md      ← やってはいけないテストの書き方
│   └── inter-repo/               ← リポジトリ間横断情報（手動メンテ）
│       ├── repo-map.md           ← 各リポジトリの責務・オーナー一覧
│       ├── dependency-graph.md   ← リポジトリ間依存グラフ
│       ├── api-contracts/        ← 公開APIスキーマ（OpenAPI等）
│       ├── event-schemas/        ← イベント定義
│       └── design/               ← リポジトリ間設計書（工程別）
│           ├── sequence/         ← リポジトリ間シーケンス図（xddp.04 specout から）
│           ├── dfd/              ← データフロー図（xddp.04 specout から）
│           ├── architecture/     ← リポジトリ間アーキテクチャ設計（xddp.05 arch から）
│           └── interface/        ← リポジトリ間IF変更設計（xddp.06 design から）
└── {repo-name}/                  ← リポジトリ単位（init時に自動作成）
    ├── specs/                    ← 承認済み仕様書（latest-specs と同じ体系）
    │   └── README.md             ← xddp.09.specs → xddp.close で昇格
    └── knowledge/
        └── lessons-learned.md   ← CR横断の知見（xddp.close が追記）
```

### latest-specs との対応

| latest-specs（各リポジトリ内） | docs/{repo}/specs/（中央ハブ） |
|---|---|
| ドラフト（未レビュー） | 承認済みベースライン |
| xddp.09.specs が生成 | xddp.close が昇格 |
| AIへの自動注入なし | AIへの事前注入対象 ★ |

---

## 5. 未確認・確認が必要な事項

- [x] ~~docs/ 直下の方法論ドキュメント（比較・評価）はどう扱うか？~~
  → XddpSettings/docs/ はそのまま（知識ハブとは別物）
- [x] ~~中央知識ハブの内部フォルダ構造は？~~
  → latest-specs 体系 + lessons-learned（セクション4参照）
- [x] ~~知識流入フロー: xddp.close 後の集約は手動か自動か？~~
  → xddp.close が docs/{repo}/specs/ に自動昇格（xddp.close 改修は別タスク）
- [ ] AI注入の手順: clone 後、どのファイルを CLAUDE.md に記載するか？
- [ ] XddpSettings/docs/ 内の既存テンプレート（projects/_template/）は削除か移植か？

---

## 6. 現時点で決まっていること

| 決定事項 | 内容 |
|---|---|
| XddpSettings/docs/ の位置付け | XDDPツール固有ドキュメント置き場（知識ハブではない） |
| 中央知識ハブの場所 | ワークスペース直下の `docs/`（xddp.init が自動作成） |
| 中央知識ハブの構造 | `shared/` + `{repo-name}/specs/` + `{repo-name}/knowledge/` |
| 管理方法 | GitHub で管理し、clone して使う |
| AI注入タイミング | 新規開発開始時に clone → AI に注入 |
| 最大リポジトリ数 | 開発リポジトリは10以内 |
| プロジェクト構造 | 開発内容により異なる（固定しない） |
| DOCS_DIR デフォルト | `../docs`（リポジトリから1つ上 = ワークスペースルート） |
| DOCS_DIR のパス基準 | リポジトリルートからの相対パス（`XDDP_DIR` と同じ基準） |

---

## 7. 実装計画

### 変更対象ファイル（3ファイル）

| ファイル | 変更内容 |
|---|---|
| `ClaudeCode/.claude/templates/xddp.config.md` | `DOCS_DIR` 設定キーを追加 |
| `ClaudeCode/.claude/skills/xddp.01.init.md` | Step 3.6: docs/ 作成ステップを追加 |
| `ClaudeCode/.claude/commands/xddp.01.init.md` | Step 3.6 の要約を追記 |

### 変更対象外（今回スコープ外）

- `xddp.close` の書き先変更（SPECS_APPROVED_DIR → DOCS_DIR 対応）は別タスク
- `xddp.09.specs` の変更なし

---

### 7-A. xddp.config.md テンプレートへの追加

「成果物ディレクトリ設定」セクションの直後に以下を追加：

```
## 知識ハブディレクトリ設定

DOCS_DIR: ../docs

承認済み仕様書・知見ログを集約する中央知識ハブのパス。
リポジトリルートからの相対パスで指定する。デフォルト: ../docs（ワークスペースルートの docs/）

# 例: DOCS_DIR: docs  →  リポジトリ内 docs/ を使う場合
```

---

### 7-B. xddp.01.init スキルへの Step 3.6 追加

Step 3.5（latest-specs/ 作成）の直後に挿入：

```
### 3.6. Create DOCS_DIR (if not exists or repo subfolder missing)

1. Read DOCS_DIR from xddp.config.md (default: ../docs).
   ※ xddp.config.md がまだ存在しない場合は ../docs をデフォルトとして使う。
2. Let REPO_NAME = basename of the current working directory.
3. If {DOCS_DIR} does not exist → 以下をすべて作成：
   - {DOCS_DIR}/AI_INDEX.md
   - {DOCS_DIR}/shared/glossary.md    （空）
   - {DOCS_DIR}/shared/lessons-learned.md  （空テーブル）
   - {DOCS_DIR}/shared/design/notes.md  （空テンプレート）
   - {DOCS_DIR}/shared/design/patterns.md  （空テンプレート）
   - {DOCS_DIR}/shared/test/patterns.md  （空テンプレート）
   - {DOCS_DIR}/shared/test/anti-patterns.md  （空テンプレート）
   - {DOCS_DIR}/shared/inter-repo/repo-map.md  （空テンプレート）
   - {DOCS_DIR}/shared/inter-repo/dependency-graph.md  （空テンプレート）
   - {DOCS_DIR}/shared/inter-repo/design/sequence/  （空フォルダ・xddp.04 specout の成果物置き場）
   - {DOCS_DIR}/shared/inter-repo/design/dfd/  （空フォルダ・xddp.04 specout の成果物置き場）
   - {DOCS_DIR}/shared/inter-repo/design/architecture/  （空フォルダ・xddp.05 arch の成果物置き場）
   - {DOCS_DIR}/shared/inter-repo/design/interface/  （空フォルダ・xddp.06 design の成果物置き場）
   - {DOCS_DIR}/{REPO_NAME}/specs/README.md
   - {DOCS_DIR}/{REPO_NAME}/knowledge/lessons-learned.md  （空テーブル）
4. If {DOCS_DIR} exists but {DOCS_DIR}/{REPO_NAME}/ does not → 以下のみ作成：
   - {DOCS_DIR}/{REPO_NAME}/specs/README.md
   - {DOCS_DIR}/{REPO_NAME}/knowledge/lessons-learned.md
5. 両方存在する場合はスキップ。
```

各ファイルの初期内容：

**AI_INDEX.md**
```markdown
# AI向けナビゲーションインデックス
> 新規開発開始時に clone してこのファイルを AI に注入してください。

## 共通知識
| ファイル | 内容 |
|---|---|
| [shared/glossary.md](shared/glossary.md) | 全リポジトリ共通用語集 |
| [shared/lessons-learned.md](shared/lessons-learned.md) | 横断的な知見・教訓 |

## リポジトリ別仕様書
| リポジトリ | 承認済み仕様書 | 知見 |
|---|---|---|
| （xddp.close 実行後に自動追記） | — | — |
```

**{REPO_NAME}/specs/README.md**
```markdown
# 承認済み仕様書: {REPO_NAME}
xddp.close で latest-specs/ から昇格した承認済みの最新仕様書を格納します。
ドラフト（未レビュー）は各リポジトリの latest-specs/ にあります。
```

**{REPO_NAME}/knowledge/lessons-learned.md** および **shared/lessons-learned.md**
```markdown
# 知見ログ: {REPO_NAME}
> xddp.close が CR クローズ時に自動追記します。

## エントリ一覧
| ID | タイトル | タグ | CR | 日付 |
|---|---|---|---|---|
| （xddp.close 実行後に追記） | — | — | — | — |
```

---

### 7-C. commands/xddp.01.init.md の更新

Step 3.5 の次に以下を追記：

```
- Step 3.6: DOCS_DIR（デフォルト ../docs）を解決し、存在しない場合は
  AI_INDEX.md / shared/ / {repo_name}/specs/ / {repo_name}/knowledge/ を作成する。
  docs/ が既存で {repo_name}/ のみ未作成の場合は repo サブフォルダのみ追加。
```

---

## 8. 動作確認方法

1. テスト用ワークスペースで `xddp.01.init` を実行
2. `../docs/` が作成されることを確認
3. `../docs/AI_INDEX.md`, `../docs/shared/`, `../docs/{repo_name}/specs/`, `../docs/{repo_name}/knowledge/` の存在を確認
4. 2回目の実行で既存 docs/ に repo サブフォルダが重複作成されないことを確認
5. `DOCS_DIR: docs` に変更して repo 内 docs/ が作成されることを確認
