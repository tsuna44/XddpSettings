# ADR-0016: xddp.common/SKILL.md をハイブリッド方式で procedures/ へ分割する理由

Status: Accepted
Date: 2026-09-21

## Context

`xddp.common/SKILL.md`（分割前 1,002 行・24 セクション）は全 26 スキル＋1 エージェント
（`xddp-test-writer-agent.md`）＋1 テンプレート（`xddp.skill-template.md`）から参照される
共通プロシージャ集である。呼び出し元スキルが `apply "## X"` する際は現行の実装上
`xddp.common/SKILL.md` を毎回丸ごと Read する必要があり、24 セクションのうち実際に使うのは
1 工程あたり数セクションのみでも、残り全セクションのトークンを毎回消費していた。

`skills/*/SKILL.md`・`agents/*.md`・`skills/*/*.md`（`templates/` 除く）から `apply "## X"` を
正規表現抽出しセクション別に集計したところ、24 セクションの直接参照ファイル数（同一ファイル内の
複数回参照は1回のReadで足りるため、回数ではなくファイル数で判断）は 1〜21 と大きく偏っていた
（`Load Config` 100行/5ファイル、`Invoke Reviewer` 56行/7ファイル（依存クロージャ込みで実効12）、
`Build TSP Output File` 15行/1ファイル 等）。

## Decision

参照ファイル数 ≥ 9 の6セクション（`Load Config`・`CR Resolution`・`Resolve Affected Repos`・
`Resolve HAS_CROSS`・`Progress Update`・`Discover CHD Files`）を `xddp.common/SKILL.md` 本体に残置し、
残り18セクションを `xddp.common/procedures/{見出しの kebab-case}.md` へ1ファイル1プロシージャで
分割する（ハイブリッド方式）。本体には新設の「## Procedures Index」が18ファイルの索引を持つ。

**閾値の例外は2件:**

- `Load Config`（直接参照5ファイル。閾値未満だが残置）: `CR Resolution`（21ファイルが参照）が
  内部で apply しており、分割すると21ファイル全てに追加 Read が発生する。施策Bによる
  スクリプト化後は20行と小さく、残置コストが低い。
- `Invoke Reviewer`（直接参照7ファイル。閾値未満だが分割）: 依存クロージャを含む実効参照は
  12ファイルで閾値を超えるが、残置すると利用しない16ファイルに56行を課す。実効利用側が
  1回の追加Readを払う方が全体では小さいため分割する。

**検討した代替案と不採用理由:**

1. 全24セクションを完全分割し `SKILL.md` を索引のみ（約35行）にする → 軽量スキル（`xddp.status` 等）
   はさらに削減できるが、`CR Resolution`（21ファイルが参照）を含む全セクションで Read が1回増える。
   完全分割との差は軽量スキルで約86行にとどまり、高頻度セクション残置による Read 回数抑制の効果の方が
   大きいと判断した。
2. セクション単位ではなく行数の均等分割 → プロシージャの Input/Output/Process という論理境界と
   一致しないため、`apply "## X"` の見出し解決（検査A）が機能しなくなる。

## Consequences

`xddp.common` 本体は分割後 243 行（残置6セクション＋フロントマター＋Procedures Index）となり、
分割後に全スキルが必ず読む固定コストが大幅に下がった。個々のスキルの実際の削減率は使用する
プロシージャの組み合わせ（依存クロージャ含む）に依存し、`xddp.06.design`・`xddp.05.arch` のような
15前後のセクションを使う重量級工程では削減率が相対的に小さく、`xddp.status` のような1〜2セクション
のみ使う軽量スキルでは削減率が大きい。

引き換えに (a) 分割されたセクションを使うスキルは procedures ファイルの追加 Read が発生する、
(b) `xddp.common` 内部のセクション間 apply 依存（分割前に自ファイル内解決で成立していたもの）は
分割後に解決不能になりうる、という2点のトレードオフを負う。(b) は分割時に全件（7箇所）を洗い出し、
Read 行の新設・書き換えで解消した（うち1箇所は `## VCS Auto-Commit` → `## VCS Commit If Dirty` の
裸 apply で、分割前は同一ファイル内解決に依存していたため Read 行自体が存在しなかった）。

再発防止として `tools/harness/refcheck.py` に検査G（`procedures/*.md` のファイル集合と
「## Procedures Index」の1:1整合、各ファイルが `## ` 見出しを1つだけ持つことの機械検査）を追加した。
検査A（`apply` 見出し整合）は既存の `_nearest_read_target()` により、分割後に Read 先の書き換えを
忘れた箇所を自動的に error として検出する（26スキル＋1エージェントの参照書き換え漏れの回帰ガード）。
