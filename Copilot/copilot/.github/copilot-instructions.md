# XDDP派生開発 プロジェクト共通ルール

このプロジェクトはXDDP（eXtreme Derivative Development Process）に従って開発する。

## 成果物構成

```
CR-YYYY-NNN/
├── CR-YYYY-NNN.md                  # 変更要求書
├── 変更要求仕様書-CRS-YYYY-NNN.md  # 変更要求仕様書
├── スペックアウト-CR-YYYY-NNN.md   # スペックアウト資料
├── TM-CR-YYYY-NNN.xlsx             # TM（Excel）
├── 変更設計書-CR-YYYY-NNN.md       # 変更設計書
├── テストケース-CR-YYYY-NNN.md     # テストケース
└── テスト結果記録-CR-YYYY-NNN.md   # テスト結果
```

## コーディングルール

- ソースコードの変更は必ず変更設計書に基づいて行う
- 変更設計書にない変更を勝手に加えない
- 変更箇所に必ず以下のタグコメントを付与する：
  - `[ADD-{仕様番号}]` 新規追加
  - `[MOD-{仕様番号}]` 変更
  - `[DEL-{仕様番号}]` 削除
- 変更前コードはGitで管理するためコメントに残さない
- リファクタリングと機能変更を同一コミットに混在させない

## コミットメッセージ規約

```
[CR-YYYY-NNN] {変更概要}

変更仕様：CRS-NNN-XX-XX, CRS-NNN-XX-XX
変更ファイル：{ファイル名}
```

## ステータス管理

仕様・テストケースのステータスは以下の4段階：
作成中 / レビュー待ち / 承認済み / 却下

## プロンプトファイルの使い方

以下のスラッシュコマンドで各フェーズのアシスタントを呼び出せる：

| コマンド | 用途 |
|---------|------|
| `/xddp-requirements` | CRから変更要求仕様書を作成 |
| `/xddp-specout` | スペックアウト調査を実施 |
| `/xddp-specout-feedback` | スペックアウト結果を仕様書に反映 |
| `/xddp-conflict-check` | 並行CRの衝突を検知 |
| `/xddp-tm-generate` | 変更設計書からTMを生成 |
| `/xddp-coding` | 変更設計書に基づいてコードを変更 |
| `/xddp-verify` | 変更後の確認項目をチェック |
| `/xddp-testcase` | テストケースを生成 |
| `/xddp-test-feedback` | テストNGを変更設計書に反映 |
