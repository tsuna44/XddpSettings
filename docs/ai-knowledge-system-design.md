# 知見・仕様書をAIツールで効率活用するためのシステム設計

作成日: 2026-04-10

---

## 基本思想：Single Source of Truth → ツール別注入

```
docs/（人間＋AI共通の単一情報源）
    ↓
CLAUDE.md / copilot-instructions.md（ツール別コンテキスト注入）
    ↓
Claude Code / Copilot Chat（使用ツール）
```

---

## レイヤー1: 知識ファイルの構造化

### `docs/` ディレクトリの整備

```
docs/
├── specs/          # xddp.09.specs が生成する最新仕様書
│   └── 09_specification.md
├── requirements/   # 要求書・変更要求仕様書
├── design/         # 設計書・実装方式検討メモ
├── glossary.md     # ドメイン用語集（ユビキタス言語）
└── AI_INDEX.md     # AI向けナビゲーションインデックス ← 重要
```

**`docs/AI_INDEX.md`** が鍵。Claude Code/Copilot どちらからでも `@mention` で参照でき、「何がどこにあるか」をAIが一発で把握できます。

```markdown
# AI向けナビゲーションインデックス

## 最新仕様書
- [09_specification.md](specs/09_specification.md) — モジュール一覧・機能仕様

## 要求書
- [CR-001](requirements/CR-001/) — ○○機能追加

## ドメイン用語
- [glossary.md](glossary.md) — プロジェクト固有用語
```

---

## レイヤー2: ツール別コンテキスト注入

### Claude Code → `CLAUDE.md`

```
プロジェクトルート/CLAUDE.md
  └─ docs/AI_INDEX.md へのリンク
  └─ 現在のCR番号・フェーズ状態
  └─ アーキテクチャ制約（変更禁止レイヤー等）
```

プロジェクト固有のCLAUDE.mdに以下を追記する運用が効果的：

```markdown
## 現在のコンテキスト
- アクティブCR: CR-005（○○機能追加）
- フェーズ: 工程7（変更設計書作成中）
- 仕様書: docs/specs/09_specification.md を必ず参照すること
- アーキテクチャ制約: docs/design/arch-constraints.md
```

### GitHub Copilot → `.github/copilot-instructions.md`

Copilotはこのファイルを**常時コンテキストに注入**します：

```markdown
# Copilot Instructions

## このリポジトリについて
- XDDP プロセスで管理。最新仕様は docs/specs/09_specification.md
- ドメイン用語は docs/glossary.md を参照

## コーディング規約
- モジュール境界を越える変更は必ず設計書(docs/design/)を確認
- 新規関数にはJSDoc/docstring必須

## 禁止事項
- ○○レイヤーへの直接アクセス禁止（仕様書Section 3参照）
```

---

## レイヤー3: ツール別の活用戦略

| 用途 | Claude Code | VSCode+Claude Code | VSCode+Copilot |
|---|---|---|---|
| **フェーズ実行** | `/xddp.05.arch` スキル | `/xddp.05.arch` コマンド | 手動 or プロンプトテンプレ |
| **仕様書参照** | CLAUDE.md自動注入 | `@docs/specs/...` | `#docs/specs/...` |
| **コード生成** | agentsで分業 | agentsで分業 | Copilot自動補完 |
| **レビュー** | `/xddp.review` | `/xddp.review` | `#file` + プロンプト |
| **知識検索** | `xddp.close`知見ログ | 同左 | `#docs/AI_INDEX.md` |

---

## レイヤー4: 知見の循環サイクル

```
xddp.close スキル
    ↓ 生成
lessons-learned.md（クローズ時の気づき）
    ↓ 反映
docs/glossary.md（用語更新）
docs/AI_INDEX.md（インデックス更新）
.github/copilot-instructions.md（禁止事項・注意点追記）
CLAUDE.md（制約更新）
```

xddp.closeのタイミングで copilot-instructions.md も更新する運用にすることで、CRごとの知見が次のCR時にCopilotにも届きます。

---

## 実装の優先順位

| # | 内容 | 状態 | 備考 |
|---|---|---|---|
| 1 | `docs/AI_INDEX.md` を作成し、既存 docs/ へのナビゲーションを整備 | ✅ 実装済み | 階層構造・テンプレートまで整備（2026-04-19） |
| 2 | `.github/copilot-instructions.md` を追加（プロジェクト共通制約を記述） | ❌ 未実施 | ファイル未作成 |
| 3 | `xddp.close` 改修: クローズ時に copilot-instructions.md も更新するステップを追加 | ❌ 未実施 | スキルに該当ステップなし |
| 4 | `xddp.09.specs` 生成物を `docs/specs/` に自動配置するパス規約を統一 | ✅ 実装済み | `latest-specs/`（ドラフト）→ `xddp.close` でレビュー後 `docs/specs/`（承認済み）へ昇格する2層構成を採用（2026-04-19） |

