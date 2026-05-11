# cc-sdd / GitHub Spec kit / OpenSpec / Spec Workflow MCP / XDDP 5ツール横断比較

作成日: 2026-04-26 / 最終更新: 2026-05-11（ラウンド2レビュー指摘反映）

---

## 調査正確性評価（2026-05-11 更新）

| セクション | 評価 | 理由 |
|---|---|---|
| ツール概要・プロセス体系（セクション1〜4） | **8/10** | 各ツールリポジトリを直接確認済み（cc-sdd / spec-kit / OpenSpec / spec-workflow-mcp） |
| XDDP の分析 | **9/10** | 本リポジトリのコードを直接読んだ結果に基づく |
| 優位性・劣位性比較（セクション5〜6） | **7/10** | 論理的推論。実プロジェクト適用事例の裏付けなし |
| Web系 vs システム系 適性（セクション7） | **6/10** | 一般的なソフトウェア工学知識からの推論。実使用データ未検証 |
| Spec Workflow MCP の分析 | **8/10** | リポジトリ直接確認済み（v2.2.7）。実プロジェクト適用事例の裏付けなし |
| **総合** | **7/10** | ツールの性格・位置づけは概ね正確。利用統計・細部仕様は要注意 |

---

## ポジショニング概要

| ツール | 提供元 | 対象組織 | 核心思想 |
|--------|--------|---------|---------|
| **cc-sdd v3.0** | gotalab（OSS） | グローバル | 自律実装エンジン（TDD + マルチエージェント） |
| **GitHub Spec kit** | GitHub（OSS） | グローバル企業 | 仕様品質を極めて実装を機械化（Intent-Driven） |
| **OpenSpec v1.3.1** | Fission AI（OSS） | スタートアップ | 軽量・探索的・フェーズロックなし |
| **Spec Workflow MCP v2.2.7** | pimzino（OSS） | 全業種 | MCPサーバー型 + ダッシュボード承認ワークフロー |
| **XDDP** | 本リポジトリ | 日本企業 | 人間AI協働 + 工程管理 + 知見蓄積 |

---

## 1. プロセス体系

| 観点 | cc-sdd | Spec kit | OpenSpec | Spec Workflow MCP | XDDP |
|------|--------|----------|----------|-------------------|------|
| フェーズ数 | 17 skills | 5コマンド | 11コマンド（coreプロファイル5 + expanded6・順序自由） | 4フェーズ（Requirements → Design → Tasks → Implementation。MCP Toolsは5種） | 15工程（厳格） |
| 人間の介入 | ゲートのみ（実装は完全自律） | ゲートのみ | Optional | ダッシュボード経由の承認ゲート必須 | 各工程マンダトリーレビュー |
| 自動化度 | 最高（TDD自律ループ） | 高 | 高 | 中（ワークフロー誘導のみ、実装は AI 任せ） | 中程度 |
| AI対応数 | 8種類 | 30以上 | 29（v1.3.1 supported-tools.md より。README表記は「25+」） | 9種類（Claude/Cursor/Cline/Windsurf/Augment/Continue/OpenCode/Codex/Gemini） | Claude Code専用 |
| マルチリポジトリ | 非公式 | AI ツール多重対応（マルチリポジトリは確認できる根拠なし） | 非公式 | 確認できる根拠なし | ✅ MULTI_REPO フラグ |
| 知見管理 | tasks.md に記録（Implementation Notes） | なし（標準機能） | なし | 実装ログ（`log-implementation` ツール）で蓄積 | CR間蓄積（lessons-learned） |
| トレーサビリティ | 境界契約レベル | 軽量 | 仕様デルタ | タスク単位（軽量） | UR/SR/SP 3層・CHD一対一対応 |
| 文書標準化 | EARS形式推奨・柔軟 | Markdown柔軟 | Markdown柔軟 | Markdown 柔軟 | USDM形式・厳密 |
| 配布方式 | `npx cc-sdd@latest` | `uv tool install specify-cli` | `openspec init` | `npx @pimzino/spec-workflow-mcp` | `git clone + bash setup.sh` |

---

## 2. 各ツールの最大の強み

### cc-sdd
`/kiro-impl` Autonomous mode が突出。Implementer・Reviewer・Debugger を動的ディスパッチしてタスク単位で TDD サイクルを自律実行。人間がゲートを承認するだけで実装が回る。

### GitHub Spec kit
コミュニティエコシステムが最強。80以上の拡張（Jira統合・Azure DevOps・セキュリティレビュー等）と30以上の AI ツール統一。企業既存ツールチェーンとの連携が追加コードゼロで実現。

