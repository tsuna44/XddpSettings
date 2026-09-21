# Regenerate CRS Excel (UR-016)

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## Regenerate CRS Excel (UR-016)

CRS Markdown から確認用 Excel を再生成する共通手順。各スキルの「Excel再生成」ステップから apply して使用する。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `CR`: CR番号
- `MD2EXCEL_PYTHON_BIN`（暗黙。呼び出し元が `## CR Resolution` 経由で解決済みの値をそのまま参照する。
  `DEVELOPMENT_MODE` 等と同じ扱いのため、apply 呼び出し時に明示的に渡す必要はない）

**Process:**
1. Let `CRS_PATH` = `{CR_PATH}/03_change-requirements/CRS-{CR}.md`.
2. Let `EXCEL_PATH` = `{CR_PATH}/03_change-requirements/CRS-{CR}.xlsx`.
3. Run via Bash:
   - `MD2EXCEL_PYTHON_BIN` が設定されている場合: `"{MD2EXCEL_PYTHON_BIN}" ~/.claude/skills/xddp-md2excel/scripts/crs_md2excel.py {CRS_PATH} {EXCEL_PATH}`
   - 未設定の場合（デフォルト）: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-md2excel/scripts/crs_md2excel.py {CRS_PATH} {EXCEL_PATH}`
4. If `crs_md2excel.py` not found: tell the user to run `setup.sh`. If errors（`ModuleNotFoundError: No module named 'openpyxl'` を含む）: display to user, and if `MD2EXCEL_PYTHON_BIN` is unset, additionally suggest configuring it in `xddp.config.md`「## 5. 実行環境設定」.
5. Report output path and UR/SR/SP counts from script stdout.

> **Design policy:** The sole definition of the Excel format is in `~/.claude/skills/xddp-md2excel/SKILL.md` and `~/.claude/skills/xddp-md2excel/scripts/crs_md2excel.py`.
> This skill does not define its own format; it always delegates to xddp-md2excel to prevent format divergence by generation path.
> To change the format, modify only xddp-md2excel/SKILL.md and crs_md2excel.py.
> **成果物の位置付け:** `CRS-{CR}.xlsx` は人間向け確認ツール（一時生成物）。xddp-close の DOCS_DIR 昇格対象外。
