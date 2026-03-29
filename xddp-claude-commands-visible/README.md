# XDDP Agent — Claude Code カスタムスラッシュコマンド

Claude Code（VSCode拡張）でXDDPプロセスを実行するカスタムコマンド一式です。
Node.js・ビルド・サーバー不要。ファイルをコピーするだけで使えます。

## 前提条件
- VSCode
- Claude Code 拡張機能（Anthropic公式）
- Anthropic API キー（Claude Code の設定で管理）

## セットアップ

```bash
# 1. ZIPを展開
unzip xddp-claude-commands.zip

# 2. プロジェクトルートにコピー
cp -r xddp-claude-commands-visible/claude your-project/

# 3. .claude/ にリネーム（先頭にドットを付ける）
mv your-project/claude your-project/.claude
```

**Windowsの場合：**
```powershell
Expand-Archive xddp-claude-commands.zip
Copy-Item xddp-claude-commands-visible\claude your-project\claude -Recurse
Rename-Item your-project\claude .claude
```

## フォルダ構成

```
.claude/
├── commands/          ← スラッシュコマンド
└── skills/
    └── xddp-coding/
        └── coding-rules.md  ← 変更コメント規約・コミットメッセージ規約
```

## 成果物フォルダ構造

```
project-root/
└── CR-YYYY-NNN/                           ← CRごとのフォルダ
    ├── CR-YYYY-NNN.md                     ← 変更要求書（入力）
    ├── 変更要求仕様書-CRS-YYYY-NNN.md     ← 要求分析成果物
    ├── スペックアウト-CR-YYYY-NNN.md      ← スペックアウト成果物
    ├── TM-CR-YYYY-NNN.md                 ← トレーサビリティマトリクス
    ├── 変更設計書-CR-YYYY-NNN.md         ← 設計・コーディング成果物
    ├── テストケース-CR-YYYY-NNN.md       ← テスト仕様書
    ├── テスト結果記録-CR-YYYY-NNN.md     ← テスト実施記録
    ├── 衝突チェック-CR-YYYY-NNN.md       ← 並行CR衝突チェック記録
    └── 修正ループ管理-CR-YYYY-NNN.md     ← テストNG修正ループ管理
```

## コマンド一覧

### メインフロー（番号順に実行）

| コマンド | フェーズ | 役割 |
|---------|--------|-----|
| `/xddp.01.req.start` | 要求分析 | CRからウォンツ/ニーズ/制約を分類・変更要求仕様書を生成 |
| `/xddp.02.req.review` | 要求分析レビュー | 👔ビジネス / 🔍影響範囲 / ⚠️リスク の3視点でレビュー |
| `/xddp.03.spec.start` | スペックアウト | 波紋検索・打ち切り基準でコード調査・Mermaid図生成 |
| `/xddp.04.spec.review` | スペックアウトレビュー | 📋網羅性 / 🔄変更影響 / 🛠️設計準備 の3視点でレビュー |
| `/xddp.05.design.start` | 設計 | 外部・内部設計書を生成 |
| `/xddp.06.design.review` | 設計レビュー | 🏗️アーキテクチャ / 🔧実装容易性 / 🔒セキュリティ の3視点でレビュー |
| `/xddp.07.code.start` | コーディング | ADD/MOD/DELタグ規約に従い差分コードを実装 |
| `/xddp.08.code.review` | コーディングレビュー | 💎品質 / 🔐セキュリティ / ⚡パフォーマンス の3視点でレビュー |
| `/xddp.09.test.spec` | テスト仕様書 | WB/回帰/統合テストケースを生成（コードは作らない） |
| `/xddp.10.test.review` | テスト仕様書レビュー | 📋網羅性 / 🎯実行可能性 / 🔄整合性 の3視点でレビュー（品質ゲート） |
| `/xddp.11.test.code` | テストコード実装 | 承認済み仕様書を元にテストコードを実装 |

