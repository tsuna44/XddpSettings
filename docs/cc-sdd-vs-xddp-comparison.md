# CC SDD vs XDDP 比較分析

作成日: 2026-04-22 / 最終更新: 2026-04-26

## 概要

| ツール | リポジトリ | バージョン | 設計思想 |
|--------|-----------|-----------|---------|
| CC SDD | https://github.com/gotalab/cc-sdd | v3.0.2 (2026-04-14) | Agent Skills + 長時間自律実装（Spec-Driven Development）、マルチプラットフォーム対応 |
| XDDP | 本リポジトリ | — | eXtreme Design-Driven Process、日本企業向け詳細工程管理 |

---

## 1. プロセス/フェーズ体系

### CC SDD v3.0（17 Agent Skills）

v3.0（2026-04-10）で従来の「3フェーズ」から **17 Agent Skills** 体系に全面刷新された。
コマンドベースのワークフローは非推奨となり、`npx cc-sdd@latest` でインストールする Skills モードが標準。

#### 主要ワークフロー

| スキル | 役割 |
|--------|------|
| `/kiro-discovery` | 新しい作業の起点。スコープを整理し `brief.md`（+ 必要時 `roadmap.md`）を生成、次のコマンドを提案して停止 |
| `/kiro-spec-init` | 単一スペックの初期化 |
| `/kiro-spec-requirements` | EARS 形式要件定義 |
| `/kiro-spec-design` | Mermaid 図 + File Structure Plan 付き設計書（boundary-first） |
| `/kiro-spec-tasks` | `_Boundary:_`・`_Depends:_` アノテーション付きタスク分解 |
| `/kiro-spec-batch` | 複数スペックの並行作成（クロススペックレビュー付き） |
| `/kiro-impl` | タスク承認後の自律実装。Autonomous mode（1タスク/反復）または Manual mode |
| `/kiro-validate-impl` | 実装後の統合検証（GO / NO-GO / MANUAL_VERIFY_REQUIRED） |
| `/kiro-steering` / `/kiro-steering-custom` | プロジェクトメモリ管理 |

#### `/kiro-impl` Autonomous mode の仕組み

各タスクに対して、ネイティブサブエージェントプリミティブで3つのロールを動的ディスパッチ：

1. **Implementer** — TDD（RED → GREEN）で実装、フィーチャーフラグ下で動作
2. **Reviewer** — 独立パスで `git diff`・テスト実行・境界準拠を検証
3. **Debugger** — Implementer がブロックした場合や Reviewer 拒否2回で自動起動（最大2回）

#### サポート対象 AI エージェント（8種類）

| エージェント | 安定性 |
|-------------|--------|
| Claude Code | Stable |
| Codex | Stable |
| Cursor IDE | Beta |
| GitHub Copilot | Beta |
| Windsurf IDE | Beta |
| OpenCode | Beta |
| Gemini CLI | Beta |
| Antigravity | Beta（実験的） |

---

### XDDP（15工程）

| スキル | 工程 |
|--------|------|
| xddp.01.init | 工程1: CR ワークスペース初期化 |
| xddp.02.analysis | 工程2: 要求分析（ANA） |
| xddp.03.req | 工程3: 変更要求仕様書作成（CRS） |
| xddp.04.specout | 工程4: スペックアウト（SPO）＋工程5: CRS更新 |
| xddp.05.arch | 工程6: 実装方式検討（DSN） |
| xddp.06.design | 工程7: 変更設計書作成（CHD）＋工程8: CRSフィードバック |
| xddp.07.code | 工程9: コーディング＋工程10: 静的検証 |
| xddp.08.test | 工程11: テスト設計〜工程14: 不具合フィードバック |
| xddp.09.specs | 工程15: 最新仕様書生成（latest-specs/） |
| xddp.close | CR クローズ・知見集約 |

---

## 2. 成果物の種類

### CC SDD

