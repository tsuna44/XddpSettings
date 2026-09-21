# Build Arch Agent Paths

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## Build Arch Agent Paths

xddp-architect-agent 呼び出しに渡す INDEX_FILE／APPROACHES_DIR を構築する共通手順（`xddp-05-arch`
Step A・Step B・Step B3 が同一の値を複製していたものを1箇所に統合）。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `REPO_NAME`: リポジトリ名
- `CR`: CR番号

**Output:** `ARCH_INDEX_FILE`, `ARCH_APPROACHES_DIR`

**Process:**
1. `ARCH_INDEX_FILE` = `{CR_PATH}/05_architecture/{REPO_NAME}/DSN-{CR}.md`
2. `ARCH_APPROACHES_DIR` = `{CR_PATH}/05_architecture/{REPO_NAME}/`
3. Return `ARCH_INDEX_FILE`, `ARCH_APPROACHES_DIR`.
