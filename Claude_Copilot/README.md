# XDDP AIエージェントツールセット

XDDP（eXtreme Derivative Development Process）派生開発の全フェーズをAIがサポートするツールセット。
Claude Code（グローバル配置）とGitHub Copilot Chatの両方に対応する。

---

## フォルダ構成

```
XDDP-AIエージェントツールセット/
├── README.md
├── ROADMAP.md
│
├── claude/                          ← ~/claude/ にそのままコピーする
│   ├── .claude/
│   │   ├── commands/                ← xddp.01〜25（グローバルコマンド）
│   │   └── skills/                  ← 全Skill・サポートファイル
│   └── xddp/
│       └── templates/               ← Markdownテンプレート（Copilotと共有）
│           ├── CR-template.md
│           ├── 変更要求仕様書-template.md
│           ├── TM-template.md
│           ├── 変更設計書-template.md
│           ├── テストケース-template.md
│           ├── テスト結果記録-template.md
│           ├── 衝突チェック-template.md
│           ├── 修正ループ管理-template.md
│           └── specout/
│               ├── specout-00-summary-template.md
│               ├── specout-01-constants-template.md
│               ├── specout-02-structure-template.md
│               ├── specout-03-process-template.md
│               ├── specout-04-control-template.md
│               └── specout-05-state-template.md
│
├── copilot/                         ← プロジェクトルートにコピーする
│   └── .github/
│       ├── copilot-instructions.md  ← 常時適用：プロジェクト共通ルール
│       ├── instructions/            ← ファイル種別ごとの自動適用ルール
│       ├── agents/                  ← @名前 or ドロップダウンで起動（必須）
│       └── prompts/                 ← /xddp.NN.xxx スラッシュコマンド（任意）
│
└── examples/                        ← 記入例（CR-2024-031）
    └── CR-2024-031/
```

---

## セットアップ手順

### Claude Code（グローバル配置）

```bash
# ~/claude/ にコピー（初回）
cp -r claude/ ~/claude/

# 更新時
cp -r claude/.claude/commands/ ~/claude/.claude/commands/
cp -r claude/.claude/skills/   ~/claude/.claude/skills/
cp -r claude/xddp/             ~/claude/xddp/
```

Claude Codeから `/xddp.01.requirements` のようにスラッシュコマンドで呼び出せる。

### GitHub Copilot Chat（プロジェクト配置）

```bash
# プロジェクトルートにコピー（agents・instructionsは必須）
cp -r copilot/.github/ ./.github/
```

#### 呼び出し方

| 方法 | 構文 | 必要ファイル |
|------|------|------------|
| ドロップダウン選択 | Chatのエージェント選択欄から選ぶ | `agents/*.agent.md`（必須） |
| @メンション | `@xddp.01.requirements` | `agents/*.agent.md`（必須） |
| スラッシュコマンド | `/xddp.01.requirements` | `prompts/*.prompt.md`（任意） |

**スラッシュコマンドが不要な場合は `prompts/` フォルダごと削除して問題ない。**
`agents/` さえあれば全機能が使える。

#### agents と prompts の違い

| | `agents/*.agent.md` | `prompts/*.prompt.md` |
|-|---|---|
| 呼び出し方 | ドロップダウン・@ | `/スラッシュコマンド` |
| handoffs（次フェーズ誘導ボタン） | ✅ あり | ❌ なし |
| 別コンテキスト起動（xddp.18・21） | ✅ `send: false` で実現 | ❌ なし |
| 内容 | 同一（どちらも全25本） | 同一 |

フェーズ間のhandoffsボタンや別コンテキスト起動を活用したい場合は
`agents/` を使うことを推奨する。

### テンプレートの共有

テンプレートは `~/claude/xddp/templates/` に一元管理されており、
Claude CodeとCopilot Chatの両方から参照する。

### カテゴリのカスタマイズ

変更要求仕様書のカテゴリは2段階で設定できる：

