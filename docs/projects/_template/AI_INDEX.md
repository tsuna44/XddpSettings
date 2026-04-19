# AI向けナビゲーションインデックス（プロジェクト: {project-name}）

> このファイルをコピーして `docs/projects/{project-name}/AI_INDEX.md` として配置してください。

---

## プロジェクト概要

| 項目 | 内容 |
|---|---|
| プロジェクト名 | {project-name} |
| 目的 | （プロジェクトの目的を記載） |
| オーナー | （担当者・チーム名） |

---

## プロジェクト固有用語集

| ファイル | 内容 |
|---|---|
| [glossary.md](glossary.md) | このプロジェクト固有の用語 |

---

## 知見・振り返り

| ファイル | 内容 |
|---|---|
| [lessons-learned.md](lessons-learned.md) | xddp.close が蓄積する気づき・知見 |

---

## リポジトリ一覧

| リポジトリ | インデックス | 役割 |
|---|---|---|
| （リポジトリを追加してください） | — | — |

> リポジトリ追加時は `repos/{repo-name}/` を作成し、上の表にエントリを追加する。

---

## リポジトリ間インターフェース

> AIはコードを直接読む代わりにこれらの文書を参照します。大規模環境でのコンテキスト枯渇を防ぐために必ず整備してください。

| ファイル | 内容 |
|---|---|
| [inter-repo/repo-map.md](inter-repo/repo-map.md) | リポジトリ責務・オーナー一覧 |
| [inter-repo/dependency-graph.md](inter-repo/dependency-graph.md) | リポジトリ間依存グラフ（手動メンテ） |
| [inter-repo/api-contracts/](inter-repo/api-contracts/) | 公開APIスキーマ（OpenAPI等） |
| [inter-repo/event-schemas/](inter-repo/event-schemas/) | イベント定義 |

---

## xddp.config.md（クロスリポジトリ設定）

> 複数リポジトリ環境では以下の設定を各リポジトリの `xddp.config.md` に追加してください。

```markdown
## クロスリポジトリ設定

SPECOUT_REPO_BOUNDARY_AS_MODULE: true
SPECOUT_CROSS_REPO_INTERFACE_DOC: docs/projects/{project-name}/inter-repo/repo-map.md
SPECOUT_CUTOFF_MODULE_BOUNDARIES: 1
```

---

## アクティブCR

| CR番号 | 概要 | フェーズ | パス |
|---|---|---|---|
| （進行中のCRを記載） | — | — | — |

### CRスコープ宣言（影響リポジトリ）

> `xddp.01.init` 時に宣言。specout がこの範囲内で調査を完結します。

| リポジトリ | 役割 |
|---|---|
| （例: repo-A） | 主変更 |
| （例: repo-B） | IFのみ |
| （例: repo-C） | 影響なし・確認済み |

---

## エージェント分業指針（大規模環境）

> 400Kstep超・複数リポジトリ環境ではエージェントをリポジトリ単位で起動しコンテキスト枯渇を防ぎます。

```
xddp-specout-agent（repo-A担当）→ SPO-repo-A.md
xddp-specout-agent（repo-B担当）→ SPO-repo-B.md
  ↓
xddp-analyst-agent が結果を統合
```

| スケール | 対応 |
|---|---|
| シングルリポジトリ・数万step | 通常運用 |
| シングルリポジトリ・100Kstep超 | `xddp.config.md` チューニング |
| 複数リポジトリ・400Kstep超 | 上記全項目の整備 + エージェント分業 |