### 随時実行コマンド（番号なし）

| コマンド | 役割 |
|---------|-----|
| `/xddp.revise` | レビュー結果＋人の指摘を反映して成果物を修正（全フェーズ共通） |
| `/xddp.spec.feedback` | スペックアウトで判明した事項を変更要求仕様書に反映 |
| `/xddp.tm.generate` | 変更設計書からTM（●変更/○参照）を自動生成 |
| `/xddp.code.verify` | コーディング後の静的確認（ADD/MOD/DELタグ・設計書整合性チェック） |
| `/xddp.test.feedback` | テストNG原因分類（A実装ミス/B設計ミス/C仕様ミス/D仕様ミス）→修正エントリ追加 |
| `/xddp.conflict.check` | 並行CR衝突検知（Type1ファイル/Type2仕様/Type3定数/Type4順序） |
| `/xddp.status` | 全フェーズ進捗を確認 |

## 標準的な使用フロー

```
CR受領
  ↓
/xddp.01.req.start   CRを分析してウォンツ/ニーズ/制約を分類
/xddp.conflict.check 並行CRとの衝突を事前確認（コーディング前に推奨）
/xddp.02.req.review  AIレビュー → /xddp.revise（必要なら）
👤 人によるレビュー・承認

/xddp.03.spec.start  波紋検索でコード調査・Mermaid図生成
/xddp.spec.feedback  判明した事項を変更要求仕様書に反映
/xddp.04.spec.review AIレビュー → /xddp.revise（必要なら）
👤 人によるレビュー・承認

/xddp.05.design.start 設計書生成
/xddp.tm.generate     変更設計書からTMを自動生成
/xddp.06.design.review AIレビュー → /xddp.revise（必要なら）
👤 人によるレビュー・承認

/xddp.07.code.start   コーディング（ADD/MOD/DELタグ規約に従う）
/xddp.code.verify     変更後の静的確認（タグ付与・設計書整合性）
/xddp.08.code.review  AIレビュー → /xddp.revise（必要なら）
👤 人によるレビュー・承認

/xddp.09.test.spec    テスト仕様書のみ生成（WB/回帰/統合）
/xddp.10.test.review  AIレビュー → /xddp.revise（仕様書の品質ゲート）
👤 人によるレビュー・承認

/xddp.11.test.code    承認済み仕様書からテストコードを実装
👤 テスト実施

  ↓ NGが発生した場合
/xddp.test.feedback   NG原因分類→修正エントリを変更設計書に追加
/xddp.conflict.check  修正による新たな衝突がないかを確認
/xddp.07.code.start   修正エントリをコードに反映
/xddp.code.verify     静的確認
  → テスト再実施（3回を超える場合はCR全体の見直しを推奨）
```

## コーディング規約

`coding-rules.md` に以下が定義されています：

**変更コメント規約：**
```c
/* [ADD-CRS-YYYY-NNN-01-01] 変更概要 */  新規追加
/* [MOD-CRS-YYYY-NNN-01-01] 変更概要 */  変更
/* [DEL-CRS-YYYY-NNN-01-01] 変更概要 */  削除
```

**コミットメッセージ規約：**
```
[CR-YYYY-NNN] 変更概要

変更仕様：CRS-NNN-XX-XX, CRS-NNN-XX-XX
変更ファイル：ファイル名
```

## 大規模コードベース（400kstep〜）での運用

`/xddp.03.spec.start` は波紋検索と5段階の打ち切り基準を実装しています：
- **基準1**: アーキテクチャ境界（引数・戻り値の型が変わらない）
- **基準2**: パススルー関数（値を加工せず渡すだけ）
- **基準3**: 別リポジトリへの影響がIF仕様変更なし
- **基準4**: テストコードのみの参照
- **基準5**: 過去CRで調査済みの箇所

打ち切り基準は「影響がない根拠」を必ずスペックアウト資料に記録してください（根拠なき打ち切りは禁止）。
