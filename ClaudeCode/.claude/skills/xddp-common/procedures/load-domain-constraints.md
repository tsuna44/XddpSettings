# Load Domain Constraints

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## Load Domain Constraints

`project-rulebook.md` から「ドメイン制約」節のみを抽出する共通手順。
`Load Steering Context` が rulebook 全体を返すのに対し、本手順は該当節のみを返す。

**Input:**
- `XDDP_DIR`: XDDPディレクトリのパス

**Output:** `DOMAIN_CONSTRAINTS`（抽出した節の本文。該当なしの場合は空文字列）

**Process:**
1. Read `{XDDP_DIR}/project-rulebook.md` (if exists)。見出し `## 1.6 ドメイン制約` を**見出し名で**探す
   （節番号が変わっても追随できるよう、番号ではなく「ドメイン制約」の語で照合する）。
   見つかった場合、次の `## ` 見出しの直前までを抽出する。
2. 抽出結果の全行が未記入（プレースホルダー `{...}` のみ、または全行「該当なし」）の場合は
   `DOMAIN_CONSTRAINTS` = 空文字列とする（未記入のテンプレートを渡してもノイズにしかならないため）。
3. Return `DOMAIN_CONSTRAINTS`.
