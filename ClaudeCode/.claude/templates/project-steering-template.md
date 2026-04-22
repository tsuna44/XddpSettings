# プロジェクト Steering（プロジェクト記憶）

> **更新ルール：**
> - 追加型で更新する（既存エントリを消さず、末尾に追記する）
> - 各エントリに更新日と理由を記載する
> - パターン中心で記述する（個別ファイルの列挙ではなく）
> - 1セクション 100〜200 行を目安に保つ
> - 認証情報・APIキーは絶対に記載しない

---

## 1. プロジェクト概要

```
PROJECT_NAME: （プロジェクト名）
LANGUAGE: （主要言語: Python / TypeScript / Go / Java / etc.）
FRAMEWORK: （フレームワーク: FastAPI / Next.js / Spring Boot / etc.）
ARCHITECTURE: （アーキテクチャ: モノリス / マイクロサービス / etc.）
DB: （データベース: PostgreSQL / MySQL / DynamoDB / etc.）
TEST_FRAMEWORK: （テストフレームワーク: pytest / Jest / JUnit / etc.）
```

---

## 2. 命名規約

### ファイル・ディレクトリ
```
# 例:
# ソースファイル: snake_case.py / camelCase.ts
# テストファイル: test_*.py / *.spec.ts
# ディレクトリ: kebab-case/ / snake_case/
```

（プロジェクト固有の命名規約をここに記述する）

### クラス・関数・変数
```
# 例:
# クラス: PascalCase
# 関数: snake_case（Python）/ camelCase（TypeScript）
# 定数: UPPER_SNAKE_CASE
# プライベート: _prefix
```

（プロジェクト固有の命名規約をここに記述する）

### DB・API
```
# 例:
# テーブル名: snake_case（複数形）
# カラム名: snake_case
# APIエンドポイント: /kebab-case/{id}
```

（プロジェクト固有の命名規約をここに記述する）

---

## 3. アーキテクチャ決定記録（ADR）

> 採用・不採用を問わず、重要な設計判断とその理由を記録する。

<!-- ADRエントリのフォーマット:
### ADR-NNN: （タイトル）
- **決定:** （採用した方式）
- **理由:** （なぜこの方式を選んだか）
- **却下した代替案:** （なぜ却下したか）
- **記録日:** YYYY-MM-DD
-->

（プロジェクト固有のアーキテクチャ決定をここに記録する）

---

## 4. 既存パターン・慣習

> コードベースで使われているパターンを記述する。新しい実装はこれに従う。

### エラーハンドリング
```
# 例:
# - 外部API呼び出しは必ず try/except で囲む
# - HTTPエラーは {code, message, detail} 形式のJSONで返す
# - ログは logger.exception() でスタックトレース付きで出力
```

### 非同期処理
```
# 例:
# - I/O待ちは async/await を使う
# - バックグラウンドタスクは Celery ではなく asyncio.create_task を使う
```

### テストパターン
```
# 例:
# - ユニットテストは tests/unit/ 配下
# - 統合テストは tests/integration/ 配下
# - フィクスチャは conftest.py に集約
# - モックは unittest.mock を使う（pytest-mock は使わない）
```

（プロジェクト固有のパターンをここに記述する）

---

## 5. 禁止事項・注意事項

> 過去の問題・インシデントや強い制約から学んだルール。

```
# 例:
# ❌ mainブランチへの直接コミット禁止
# ❌ 本番DBへの直接接続（必ずread replicaを経由）
# ❌ Secrets のハードコード（必ず環境変数 or Secrets Manager）
# ⚠️ Xライブラリのバージョンを上げると Y機能が壊れる（Issue #123 参照）
```

（プロジェクト固有の禁止事項・注意事項をここに記述する）

---

## 6. モジュール構成メモ

> 主要モジュールの役割と境界を記述する。新規実装前に参照すること。

```
# 例:
# src/
#   api/        - HTTPエンドポイント（FastAPI router）。ビジネスロジックは持たない
#   services/   - ビジネスロジック。DBに直接アクセスしない
#   repositories/ - DB操作。SQLAlchemyモデルを直接扱う
#   models/     - SQLAlchemyモデル定義
#   schemas/    - Pydanticスキーマ（リクエスト/レスポンス）
#   utils/      - 純粋関数のユーティリティ
```

（プロジェクト固有のモジュール構成をここに記述する）

---

## 7. 変更履歴

| 日付 | 更新者 | 更新内容 |
|------|--------|---------|
| YYYY-MM-DD | CR番号 | 初期作成 |
