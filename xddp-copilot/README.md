# XDDP Agent — GitHub Copilot Chat プロンプトファイル一式

GitHub Copilot Chat の Agent Mode でXDDPプロセスを実行するプロンプトファイル一式です。
Node.js・ビルド不要。ファイルをコピーするだけで使えます。

## 前提条件
- VSCode 1.99 以上
- GitHub Copilot ライセンス（Agent Mode 対応）

## セットアップ

```bash
# 1. .github/ フォルダをプロジェクトルートにコピー
cp -r xddp-copilot/.github your-project/
```

**既存の `copilot-instructions.md` との共存：**
XDDPルールは `.github/xddp-instructions.md` として分離されています。
各プロンプトファイルが `#file:.github/xddp-instructions.md` で参照するため、
既存の `copilot-instructions.md` を変更する必要はありません。

## フォルダ構成

```
.github/
├── xddp-instructions.md                    ← XDDPルール（常時参照）
├── instructions/
│   └── xddp-coding-rules.instructions.md  ← C/C++/Python/TS変更時に自動適用
└── prompts/
    ├── xddp-01-req-start.prompt.md         ← フェーズ1: 要求分析
    ├── xddp-02-req-review.prompt.md        ← 要求分析レビュー
    ├── xddp-03-spec-start.prompt.md        ← フェーズ2: スペックアウト
    ├── xddp-04-spec-review.prompt.md       ← スペックアウトレビュー
    ├── xddp-05-design-start.prompt.md      ← フェーズ3: 設計
    ├── xddp-06-design-review.prompt.md     ← 設計レビュー
    ├── xddp-07-code-start.prompt.md        ← フェーズ4: コーディング
    ├── xddp-08-code-review.prompt.md       ← コーディングレビュー
    ├── xddp-09-test-spec.prompt.md         ← フェーズ5: テスト仕様書
    ├── xddp-10-test-review.prompt.md       ← テスト仕様書レビュー
    ├── xddp-11-test-code.prompt.md         ← フェーズ6: テストコード実装
    ├── xddp-revise.prompt.md               ← 再修正（随時）
    ├── xddp-spec-feedback.prompt.md        ← スペックアウトフィードバック（随時）
    ├── xddp-tm-generate.prompt.md          ← TM自動生成（随時）
    ├── xddp-code-verify.prompt.md          ← 変更後静的確認（随時）
    ├── xddp-test-feedback.prompt.md        ← テストNGフィードバック（随時）
    ├── xddp-conflict-check.prompt.md       ← 並行CR衝突検知（随時）
    └── xddp-status.prompt.md               ← 進捗確認（随時）
```

## 使い方

### 1. Agent Mode を有効にする
Copilot Chat（Ctrl+Shift+I）でモードを **Agent** に切り替えます。

### 2. プロンプトファイルを選択して実行

```
# Copilot Chat で 📎 をクリックしてファイルを選択
.github/prompts/xddp-01-req-start.prompt.md
→ 変更目的と既知の影響箇所を入力
```

または Chat に直接入力：
```
#xddp-01-req-start.prompt.md
変更目的：在庫管理システムにSlack通知を追加したい
```

### 3. フロー

```
#xddp-01-req-start.prompt.md   要求分析
#xddp-02-req-review.prompt.md  AIレビュー → #xddp-revise.prompt.md（必要なら）
👤 人によるレビュー・承認

#xddp-03-spec-start.prompt.md  スペックアウト（波紋検索）
#xddp-spec-feedback.prompt.md  スペックアウト→仕様書フィードバック
#xddp-04-spec-review.prompt.md AIレビュー
👤 人によるレビュー・承認

#xddp-05-design-start.prompt.md 設計
#xddp-tm-generate.prompt.md    TM自動生成
#xddp-06-design-review.prompt.md AIレビュー
👤 人によるレビュー・承認

#xddp-07-code-start.prompt.md  コーディング（ADD/MOD/DELタグ規約）
#xddp-code-verify.prompt.md    変更後静的確認
#xddp-08-code-review.prompt.md AIレビュー
👤 人によるレビュー・承認

#xddp-09-test-spec.prompt.md   テスト仕様書（WB/回帰/統合）
#xddp-10-test-review.prompt.md AIレビュー（品質ゲート）
👤 人によるレビュー・承認

#xddp-11-test-code.prompt.md   テストコード実装
👤 テスト実施

  ↓ NGが発生した場合
#xddp-test-feedback.prompt.md  NG原因分類→修正エントリ追加
#xddp-conflict-check.prompt.md 衝突確認
#xddp-07-code-start.prompt.md  修正実装
```

## Claude Code版との対応関係

| Claude Code | Copilot Chat |
|-------------|-------------|
| `/xddp.01.req.start` | `#xddp-01-req-start.prompt.md` |
| `/xddp.revise` | `#xddp-revise.prompt.md` |
| `/xddp.conflict.check` | `#xddp-conflict-check.prompt.md` |
| （他も同様にドット→ハイフン・スラッシュ→#に変換）| |

動作内容・レビュー観点・出力フォーマットはClaude Code版と同一です。
