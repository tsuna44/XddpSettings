# Load Domain Constraints

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## Load Domain Constraints

`project-rulebook.md` から「ドメイン制約」節のみを抽出する共通手順。
`Load Steering Context` が rulebook 全体を返すのに対し、本手順は該当節のみを返す。

**Input:**
- `XDDP_DIR`: XDDPディレクトリのパス

**Output:** `DOMAIN_CONSTRAINTS`（記入済みのドメイン制約の行と表の見出しの行。記入済みの行が無ければ空文字列）

**Process:**
1. Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/rulebook_files.py domain-constraints --file {XDDP_DIR}/project-rulebook.md`
   （見出しは「ドメイン制約」の語で探す。表のうち「制約内容」の列が `{制約内容}` でも「該当なし」でもない行だけを、
   表の見出しの行と一緒に出す。根拠が「未確認」の行も出す。ファイル・節・記入済みの行が無ければ何も出さない）
2. Let `DOMAIN_CONSTRAINTS` = stdout（空なら空文字列）.
3. Return `DOMAIN_CONSTRAINTS`.
