# AI向けナビゲーションインデックス（リポジトリ: {repo-name}）

> このファイルをコピーして `docs/projects/{project-name}/repos/{repo-name}/AI_INDEX.md` として配置してください。

---

## リポジトリ概要

| 項目 | 内容 |
|---|---|
| リポジトリ名 | {repo-name} |
| 言語・フレームワーク | （例: Python / FastAPI） |
| 役割 | （このリポジトリの責務） |
| オーナー | （担当者・チーム名） |

---

## 承認済み仕様書（ベースライン）

> `xddp.close` が `latest-specs/` からレビュー確認後に昇格します。AIへの参照はこちらを使用してください。

| ファイル | バージョン | 最終更新CR | 内容 |
|---|---|---|---|
| （xddp.close 実行後に追記） | — | — | — |

---

## ドラフト仕様書（レビュー待ち）

> `xddp.09.specs` が自動生成します。未レビュー差分を含む可能性があるため、AIへの自動注入は行いません。

| パス | 説明 |
|---|---|
| `latest-specs/` | 最新生成ドラフト（承認前） |

---

## 知見・Tips

> `xddp.close` が蓄積します。承認不要で即時参照可能です。

| ファイル | 内容 |
|---|---|
| [knowledge/lessons-learned.md](knowledge/lessons-learned.md) | CR横断の気づき・教訓 |
| [knowledge/patterns.md](knowledge/patterns.md) | 実装パターン・設計Tips |

---

## モジュール一覧

| モジュール | インデックス | 役割 |
|---|---|---|
| （モジュールを追加してください） | — | — |

> モジュール追加時は `modules/{module-name}/` を作成し、上の表にエントリを追加する。

---

## アーキテクチャ制約

| ファイル | 内容 |
|---|---|
| [arch-constraints.md](arch-constraints.md) | 変更禁止レイヤー・設計上の制約 |

---

## 公開インターフェース（他リポジトリ向け）

| ファイル | 内容 |
|---|---|
| [public-api.md](public-api.md) | 公開API・イベントスキーマの概要 |

---

## xddp.config.md（このリポジトリの設定）

> クロスリポジトリ環境では以下をこのリポジトリの `xddp.config.md` に設定してください。

```markdown
## クロスリポジトリ設定

SPECOUT_REPO_BOUNDARY_AS_MODULE: true
# リポジトリ境界でモジュール境界とみなして調査を打ち切る（コンテキスト枯渇防止）

SPECOUT_CROSS_REPO_INTERFACE_DOC: docs/projects/{project-name}/inter-repo/repo-map.md
# クロスリポジトリ調査時に参照するIF文書パス

SPECOUT_CUTOFF_MODULE_BOUNDARIES: 1
# クロスリポジトリ環境では1〜2を推奨（シングルリポジトリは3）
```
