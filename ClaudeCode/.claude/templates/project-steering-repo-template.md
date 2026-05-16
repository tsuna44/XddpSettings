# {REPO_NAME} リポジトリ Steering

> **このファイルについて:**
> - このリポジトリ固有の規約・パターンのみ記載する
> - プロジェクト全体の規約は `project-steering.md`（共通）に委ねる
> - クロスリポジトリのインタフェース規約は `project-steering-cross.md` に委ねる
>
> **更新ルール:**
> - 追加型で更新する（既存エントリを消さず、末尾に追記する）
> - 各エントリに更新日と理由を記載する
> - パターン中心で記述する（個別ファイルの列挙ではなく）
> - 1セクション 100〜200 行を目安に保つ
> - 認証情報・APIキーは絶対に記載しない
> - 未記入セクションは `/xddp.fill-steering {REPO_NAME}` を実行することで CR の記述内容をもとに自動ドラフトできます

---

## 1. リポジトリ基本情報

```
REPO_NAME: （リポジトリ名 = xddp.config.md の REPOS: キー名と一致）
LANGUAGE: （主要言語: Python / TypeScript / Go / Java / etc.）
FRAMEWORK: （フレームワーク: FastAPI / Next.js / Spring Boot / etc.）
BUILD_TOOL: （ビルドツール: pip / npm / gradle / cargo / etc.）
TEST_FRAMEWORK: （テストフレームワーク: pytest / Jest / JUnit / etc.）
ROLE: （このリポジトリの役割: REST APIサーバー / バックグラウンドジョブ / 共有ライブラリ / etc.）
```

### 主要モジュール役割

```
# 例:
# src/api/       - HTTPエンドポイント（ルーティング・バリデーション）。ビジネスロジックは持たない
# src/services/  - ビジネスロジック。DBに直接アクセスしない
# src/repos/     - DB操作。モデルを直接扱う
# src/models/    - データモデル定義
# src/schemas/   - リクエスト/レスポンス スキーマ
```

（このリポジトリの主要モジュールとその役割をここに記述する）

---

## 2. アーキテクチャ概要

### ディレクトリ構造ルール

```
# 例:
# src/
#   {domain}/          - ドメイン単位でディレクトリを切る
#     routes.py        - FastAPI router
#     service.py       - ビジネスロジック
#     repository.py    - DB操作
#     schemas.py       - Pydantic スキーマ
# tests/
#   unit/              - ユニットテスト
#   integration/       - 統合テスト
```

（このリポジトリのディレクトリ構造ルールをここに記述する）

### 主要コンポーネント依存関係

```
# 例:
# routes → services → repositories → models
# routes → schemas（バリデーション）
# ※ routes から repositories への直接アクセス禁止（services を経由すること）
```

（このリポジトリのコンポーネント依存関係をここに記述する）

---

## 3. 命名規約

### ファイル・ディレクトリ
```
# 例:
# ソースファイル: snake_case.py
# テストファイル: test_*.py
# ディレクトリ: snake_case/
```

（このリポジトリ固有の命名規約をここに記述する）

### クラス・関数・変数
```
# 例:
# クラス: PascalCase
# 関数・メソッド: snake_case
# 定数: UPPER_SNAKE_CASE
# プライベート: _prefix
# 型エイリアス: PascalCase（例: UserId = int）
```

（このリポジトリ固有の命名規約をここに記述する）

### DB・API
```
# 例:
# テーブル名: snake_case（複数形）
# カラム名: snake_case
# APIエンドポイント: /kebab-case/{id}
# イベント名: {entity}.{action}（例: task.created）
```

（このリポジトリ固有の DB・API 命名規約をここに記述する）

---

## 4. コーディング規約・既存パターン

> コードベースで使われているパターンを記述する。新しい実装はこれに従う。

### このリポジトリ固有のエラーハンドリング
```python
# 例: カスタム例外クラスの使用
# class TaskNotFoundError(AppError):
#     def __init__(self, task_id: int):
#         super().__init__(f"Task {task_id} not found", code="TASK_NOT_FOUND")
```

（このリポジトリ固有のエラーハンドリングパターンをここに記述する）

### 非同期処理パターン
```
# 例:
# - DB操作は async/await で統一
# - バックグラウンドタスクは Celery（direct call 禁止）
```

（このリポジトリ固有の非同期処理パターンをここに記述する）

### テストパターン
```
# 例:
# - ユニットテストは tests/unit/ 配下
# - フィクスチャは conftest.py に集約
# - 外部依存はモックする（DB は TestClient + テスト用 DB を使う）
```

（このリポジトリ固有のテストパターンをここに記述する）

---

## 5. アーキテクチャ決定記録（ADR）

> このリポジトリに固有の設計判断を記録する。
> プロジェクト全体の ADR は `project-steering.md` に記載する。

<!-- ADRエントリのフォーマット:
### ADR-NNN: （タイトル）
- **決定:** （採用した方式）
- **理由:** （なぜこの方式を選んだか）
- **却下した代替案:** （なぜ却下したか）
- **記録日:** YYYY-MM-DD / **更新CR:** {CR}
-->

（このリポジトリ固有のアーキテクチャ決定をここに記録する）

---

## 6. 禁止事項・注意事項

> このリポジトリ固有の過去問題・インシデントから学んだルール。

```
# 例:
# ❌ routes から repository を直接 import 禁止（services を必ず経由）
# ❌ SQLAlchemy セッションを routes 層でクローズ禁止（依存注入で管理）
# ⚠️ {ライブラリ} を X.Y 以上に上げると {機能} が壊れる（Issue #NNN 参照）
```

（このリポジトリ固有の禁止事項・注意事項をここに記述する）

---

## 7. 変更履歴

| 日付 | 更新CR | 更新内容 |
|------|--------|---------|
| YYYY-MM-DD | {CR} | 初期作成 |
