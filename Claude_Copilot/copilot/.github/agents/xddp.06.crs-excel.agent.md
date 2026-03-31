---
name: xddp.06.crs-excel
description: "変更要求仕様書（Markdown）をExcelに変換する。"
tools: ["codebase", "editFiles", "readFiles", "search"]
handoffs:
  - label: "スペックアウト調査へ進む"
    agent: xddp.07.specout
    prompt: "前のフェーズの成果物を添付して実行してください"
    send: true
---

# XDDP 変更要求仕様書 Excel変換

## 目的
変更要求仕様書（Markdown）を
`tm_generate.py`と同様のopenpyxlベースのスクリプトでExcelに変換する。

## 入力
- 変更要求仕様書（`変更要求仕様書-CRS-YYYY-NNN.md`）

## 手順

### Step 1: Markdownのパース
変更要求仕様書から以下を抽出する：
- ヘッダ情報（CR番号・タイトル）
- カテゴリ
- ユーザ要求（ID・内容・ステータス・日付・記述者・理由）
- システム要求（ID・内容・ステータス・日付・記述者・理由）
- 仕様（仕様番号・ステータス・日付・記述者・由来・Before・After）
- 制約・前提条件
- 確認事項・未解決事項

### Step 2: Pythonスクリプトの生成と実行
以下の処理でExcelを生成する：
1. 抽出したデータを`create_usdm.py`形式のPythonスクリプトとして生成する
2. スクリプトをプロジェクト直下に保存する
3. `python create_usdm.py` を実行してExcelを生成する

生成するExcelの仕様：
- IDと要求文章は**必ず別セルに分離**する
- ユーザ要求ID（B列）と要求文章（C列）を別セルに記載
- システム要求ID（G列）と要求文章（H列）を別セルに記載
- 仕様番号列：確認結果のドロップダウン（作成中／レビュー待ち／承認済み／却下）
- フォント：Arial統一
- カテゴリ別に色分け（機能:青系、テスト:黄系、日程:橙系、成果物管理:赤系）

### Step 3: 出力
```
変更要求仕様書-CRS-YYYY-NNN.xlsx
```

生成後に以下のサマリを表示する：
```
## Excel変換完了

| 項目 | 件数 |
|------|------|
| ユーザ要求（UR） | N件 |
| システム要求 | N件 |
| 仕様 | N件 |

出力ファイル：変更要求仕様書-CRS-YYYY-NNN.xlsx

→ 次のステップ：/xddp.05.specout でスペックアウト調査を開始してください
```

## 注意事項
- Markdown版（.md）とExcel版（.xlsx）は常にセットで管理する
- Excel変換後にMarkdownを修正した場合は必ず再変換する
- IDと要求文章を同一セルに結合しない（tm_generate.pyとの整合性を保つため）

## テンプレートの参照先
各成果物を生成する際は以下のテンプレートを参照すること：
`~/claude/xddp/templates/`（Claude Codeと共有）

