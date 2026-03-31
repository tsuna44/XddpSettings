# XDDP派生開発 プロジェクト共通ルール

このプロジェクトはXDDP（eXtreme Derivative Development Process）に従って開発する。

## テンプレートの場所

Markdownテンプレートは Claude Code と共有しており、以下のパスに格納されている：

```
~/claude/xddp/templates/
├── CR-template.md
├── 変更要求仕様書-template.md
├── TM-template.md
├── 変更設計書-template.md
├── テストケース-template.md
├── テスト結果記録-template.md
├── 衝突チェック-template.md
├── 修正ループ管理-template.md
└── specout/
    ├── specout-00-summary-template.md
    ├── specout-01-constants-template.md
    ├── specout-02-structure-template.md
    ├── specout-03-process-template.md
    ├── specout-04-control-template.md
    └── specout-05-state-template.md
```

各エージェントを実行する際は、上記テンプレートを参照して成果物を生成すること。

## 成果物構成

```
CR-YYYY-NNN/
├── CR-YYYY-NNN.md                  # 変更要求書
├── 変更要求仕様書-CRS-YYYY-NNN.md  # 変更要求仕様書（Markdown）
├── 変更要求仕様書-CRS-YYYY-NNN.xlsx # 変更要求仕様書（Excel）
├── specout/                        # スペックアウト資料（自動分割）
│   ├── specout-00-summary.md
│   ├── specout-01-constants.md
│   ├── specout-02-structure.md
│   ├── specout-03-process.md
│   ├── specout-04-control.md
│   └── specout-05-state.md
├── TM-CR-YYYY-NNN.xlsx             # TM（Excel）
├── 変更設計書-CR-YYYY-NNN.md       # 変更設計書
├── テストケース-CR-YYYY-NNN.md     # テストケース
├── テスト結果記録-CR-YYYY-NNN.md   # テスト結果
├── 衝突チェック-CR-YYYY-NNN.md     # 衝突チェック記録
└── 修正ループ管理-CR-YYYY-NNN.md   # 修正ループ管理
```

## コーディングルール

- ソースコードの変更は必ず変更設計書に基づいて行う
- 変更設計書にない変更を加えない
- 変更箇所に必ず以下のタグコメントを付与する：
  - `[ADD-{仕様番号}]` 新規追加
  - `[MOD-{仕様番号}]` 変更
  - `[DEL-{仕様番号}]` 削除
- 変更前コードはGitで管理するためコメントに残さない

## コミットメッセージ規約

```
[CR-YYYY-NNN] {変更概要}

変更仕様：CRS-NNN-XX-XX, CRS-NNN-XX-XX
変更ファイル：{ファイル名}
```

## ステータス管理

仕様・テストケースのステータスは以下の4段階：
作成中 / レビュー待ち / 承認済み / 却下

## エージェントの使い方

Copilot Chatの入力欄左のエージェントドロップダウンから選択するか、
`@xddp.01.requirements` のように@で呼び出す。

各エージェントはフェーズ完了後に次フェーズへのhandoffボタンを表示する。
別コンテキストが必要なレビュー（xddp.18・xddp.21）はsend: falseで
新セッションとして起動するため、前のコンテキストを引き継がない。