### OpenSpec
最も軽量・高速。フェーズロックなし、`/opsx:explore` で要求が曖昧な段階から開始可能、プロファイルで有効コマンドを絞れる。プロトタイプ・探索的開発に最適。

### Spec Workflow MCP
**MCP プロトコル標準化**が最大の強み。特定フレームワークに依存せず MCP クライアント設定のみで Claude Code・Cursor・Cline など 9 種類の AI ツールに統一インタフェースを提供できる。Web ダッシュボード（localhost:5000）と VSCode Extension による可視化・承認ワークフローは非エンジニアのステークホルダーも参加できる点が他ツールにない特徴。

### XDDP
知見蓄積と大規模変更対応が突出。SPO（母体システム影響範囲調査）、UR/SR/SP 3層トレーサビリティ、lessons-learned・improvement-backlog による CR 間学習、Excel/USDM 対応で非エンジニアが参画できるツール。

---

## 3. コマンド/フェーズ体系の詳細

### cc-sdd v3.0（17 Agent Skills）

| スキル | 役割 |
|--------|------|
| `/kiro-discovery` | 作業起点。スコープ整理・brief.md 生成 |
| `/kiro-spec-init` | 単一スペックの初期化 |
| `/kiro-spec-requirements` | EARS 形式要件定義 |
| `/kiro-spec-design` | Mermaid 図 + File Structure Plan 付き設計書 |
| `/kiro-spec-tasks` | `_Boundary:_`・`_Depends:_` アノテーション付きタスク分解 |
| `/kiro-spec-batch` | 複数スペック並行作成（クロススペックレビュー付き） |
| `/kiro-impl` | タスク承認後の自律実装（Autonomous / Manual mode） |
| `/kiro-validate-impl` | 実装後の統合検証（GO / NO-GO / MANUAL_VERIFY_REQUIRED） |
| `/kiro-validate-gap` | スペック欠損・ギャップの検証 |
| `/kiro-validate-design` | 設計の整合性検証 |
| `/kiro-steering` | プロジェクトメモリ管理 |

※ kiro-debug・kiro-review・kiro-spec-quick・kiro-spec-status・kiro-steering-custom・kiro-verify-completion の6スキルは kiro-impl から自動ディスパッチされる内部サポートスキル（合計17スキル）。

### GitHub Spec kit v0.8.8.dev0（5コマンド＋オプション3件）

| コマンド | 内容 |
|---------|------|
| `/speckit.constitution` | プロジェクト原則・制約の確立 |
| `/speckit.specify` | ユーザージャーニー・成功指標を言語化 |
| `/speckit.plan` | 技術スタック・アーキテクチャ・制約の決定 |
| `/speckit.tasks` | 仕様を小さなレビュー可能な単位に分解 |
| `/speckit.implement` | タスク実行 |
| `/speckit.clarify`（オプション） | 要件・仕様の曖昧な点を明確化 |
| `/speckit.analyze`（オプション） | 既存コードベース・仕様の分析 |
| `/speckit.checklist`（オプション） | チェックリスト形式での品質確認 |

### OpenSpec v1.3.1（11コマンド・アクションベース）

coreプロファイル（デフォルト5コマンド）＋ expandedプロファイル（追加6コマンド）の構成。

| コマンド | プロファイル | 内容 |
|----------|------|------|
| `/opsx:explore` | core | アイデア探索・問題調査・要件明確化 |
| `/opsx:propose` | core | 変更を作成し計画アーティファクトを一括生成 |
| `/opsx:apply` | core | タスクを実装・アーティファクト更新 |
| `/opsx:sync` | core | デルタ仕様を main に同期（オプション） |
| `/opsx:archive` | core | 完了した変更をアーカイブ |
| `/opsx:new` | expanded | 新しい変更のスキャフォルドを開始 |
| `/opsx:continue` | expanded | 次のアーティファクトを1つ作成 |
| `/opsx:ff` | expanded | 計画アーティファクトを一括生成（fast-forward） |
| `/opsx:verify` | expanded | 実装をアーティファクトに対して検証 |
| `/opsx:bulk-archive` | expanded | 複数の完了変更を一括アーカイブ |
| `/opsx:onboard` | expanded | 新規メンバー・AI へのプロジェクトオンボーディング |

### Spec Workflow MCP v2.2.7（5 MCP Tools）

| ツール | 内容 |
|--------|------|
| `spec-workflow-guide` | ワークフロー全体の開始ガイド（最初に呼ぶ） |
| `steering-guide` | プロジェクトステアリングコンテキストのロード |
| `spec-status` | 仕様・タスク・進捗の一覧表示 |
| `approvals` | ダッシュボード経由の承認管理（request/status/delete） |
| `log-implementation` | 実装タスクとコード統計のログ記録 |

### XDDP（15工程・9スキル）

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

