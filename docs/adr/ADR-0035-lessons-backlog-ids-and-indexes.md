# ADR-0035: 知見ログ・改善バックログの ID に CR を含め、表をスクリプトが作り直し、`{DOCS}` の backlog を正として足し込む理由

Status: Accepted
Date: 2026-11-08

前提: [ADR-0013](ADR-0013-close-promote-script.md)・[ADR-0034](ADR-0034-ai-index-docs-index.md)。
経緯: PLAN-20261105-lessons-backlog（約束の監査 [docs/xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) の P3）。

## Context

約束の監査は、知見ログ（LL）・改善バックログ（IDEA）・気づき・提案メモの約束（A3）に食い違いを挙げた。もとは次の5つにまとまる。

- **ID が通し番号で、場所をまたいで重なる。** Layer 1（`{XDDP_DIR}/lessons-learned.md`）・update-knowledge（Layer 2 に直接書く）・
  別のワークスペース・アーカイブの後で `LL-NNN` を別々に採っていた。Layer 2 は ID が同じなら足さないので、後の LL が黙って入らなかった。
- **決まった手順で作れる表を LLM が書き、書く側ごとに形が違う。** タグ別インデックス・エントリ一覧・バックログのサマリと一覧の区切り・書式・
  どの表かが決まっておらず、Layer 2 のヘッダーを書く側が4つあった（1つはヘッダーを書かなかった）。
- **気づきの収集の対象が書く側とずれている。** cross の TSP・progress.md を集めず、書く側の無い CODING・VERIFY の節を集め、
  今の CR と関係の無い latest-specs の節を毎回集め、「なし」・HTML コメントを1件と数えた。
- **promote.py の判定と報告が足りない。** LL の `repo` 欄を確かめずにパスにし、cross の置き場所を今の CR の cross の成果物の有無で決め、
  `{DOCS}` の backlog を丸ごと上書きし、cross・system・共通ファイルの昇格の失敗が人に示されなかった。close の再実行で LL・IDEA が重複したまま昇格した。
  コードブロックの中の見出しでエントリを切り、短いフェンスで長いフェンスが閉じた。
- **読む側が受け取り口を持たない・記述が実物と違う。**

## Decision

1. **LL・IDEA の ID に CR を含める。** close が書くものは `LL-{CR}-{NN}`・`IDEA-{CR}-{NN}`。CR を持たない登録（update-knowledge の lesson、
   abort の後に人が書く IDEA 等）は `LL-M{YYYYMMDD}-{NN}`・`IDEA-M{YYYYMMDD}-{NN}` とし、番号は `promote.py index` が書くファイルの中の
   最大値 + 1（`next_manual_id`）で決める。CR のフォルダ名はワークスペースをまたいで一意なので、番号を採るときにほかの場所を見なくてよい。
   今の CR のエントリは ID の全体一致（前方一致にしない）で数える。
2. **決まった手順で作れる表はスクリプトが作り直す。** 知見ログ（Layer 1・Layer 2）のエントリ一覧・タグ別インデックスと、バックログの
   サマリ・一覧は `promote.py index` だけが書く。LLM・人はエントリだけを書く。Layer 2 のヘッダーの定義も `promote.py` に1つだけ置き、
   01-init は Layer 2 の知見ログを作らない。
3. **close の再実行では、今の CR のエントリが既にあれば Step B・C は追記しない**（`index --check` で数える）。作り直すときは人が消して再実行する。
4. **`{DOCS}/improvement-backlog.md` を正とし、足し込む。** `{XDDP_DIR}/improvement-backlog.md` は新しい IDEA の受け口で、close は
   `{DOCS}` に無い ID だけを §3 の末尾に足す。同じ ID は上書きしない。今の CR の ID だけ、close が書き人が直さない部分（タイトル・カテゴリ・
   repo・発生源・内容・発生経緯・期待効果・推定影響範囲）を比べ、違えば報告する。取り消しはエントリを消さずステータスを `❌ 却下` にする。
   Layer 2 の LL も同じく、同じ ID が無ければ足し、1つあり本文が違えば上書きせず報告する（比べる前に区切りの `---`・空行の違いを正規化する）。
5. **気づきの収集は今の CR が書いた・足したものだけにする。** CR の成果物に cross の TSP・progress.md を足す。latest-specs は工程11 の一覧と
   `last-updated-cr` が今の CR のファイルの和集合を走査し、`has_insights: false` を飛ばし、`{DOCS}` の承認済みの版（Step A は `{DOCS}` の pull の前）に
   ある項目を除く。前回の close が昇格した後の再実行では `{DOCS}` に今の CR の版があるので、比べずに前回の収集結果を引き継ぐ。
   節の検出・項目の定義（数えない行・「なし」の語）・`has_insights` の期待値の規則は `docs_layout.py` に1つだけ置く。
