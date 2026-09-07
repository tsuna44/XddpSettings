# ADR-0014: xddp-reviewer のチェックリストを DOCUMENT_TYPE 別ファイルへ分割し遅延ロードする理由

Status: Accepted
Date: 2026-09-07

## Context

`xddp-reviewer.md`（392行。2026-09-06 `wc -l` 実測）は 8 種類の `DOCUMENT_TYPE`（ANA / CRS / SPO /
DSN / CHD / TSP / SPEC / PLAN）分のペルソナ・主チェックリスト・次工程受け取り可否チェックリストを
単一ファイルに保持していたが、1 回のレビュー起動で実際に使うのは 1 ペルソナ＋1 主チェックリスト＋
高々 1 ペアの次工程チェックリストのみである。それ以外（他 7 種のペルソナ・他 7 種の主チェックリスト・
他 6 ペアの次工程チェックリスト＝合計約 250 行）は毎回ロードされるが一度も参照されない。
`xddp-reviewer` は AI レビューを行う全工程（工程 2/3/4/5/6/9/11 ＋ `xddp.review`・`xddp.plan-review`・
`xddp.survey`）から、かつ 1 工程あたり複数ラウンド × 複数バッチで起動されるため、この固定コストは
CR 全体で最も累積しやすい。

## Decision

DOCUMENT_TYPE 別 1 ファイル（ペルソナ＋主チェックリスト＋次工程観点を同梱）へ分割し、
エージェント本体（`agents/xddp-reviewer.md`）からは該当 1 ファイルのみを実行時 Read する
遅延ロード方式へ変更する。配置は `ClaudeCode/.claude/skills/xddp.common/reviewer-checklists/`
（`agents/` 配下ではなく `skills/xddp.common/` 配下。`~/.claude/agents/` は Claude Code が
エージェント定義として走査するディレクトリであり、フロントマターを持たない参照ファイルを置いた
場合の扱いが保証されないため）。

**検討した代替案と不採用理由:**

1. ペルソナ・チェックリスト・次工程観点を別々のファイルに分ける → Read が 2〜3 往復に増え、
   削減分をレイテンシで相殺する。
2. 次工程観点をペア単位ファイル（`ANA-CRS.md` 等）にする → CRS のように次工程が 3 通りある型で
   ファイル数が増え、呼び出し側が `NEXT_DOCUMENT_TYPE` 未指定のとき解決先が曖昧になる。
3. `## Downstream Readiness Checklists` の出力書式（次工程受け取り可否レビューの共通書式・
   CRITICAL OUTPUT RULE）を 8 ファイルへ複製する → DOCUMENT_TYPE に依存しない共通仕様の重複が
   生まれる。単独ファイルへ切り出す案も、`NEXT_DOCUMENT_TYPE` が渡される呼び出しが多数派のため
   Read 回数だけが増えて削減効果がほぼ無い。よってこの 41 行は本体（`xddp-reviewer.md`）に残置する。
4. `agents/xddp-reviewer/` サブディレクトリ配置 → 上記の理由で不採用。

分割で最も危険なのは「エージェントが Read を省略し、記憶ベースの一般的レビューを行って合格判定を
出す」サイレント劣化である。これを (a) `## Load Checklist` を MANDATORY な最初の行動として指示する、
(b) Read 失敗時はレビュー自体を中止させる（`OUTPUT_FILE` も書かない）、(c) チェックリストファイルの
`## Persona` 末尾に日本語ペルソナ名を固定表記させ、レビュー結果の「レビュアー」欄にそのまま転記させる
ことで読み込み証跡を残す、(d) `tools/harness/refcheck.py` に検査E（DOCUMENT_TYPE ↔ チェックリスト
ファイルの実在・構造整合を静的検査）を追加する、の 4 段で抑止する。検査Eが必要な理由は、遅延ロードの
パスが `{DOCUMENT_TYPE}` プレースホルダーを含み、既存の検査A（`apply` 見出し整合）では
`resolve_claude_path()` がプレースホルダーを解決できず静的検証の対象外になるため。

## Consequences

DOCUMENT_TYPE 別ファイルの実測行数は 188〜248 行（本体 165 行＋チェックリスト 23〜83 行）で、
分割前の 392 行から 3.7〜5.2 割の削減となった（見込みの 6〜7 割には届かない。`## Downstream Readiness
Checklists` の共通出力書式と `## Task`/`### Inputs` が DOCUMENT_TYPE 非依存の共通部分として本体に
残るため）。

引き換えに (a) チェックリスト分の Read が 1 往復増える、(b) エージェントが Read を省略した場合の
サイレント劣化リスクが生じる、という 2 点のトレードオフを負う。(b) は上記 4 段の抑止で軽減する。
`tools/harness/refcheck.py` の既定 `--checks` を `ABCD` から `ABCDE` へ変更したため、以降の
リポジトリ変更でチェックリストファイルの欠落・見出し破損が発生した場合は `make test` が検出する。
