# XDDP AIエージェント — GitHub Copilot Chat 版

## フォルダ構成

```
.github/
├── copilot-instructions.md          # 常時適用：プロジェクト共通ルール
├── instructions/
│   └── xddp-coding-rules.instructions.md  # C/C++ファイル編集時に自動適用
└── prompts/
    ├── xddp-requirements.prompt.md        # /xddp-requirements
    ├── xddp-specout.prompt.md             # /xddp-specout
    ├── xddp-specout-feedback.prompt.md    # /xddp-specout-feedback
    ├── xddp-conflict-check.prompt.md      # /xddp-conflict-check
    ├── xddp-tm-generate.prompt.md         # /xddp-tm-generate
    ├── xddp-coding.prompt.md              # /xddp-coding
    ├── xddp-verify.prompt.md              # /xddp-verify
    ├── xddp-testcase.prompt.md            # /xddp-testcase
    └── xddp-test-feedback.prompt.md       # /xddp-test-feedback
```

## セットアップ手順

1. このフォルダの内容をプロジェクトのルートにコピーする
2. VSCodeでプロジェクトを開く
3. GitHub Copilot拡張機能がインストールされていることを確認する
4. Copilot Chatを開く（`Ctrl+Shift+I` / `Cmd+Shift+I`）

## 使い方

### プロンプトファイルの呼び出し

Copilot Chatの入力欄に `/` と入力するとプロンプト一覧が表示される。

```
/xddp-requirements   # CRを分析して変更要求仕様書を作成
/xddp-specout        # スペックアウト調査を実施
/xddp-coding         # 変更設計書に基づいてコードを変更
/xddp-verify         # 変更後の確認項目をチェック
/xddp-testcase       # テストケースを生成
/xddp-test-feedback  # テストNGを変更設計書に反映
/xddp-conflict-check # 並行CRの衝突を検知
/xddp-specout-feedback # スペックアウト結果を仕様書に反映
/xddp-tm-generate    # 変更設計書からTMを生成
```

### ファイルのアタッチ

各プロンプトを呼び出す際は、関連ファイルをアタッチすると精度が上がる。

```
例：/xddp-requirements #CR-2024-031.md
例：/xddp-coding #変更設計書-CR-2024-031.md #sensor_detect.c
例：/xddp-conflict-check #TM-CR-2024-031.xlsx #TM-CR-2024-032.xlsx
```

## Claude Code版との対応関係

| Claude Code | GitHub Copilot Chat | 説明 |
|---|---|---|
| `CLAUDE.md` | `copilot-instructions.md` | 常時適用のプロジェクトルール |
| `.claude/skills/*/SKILL.md` | `.github/prompts/*.prompt.md` | `/コマンド名`で呼び出すプロンプト |
| `coding-rules.md`（Skill内参照） | `*.instructions.md`（applyToで自動適用） | ファイル種別ごとのルール |