6. **cross の知見・rulebook の置き場所は IS_MULTI で決める。** cross の知見・rulebook は CR をまたいで蓄積するもので、今の CR が cross の
   成果物を作ったかとは関係しない（今の CR の cross の成果物の写しは HAS_CROSS のまま）。LL の `repo` 欄は REPOS のキー・IS_MULTI の `cross` だけを
   振り分け先とし、それ以外は理由つきで人に示す。
7. **昇格の結果は repo・cross・system・共通ファイルごとに「成功／失敗／対象外」で出す。** 失敗した対象はすべて Step D・E に示す。
8. **LL の切り分けは CommonMark のフェンスの規則に合わせる。** フェンスの中の行は見出しとして扱わず、閉じるのは同じ文字で長さが開いたフェンス以上の行だけ。
   閉じないフェンスを含むエントリは `unclosed-fence` として人に示す。

却下した案:

- **ID は通し番号のまま、Layer 2 の重複判定を (ID, CR) にする:** 別の作業場所の同じ ID が Layer 2 に並び、アーカイブの後の採番に
  Layer 1・アーカイブ・Layer 2 の最大値を見る規則が要る。
- **latest-specs の気づきの表に CR の列を足す:** 工程11 の agent・SKILL・survey のすべてが列を書く必要があり、書き忘れを検出できない。
- **latest-specs を工程11 の一覧のファイルだけに絞る（比べない）:** 毎回更新するファイルでは前の CR の項目が毎回集まる。
- **latest-specs を `last-updated-cr` だけで選ぶ:** `last-updated-cr` を書かないファイル・人が直したファイルを取りこぼしうる。
- **`{DOCS}` の backlog で内容の違う IDEA を Layer 1 の内容で上書きする:** 別の作業場所や人が `{DOCS}` で直したステータスを黙って戻す。
- **`{DOCS}` の backlog で、すべての ID の内容の違いを報告する:** `{DOCS}` でステータスを直すと同じ報告が以後の close で毎回出続け、本当の競合が埋もれる。
- **`{DOCS}` の内容で Layer 1 の IDEA を揃える（逆向きの同期）:** Layer 1 を正と誤解させる。
- **`has_insights` と節の不一致の自動修正を LLM に任せる（向きを決めない）:** `has_insights` を `false` に変えると、そのファイルが気づきの収集から黙って外れる。
- **タグ別インデックスは LLM のまま、区切りだけ決める:** 決まった手順で作れる表なのでスクリプトにする。
- **01-init が Layer 2 を同じヘッダーで作る:** ヘッダーの定義が SKILL.md とスクリプトの2か所になる。

## Consequences

- 表の形・ID の形・節の名前を変えるときは `promote.py`（と `docs_layout.py`）を直す。テンプレートとの一致は、実物のテンプレートから作った
  Layer 1 を `index`・`extract-ll`・`run` と読み手（`load-lessons-context.md` の読み方・`domain_refs.py`）に通すテストで守る。
- 既存の `LL-NNN`・`IDEA-NNN` は移し替えない。切り分けは ID の形を問わないので読めるが、今の CR のエントリの数え上げは新しい形の ID だけを数える。
- 残る約束（スクリプトでは守れない）:
  - エントリそのもの（LL の見出しとメタ行、IDEA の項目の表）は LLM・人が書く。書式は close の Step B・C に1つだけ定義し、崩れたものは
    `unparsed_ll`・`bad_ideas` で Step D に示す。
  - 手で登録する ID は、別の作業場所から同じ `{DOCS}` のファイルに同じ日に登録すると重なりうる。close の `run` か update-knowledge の `index` が
    そのファイルに触れたときに `duplicate_ids` で示す。
  - IDEA のステータス等を `{XDDP_DIR}` 側で直しても `{DOCS}` に届かないこと・`{DOCS}` でエントリを消すと戻ることは、テンプレートの注記と Step D で示すだけ。
  - 気づきの収集で `{DOCS}` と比べるのは Step A の時点（pull の前）の版。同じ `{XDDP_DIR}` で close していない別の CR が同じ latest-specs のファイルに
    足した項目は、今の CR の項目として集まりうる（多く集める側の誤り）。同じ latest-specs のファイルを並行する CR で更新しないことは運用で守る。
- 全 repo に当てはまる LL（進め方の知見等）の Layer 2 の置き場所は無い（`repo` 欄の `全リポジトリ` は振り分け先が無い値として人に示す）。
  置き場所と読み手を決める別のプランにする。
