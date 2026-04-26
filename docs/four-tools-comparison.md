# CC SDD / GitHub Spec kit / OpenSpec / XDDP 4ツール横断比較

作成日: 2026-04-26

---

## ポジショニング概要

| ツール | 提供元 | 対象組織 | 核心思想 |
|--------|--------|---------|---------|
| **CC SDD v3.0** | gotalab（OSS） | グローバル | 自律実装エンジン（TDD + マルチエージェント） |
| **GitHub Spec kit** | GitHub（OSS） | グローバル企業 | 仕様品質を極めて実装を機械化（Intent-Driven） |
| **OpenSpec v1.3.1** | Fission AI（OSS） | スタートアップ | 軽量・探索的・フェーズロックなし |
| **XDDP** | 本リポジトリ | 日本企業 | 人間AI協働 + 工程管理 + 知見蓄積 |

---

## 1. プロセス体系

| 観点 | CC SDD | Spec kit | OpenSpec | XDDP |
|------|--------|----------|----------|------|
| フェーズ数 | 17 skills | 5コマンド | 9コマンド（順序自由） | 15工程（厳格） |
| 人間の介入 | ゲートのみ（実装は完全自律） | ゲートのみ | Optional | 各工程マンダトリーレビュー |
| 自動化度 | 最高（TDD自律ループ） | 高 | 高 | 中程度 |
| AI対応数 | 8種類 | 30以上 | 30以上 | Claude Code専用 |
| マルチリポジトリ | 非公式 | 拡張対応 | 非公式 | ✅ MULTI_REPO フラグ |
| 知見管理 | セッション内（Implementation Notes） | なし（標準機能） | なし | CR間蓄積（lessons-learned） |
| トレーサビリティ | 境界契約レベル | 軽量 | 仕様デルタ | UR/SR/SP 3層・CHD一対一対応 |
| 文書標準化 | EARS形式推奨・柔軟 | Markdown柔軟 | Markdown柔軟 | USDM形式・厳密 |
| 配布方式 | `npx cc-sdd@latest` | `uv tool install specify-cli` | `openspec init` | `git clone + bash setup.sh` |

---

## 2. 各ツールの最大の強み

### CC SDD
`/kiro-impl` Autonomous mode が突出。Implementer・Reviewer・Debugger を動的ディスパッチしてタスク単位で TDD サイクルを自律実行。人間がゲートを承認するだけで実装が回る。

### GitHub Spec kit
コミュニティエコシステムが最強。80以上の拡張（Jira統合・Azure DevOps・セキュリティレビュー等）と30以上の AI ツール統一。企業既存ツールチェーンとの連携が追加コードゼロで実現。

### OpenSpec
最も軽量・高速。フェーズロックなし、`/opsx:explore` で要求が曖昧な段階から開始可能、プロファイルで有効コマンドを絞れる。プロトタイプ・探索的開発に最適。

### XDDP
知見蓄積と大規模変更対応が突出。SPO（母体システム影響範囲調査）、UR/SR/SP 3層トレーサビリティ、lessons-learned・improvement-backlog による CR 間学習、Excel/USDM 対応で非エンジニアが参画できる唯一のツール。

---

## 3. コマンド/フェーズ体系の詳細

### CC SDD v3.0（17 Agent Skills）

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
| `/kiro-steering` | プロジェクトメモリ管理 |

### GitHub Spec kit（5コマンド）

| コマンド | 内容 |
|---------|------|
| `/speckit.constitution` | プロジェクト原則・制約の確立 |
| `/speckit.specify` | ユーザージャーニー・成功指標を言語化 |
| `/speckit.plan` | 技術スタック・アーキテクチャ・制約の決定 |
| `/speckit.tasks` | 仕様を小さなレビュー可能な単位に分解 |
| `/speckit.implement` | タスク実行 |

### OpenSpec v1.3.1（9コマンド・アクションベース）

| コマンド | 内容 |
|----------|------|
| `/opsx:explore` | アイデア探索・問題調査・要件明確化 |
| `/opsx:propose` | 変更を作成し計画アーティファクトを一括生成 |
| `/opsx:new` | 新しい変更のスキャフォルドを開始 |
| `/opsx:continue` | 次のアーティファクトを1つ作成 |
| `/opsx:ff` | 計画アーティファクトを一括生成（fast-forward） |
| `/opsx:apply` | タスクを実装・アーティファクト更新 |
| `/opsx:verify` | 実装をアーティファクトに対して検証 |
| `/opsx:archive` | 完了した変更をアーカイブ |
| `/opsx:bulk-archive` | 複数の完了変更を一括アーカイブ |

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