```
優先順位1：プロジェクトルートの .xddp/categories.md  ← プロジェクト固有
優先順位2：~/claude/xddp/categories.md               ← グローバル共通
優先順位3：コマンド内デフォルト定義                    ← フォールバック
```

**カテゴリを変更したい場合：**
```bash
# プロジェクト固有に設定する場合
mkdir -p .xddp
cp examples/.xddp/categories.md .xddp/categories.md
# categories.md を編集してカテゴリを追加・変更・削除する
```

`~/claude/xddp/categories.md` を編集すると全プロジェクト共通のカテゴリが変わる。

---

## コマンド一覧（全25本）

### フェーズとコマンドの対応

```
【要求分析フェーズ】
  xddp.01.requirements      CR → 要求分析結果
  xddp.02.req-ai-review     AIによる批判的レビュー（🔴必須修正→ループ）
  xddp.03.req-review-fix    指摘反映 → AI再レビュー → 人間承認

【変更要求仕様書フェーズ】
  xddp.04.crs-draft         要求分析結果 → 変更要求仕様書ドラフト（Markdown）
  xddp.05.crs-ai-review     AIによる批判的レビュー（🔴必須修正→ループ）
  xddp.06.crs-excel         Markdown → Excel変換

【ソース調査フェーズ】
  xddp.07.specout           スペックアウト調査（波紋検索・打ち切り基準・自動分割）
  xddp.08.specout-ai-review AIによる批判的レビュー（🔴必須修正→ループ）
  xddp.09.specout-review-fix 指摘反映 → AI再レビュー → 人間承認
  xddp.10.specout-feedback  スペックアウト結果 → 仕様書フィードバック

【変更設計フェーズ】
  xddp.11.tm-generate       スペックアウト資料 → TM自動生成
  xddp.12.design-draft      TM＋スペックアウト資料 → 変更設計書ドラフト生成
  xddp.13.design-ai-review  AIによる批判的レビュー（🔴必須修正→ループ）
  xddp.14.design-review-fix 指摘反映 → AI再レビュー → 人間承認

【並行CR管理】
  xddp.15.conflict-check    並行CR衝突検知（コーディング開始前に実行）

【実装フェーズ】
  xddp.16.coding            変更設計書 → ソースコード変更
  xddp.17.verify            自己確認（設計書の確認項目とコードの照合）
  xddp.18.coding-ai-review  別コンテキストAIによるコードレビュー（🔴必須修正→ループ）
  xddp.19.coding-review-fix 指摘反映 → AI再レビュー → 人間承認

【テストフェーズ】
  xddp.20.testcase          テストケース生成
  xddp.21.testcase-ai-review 別コンテキストAIによるレビュー（TC漏れ検出含む）
  xddp.22.testcase-review-fix 指摘反映 → AI再レビュー → 人間承認
  xddp.23.test-feedback     テストNG → 変更設計書フィードバック
                            （原因A:実装/B:設計/C:仕様/D:テスト仕様）

【ベースライン更新フェーズ】（テスト完了後・一定期間ごと）
  xddp.24.spec-update       システム仕様書の更新（変更後の全体構成）
  xddp.25.design-update     システム設計書の更新（7種類の図）
```

### レビューループの共通ルール

```
AIレビュー（xddp.NN.xxx-ai-review）
  ↓ 🔴必須修正あり
指摘反映（xddp.NN.xxx-review-fix）→ AIが必ず再レビュー → 🔴なしまでループ
  ↓ 🔴必須修正なし
人間レビュー ← 必ず実施（AIレビューのみで次フェーズへ進まない）
  ↓ 指摘あり
指摘反映（xddp.NN.xxx-review-fix）→ AIが必ず再レビュー
  ↓ 人間承認
次フェーズへ
```

---

## 記入例

`examples/CR-2024-031/` に「温度センサー異常検知のしきい値変更」を題材にした
一貫したサンプルが含まれている。