| 成果物 | 説明 |
|--------|------|
| `brief.md` | Discovery フェーズで生成するスコープ要約 |
| `roadmap.md` | 複数スペックに分解する場合のロードマップ |
| `requirements.md` | EARS 形式の要件（受け入れ基準付き） |
| `design.md` | Mermaid 図 + File Structure Plan 付き設計書 |
| `tasks.md` | `_Boundary:_`・`_Depends:_` アノテーション付きタスクリスト（`## Implementation Notes` で後続タスクへ知見伝播） |
| Steering files | プロジェクトメモリ（命名規約・アーキテクチャ決定・既存パターン） |
| 形式 | 柔軟、13言語対応、Kiro IDE スペックと互換 |

### XDDP

| 成果物 | 説明 |
|--------|------|
| `REQ-{CR}.md` | 要求書（入力） |
| `ANA-{CR}.md` | 要求分析メモ |
| `CRS-{CR}.md` / `.xlsx` | 変更要求仕様書（Markdown & Excel） |
| `SPO-{CR}.md` + `modules/*-spo.md` + `cross-module/*` | スペックアウト（3種） |
| `DSN-{CR}.md` | 実装方式設計メモ（Mermaid 図付き） |
| `CHD-{CR}.md` | 変更設計書（トレーサビリティマトリクス付き） |
| `CODING-{CR}.md` | コーディング実装メモ |
| `VERIFY-{CR}.md` | 静的検証レポート |
| `TSP-{CR}.md` | テスト仕様書 |
| `TSR-{CR}.md` | テスト結果レポート |
| `latest-specs/{module}/*-spec.md` | 最新仕様書（バージョン管理） |
| `progress.md` | CR 進捗管理 |
| `lessons-learned.md` | 知見ログ |
| `improvement-backlog.md` | 改善バックログ |
| `project-steering.md` | プロジェクトメモリ（工程05・06 で AI が参照） |

---

## 3. ファイル構成

### CC SDD

```
.agents/
  skills/
    cc-sdd-new-agent.md    ← 新エージェント追加手順 SOP（1ファイルのみ）
.kiro/
├── settings/
│   ├── rules/       ← 設計・生成・レビュー基準 12ファイル
│   │                   （design-principles, gap-analysis, ears-format,
│   │                    requirements-review-gate, design-review-gate,
│   │                    tasks-generation, tasks-parallel-analysis 等）
│   └── templates/   ← ドキュメント様式テンプレート
│       ├── steering/        ← プロジェクトメモリテンプレート
│       ├── steering-custom/ ← カスタムステアリングテンプレート
│       └── specs/           ← スペックテンプレート
└── specs/           ← スペック例
AGENTS.md
CLAUDE.md
tools/               ← npm パッケージ本体（17 skills をインストール先に展開）
docs/                ← ガイド類
```

> 17 skills の実体はターゲットプロジェクトの `.claude/skills/`（または各 AI ツール対応ディレクトリ）にインストールされる。

### XDDP

```
ClaudeCode/.claude/
├── skills/
│   └── xddp.0X.*.md     ← 工程別スキル実装
├── commands/
│   └── xddp.0X.*.md     ← スキルの要約版（1:1対応）
├── templates/
│   ├── xddp.config.md            ← プロジェクト設定テンプレート
│   ├── project-steering-template.md ← プロジェクトメモリテンプレート
│   ├── xddp.05.rules.md          ← DSN 品質ゲート定義
│   ├── xddp.06.rules.md          ← CHD 品質ゲート定義
│   ├── xddp.07.rules.md          ← コーディング品質ゲート定義
│   └── *-template.md             ← 各工程の成果物テンプレート
└── agents/              ← サブエージェント定義
```

---

## 4. 設計思想の比較