| 成果物 | CC SDD | Spec kit | OpenSpec | XDDP |
|--------|--------|----------|----------|------|
| 要求仕様 | requirements.md（EARS形式） | Specification | proposal.md + specs/ | CRS（3層・Excel対応） |
| 設計書 | design.md（Mermaid + File Structure） | Technical Plan | design.md | DSN + CHD（Before/After） |
| 影響範囲調査 | — | — | — | SPO（モジュール/クロスモジュール） |
| テスト | TDD自律ループ（実装に統合・高自動化） | 実装ワークフロー内 | 実装内 | TSP + TSR（独立工程・低自動化） |
| 知見管理 | Implementation Notes（会話履歴に蓄積） | なし（標準機能） | なし | lessons-learned + backlog（CR間蓄積） |
| 最新仕様書 | — | — | openspec/specs/ | latest-specs/（バージョン管理） |
| 進捗管理 | タスクリスト＋GO/NO-GO（専用成果物なし） | タスク分解フロー（専用成果物なし） | コマンド実行・アーカイブ状態（専用成果物なし） | progress.md（15工程ステータス） |
| プロジェクトメモリ | Steering files | `.kiro/steering/` | — | project-steering.md |
| 品質ゲート外部化 | `.kiro/settings/rules/`（12ファイル） | 拡張機能で対応 | — | xddp.05/06/07.rules.md |

---

## 5. 設計思想の本質的な違い

```
CC SDD      →  「AIが自律的に TDD サイクルを回す。人間はゲートを承認するだけ」
Spec kit    →  「仕様の質を極めることで、実装を機械化する」
OpenSpec    →  「アーティファクトが存在し合意が取れた状態で実装を始める」
XDDP        →  「人間と AI の協働を前提に、知見を蓄積していく」
```

最大の設計上の違いは **自動化の境界**：
- CC SDD は実装ループを自律化してゲートを最小化
- Spec kit / OpenSpec はゲートで合意を取り、実装は AI 主導
- XDDP は各工程に人間のレビューゲートを置いてトレーサビリティを最大化

---

## 6. ツール選択指針

```
緊急のプロトタイプ・小規模機能
  → OpenSpec（最速・フェーズロックなし・探索対応）

多数のAIツール・ツールチェーン統合が必要
  → GitHub Spec kit（30+対応・80+拡張）

品質重視・TDD・AIに任せたい大型機能
  → CC SDD（自律実装エンジン）

日本企業・長期保守・大規模変更・品質監査対応
  → XDDP（工程管理＋知見蓄積＋トレーサビリティ）
```

---

## 7. XDDPが未実装の主要ギャップ

### 優先度: 高
| 項目 | 内容 | 参考ツール |
|------|------|----------|
| Explore フェーズの導入 | 要求が曖昧な段階からの開始を可能にする前段オプション | OpenSpec `/opsx:explore` |
| Quick Mode | 小規模CR向け簡略フロー（Step 01 → 03 → 07 → 09） | OpenSpec `/opsx:ff` |

### 優先度: 中
| 項目 | 内容 | 参考ツール |
|------|------|----------|
| lessons-learned タグスキーマ統一 | `#XDDP_{フェーズ番号}_{フェーズ名}` に統一し検索容易に | CC SDD / Spec kit |
| gap-analysis フレームワーク | ANA に Option A/B/C 比較セクションを追加 | Spec kit |
| コミュニティ拡張の仕組み | rules / templates を外部リポジトリで共有できる仕組み | Spec kit |

### 優先度: 低
| 項目 | 内容 | 参考ツール |
|------|------|----------|
| プロファイルシステム | `QUALITY_PROFILE: core/full` で有効フェーズを制御 | OpenSpec |
| マルチプラットフォーム対応 | Cursor/Copilot など複数ツール対応の拡大 | CC SDD / OpenSpec |
| `QUALITY_GATE_MAX_ITERATIONS` | xddp.config.md にレビューループ上限パラメータを追加 | — |

### 既に実装済み（他ツールから学んで導入済み）
| 項目 | 実装日 |
|------|--------|
| project-steering.md（プロジェクトメモリ管理） | 2026-04-22 |
| フェーズ別品質ゲート外部化（xddp.05/06/07.rules.md） | 2026-04-22〜26 |
| マルチリポジトリ対応（MULTI_REPO フラグ） | 2026-04-22 |
| 仕様デルタ（CRS Before/After 列） | 当初から実装 |
| 検証コマンド（VERIFY 静的検証） | 当初から実装 |

---

## 8. 詳細比較ドキュメント

各ツールとの詳細比較は以下を参照：

- [cc-sdd-vs-xddp-comparison.md](cc-sdd-vs-xddp-comparison.md)
- [github-spec-kit-vs-xddp-comparison.md](github-spec-kit-vs-xddp-comparison.md)
- [openspec-vs-xddp-comparison.md](openspec-vs-xddp-comparison.md)
