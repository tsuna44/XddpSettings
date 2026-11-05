# ADR-0034: AI_INDEX を `{DOCS}` の索引として `ai_index.py` だけが作り直し、工程2 は AI_INDEX を読まない理由

Status: Accepted
Date: 2026-11-05

前提: [ADR-0005](ADR-0005-knowledge-guide-once.md)（本 ADR で置き換え）・[ADR-0013](ADR-0013-close-promote-script.md)・[ADR-0033](ADR-0033-constraints-module-key.md)。
経緯: PLAN-20261103-domain-refs-shared-knowledge（約束の監査 [docs/xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) の P1）。

## Context

`{DOCS}/AI_INDEX.md` を4か所が書いていた。close の `promote.py`（latest-specs から書き足す）、工程11 の先行更新（LLM）、
01-init（LLM がひな形を書く）、survey（LLM が行を足す）。表の定義もそれぞれが持っていた。工程2 の `domain_refs.py` は
AI_INDEX の表のラベルとリンクから `{DOCS}` のパスを組み立てて引いていた。

このため次の食い違いが起きていた（監査の報告書の P1 の17件）。

- 書く側と読む側でラベル・パスの形が違う（code-knowledge の `_structures` のラベル、cross のインタフェース仕様のパス）。
  `_structures`・`_constants` はラベルが一致した場合だけディレクトリを渡し、analyst はディレクトリを Read できなかった。
- CR の差分から書き足すので、今の CR が触っていない行にも「最終更新CR」が付き、キー列の変化で行が重複し、削除が伝わらない。
  破壊的変更の印は CHD の名前とケバブ形式のディレクトリ名を比べていて付かず、付けばキー列が変わって行が増えた。
- 工程11 の先行更新は、リンク先が close まで存在せず、`{DOCS}` をコミットせずに書き換えるので close の `git pull` を止めうる。
  01-init が `{DOCS}/{repo}/specs/` を必ず作るので、工程2 の latest-specs へのフォールバックも働かなかった。
- 工程5・6 は過去の DSN・CHD を AI_INDEX から探していたが、書く側が無かった。

## Decision

1. **AI_INDEX は `{DOCS}` の中身の索引とし、`ai_index.py build` だけが書く。** 書くたびに `{DOCS}` を走査して管理する節を
   作り直す（冪等。人が足した節は残す。廃止した節は消す）。最終更新CR は各ファイルのフロントマター `last-updated-cr`
   （CRS・TSP・TRS はファイル名）から取り、今の CR を付けない。01-init・close（Step D2）・survey・update-knowledge はこれを呼ぶ。
   LLM は AI_INDEX を書かない。
2. **close は「クローズ完了」と削除の後（Step D2）に作り直す。** C2 の時点で作ると C3.6 の code-knowledge と C6 の rulebook が
   載らず、Step D の前に作ると Step D で消したモジュールと人の直接編集が載らない。アーカイブ候補は PENDING-PROMOTE ではなく
   Step F で示し、行を減らすには行のもとのファイルを移すよう案内する（行だけを消しても次の作り直しで戻る）。
3. **工程11 の先行更新を廃止する。** 先行更新の目的（close の前に次の CR の工程2 が最新仕様を参照できる）は、工程2 が
   `{DOCS}` に無いファイルを latest-specs から読むことで果たす。
4. **工程2 の `domain_refs.py` は AI_INDEX を読まず、`{DOCS}` と latest-specs を直接列挙する。** 名前は両方のディレクトリ名の
   和集合から選び、`{DOCS}` 側のファイル（承認済み）を優先し、latest-specs にだけあるものは `degraded` として渡す。
   `_structures/`・`_constants/` は直下の `.md` をファイル単位で、キーワードで絞らずに渡す（制約の直接列挙〔ADR-0033〕と同じ考え方）。
5. **破壊的変更の印は工程11 が書くフロントマター `breaking:` で決める。** 今回の CHD の「インタフェース変更サマリ」にある
   インタフェースだけ書き、サマリに無いものは変えない（`breaking:` は `last-updated-cr` の CR での更新を表す）。
   LLM が書く値なので `artifact_lint.py` で語彙（`true`／`false`）を検査する。
6. **過去の DSN・CHD を読む側を消す。** CHD はその時点のコードに対する差分で、後の CR から読むと古い Before と今の仕様が並ぶ。
   今の姿は最新仕様、変更の理由は CRS の写し、設計判断は project-rulebook の ADR が受け持つ。`{DOCS}/{repo}/design/` は作らない。
7. **共有の値は1か所に定義して import する。** `{DOCS}`・latest-specs の配置、フロントマターの読み方、ユースケースの目的と
   関連モジュール、共有の知見のディレクトリ名と種別名、`breaking:` の語彙は `docs_layout.py` に置き、`promote.py`・
   `domain_refs.py`・`ai_index.py`・`artifact_lint.py` が import する。AI_INDEX の節・列は `ai_index.py` だけが持つ。

却下した案:
- 今の書き足す仕組みを残し、指摘を1つずつ直す: 書く人（4か所）ごとにラベル・最終更新CR・キー列・ひな形を揃え続ける必要がある。
- 先行更新を残し、スクリプトにする: リンクが close まで壊れたままで、`{DOCS}` をコミットせずに書き換えるので close の pull が止まりうる。
- close で DSN・CHD を `{DOCS}/{repo}/design/` に写す: CHD は差分で、後の CR から読むと古い Before と今の仕様が並ぶ。
- `_structures` のラベルを書く側に合わせるだけ: ディレクトリを渡す問題と、AI_INDEX に行の無い知見が見えない問題が残る。
- ディレクトリを渡し、analyst に配下を Glob させる: 決定的な列挙を LLM に任せることになる。

## Consequences

- 書く側と読む側の間のラベル・パスの約束が無くなる。残る約束は `docs_layout.py` の import と、latest-specs →
  `promote_specs` → `{DOCS}` → `domain_refs.resolve`・`ai_index.build` を通すテストで守る。
- 01-init・survey・update-knowledge が AI_INDEX をコミットせずに作り直すので、close の C0-2 で `{DOCS}` の pull が
  AI_INDEX.md の未コミットの変更で止まる・衝突する場合が増える。C0-2 は、AI_INDEX.md だけなら手元の変更を捨てて
  pull し直す案・取り込む側を採って merge を終える案を示し、merge・rebase の途中のまま昇格を書き込まない。
- 工程2 は latest-specs にだけある仕様を毎回読む。進行中の CR の新しいモジュールのほかに、latest-specs に残った古い仕様
  （工程11 の後に abort した CR・承認されなかった survey・別のワークスペースの close が `{DOCS}` から消したモジュール）も
  `degraded` で入る。ANA §0 の出典と注記で人が見分けられる。latest-specs から消す仕組みは別のプラン（P4）で決める。
- 管理する節を人が手で直していた場合、その直しは次の作り直しで消える。
- 残る約束: code-knowledge を書くのは LLM（close・survey の昇格・手での登録）で、置き場所は `code-knowledge-boundary.md` の
  宛先のルーティング表が決める。`docs_layout.py` のディレクトリ名・「直下の `*.md`」との一致は import でもテストでも
  守られない。書く側を直すプラン（P2）で揃え方を決める。
- 工程9 の Step 0 は AI_INDEX から過去の TSP・TRS を探し、TSP の節に記録させる。テンプレートに無い節に記録させる点は
  本 ADR では直していない（監査の報告書の 2b-3）。