最終確認日: 2026-04-19

---

---

## 大規模環境（400Kstep・複数リポジトリ）でのスケーラビリティ

### 結論：そのままでは厳しい、追加設計が必要

---

### 主なボトルネック

#### 1. コンテキストウィンドウの壁（最大の問題）

```
Claude Sonnet 4.6: ~200K tokens
400Kstep ≈ 10〜20MB のコード
→ 全体をコンテキストに乗せることは不可能
```

`xddp.04.specout`（波及調査）は読んだファイルをコンテキストに積み上げる方式のため、波及範囲が広いCRでコンテキストが枯渇します。

#### 2. クロスリポジトリ波及調査

```
SPECOUT_MAX_AFFECTED_FILES: 20
```

波及調査は打ち切らず全依存を追い切る設計に変更済み（2026-04-22）。
`SPECOUT_MAX_AFFECTED_FILES` 超過時は CR 分割を警告するが調査は継続する。
循環参照は訪問済みノード管理で防止する。

#### 3. 各フェーズ別のリスク評価

| フェーズ | リスク | 理由 |
|---|---|---|
| xddp.02 分析 | 中 | 対象を絞れれば問題なし |
| xddp.04 specout | **高** | クロスリポジトリ波及でコンテキスト枯渇 |
| xddp.05 arch | 中 | リポジトリ間IFの把握が難しい |
| xddp.07 code | 低〜中 | 1リポジトリ内ならほぼ問題なし |
| xddp.08 test | 中 | 結合テストのスコープ管理が複雑 |

---

### 必要な追加設計

#### A. ✅ リポジトリ間インターフェース文書を静的管理（実装済み: 2026-04-19）

> テンプレートを `docs/projects/_template/inter-repo/` に整備済み。

```
docs/projects/{project-name}/inter-repo/
    ├── repo-map.md          # 各リポジトリの責務・オーナー一覧
    ├── api-contracts/       # 公開APIスキーマ（OpenAPI等）
    ├── event-schemas/       # イベント定義
    └── dependency-graph.md  # リポジトリ間依存グラフ（手動メンテ）
```

**AIはコードを読む代わりにこのドキュメントを読む。** コード全体を舐める必要がなくなります。

#### B. ✅ xddp.config.md のクロスリポジトリ設定追加（実装済み: 2026-04-19）

> プロジェクト・リポジトリ両テンプレートに設定スニペットを記載済み。

```markdown
## クロスリポジトリ設定

MULTI_REPO: true
REPOS:
  api: ../my-api
  worker: ../my-worker
  shared: ../my-shared
# リポジトリ境界を越えて波及調査を継続する（打ち切りなし）

SPECOUT_MAX_AFFECTED_FILES: 30
# この値を超えたら CR 分割を警告（調査は継続）
```

#### C. ✅ CRスコープの明示化（実装済み: 2026-04-19）

> プロジェクトテンプレートの「アクティブCR」セクションに影響リポジトリ宣言テーブルを追加済み。

```markdown
## 影響リポジトリ
- repo-A（主変更）
- repo-B（IFのみ）
- repo-C（影響なし、確認済み）
```

これにより specout が**宣言済みリポジトリの範囲内で調査**を完結できます。

#### D. ✅ エージェントのリポジトリ分業（実装済み: 2026-04-19）

> プロジェクトテンプレートに起動パターンとスケール別対応表を記載済み。

agent 定義を**リポジトリ単位で起動**する運用に変更：

```
xddp-specout-agent（repo-A担当）
xddp-specout-agent（repo-B担当）
  ↓ 各エージェントが独立してSPOを作成
xddp-analyst-agent が結果を統合
```

コンテキストをリポジトリ単位に分割することで枯渇を回避。

---

### 実用的な運用指針

```
400Kstep / 複数リポジトリ の場合

1CR あたりの主変更リポジトリ: 1〜2個に抑える
1CR あたりの影響ファイル数: 20〜30ファイル以内に分割
クロスリポジトリ変更: 必ずリポジトリ単位でCRを分割
```

---

### スケール別の対応まとめ

| 前提 | 対応 |
|---|---|
| シングルリポジトリ、数万step | 現状のままで動作 |
| シングルリポジトリ、100Kstep超 | xddp.config.md のチューニング必要 |
| 複数リポジトリ、400Kstep | 上記A〜Dの追加設計が必要 |

`docs/projects/{project-name}/inter-repo/repo-map.md` の整備と `SPECOUT_REPO_BOUNDARY_AS_MODULE` 設定の追加が、最もコストパフォーマンスの高い対策。