---

## 4. 成果物の充実度

| 成果物 | cc-sdd | Spec kit | OpenSpec | Spec Workflow MCP | XDDP |
|--------|--------|----------|----------|-------------------|------|
| 要求仕様 | requirements.md（EARS形式） | Specification | proposal.md + specs/ | Requirements ドキュメント（Markdown） | CRS（3層・Excel対応） |
| 設計書 | design.md（Mermaid + File Structure） | Technical Plan | design.md | Design ドキュメント（Markdown） | DSN + CHD（Before/After） |
| 影響範囲調査 | 設計書内（design.md + File Structure Plan + _Boundary:_/_Depends:_ アノテーション） | — | — | — | SPO（モジュール/クロスモジュール） |
| テスト | TDD自律ループ（実装に統合・高自動化） | 実装ワークフロー内 | 実装内 | Tasks 内に統合（独立工程なし） | TSP + TSR（独立工程・低自動化） |
| 知見管理 | Implementation Notes（tasks.md に記録・後続タスクに注入） | なし（標準機能） | なし | 実装ログ（コード統計付き） | lessons-learned + backlog（CR間蓄積） |
| 最新仕様書 | — | — | openspec/specs/ | `.spec-workflow/` ディレクトリ | latest-specs/（バージョン管理） |
| 進捗管理 | タスクリスト＋GO/NO-GO（専用成果物なし） | タスク分解フロー（専用成果物なし） | コマンド実行・アーカイブ状態（専用成果物なし） | Web ダッシュボード（リアルタイム更新） | progress.md（15工程ステータス） |
| プロジェクトメモリ | Steering files | `.kiro/steering/` | — | steering-guide ツール | project-steering.md |
| 品質ゲート外部化 | `.kiro/settings/rules/`（12ファイル） | 拡張機能で対応 | — | ダッシュボード承認（外部化されている） | xddp.05/06/07.rules.md |

---

## 5. 設計思想の本質的な違い

```
cc-sdd            →  「AIが自律的に TDD サイクルを回す。人間はゲートを承認するだけ」
Spec kit          →  「仕様の質を極めることで、実装を機械化する」
OpenSpec          →  「アーティファクトが存在し合意が取れた状態で実装を始める」
Spec Workflow MCP →  「MCP標準で統一し、ダッシュボード承認でワークフローを可視化する」
XDDP              →  「人間と AI の協働を前提に、知見を蓄積していく」
```

最大の設計上の違いは **自動化の境界**：
- cc-sdd は実装ループを自律化してゲートを最小化
- Spec kit / OpenSpec はゲートで合意を取り、実装は AI 主導
- Spec Workflow MCP は MCP 標準でツール横断のワークフローを統一し、ダッシュボードで可視化
- XDDP は各工程に人間のレビューゲートを置いてトレーサビリティを最大化

---

## 6. ツール選択指針

```
緊急のプロトタイプ・小規模機能
  → OpenSpec（最速・フェーズロックなし・探索対応）

多数のAIツール・ツールチェーン統合が必要
  → GitHub Spec kit（30+対応・80+拡張）

品質重視・TDD・AIに任せたい大型機能
  → cc-sdd（自律実装エンジン）

ツール非依存でMCP対応AIに統一インタフェースを使いたい
  → Spec Workflow MCP（9ツール対応・ダッシュボード可視化）

日本企業・長期保守・大規模変更・品質監査対応
  → XDDP（工程管理＋知見蓄積＋トレーサビリティ）
```

---

## 7. Web系 vs システム系 適性分析

### 開発特性の違いが適性を決める

| 特性 | Web系（SaaS・アプリ） | システム系（業務基幹・組込み・インフラ） |
|---|---|---|
| 変更頻度 | 高い（週〜日単位） | 低い（月〜四半期単位） |
| 変更1件の影響範囲 | 小〜中 | 中〜大 |
| 設計書の要求 | 任意 | 必須（契約・監査・規制） |
| リリースコスト | 低い（CI/CD） | 高い（検証・承認フロー） |
| 既存システム依存度 | 中 | 高 |

### 適性マップ

```
                  Web系（軽量・高速）  ←→  システム系（重厚・厳密）

cc-sdd            ◎◎◎              ○
GitHub Spec kit   ◎◎◎              △
OpenSpec          ◎◎               △
Spec Workflow MCP ◎◎               ○
XDDP              △〜○             ◎◎◎
```

**cc-sdd / Spec kit / OpenSpec が Web系に強い理由:**
- TDD・フィーチャーフラグ・CI/CD との親和性
- 小さい変更を高速に回すことを前提とした設計
- GitHub PR ベースのワークフローに自然に乗る

