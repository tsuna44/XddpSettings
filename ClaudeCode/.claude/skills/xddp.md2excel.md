---
description: CRS Markdown から USDM 形式の Excel を生成する（UR-017/018/020）。「ExcelファイルをCRSから生成して」「変更要求仕様書のExcelを出力して」などで起動する。
---

You are executing **XDDP CRS → Excel Generation** (Markdown → Excel).

**Arguments:** $ARGUMENTS = [CR_NUMBER]（省略可）
- CR_NUMBER: 省略時は XDDP_DIR 配下から自動検出

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.

(xddp.config.md の探索は xddp.common.md 内で完了済み。WORKSPACE_ROOT・XDDP_DIR を引き続き使用する)
Let `CRS_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.md`
Let `OUT_PATH`  = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.xlsx`

---

## 1. Generate Excel

`~/.claude/templates/crs_md2excel.py` が Markdown パース・Excel 生成・変更履歴シート出力をすべて担う。

Bash で実行する：

```bash
python ~/.claude/templates/crs_md2excel.py {CRS_PATH} {OUT_PATH}
```

エラーが出た場合はそのままユーザーに表示する。
`~/.claude/templates/crs_md2excel.py` が見つからない場合は「`setup.sh` を実行してください」と案内する。

---

## 2. Save and report

出力パス・UR/SR/SP 件数を日本語で報告する。
件数はスクリプトの stdout（`Generated: ... (rows: N)`）から取得する。
UR/SR/SP の個別件数が必要な場合は `parse_crs_md()` の結果から算出してよい。
