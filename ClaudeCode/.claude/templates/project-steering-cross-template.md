# クロスリポジトリ Steering

> **このファイルについて:**
> - リポジトリ間にまたがるインタフェース規約・命名規則・変更手順を記載する
> - 単一リポジトリ内の規約は各 `project-steering-{repo}.md` に委ねる
> - プロジェクト全体の規約（チーム・開発プロセス等）は `project-steering.md`（共通）に委ねる
>
> **更新ルール:**
> - 追加型で更新する（既存エントリを消さず、末尾に追記する）
> - 各エントリに更新日と理由を記載する
> - インタフェース変更時は必ず §6「インタフェース変更手順」に従う
> - 認証情報・APIキーは絶対に記載しない
> - 未記入セクションは `/xddp.fill-steering cross` を実行することで CR の記述内容をもとに自動ドラフトできます

---

## 1. 対象リポジトリ一覧

> `xddp.config.md` の `REPOS:` と一致させること。

| リポジトリ名 | 役割 | 提供インタフェース | 消費インタフェース |
|------------|------|----------------|----------------|
| （例）tasksaas-api | REST API サーバー | POST /jobs, GET /tasks | — |
| （例）tasksaas-worker | バックグラウンドジョブ | POST /notify（経由） | POST /jobs |
| （例）tasksaas-shared | 共有モデル | TaskSchema, JobSchema | — |

### リポジトリ間依存関係

```
# 提供 → 消費 の形式で記述する（トポロジカル順序）
# 例:
# tasksaas-shared → tasksaas-api（モデル import）
# tasksaas-shared → tasksaas-worker（モデル import）
# tasksaas-api    → tasksaas-worker（POST /jobs でジョブ投入）
# tasksaas-worker → tasksaas-notify（HTTP POST で通知トリガー）
```

（実際のリポジトリ間依存関係をここに記述する）

---

## 2. API バージョニング規約

### バージョン形式

セマンティックバージョニング（MAJOR.MINOR.PATCH）を採用する。

| 変更種別 | バージョン変更 | breaking |
|---------|--------------|---------|
| フィールド削除・型変更・エンドポイント削除 | MAJOR を+1（例: 1.x.x → 2.0.0） | true |
| フィールド追加・オプション引数追加 | MINOR を+1（例: 1.0.x → 1.1.0） | false |
| ドキュメント修正のみ | PATCH を+1（例: 1.0.0 → 1.0.1） | false |
| 新規インタフェース（初版） | 1.0.0 から開始 | false |

### breaking: true の場合の必須対応

```
1. cross/CHD の「インタフェース変更サマリ」に breaking: true を明記する
2. §6「インタフェース変更手順」の通知手続きを行う
3. 移行期間中は旧バージョンとの並行運用（デュアルサポート）を行う
4. xddp.close 時に AI_INDEX.md に「⚠️ 破壊的変更あり」として記録される
```

（プロジェクト固有の SemVer 運用ルールをここに追記する）

---

## 3. インタフェース命名規則

### APIエンドポイント
```
# 形式: /{resource}/{id}/{sub-resource}
# 例:
# GET  /tasks           - リスト取得
# GET  /tasks/{id}      - 単件取得
# POST /tasks           - 新規作成
# PUT  /tasks/{id}      - 全項目更新
# PATCH /tasks/{id}     - 部分更新
# DELETE /tasks/{id}    - 削除
```

### イベント・メッセージキー
```
# 形式: {entity}.{action}（ドット区切り・スネークケース）
# 例:
# task.created
# task.updated
# job.completed
# job.failed
```

### 共有モデル・スキーマ
```
# 形式: PascalCase + 用途サフィックス
# 例:
# TaskSchema      - API リクエスト/レスポンス用
# TaskModel       - DB モデル用
# TaskEvent       - イベントペイロード用
```

（プロジェクト固有の命名規則をここに追記する）

---

## 4. エラーコード・ステータスコード体系

### HTTPステータスコード運用

```
# 200 OK         - 成功（GET・PUT・PATCH）
# 201 Created    - 作成成功（POST）
# 204 No Content - 削除成功（DELETE）
# 400 Bad Request      - バリデーションエラー（クライアント起因）
# 401 Unauthorized     - 認証失敗
# 403 Forbidden        - 認可失敗
# 404 Not Found        - リソース不存在
# 409 Conflict         - 重複・競合
# 422 Unprocessable    - スキーマ違反
# 500 Internal Server Error - サーバー起因エラー
```

### アプリケーションエラーコード
```
# 形式: {DOMAIN}_{ERROR_TYPE}（大文字スネークケース）
# 例:
# TASK_NOT_FOUND
# TASK_ALREADY_COMPLETED
# JOB_QUEUE_FULL
```

（プロジェクト固有のエラーコード一覧をここに記述する）

---

## 5. サービス間認証方式

```
# 例:
# 方式: JWT Bearer Token（service-to-service）
# トークン発行: 認証サービス（tasksaas-auth）が発行
# 有効期限: 1時間（リフレッシュトークン: 30日）
# ヘッダー: Authorization: Bearer {token}
# 内部通信: mTLS（本番環境のみ）
```

（プロジェクト固有の認証方式をここに記述する）

---

## 6. インタフェース変更手順

### 事前通知ルール

```
1. 変更する CR の CRS-{CR}.md に「影響リポジトリ」と「インタフェース変更内容」を記載する
2. breaking: true の場合は、影響を受けるダウンストリームリポジトリの担当者に通知する
3. xddp.05.arch で cross/DSN を先行生成し、ダウンストリームの実装より前にインタフェース契約を確定する
```

### 移行期間定義

```
# breaking: true の MAJOR バージョンアップ時:
# - 最低 {N} スプリント（例: 2スプリント = 4週間）の並行運用期間を設ける
# - 旧バージョンの廃止日を cross/interfaces/{name}-spec.md の「移行ガイド」セクションに明記する
# - 廃止日以降は旧バージョンのエンドポイントを削除してよい
```

（プロジェクト固有の移行期間ルールをここに記述する）

---

## 7. 変更履歴

| 日付 | 更新CR | 更新内容 |
|------|--------|---------|
| YYYY-MM-DD | {CR} | 初期作成 |
