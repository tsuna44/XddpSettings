# Build TSP Output File

> xddp.common の共通プロシージャ。呼び出し元スキルから apply される。

## Build TSP Output File

TSP 出力ファイルのパスを構築する共通手順（`xddp.09.test` Step A・Step B が同一定義を複製していた
ものを1箇所に統合）。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `REPO_NAME`: リポジトリ名
- `CR`: CR番号

**Output:** `TSP_OUTPUT_FILE`

**Process:**
1. `TSP_OUTPUT_FILE` = `{CR_PATH}/09_test-spec/{REPO_NAME}/TSP-{CR}.md`
2. Return `TSP_OUTPUT_FILE`.