| 観点 | CC SDD | XDDP |
|------|--------|------|
| 自動化レベル | 非常に高い（Autonomous mode: TDD + 独立レビュー + 自動デバッグ / タスク） | 中程度（AI→人間レビュー→修正の反復） |
| 人間の介入 | フェーズゲート（要件・設計・タスク）のみ、実装は自律 | 各工程ごとのレビュー＋修正ループ（最大5回） |
| 仕様と実装の関係 | 仕様はモジュール境界の契約。コードが真実の源泉 | 仕様は UR→SR→SP の段階的分解で追跡可能 |
| 設計の粒度 | boundary-first（File Structure Plan + `_Boundary:_` / `_Depends:_` アノテーション） | SP 単位（Before/After コード定義） |
| スコープ | 単一機能（per feature）または複数スペック（batch） | 単一変更要求（per CR）で大規模変更にも対応 |
| 知見・学習管理 | タスク間の `## Implementation Notes` 伝播（会話履歴に蓄積） | lessons-learned + improvement-backlog で CR 間蓄積 |
| テスト位置づけ | TDD（RED→GREEN）を自律実装の中核に組み込み | 専用工程（08）で仕様要件との整合確認 |
| 文書標準化 | テンプレート推奨だが柔軟、EARS 形式推奨 | 各工程の成果物形式を厳密に定義（USDM対応） |
| グローバル対応 | 13言語・8種類 AI ツール対応、NPM パッケージ | 日本語ベース、Claude Code 専用 |
| 配布方式 | `npx cc-sdd@latest`（NPM パッケージ） | git clone + `bash setup.sh` |

---

## 5. CC SDD にあって XDDP にないもの

| 機能・特徴 | 説明 |
|-----------|------|
| マルチプラットフォーム対応 | Claude Code, Codex, Cursor, Copilot, Windsurf, OpenCode, Gemini CLI, Antigravity の 8 ツールを統一スキルセットで対応 |
| NPM パッケージ配布 | `npx cc-sdd@latest` で即インストール、言語とエージェントをオプション選択 |
| 言語選択（13言語） | 英語・日本語・繁体字中国語・スペイン語など多言語対応 |
| `/kiro-spec-batch` によるマルチスペック並行作成 | ロードマップを複数スペックに分解し、クロススペックレビューで矛盾・責任重複・インターフェース不整合を自動検出 |
| TDD 駆動の自律実装 | `/kiro-impl` Autonomous mode で RED→GREEN サイクル + 独立レビューエージェント + 自動デバッグを各タスクで実行 |
| `/kiro-validate-impl` による統合検証 | 実装後に要件カバレッジ・設計整合・テストスイート証跡を横断確認、GO/NO-GO を判定 |
| boundary-first spec discipline | `design.md` に File Structure Plan を含め、タスクに `_Boundary:_`・`_Depends:_` アノテーションを付与して境界違反を自動検出 |
| learnings propagation | タスク実行中の発見を `## Implementation Notes` に記録し後続タスクの Implementer に注入 |
| `brief.md` / `roadmap.md` | Discovery フェーズの成果物。スコープと複数スペックの構成を記録 |
| EARS 形式の要件定義 | `ears-format.md` ルールに基づく標準化された要件記述 |
| `settings/rules/` によるフェーズ別判断基準外部化 | `gap-analysis.md` 等 12 ファイルで判断基準を独立管理 |
| Kiro IDE 互換 | Amazon Kiro IDE のスペックと互換・移行可能 |

---

## 6. XDDP にあって CC SDD にないもの