**Spec Workflow MCP が Web系に向く理由:**
- ダッシュボード可視化・承認ワークフローは軽量チームに適合
- MCP プロトコルで複数 AI ツールを横断できる
- システム系には工程数が不足（影響範囲調査・独立テスト工程なし）

**XDDP がシステム系に強い理由:**
- 変更1件の影響範囲が大きいほど specout（工程4）の価値が増す
- 設計書・仕様書が法令・契約・社内規程で求められる環境に適合
- CHD・ANA に設計根拠が残るため、数年後の保守でも追跡できる

### Web系でXDDPが活きる例外ケース

| ケース | 理由 |
|---|---|
| 金融・医療・行政のWebAPI | 変更履歴・設計根拠の監査要求がある |
| B2B SaaSの基幹機能変更 | 顧客契約に基づく変更管理が必要 |
| マイクロサービスの境界変更 | インタフェース変更の影響が複数サービスに波及する |
| レガシー移行（ストラングラー） | 既存仕様の把握が先決（specout が威力を発揮） |

> **判断基準**: 「Web系 vs システム系」の二分法より「変更1件のコストと影響範囲」で適性を判断する方が実態に即している。変更コストが高くなるほど XDDP の投資対効果が上がる。

---

## 8. XDDPが未実装の主要ギャップ

### 優先度: 高
| 項目 | 内容 | 参考ツール |
|------|------|----------|
| Explore フェーズの導入 | 要求が曖昧な段階からの開始を可能にする前段オプション | OpenSpec `/opsx:explore` |
| Quick Mode | 小規模CR向け簡略フロー（Step 01 → 03 → 07 → 09） | OpenSpec `/opsx:ff` |
| ダッシュボード可視化 | 仕様・タスク・進捗をリアルタイム表示する Web ダッシュボード | Spec Workflow MCP `spec-status` |
| MCP Server 化 | 複数 AI ツール（Claude Code/Cursor/Cline 等）から統一インタフェースで呼べる仕組み | Spec Workflow MCP |

### 優先度: 中
| 項目 | 内容 | 参考ツール |
|------|------|----------|
| lessons-learned タグスキーマ統一 | `#XDDP_{フェーズ番号}_{フェーズ名}` に統一し検索容易に | cc-sdd / Spec kit |
| gap-analysis フレームワーク | ANA に Option A/B/C 比較セクションを追加 | Spec kit |
| コミュニティ拡張の仕組み | rules / templates を外部リポジトリで共有できる仕組み | Spec kit |

### 優先度: 低
| 項目 | 内容 | 参考ツール |
|------|------|----------|
| プロファイルシステム | `QUALITY_PROFILE: core/full` で有効フェーズを制御 | OpenSpec |
| マルチプラットフォーム対応 | Cursor/Copilot など複数ツール対応の拡大 | cc-sdd / OpenSpec |
| `QUALITY_GATE_MAX_ITERATIONS` | xddp.config.md にレビューループ上限パラメータを追加 | — |

### 既に実装済み
| 項目 | 実装日 |
|------|--------|
| project-steering.md（プロジェクトメモリ管理） | 2026-04-22 |
| フェーズ別品質ゲート外部化（xddp.05/06/07.rules.md） | 2026-04-22〜26 |
| マルチリポジトリ対応（MULTI_REPO フラグ） | 2026-04-22 |
| 仕様デルタ（CRS Before/After 列） | 当初から実装 |
| 検証コマンド（VERIFY 静的検証） | 当初から実装 |

---

## 9. 出典

| ツール | 出典 |
|---|---|
| cc-sdd | [gotalab/cc-sdd GitHub リポジトリ](https://github.com/gotalab/cc-sdd) |
| GitHub Spec kit | [GitHub Spec kit 公式ドキュメント](https://github.github.com/spec-kit/) |
| GitHub Spec kit | [GitHub Blog: Spec-Driven Development with AI](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/) |
| OpenSpec | [openspec.dev 公式サイト](https://openspec.dev/) |
| OpenSpec | [Fission-AI/OpenSpec GitHub リポジトリ](https://github.com/Fission-AI/OpenSpec) |
| Spec Workflow MCP | [pimzino/spec-workflow-mcp GitHub リポジトリ](https://github.com/pimzino/spec-workflow-mcp) |
| 比較分析 | [Martin Fowler: Understanding Spec-Driven-Development tools](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) |
| 比較分析 | [Hashrocket: OpenSpec vs Spec Kit](https://hashrocket.com/blog/posts/openspec-vs-spec-kit-choosing-the-right-ai-driven-development-workflow-for-your-team) |
| XDDP 詳細 | 本リポジトリ `ClaudeCode/.claude/skills/`、`ClaudeCode/.claude/agents/`（直接コード読取） |