| 機能・特徴 | 説明 |
|-----------|------|
| CR 単位のワークスペース管理 | 各変更要求を独立した `{CR}/` フォルダで管理 |
| progress.md による 15 工程ステータス追跡 | ✅/🔄/👀/🔁/⬜ で状態管理、完了日記録 |
| UR/SR/SP 3層仕様分類 | ユーザ要求の段階的な分解プロセスを工程化 |
| SPO（Specout = 母体システム影響範囲調査） | モジュール単位・クロスモジュール単位で分析 |
| DSN（実装方式の代替案比較） | 複数案の QCD 比較と採用理由を記録、Mermaid 図で可視化 |
| 静的検証（VERIFY） | 設計書の After コード定義と実装コードの乖離を工程として検証 |
| テスト実行と不具合修正の一体化 | 工程08 でテスト仕様→実行→バグ修正→フィードバックを一括処理 |
| latest-specs/ による最新仕様書自動生成 | モジュール/機能単位の spec ファイルをバージョン管理 |
| 知見ログ（lessons-learned） | 各 CR での気づき・教訓を蓄積し次の CR で参照 |
| 改善バックログ | 未対応の改善案を ID 付きで管理 |
| Excel ↔ Markdown 双方向変換 | CRS を USDM 形式 Excel で編集可能 |
| `project-steering.md` による工程横断プロジェクトメモリ | xddp.01.init 初期化時に生成。工程05・06 で `STEERING_CONTEXT` として参照 |
| 工程別品質ルールファイル（xddp.05/06/07.rules.md） | DSN・CHD・コーディングの品質ゲート定義を独立ファイルで管理。ルール単体での更新が可能 |
| マルチリポジトリ対応 | `xddp.config.md` の `MULTI_REPO: true` + `REPOS:` マッピングで、工程04（specout）・工程09（コーディング）がリポジトリ境界をまたいで動作 |

---

## 7. プロジェクト横断ルール管理の比較

### CC SDD の `.kiro/settings/templates/steering/`

**プロジェクトメモリ管理ファイル** として設計されており、以下を記録する：

- 組織構造・命名規約・インポート戦略
- アーキテクチャ的決定・技術標準
- 既存パターン・慣習

**管理方針3原則：**
1. **パターン中心**（個別ファイルの列挙ではなく）
2. **100〜200行程度**（単一トピック）
3. **追加型更新**（既存内容を置き換えない、タイムスタンプと理由を記載）

### XDDP の `project-steering.md`（実装済み）

`/xddp.01.init` 実行時に `project-steering-template.md` からコピー生成される。
工程05（DSN）・工程06（CHD）で `STEERING_CONTEXT` として読み込まれ、AI がプロジェクト固有の慣習に従って成果物を生成できる。
CC SDD の steering 思想を XDDP プロセスに取り込んだ設計。

### CC SDD アイデアの XDDP 実装状況

| アイデア | 優先度 | 状態 |
|---------|--------|------|
| `project-steering.md` テンプレートの新設 | 高 | ✅ 実装済み |
| フェーズ別設計品質ゲートの外部化（rules ファイル） | 中 | ✅ 実装済み（xddp.05/06/07.rules.md） |
| lessons-learned のタグスキーマ統一 | 中 | ⬜ 未実装 |
| gap-analysis テンプレートの導入 | 低 | ⬜ 未実装 |
| `xddp.config.md` に `QUALITY_GATE_MAX_ITERATIONS` パラメータ追加 | 低 | ⬜ 未実装 |

---

## まとめ

**CC SDD v3.0** は「**自律実装エンジン**」——タスク単位で Implementer・Reviewer・Debugger を動的ディスパッチし、人間の介入なしに TDD サイクルを回す。コードが真実の源泉であり、仕様はモジュール境界の契約に徹する。

**XDDP** は「**工程進行管理＋知見蓄積システム**」——詳細な仕様追跡（UR/SR/SP）と人間レビューの反復により品質を担保し、CR 間で教訓を引き継ぐ。

両者の最大の設計上の違いは **自動化の境界**——CC SDD は実装ループを自律化してゲートを最小化し、XDDP は各工程に人間のレビューゲートを置いてトレーサビリティを最大化する。XDDPが CC SDD から取り込み済みの最大の成果は **「AIが参照する判断基準ファイルの体系化」**（project-steering.md + rules ファイル群）であり、プロジェクト固有の慣習を AI が毎回スクラッチで判断する問題を解消している。
