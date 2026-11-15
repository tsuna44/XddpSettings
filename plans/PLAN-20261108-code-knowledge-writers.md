# PLAN-20261108-code-knowledge-writers

作成日: 2026-11-08（PLAN-20261103-contract-audit の段階3 の P2）  
ステータス: 草案 / 承認待ち / 承認済み / **実装完了**

---

## 1. 背景・目的

### 1.1 起きていること

約束の監査（[docs/xddp-contract-audit-2026-11.md](../docs/xddp-contract-audit-2026-11.md)）は、code-knowledge の約束（A1）に17件の指摘を挙げた。そのうち A1-7・A1-8 は P1 で直したので、残りの15件と、段階1 の R1・R4・R5 を P2 としてこのプランに割り当てた（報告書の 8.2・8.1）。P1（c15454f）・P3・P4（06f2185）の実装の後の状態を見て書く。

食い違いのもとは、次の4つにまとまる。
- **制約（`constraints.md`）のエントリを LLM が書き、同じエントリかを「同じ出典」で決めている:** 1回の survey の昇格・1回のクローズの SPO §5.6 の行はすべて同じ出典を持つので、同じ置き場所に入る制約が互いに置き換わり、最後の1件しか残らない（A1-1・A1-3）。手での登録も同じ出典なら黙って置き換える（A1-2）。TRS の NG の鍵に実行回が入っていない（A1-4）。出典の書式・`**対象:**` 欄も経路とテンプレートで揃っていない（A1-5・A1-6）。
- **置き場所を決めるスクリプト（`knowledge_place.py`）と読む側の食い違い:** 予約名と同じ名前のディレクトリの制約は書かれるが読まれない（R1）。ワークスペースの外の絶対パスの `status` が規約と違う（R4）。人の入力をそのまま JSON に入れると、`\` で黙って `no-path` になる（A1-17）。
- **宛先のパスを、単一情報源（`code-knowledge-boundary.md` の宛先ルーティング表）以外でも定義している:** update-knowledge・survey・survey-promote-agent が自分でパスを書いている（A1-13・A1-14）。P1 の申し送り（ルーティング表のディレクトリ名と `docs_layout.py` の `SHARED_KNOWLEDGE_DIRS`・「直下の `*.md`」の約束が、import でもテストでも守られない）もここに入る。
- **記述が実物と違う・読む側がいない:** SPO §4.5 と `_constants` テンプレートの列（A1-9）、Step D で示さない一覧（A1-10）、暫定ドメイン名の一覧の漏れ（A1-11）、callgraph の入力項目（A1-12）、survey の topic の説明（A1-15）、読む側の無い `confirmed_modules`（A1-16）、標準ライブラリの再実装（R5）。

### 1.2 割り当てた指摘（P2）

指摘の詳細は、監査の報告書の付録（[A1 の報告](../docs/contract-audit-2026-11/A1-audit.md)「3. 指摘」、[V1 の報告](../docs/contract-audit-2026-11/V1-verify.md)）と段階1 の報告（[docs/review-fbf3956-2026-11.md](../docs/review-fbf3956-2026-11.md)）にある。行番号は監査の対象リビジョン ecb54c4（段階1 は fbf3956）の値で、今のファイルの行とは違う。今のファイルで残っていることは、2026-11-08 にこのプランを書くときに確かめた（下の表の「今の箇所」。行番号は 2026-11-08 の値）。

| # | 重大度 | 内容（要約） | 今の箇所 | 直す節 |
|---|---|---|---|---|
| A1-1 | 🔴 | survey の昇格で、§2.6 の制約どうしが同じ出典 `SURVEY-{TODAY}` で置き換わる | `xddp-survey-promote-agent.md`「### Process」の 3.・4. | 3.1・3.2 |
| A1-2 | 🟡 | 手での登録で、同じ出典の別の制約を置き換え、プレビューにも示さない | `xddp-update-knowledge/SKILL.md` Step 3 の constraint | 3.1・3.3 |
| A1-3 | 🟡 | クローズの SPO §5.6・LL 由来の制約に upsert の鍵が無い | `xddp-close-knowledge-agent.md`「### Step C3.6」の「昇格する制約」 | 3.1・3.2 |
| A1-4 | 🟡 | TRS の NG の鍵 `CR-{CR} / NG-{NNN}` に実行回が入っていない（NG は回ごとに `NG-001` から振る） | 同上の TRS 不具合エントリ、`10_test-results-template.md` の `### NG-001` | 3.1・3.2 |
| A1-5 | 🔵 | 出典の `CR-{CR_NUMBER}` で、CR フォルダ名が `CR-` で始まると接頭辞が二重になる | 同上の TRS の出典、code-knowledge のテンプレートの「出典は（CR-NNN）」 | 3.1・3.2・3.6 |
| A1-6 | 🔵 | 「対象」を書くよう指示しているのに、constraints テンプレートの2つの節に `**対象:**` 欄が無い | `code-knowledge-constraints-template.md` の「仕様上の暗黙の前提」「パフォーマンス・非機能特性」 | 3.1・3.6 |
| A1-9 | 🔵 | SPO §4.5 の `定義モジュール` と `_constants` テンプレートの `定義場所` の列が合わない | `04_specout-summary-template.md` §4.5、`code-knowledge-constants-template.md` | 3.6 |
| A1-10 | 🔵 | 「## 昇格見送り一覧」を close の Step D で示さない | `xddp-close/SKILL.md`「## Step D」 | 3.2 |
| A1-11 | 🔵 | `_domain名要確認一覧` に載せる対象が一部（callgraph と per-repo の定数）だけ。cross の `_constants`・`_structures` が漏れる | `xddp-close-knowledge-agent.md`「### Step C3.6」 | 3.2 |
| A1-12 | 🔵 | update-knowledge の callgraph で、入力させた「フロー名」をファイル名に使わない | `xddp-update-knowledge/SKILL.md` Step 1 の callgraph・Step 3 | 3.3 |
| A1-13 | 🔵 | update-knowledge が flow・callgraph のパスとテンプレートを自分で定義している | 同上 Step 3 の flow・callgraph | 3.3 |
| A1-14 | 🔵 | survey が昇格先のパスを自分で定義している | `xddp-survey/SKILL.md` Step 5 の表、`xddp-survey-promote-agent.md`「### Process」の 2. | 3.4 |
| A1-15 | 🔵 | survey の「topic では §2.6 の昇格は発生しない」が誤り | `xddp-survey/SKILL.md` Step 5 の `MODULE_FALLBACK` | 3.4 |
| A1-16 | 🔵 | `specout_bfs.py status` の `confirmed_modules`（第1階層）を読むのがテストだけ | `specout_bfs.py` の `cmd_status` の末尾 | 3.5 |
| A1-17 | 🔵 | ヒアドキュメントに人の入力をそのまま JSON に埋め込むので、`\` で exit 2 になるか、`\n` 等で黙って `no-path` になる | `xddp-update-knowledge/SKILL.md` Step 1.5、`xddp-survey/SKILL.md` Step 5 の `MODULE_FALLBACK` | 3.1・3.3・3.4 |
| R1 | 🟡 | 予約名（`_structures` 等）と同じ名前のディレクトリの制約は、置き場所がその予約名になり、`list_places` が除くので読まれない | `knowledge_place.py` の `_module_of`・`list_places` | 3.1 |
| R4 | 🔵 | ワークスペースの外の絶対パスの `status` が `outside-repo` ではなく `not-found` になる | `knowledge_place.py` の `place_target` | 3.1 |
| R5 | 🔵 | `_common_dir` は `posixpath.commonpath` の再実装 | `knowledge_place.py` の `_common_dir` | 3.1 |

**監査の外で、このプランを書くときに見つけたもの（同じ型）:**
- `specout_bfs.py doc-targets` の出力 `doc_target_modules` も、`_module_dir_for_file`（第1階層）で作り、読む側はテストだけ（`grep -rn doc_target_modules ClaudeCode tools docs/adr README.md` で確認。SKILL・エージェント・手順のファイルに無い）。A1-16 と同じ扱いにする（3.5。7. の 4.）。
- code-knowledge-boundary.md の「overview/ vs _structures/ の役割分担」は、`{DOCS}/{repo}/…/_structures/` の書き手に xddp-close を挙げるが、close-knowledge-agent が `_structures/` に書くのは cross（`{XKNOW}`）だけ（V1 の A1-11 の補足）。記述を直す（3.6）。per-repo の `_structures/` をクローズで書く手順を足すことはしない（6.）。

### 1.3 方針

1. **制約のエントリはスクリプトが書く。** 置き場所の決定・`[CK-NNN]` の採番・同じエントリかの判定（鍵）・節と欄の書式・`**対象:**` は `knowledge_place.py` の新しいサブコマンドが決める。LLM は、どの知見を昇格するか・本文（内容・回避策等）・鍵の元になる項目の位置を決めるだけにする（CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」）。
2. **エントリの同一性は、出典ではなく「鍵」で決める。** 鍵は元の文書の項目を指す（TRS の実行回と NG、SPO §5.6 の行、LL の ID、SURVEY の §2.6 の項目）。出典は人が読む表示で、鍵には使わない。
3. **置き場所は読まれる場所にだけ書く。** 予約名と衝突したら、読まれる置き場所（`fallback`）に置く。
4. **宛先のパスは宛先ルーティング表だけが定義する。** 他のファイルは表の行の名前で引く。ディレクトリ名は `docs_layout.py` に置き、表とスクリプトの一致をテストで、他のファイルにパスを書いていないことを refcheck で確かめる。

### 1.4 目的

- 1.2 の18件（監査の報告書 8.2 が P2 に数える17件と、同じ表で括弧書きにしている段階1 の R5）と、監査の外の2件を直す。
- code-knowledge の書く側（close・survey・update-knowledge）→ 読む側（下調べ・工程2・AI_INDEX）の受け渡しを、スクリプトの定義とテストで守る形にする（3.7 の再発防止）。

---

## 2. 変更対象ファイル

パスの `CC/` は `ClaudeCode/.claude/` の略。

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `CC/skills/xddp-common/scripts/knowledge_place.py` | 修正 | `upsert` サブコマンド（置き場所の決定と `constraints.md` への書き込み。鍵の接頭辞・`subjects`・`replace`・`emptied`。3.1）。予約名との衝突（R1）・ワークスペースの外の絶対パス（R4）・`commonpath`（R5）・入力の制御文字（A1-17）。予約名は `docs_layout` から import する |
| `CC/skills/xddp-common/scripts/docs_layout.py` | 修正 | code-knowledge の予約名（制約の置き場所にしないディレクトリ名）と `constraints.md` のファイル名を足す（3.7） |
| `CC/skills/xddp-common/scripts/ai_index.py`・`CC/skills/xddp-02-analysis/scripts/domain_refs.py` | 修正 | `constraints.md` のファイル名を `docs_layout` から使う（3.7。動作は変えない） |
| `CC/skills/xddp-04-specout/scripts/specout_bfs.py` | 修正 | `status` の `confirmed_modules`・`doc-targets` の `doc_target_modules` と、その説明のコメントを消す（3.5） |
| 上のスクリプトのテスト（`test_knowledge_place.py`・`test_docs_layout.py`・`test_specout_bfs.py`）と、`CC/skills/xddp-02-analysis/scripts/tests/test_domain_refs.py`・`CC/skills/xddp-common/scripts/tests/test_ai_index.py` | 修正 | 3.8 |
| `tools/harness/refcheck.py`・`tools/harness/tests/test_refcheck.py` | 修正 | 検査H（宛先ルーティング表の単一情報源。3.7。7. の 3.） |
| `CC/agents/xddp-close-knowledge-agent.md` | 修正 | Step C3.6 の制約の昇格を `upsert` に置き換え、鍵・出典を決める。`_domain名要確認一覧` の規則。共有定数の昇格の「SPO §4.5 の `定義モジュール` → `定義場所`」の対応。「### Output Format」の新しい節「## 前回のクローズで書き、今回は書かなかった制約」（3.2・3.6） |
| `CC/agents/xddp-survey-promote-agent.md` | 修正 | §2.6 の昇格を `upsert` に置き換える（`section` は項目ごとに選ぶ）。出典の書式は code-knowledge-boundary.md を参照する（「### Process」の 4.）。返答に「前回の昇格で書き、今回は書かなかった制約」を足す。宛先は表の行の名前で引く（3.2・3.4・3.6） |
| `CC/skills/xddp-update-knowledge/SKILL.md` | 修正 | constraint を `upsert`（プレビューは `--dry-run`。「対象」は `subjects`）に置き換え、置き換えるかを人が選ぶ。Step 2 の書き先は `upsert` の出力から示す。callgraph の入力項目。flow・callgraph の宛先を表で引く（3.3） |
| `CC/skills/xddp-survey/SKILL.md` | 修正 | Step 5 の表の昇格先を表の行の名前にする。`MODULE_FALLBACK` の topic の説明（3.4）。Step 9 で前回は書いたが今回は書かなかった制約を示す（3.2） |
| `CC/skills/xddp-close/SKILL.md` | 修正 | Step D で「昇格見送り一覧」と、前回は書いたが今回は書かなかった制約も示す（3.2） |
| `CC/skills/xddp-rules/code-knowledge-boundary.md` | 修正 | 書く側を `upsert` にする。鍵・出典・予約名との衝突・`outside-repo` の説明。`_structures/` の書き手。ルーティング表の `{XKNOW}/_flows/...` の省略をやめる（3.1・3.6） |
| `CC/skills/xddp-close/templates/code-knowledge-constraints-template.md` | 修正 | 3つの節すべてに `**対象:**`。鍵の行。更新ルールと出典の説明（3.6） |
| `CC/skills/xddp-close/templates/code-knowledge-constants-template.md`・`code-knowledge-structures-template.md`・`code-knowledge-flows-*-template.md` | 修正 | 出典の説明と見本の値（CR 番号）。`_constants` の「定義場所」の説明（3.6） |
| `README.md`・`CLAUDE.md`・`Makefile`（コメント） | 修正 | 3.9 |
| `docs/adr/ADR-0037-constraints-entry-keys.md` | 追加 | 3.9 |
| `docs/adr/ADR-0033-constraints-module-key.md`・`docs/adr/README.md` | 修正 | 3.9 |
| `docs/xddp-contract-audit-2026-11.md` | 修正 | 8.2・8.3 の P2 の名前（3.9） |
| `CC/skills/xddp-04-specout/templates/04_specout-summary-template.md` | 修正 | §4.5 の2つの HTML コメントが書き写している宛先のパスを、宛先ルーティング表の行の名前にする（3.6） |
| `docs/document-flow.md` | 修正 | constraints.md の更新を「CK-NNN ID をキーに upsert」から「鍵（元の文書の項目）で照合して `upsert` が書く」にする（3.9） |

---

## 3. 変更内容

### 3.1 `knowledge_place.py`（A1-1〜A1-6・A1-17・R1・R4・R5）

**変更前:**
- `place` サブコマンドが置き場所を返すだけで、`constraints.md` への書き込み（`[CK-NNN]` の採番・upsert・節と欄の書式）は3つの経路の LLM がそれぞれ行う。upsert の鍵は経路ごとに違い、survey・手での登録・クローズの SPO §5.6 は「同じ出典」、TRS は `CR-{CR} / NG-{NNN}`。
- `_module_of` は、共通の先頭の第1要素が予約名なら `reserved_collision` を true にするが、置き場所はその予約名のまま返す。`list_places` は第1要素が `_structures`・`_constants`・`_flows`・`_cochange` のものを除くので、その制約はどこからも読まれない（R1）。
- `/` で始まり、ワークスペースの下でもリポジトリの下でもないパスは、リポジトリのルートからのパスとしての候補も足し、その候補がリポジトリの下にあるので `not-found` を返す（R4）。
- `_common_dir` は `posixpath.commonpath` と同じ処理を自前で書いている（R5）。
- 入力 JSON の文字列に制御文字（`\n`・`\f` 等。人の入力 `src\network\foo.c` を JSON に埋め込むとこうなる）があっても、そのまま扱い、黙って `no-path` になる（A1-17）。

**変更後:**

(a) **`upsert` サブコマンド（追加）:** `knowledge_place.py upsert --docs {DOCS} --repo {repo} --repo-root {REPOS_MAP[repo] の値} --workspace-root {WORKSPACE_ROOT} [--input {入力 JSON のファイル}] [--batch-cr {CR_NUMBER} | --batch-survey {SURVEY_FILE}] [--dry-run]`（以下、`--batch-cr`・`--batch-survey` のどちらかを指定することを「`--batch` を指定する」と書く）
- `--input` は `place` と同じく任意で、省略すると stdin から読む。エージェントは Write で入力 JSON をファイルに書いて `--input` で渡し、スキルは引用符付きのヒアドキュメント（`<<'EOF'`）で stdin に渡してよい（今の `place` の約束と同じ）。
- `--repo cross` は終了コード 2（制約は `{XKNOW}` に置かない。code-knowledge-boundary.md「### 宛先への当てはめ」）。
- 入力（1回の呼び出しで、その repo の知見をまとめて渡す。空のリストでもよい）: `[{"id", "targets", "subjects", "fallback", "section", "title", "fields", "source", "key", "replace"}, …]`
  - `id`・`targets`・`fallback`: `place` と同じ。置き場所は `targets` だけから決める。`upsert` では `fallback` が書き先のディレクトリになるので、`_general`・`_root`、またはリポジトリのルートからの相対パス（`/` 区切り。空・`.`・`..` の要素・先頭の `/`・ドライブ名・`\` を含まず、第1要素が 3.7 の「制約の置き場所にしない予約名」でない）だけを受け付け、違えば終了コード 2（`{KNOW}` の外や、読まれない置き場所に書かない）。
  - `subjects`（任意）: 置き場所の決定に使わず、`**対象:**` に表示だけする対象の表記（文字列のリスト）。手での登録の自由記述の「対象」に使う（3.3）。
  - `section`: 節の語彙（`constraint`＝既知の制約・落とし穴、`assumption`＝仕様上の暗黙の前提、`performance`＝パフォーマンス・非機能特性）。
  - `title`・`fields`: 見出しと、節ごとの欄。`fields` は、節ごとに決まった英語のキーを持つオブジェクト（`constraint`: `content`＝内容・`workaround`＝回避策、`assumption`: `premise`＝前提・`reason`＝理由、`performance`: `observation`＝観察・`implication`＝示唆）。その節のキーはすべて必須で、値は文字列（空でもよく、空なら `—` と書く。元の文書に回避策の書かれていない項目等）。節に無いキー・キーの欠け・文字列でない値は終了コード 2。欄の見出し（`**内容:**` 等）はスクリプトがテンプレートのとおりに書く。
  - `source`: 出典の表示（3.2 の書式）。
  - `key`: 元の文書の中での項目の鍵（3.2 の書式）。`--batch` を指定したときは必須で、書く鍵は `{接頭辞}{key}`（接頭辞は下の `--batch-cr`・`--batch-survey`）。`--batch` が無いときは指定できず、スクリプトが `manual:{file}:{CK-NNN}`（書き先の `{KNOW}` からの相対パスと、付けた番号）の鍵を付けて新規に足す（同じ `{KNOW}` の中で重ならない）。
  - `replace`（任意。`--batch` が無いときだけ）: 置き換える既存のエントリの `[CK-NNN]`（手での登録で人が選んだとき。3.3）。鍵の行の無いエントリ（人が直接書いたもの）も指定できる。置き換えたエントリの鍵は新しい `manual:` の鍵にする（人が書き直した内容を、元の経路のやり直しで上書きしない。元の経路をやり直すと、元の項目は別のエントリとしてもう一度足される）。
  - 1回の入力の中で書く鍵が重なる、または `replace` が重なる場合は終了コード 2（黙って後勝ちにしない）。
- `--batch-cr {CR_NUMBER}`・`--batch-survey {SURVEY_FILE}`（どちらか1つ）: 鍵の接頭辞をスクリプトが決める。`--batch-cr` は `cr:{CR_NUMBER}:`、`--batch-survey` は `survey:{SURVEY_FILE を WORKSPACE_ROOT からの相対パスに正規化したもの（/ 区切り・./ なし）}:`。`--batch-survey` のパスがワークスペースの下に無ければ終了コード 2。経路の名前空間（`cr:`・`survey:`・`manual:`）を固定の接頭辞で分けるので、CR フォルダ名が `manual`・`SURVEY` 等でも鍵の照合・`not_written` が他の経路のエントリと混ざらない。LLM が接頭辞を組み立てないので、やり直しで接頭辞が揺れない。
- 処理:
  1. 置き場所を `place` と同じ規則で決める（(b) の衝突の扱いを含む）。書き先は `{KNOW}/{MODULE}/constraints.md`（`{KNOW}` は `docs_layout.code_knowledge_dir(docs, repo)`）。
  2. 同じ鍵のエントリを `{KNOW}` の下のすべての `constraints.md` から探す。同じファイルの同じ節にあれば `[CK-NNN]` を保って置き換える（`replaced`）。同じファイルの別の節にあれば（survey のやり直しでエージェントが `section` を選び直したとき等）、`[CK-NNN]` を保って新しい節の末尾へ移す（`moved`）。別の置き場所にあれば、そこから消して新しい置き場所に足す（置き場所が変わったとき、古い置き場所に残さない。`moved`）。`[CK-NNN]` はファイルごとの番号なので、新しい置き場所のファイルの最大の番号＋1 で付け直す（出力の `ck` は新しい番号、古い番号は出力の `moved_from`〔古いファイルの `{KNOW}` からの相対パスと `CK-NNN`〕で示す）。無ければ、そのファイルの最大の番号＋1 で足す（ファイルが無ければ 5. のとおり作り、`001`）。エントリを消した結果、エントリが1件も無くなった `constraints.md` は消さず、出力の `emptied` に返す。
  3. `--batch` を指定したときは、`{KNOW}` の下で鍵がその接頭辞で始まり、今回の入力に無いエントリを探して出力に返す。消さない（同じ CR のクローズ・同じ SURVEY の昇格をやり直したとき、前回は書いたが今回は書かなかった制約を人に示し、消すかは人が決める。7. の 2.）。入力が空のリストでも行う（やり直しで昇格する制約が0件になったとき、前回のエントリをすべて示す）。
  4. エントリの書式は、テンプレート（`code-knowledge-constraints-template.md`）の節・欄に従う。3つの節すべてに `**対象:**`（`targets` と `subjects` の表記をすべてそのまま `, ` で並べる。どちらも空なら `—`）と `**出典:**` を書き、鍵は見出しの次の行に `<!-- key: {鍵} -->` で書く（人の読む表示に出さない）。
  - **既存のファイルの読み方（エントリの切り出し）:** フェンスのコードブロック（` ``` `・`~~~`）の外の行だけを見出しとして扱う。節は `## ` の行から次の `## ` の行の前まで、エントリは `### [CK-NNN]` の行から、次の `### `・`## ` の行の前まで。鍵は、エントリの見出しの次の行が `<!-- key: … -->` のときだけ読む。`### [CK-NNN]` で始まらない `### ` の見出し（人が書いたもの）の範囲は、エントリとして扱わず、そのまま残す。
  - **本文の欄の検査:** `fields`・`source` の値に、フェンスのコードブロックの外で `#` から始まる見出しの形の行（`^#{1,6} `）や `<!-- key:` で始まる行があれば終了コード 2（書いた後に読み直したとき、エントリの境界や鍵を取り違えないため。コード片の中のコメントはフェンスで囲めば書ける）。
  5. ファイルを新しく作るときは、テンプレートの見出し（`# {置き場所} 制約・注意事項` の置き場所を `{MODULE}` で埋める）と、更新ルールの blockquote（3.6 で書き直したもの。人が直接書き直すときの約束を伝える）と、3つの節の見出しを作り、テンプレートの見本のエントリ（`[CK-001] {タイトル}` 等）は書かない。
  6. 鍵の行の無いエントリ（人が直接書いたもの等）は、鍵による照合と `not_written` の対象にせず、消さない（`replace` で人が指定したときだけ置き換える）。
  7. **書く順序:** すべての入力の検証（終了コード 2 の条件すべて。書き先を決めてからでないと分からない `replace`・`fallback` を含む）と、すべてのファイルの書いた後の内容の決定を先に終え、その後でファイルを書く。終了コード 2 のときはどのファイルも変えない（手での登録の呼び直しで重複させない。`moved` で古いファイルから消しただけの状態を残さない）。各ファイルは一時ファイルに書いて置き換える。
- 出力（stdout の JSON 1行）: オブジェクト `{"entries": […], "not_written": […], "emptied": […]}`。
  - `entries`: 入力の順に、`place` の出力の要素（`id`・`module`・`reserved_collision`・`targets`）に `file`（`{KNOW}` からの相対パス）・`ck`（`CK-NNN`）・`action`（`added`＝新規、`replaced`＝同じファイルの同じ節で置き換え、`moved`＝同じファイルの別の節か別のファイルへの移動。`--dry-run` のときは、書いたらそうなる値）を足したもの。`moved` のときは `moved_from`（移す前の `file`・`ck`）も足す。
  - `not_written`: 3. で見つけたエントリの `file`・`ck`・`key`・`title`（`--batch` が無ければ空のリスト）。
  - `emptied`: 2. のファイルの `{KNOW}` からの相対パス。
  - `--dry-run` のときは何も書かず、`existing` を足す。`existing` は書き先ごとのオブジェクト `{"{file}": [{"ck", "title", "key"}, …]}`（書き先が無ければ空のリスト。3.3 のプレビュー）。
- 終了コード: `place` と同じ（0＝成功、1＝`--repo-root` が無い、2＝引数・入力の誤り）。次も 2: `replace` の `[CK-NNN]` が書き先に無い、入力の中で鍵や `replace` が重なる、`--batch` があるのに `key` が無い・`--batch` が無いのに `key` がある・`--batch` と `replace` を同時に使う・`--batch-cr` と `--batch-survey` を同時に使う、`--repo cross`、`--batch-survey` がワークスペースの外、`fallback`・`fields` の誤り、本文の欄の検査に当たる。
- 人に示すもの（`status` が `placed` 以外の対象・`reserved_collision`）の約束は今のまま。

(b) **予約名との衝突（R1）:** 共通の先頭の第1要素が、制約の置き場所にしない予約名（`_structures`・`_constants`・`_flows`・`_cochange`。3.7 で `docs_layout` に置く）なら、置き場所をその知見の `fallback` にし、`reserved_collision` を true にする。`_root`・`_general` と同じ名前のディレクトリは今のまま（その置き場所に混ざるが読まれる）。7. の 1.。

(c) **ワークスペースの外の絶対パス（R4）:** `/` で始まるパスのうち、そのままの絶対パスがワークスペースの下でもリポジトリの下でもないものは、リポジトリのルートからのパスとしての候補（`{repo_root}/…`）の所在ディレクトリが無ければ `outside-repo` にする。`not-found` は、相対パスと、リポジトリの下の絶対パス（`{repo_root}/…` の形）で所在ディレクトリが無いときだけ。
- 受け入れる限界: リポジトリのルートからの意味で `/` を付けて、まだ無いディレクトリを書いたもの（`/src/newdir/x.c`）も `outside-repo` になる（実在しないディレクトリでは、ワークスペースの外の絶対パスと区別できない）。code-knowledge-boundary.md の `status` の説明と ADR-0037 に書く。

(d) **`commonpath`（R5）:** `_common_dir` を消し、`posixpath.commonpath` を使う（呼び出し元はリポジトリ直下を含む場合を先に除くので、結果は同じ）。

(e) **入力の制御文字（A1-17）:** `place`・`upsert` の入力の `id`・`targets`・`subjects`・`fallback`・`key`・`replace`・`title` に制御文字（U+0000〜U+001F・U+007F）があれば、終了コード 2 にし、stderr に「JSON の `\` は `\\` と書く（パスは `/` で区切ってよい）」と出す。黙って `no-path` にしない。`fields`・`source` は改行・タブ・`\r` を許し、`\r\n`・`\r` は `\n` にそろえる（本文にはコード片の字下げや、貼り付けた CRLF が入るため）。
- 受け入れる限界: 本文の欄（`fields`・`source`）で `\` を書き漏らして `\n`・`\t` になったもの（`C:\temp` 等）は検出できない（本文には改行・タブが普通に入るため）。

**理由:** 3つの経路がそれぞれ upsert を解釈していたことが、A1-1〜A1-4 の共通のもと。採番・照合・書式は決定的なのでスクリプトにし、鍵を明示して入力に持たせる（7. の 2.・6.）。書き先とエントリの書式を、置き場所を決める同じスクリプトに置くので、書いた場所が `list_places` で読まれることをテストで確かめられる（3.8）。R1 は「読まれない場所に書く」ことが問題なので、読まれる `fallback` に置く。

### 3.2 クローズ・survey の昇格（A1-1・A1-3・A1-4・A1-5・A1-10・A1-11）

**変更前:**
- close-knowledge-agent の Step C3.6 は、制約の対象を拾って `place` に渡し、返った置き場所の `constraints.md` に自分で upsert する。鍵は TRS だけに定めがある（`CR-{CR_NUMBER} / NG-{NNN}`）。出典は SPO §5.6 が `{CR_NUMBER}`、TRS が `CR-{CR_NUMBER} / NG-{NNN} / 発見日: {TODAY}`、LL は定めが無い。
- `_domain名要確認一覧` に「Add」と書いているのは callgraph と per-repo の共有定数だけ。
- close の Step D は、PENDING-KNOWLEDGE の「## _domain名要確認一覧」と「## 置き場所の確認が要る制約」を示し、「## 昇格見送り一覧」を示さない。
- survey-promote-agent の §2.6 の昇格は、`place` の後に自分で upsert し、「constraints.md は同一出典があれば置換」、出典は `SURVEY-{TODAY}`。

**変更後:**
- close-knowledge-agent の Step C3.6 の制約の昇格は、repo ごとに、昇格する制約を入力 JSON に書いて `upsert --batch-cr {CR_NUMBER}` を1回実行する（エージェントは `constraints.md` を直接 Edit・Write しない。C3.6 の今の 3.〔`{KNOW}/{MODULE}/constraints.md` に upsert する〕と、TRS の「Upsertキー」の手順を消す）。昇格する制約が0件の repo でも、空のリストで実行する（今の 1. の「昇格する制約が無ければ 2.・3. を行わない」を消す。3.1 (a) の 3.）。入力の `key` と出典（書く鍵は `cr:{CR_NUMBER}:{key}`）:

| 元 | `section` | 入力の `key` | 出典 |
|---|---|---|---|
| SPO §5.6 の行（影響度 高・中） | `performance` | `SPO-5.6:{行の順番}`（表のデータ行の順番。影響度で絞る前に数える） | `{CR_NUMBER} / SPO §5.6` |
| LL `#リスク`・`#見落とし` | `constraint` | `{LL の ID}:constraint` | `{LL の ID}` |
| LL `#仕様定義` | `assumption` | `{LL の ID}:assumption` | `{LL の ID}` |
| TRS の NG | `constraint` | `{TRS のファイル名の拡張子を除いた部分}:{NG-NNN}` | `{CR_NUMBER} / {TRS のファイル名の拡張子を除いた部分} / {NG-NNN} / 発見日: {TODAY}` |

  - LL はタグを複数持てるので、1件の LL が `constraint` と `assumption` の両方に昇格することがある。LL の鍵に `section` を入れて、2件が重ならないようにする（それでも重なれば 3.1 (a) で終了コード 2）。
  - 出典・鍵の CR は `{CR_NUMBER}` をそのまま使い、`CR-` を足さない（A1-5）。
  - 昇格しなかった repo（終了コードが 0 以外）・`placed` 以外の対象・`reserved_collision` を「## 置き場所の確認が要る制約」に書く約束は今のまま。`upsert` の出力の `not_written` と `emptied` は、OUTPUT_FILE の新しい節「## 前回のクローズで書き、今回は書かなかった制約」に1行ずつ書く（`{repo}: {file} [CK-NNN] {タイトル}`、`emptied` は `{repo}: {file}（エントリが無くなったファイル）`。なければ「なし」）。消さない。
- close の Step D に「**前回のクローズで書き、今回は書かなかった制約（不要なら `constraints.md` から直接消してください）:** {KNOWLEDGE_RESULT の同じ節, or "なし"}」を足す。
- `_domain名要確認一覧`: Step C3.6 の個々の「Add」をやめ、「共有の知見（`_structures/`・`_constants/`・`_flows/`。per-repo・cross とも）のファイルを新規に作ったとき、またはドメイン名に暫定の `shared` を使ったときは、そのファイルを一覧に足す」という1つの規則にする（A1-11）。
- close の Step D に「**昇格見送り（code-knowledge の昇格条件を満たさなかったもの）:** {KNOWLEDGE_RESULT の「## 昇格見送り一覧」, or "なし"}」を足す（A1-10）。
- survey-promote-agent の §2.6 の昇格は、入力 JSON に書いて `upsert --batch-survey {SURVEY_FILE}` を1回実行する（エージェントは `constraints.md` を直接 Edit・Write しない）。入力の `key` は `2.6:{項目の順番}`（書く鍵は `survey:{SURVEY_FILE の WORKSPACE_ROOT からの相対パス}:2.6:{項目の順番}`。相対パスはスクリプトが作る）、出典は `SURVEY-{TODAY} / {SURVEY_FILE のファイル名}`、`section` は項目ごとに `constraint`（制約）か `assumption`（前提）をエージェントが選ぶ（§2.6 は「制約・前提条件」なので両方を含みうる。意味判定）。§2.6 を `SELECTED_SECTIONS` に選んだときは、昇格する項目が0件でも空のリストで実行する。選ばなかったときは実行しない（人が今回は制約を昇格しないと選んだので、前回のエントリの一覧も出さない）。`not_written`・`emptied` はエージェントの返答の「前回の昇格で書き、今回は書かなかった制約」に書き、survey の Step 9 で示す（不要なら人が直接消す）。

**理由:** 鍵が元の文書の項目を指すので、1回の実行の中で互いに置き換わらず（A1-1・A1-3）、実行回の違う NG も別のエントリになる（A1-4）。やり直しでは同じ鍵が置き換わる。`--batch` の接頭辞は、同じ CR・同じ SURVEY のやり直しだけを対象にし、他の CR・人が書いたエントリは一覧にも出さない。接頭辞（CR 番号・SURVEY ファイルの相対パス）はスクリプトが付けるので、LLM の書き方の揺れで鍵が変わることはない（方針 1.）。
やり直しで今回書かなかった理由は、人が元の項目を消した・行の番号がずれた（SPO §5.6・SURVEY §2.6 の鍵は行・項目の順番なので、途中を消すと後ろの鍵がずれ、同じ内容が別の鍵で書き直されて、古い鍵のエントリが一覧に出る）・LLM の昇格の判断が変わった（LL の `#仕様定義` 等）のどれもありうる。最後の場合は誤りではない知見なので、スクリプトは消さず、人に示す（CLAUDE.md「人の依頼は LLM の関係判断で拒否しない」の、LLM の判断で扱いを変えたものは人が見直せる形で残す、と同じ）。

### 3.3 update-knowledge（A1-2・A1-12・A1-13・A1-17）

**変更前:**
- constraint: Step 1.5 で入力のパスをヒアドキュメントの JSON に埋め込んで `place` に渡す。Step 3 は「同じ出典があれば置き換え、無ければ足す」。Step 2 のプレビューは置き換えを示さない。
- callgraph: Step 1 で「フロー名（ファイル名のベース）」を入力させるが、Step 3 のファイル名は `{DOMAIN}-{VAR_NAME}-callgraph.md` で、フロー名を使わない。
- flow・callgraph: Step 3 がパス（`{KNOW_DIR}/code-knowledge/_flows/…`）とテンプレートのパスを自分で書いている。

**変更後:**
- constraint:
  - Step 1.5: 入力を1件の知見にして `upsert --dry-run` を実行する。`targets` は「対象のファイルまたはディレクトリ」の1要素（空なら空のリスト）、`subjects` は「対象」の入力を分けずにそのまま1要素、`fallback` は `_general`、`section` は `constraint`、`fields` は `content`＝内容・`workaround`＝回避策、`key` は書かない。入力 JSON は引用符付きのヒアドキュメントで stdin に渡し、人の入力の `\` を `\\`、`"` を `\"` にして書く（`\` を書き漏らすと 3.1 (e) で終了コード 2 で止まる）。
    - 置き場所は `targets` だけから決まるので、「対象のファイルまたはディレクトリ」だけで決まる（「対象」にパスが書かれていても置き場所は変わらない。3.1 (a) の `subjects`）。「対象のファイルまたはディレクトリ」が空なら `fallback` の `_general` になる。
    - `status` が `placed` 以外のときの扱い（入力し直す／パスなし）は今のまま。パスなしを選んだら、その表記を `subjects` の先頭に移し、`targets` を空にしてやり直す（置き場所は `_general`）。
  - Step 2: プレビューに、`upsert --dry-run` の出力の書き先（`file`）と、`existing`（書き先の既存のエントリの `[CK-NNN]` とタイトル）を示し、「新しいエントリとして足す（既定）／既存の [CK-NNN] を置き換える」を人に尋ねる（A1-2）。書き先のパスをスキルで組み立てない（今の Step 2 の `{KNOW_DIR}/code-knowledge/{MODULE}/constraints.md` を消す。3.7 の 3. の検査H）。
  - Step 3: Step 1.5 と同じ入力で `upsert` を実行する（置き換えるときは `replace` に `[CK-NNN]` を入れる）。出典で置き換えない。今の Step 3 の constraint の手順（採番・「same 出典」の upsert・テンプレートからの作成）を消す。
- callgraph: Step 1 の「フロー名」の項目を消す（ファイル名は宛先ルーティング表のとおり `{VAR_NAME}` から作る）（A1-12）。
- flow・callgraph・structure: 出力パスとテンプレートは `KNOWLEDGE_ROUTING` の該当行（「機能間フロー（シーケンス）」「データフロー図（DFD）」「変数データフロー（callgraph）」「構造体依存関係」）で引き、スキルにパスを書かない（A1-13）。

**理由:** 手での登録は人が置き換えるかを決められるので、出典の一致で LLM に決めさせない（CLAUDE.md「人の依頼は LLM の関係判断で拒否しない」の、要否を人に尋ねる考え方と同じ）。人が明示した置き場所（対象のファイルまたはディレクトリ）を、自由記述の「対象」で変えないために、置き場所の入力（`targets`）と表示だけの対象（`subjects`）を分ける。

### 3.4 survey（A1-14・A1-15・A1-17）

**変更前:**
- Step 5 の「SURVEY 節 → knowledge 昇格の対応と昇格条件」の表の「昇格先」列と、survey-promote-agent の「### Process」の 2. が、宛先のパス（`_constants/{DOMAIN}-constants.md` 等）を書いている。
- `MODULE_FALLBACK` の topic スコープの説明が「2.6 由来の constraints.md 昇格は module スコープのみで発生する」。
- `MODULE_FALLBACK` を決めるとき、SURVEY の「ディレクトリ」欄の値をヒアドキュメントの JSON に埋め込む。

**変更後:**
- 表の「昇格先」列を「宛先ルーティング表の行」列（「共有定数・列挙値」「変数データフロー（callgraph）」「制約・落とし穴」「構造体依存関係」「機能間フロー（シーケンス）」）にする。survey-promote-agent の 2. も行の名前だけを書く（パスは `KNOWLEDGE_ROUTING` から引く）。`{MODULE}` は 3.2 の `upsert` が決める（A1-14）。
- topic スコープの説明を「`_general`（§2.6 の項目は、対象のパスがあればその置き場所、無ければ `_general`）」にする（A1-15）。
- 「ディレクトリ」欄の値を JSON に入れるときは `\` を `\\` にする。書き漏らしは 3.1 (e) で終了コード 2 になり、今の手順（`MODULE_FALLBACK` を `_general` にし、その旨を Step 9 で示す）に乗る（A1-17）。

**理由:** 宛先ルーティング表の「この表以外に定義してはならない」に合わせる。値は今は一致しているが、表を変えたときに食い違う（A1-13 と同じ）。

### 3.5 `specout_bfs.py`（A1-16）

**変更前:** `status`（`--brief` なし）が `confirmed_modules`（`_module_dir_for_file`＝パスの第1要素）を出す。`doc-targets` が `doc_target_modules`（同じ関数）を出す。どちらも読む側はテストだけで、値は ADR-0033 で廃止した置き場所の規則（第1階層）。

**変更後:** 2つのフィールドを出さない。`cmd_status` の、フィールドを説明するコメント（`# PLAN-20260809: MODE: document Step 1.5 …`）も消し、モジュールの docstring と `--help` に2つのフィールドの説明があれば直す。`_module_dir_for_file` は `_catalog_module_for_file` の一致しないときの扱いにだけ残す（P4 の 3.10 のとおり変えない）。`init` の `module_priority_map` を作るローカル変数 `confirmed_modules`（`_catalog_module_for_file` で作る別のもの）は変えない。`test_specout_bfs.py` の2つのフィールドを確かめるテストは、出力に無いことを確かめる形にする。

**理由:** 読む側の無い値を、廃止した規則で出し続けると、後で読む側を足したときに ADR-0033 の規則と食い違う。code-knowledge の置き場所が要る読む側は `knowledge_place.applicable_places` を使う。

### 3.6 記述・テンプレート（A1-5・A1-6・A1-9・`_structures/` の書き手）

**変更前:**
- constraints テンプレートは「既知の制約・落とし穴」の節にだけ `**対象:**` があり、更新ルールは「[CK-NNN] で識別」「出典は（CR-NNN）で記録」。
- 他の code-knowledge のテンプレートも「出典は（CR-NNN）で記録」。
- `_constants` テンプレートの「定義場所」は `{ファイルパス:行}`。クローズの元（SPO §4.5「モジュール横断共有定数・列挙値」）の列は `定義モジュール`、survey の元（§2.4）は `定義場所（ファイル:行）`。
- code-knowledge-boundary.md の「overview/ vs _structures/ の役割分担」は、`{DOCS}/{repo}/…/_structures/` の書き手に xddp-close（クローズ時に蓄積）を挙げる。

**変更後:**
- constraints テンプレート: 3つの節すべてに `**対象:**` を置く。見出しの次の行に `<!-- key: {鍵} -->` を置く。更新ルールを「エントリは `knowledge_place.py upsert` が書く。同じエントリかは鍵で決める。人が直接書いたエントリ（鍵の行が無いもの）は、鍵による照合と削除の対象にしない（手での登録で人が置き換えを選んだときだけ置き換える）。自動の経路で書いたエントリを直接書き直したときは、鍵の行（`<!-- key: … -->`）も消す（消さないと、同じ CR のクローズ・同じ SURVEY の昇格をやり直したときに上書きされる）」にする。出典の説明を「出典は経路ごとの書式（code-knowledge-boundary.md）」にする（A1-5・A1-6）。
- 他の code-knowledge のテンプレートの「出典は（CR-NNN）で記録」を「出典は経路ごとの書式（code-knowledge-boundary.md）」にする（A1-5。CR・survey・手での登録のどの経路も同じテンプレートに書くので、CR 番号だけを書かない）。`_constants` テンプレートの出典列の注記（`SURVEY-{YYYYMMDD}`。survey-promote-agent が書く `SURVEY-{TODAY}` は YYYY-MM-DD で、食い違っている）も同じく boundary を指す形にする。
- 見本の値の出典も直す（A1-5。close-knowledge-agent はシーケンス図・DFD・cross の構造体の出典の書式を指示しないので、LLM は見本に倣う）: flows-sequence・flows-dfd・structures の `**出典:** CR-NNN …`、constants の表の出典列と注記、constraints の各エントリの `**出典:** CR-NNN …` の `CR-NNN` を `{出典}` にする（経路ごとの書式は code-knowledge-boundary.md にある）。
- `_constants` テンプレートの「定義場所」を `{ファイルパス:行。ファイルが分からなければ定義モジュール}` にし、close-knowledge-agent の共有定数の昇格に「SPO §4.5 の `定義モジュール` → `定義場所`」の対応を書く（A1-9。SPO のテンプレートは変えない。理由は 6.）。
- `04_specout-summary-template.md` の §4.5 の HTML コメント（「`_constants/{domain}-constants.md` に昇格される」「`_flows/{domain}-{varname}-callgraph.md` に昇格される」）を、宛先ルーティング表の行の名前（「共有定数・列挙値」「変数データフロー（callgraph）」）にする（A1-14 と同じ型の写し。`templates/` の下なので検査H は当てないが、このプランで直す）。
- code-knowledge-boundary.md:
  - 「## 知見の置き場所（MODULE）」の「書く側」に `upsert`（入力〔`subjects` を含む〕・出力〔`not_written`・`emptied`・`existing`〕・鍵と経路の名前空間・`--batch-cr`・`--batch-survey`・`--dry-run`・`replace`・`fallback` の検査・エントリの切り出しと本文の欄の検査）を書き、制約は `upsert` で書く（エージェント・スキルが `constraints.md` を直接 Edit・Write しない）と書く。経路ごとの鍵と出典の書式（3.2 の表と、survey・手での登録）もここに書き、各経路はこの節を参照する。出典の書式は制約だけでなく code-knowledge のすべての知識種別について経路ごとに書く: CR の経路（close）は `{CR_NUMBER}`（`CR-` を足さない）に元の文書を添えたもの、survey は `SURVEY-{TODAY} / {SURVEY_FILE のファイル名}`（`TODAY` は YYYY-MM-DD。§2.6 以外の節も同じ。survey-promote-agent の「### Process」の 4. はこの書式を参照する）、手での登録は人の入力のまま。survey の §2.6 の鍵の「項目の順番」は、§2.6 の最上位の箇条書きの項目の順番（箇条書きが無ければ段落の順番。入れ子の箇条書きは親の項目に含める）で数える。
  - `status` の説明に R4 の扱いと受け入れる限界（3.1 (c)）、予約名の説明に R1 の扱い（`fallback` に置く）を書く。
  - 「overview/ vs _structures/ の役割分担」の `_structures/` の書き手を「xddp-close（cross の `{XKNOW}` のみ）／ xddp-survey ／ xddp-update-knowledge」にする。
  - 宛先ルーティング表の「機能間フロー（シーケンス）」行の `{XKNOW}/_flows/...` を、省略しない `{XKNOW}/_flows/{DOMAIN}-{FLOW_NAME}-sequence.md` にする（3.7 の 1. の表のテストが、すべての出力パスのファイル名を読めるようにする）。

**理由:** テンプレートを `upsert` の書式の正とし、スクリプトの定数をテストでテンプレートと突き合わせる（P4 の 3.13 と同じ。テンプレートは人も読むので Python の定数にできない）。

### 3.7 再発防止（PLAN-20261103-contract-audit 3.3）

**1. 書く側→読む側のテスト:**
- `upsert` で書いた `constraints.md` の置き場所が `list_places` に入り、対象のファイルに `applicable_places` が当てはまる（R1 の衝突の場合を含む。予約名と同じ名前のディレクトリの対象は `_general` に入り、`list_places` に出る）。
- `upsert` で書いた `constraints.md` を、`domain_refs.resolve` と `ai_index` の code-knowledge インデックスに通し、制約が集まる。
- `upsert` が書くエントリの節・欄が、`code-knowledge-constraints-template.md` の節・欄（3つの節の見出しと `**対象:**`・各節の欄・`**出典:**`・鍵の行）と一致する。読む側（module-documentation.md の観察 f）が使う `[CK-NNN]` と `**対象:**` の書式を、テンプレートから読んで確かめる。
- `code-knowledge-boundary.md` の宛先ルーティング表を読み、出力パスの `{KNOW}`・`{XKNOW}` の次の要素が `{MODULE}` か `docs_layout.SHARED_KNOWLEDGE_DIRS` のディレクトリ名で、共有の知見のファイルがそのディレクトリの直下（`domain_refs.py` が読む「直下の `*.md`」）である。表のテンプレートのパスが実在する。
- TRS テンプレートの `### NG-` の書式と、3.2 の鍵の作り方が合う（TRS のファイル名の形は `xddp-10-test-run` の `OUTPUT_FILE`。LLM の手順なので unittest では確かめず、下の同期の確認で確かめる）。

**2. 共有の値の単一定義:**
- `docs_layout.py`: code-knowledge の予約名のうち制約の置き場所にしないもの（`SHARED_KNOWLEDGE_DIRS` のキーと `_cochange` の和集合。重複を除くので、cochange-knowledge のプランが `_cochange` を `SHARED_KNOWLEDGE_DIRS` に足しても二重にならず、片方だけ直す必要もない）と、`constraints.md` のファイル名。`knowledge_place.py`（`RESERVED`・`list_places`）・`ai_index.py`・`domain_refs.py` が import する。今は `knowledge_place.NON_CONSTRAINT_DIRS` と `docs_layout.SHARED_KNOWLEDGE_DIRS` が別々に同じ名前を持っている。
- `knowledge_place.py`: 制約のエントリの書式（節の語彙・欄・鍵の行）と、鍵による照合。書く側（3経路）はこのスクリプトだけを通す。
- 単一定義にしないもの: 宛先ルーティング表（LLM が読む）は Python の定数にできないので、1. のテストで `docs_layout` と突き合わせる。共有の知見（`_structures/`・`_constants/`・`_flows/`）のエントリは LLM が書く（ドメイン名・図の中身は意味判定）ので、スクリプトにしない。
- P1 の申し送り（ルーティング表と `docs_layout.py` のディレクトリ名・「直下の `*.md`」の約束）は、1. の表のテストと、下の 3. の検査Hで守る。

**3. refcheck の検査H（足す。7. の 3.）:** `CC/skills/**/*.md`・`CC/agents/*.md` のうち `xddp-rules/code-knowledge-boundary.md` と `templates/` の下を除くファイルに、code-knowledge の宛先のパスがあればエラーにする。宛先のパスは次の2つの形（前に `code-knowledge/`・略記の `{KNOW}/`・`{XKNOW}/` が付いても付かなくても当てる）。
  - `_structures/`・`_constants/`・`_flows/` の直後のファイル名にプレースホルダーを含む形（`_flows/{DOMAIN}-…` 等）。ディレクトリ名だけの言及（`_structures/`）は当てない。
  - `{MODULE}/constraints.md`。
  A1-13・A1-14 のように、他のファイルがパスを書き写すのを防ぐ（A1-14 の survey の表は、接頭辞の無い `_constants/{DOMAIN}-constants.md` の形で書き写していた）。ディレクトリ名は `docs_layout.SHARED_KNOWLEDGE_DIRS` から取る（refcheck は今は標準ライブラリだけを import しているので、refcheck 自身の場所からの相対パス〔`ClaudeCode/.claude/skills/xddp-common/scripts/docs_layout.py`〕を `importlib` でファイルとして読む。ディレクトリ名はツールの定数で、検査する木の中身ではないので、`test_refcheck.py` の一時ディレクトリの見かけのリポジトリにも置かなくてよい）。
- 今の `CC/` で当たるのは、update-knowledge の Step 2（constraint の書き先）と Step 3（flow・callgraph）、survey の Step 5 の「SURVEY 節 → knowledge 昇格の対応と昇格条件」の表の「昇格先」列、survey-promote-agent の「### Process」の 2.、close-knowledge-agent の C3.6 の 3.（2026-11-08 に grep で確かめた）。どれも 3.2〜3.4 で消す。

### 3.8 テスト・fixture

- `test_knowledge_place.py`:
  - `upsert`: 1回の入力の同じ置き場所の複数の項目が別々のエントリになる（A1-1 の再現の逆）。同じ鍵で置き換わり `[CK-NNN]` を保つ。置き場所が変わった鍵は古いファイルから消え（`moved`。新しいファイルの最大＋1 の番号が `ck` に、古いファイルと番号が `moved_from` に出る）、エントリが無くなった古いファイルは残って `emptied` に入る。`--batch` が接頭辞の一致するエントリのうち今回の入力に無いものだけを `not_written` に返し、どのエントリも消さない。他の接頭辞・鍵の行の無いエントリは `not_written` に入らない。行の番号がずれた入力（3件→途中の1件を除いた2件）で、最後の鍵のエントリが `not_written` に入る。空のリストの入力と `--batch` で、前回のエントリがすべて `not_written` に入る。`--batch-survey` の表記が違っても（`./` 付き・絶対パス・相対パス）同じ接頭辞になり、ワークスペースの外なら終了コード 2。CR 番号が `manual`・`survey` の `--batch-cr` でも、手での登録・survey のエントリが `not_written` に入らない。1件の LL の `{LL の ID}:constraint` と `{LL の ID}:assumption` が別々のエントリになる。入力の中で鍵が重なれば終了コード 2。`subjects` が `**対象:**` に出て、置き場所を変えない（`targets` が空なら `fallback`）。`replace` が指定の `[CK-NNN]`（鍵の行の無いエントリを含む）を置き換えて鍵を `manual:` にし、書き先に無ければ終了コード 2。`--batch` と `replace`・`--batch` と `key` の欠け・`--batch` なしの `key` は 2。`--repo cross` は 2。`--dry-run` が書かずに、書き先ごとの `existing` を返す。出力がオブジェクト（`entries`・`not_written`・`emptied`）である。同じ鍵で `section` を変えた入力で、`[CK-NNN]` を保って新しい節の末尾へ移る（`moved`）。2件目が終了コード 2 になる入力（`replace` の番号が無い・本文の欄の検査に当たる）で、1件目も書かれず、どのファイルも変わらない。新しく作ったファイルに更新ルールの blockquote がある。survey の出典が `SURVEY-{TODAY} / {ファイル名}` の形でも鍵・照合に影響しない。3つの節すべてに `**対象:**` を書き、`targets` と `subjects` がどちらも空なら `—`。`fields` のキーの欠け・節に無いキーが終了コード 2、空の値は `—` で書かれる。`fallback` の `../x`・`/abs`・`_structures` が終了コード 2。本文の欄に、フェンスの外の `## ` の行・`<!-- key:` の行があれば終了コード 2、フェンスの中なら通る。既存のファイルで、エントリの本文のフェンスの中の `## ` の行や、人が書いた `### ` の見出し（`[CK-NNN]` で始まらない）を、エントリの境界・エントリとして扱わず、置き換え・移動の後もそのまま残る。ファイルが無ければテンプレートの見出し（置き場所を埋める）と3つの節の見出しで作り、見本のエントリを書かず `001`。
  - R1: 第1要素が `_structures` のディレクトリの対象は `fallback` に置かれ `reserved_collision` が true。`_general` という名前のディレクトリは今のまま `_general`。
  - R4: `/usr/include/stdio.h` 相当（ワークスペースとリポジトリの外）が `outside-repo`。リポジトリのルートからの意味の `/src/x.c`（実在する）は今のまま `placed`、`/nodir/x.c`（リポジトリのルートからの意味でも無いディレクトリ）は `outside-repo`（3.1 (c) の限界）。相対パスの `nodir/x.c` と、リポジトリの下の絶対パス `{repo_root}/nodir/x.c` は `not-found`。
  - A1-17: `targets`・`subjects` に `\n`・`\f` を含む入力が終了コード 2。`fields` の改行・タブは通り、`\r\n` は `\n` になる。
  - 3.7 の 1. のテスト（`list_places`・`applicable_places`・テンプレートとの突き合わせ・ルーティング表）。
- `test_docs_layout.py`: 予約名の定数が `SHARED_KNOWLEDGE_DIRS` のキーと `_cochange` をすべて含み、重複が無い。
- `test_domain_refs.py`・`test_ai_index.py`: `upsert` で書いた `constraints.md` が集まる（3.7 の 1.）。
- `test_specout_bfs.py`: `confirmed_modules`・`doc_target_modules` が出力に無い（3.5）。
- `test_refcheck.py`: 検査H が、パスを書いたファイル（`code-knowledge/_flows/{DOMAIN}-…` の形、略記の `{KNOW}/_flows/{DOMAIN}-…`・`{KNOW}/{MODULE}/constraints.md` の形、接頭辞の無い `_constants/{DOMAIN}-constants.md` の形）でエラーになり、ディレクトリ名だけの言及（`_structures/`）では出ず、boundary と `templates/` の下では出ない。今の `CC/` でエラーが無い（3.2〜3.4 の後）。
- fixture: `test-fixtures/**` の既存の `constraints.md` は変えない（鍵の行の無いエントリとして読まれ、置き換えも削除もされない。読む側は鍵の行を使わない）。
- smoke のシード: 変えない。`phaseClose-single` の close で Step C3.6 が `upsert` を通るかは smoke で確かめる（実行はユーザー）。survey の昇格（§2.6）と update-knowledge の constraint（`--dry-run`→人の選択→`upsert`）は smoke のシナリオが無いので、5. の手での確認で確かめる（実行はユーザー）。

### 3.9 ドキュメント・ADR

- README:
  - 「決定的処理スクリプト」の表の `knowledge_place.py` の行に `upsert`（制約のエントリの書き込み・鍵・`--batch-cr`・`--batch-survey`・`--dry-run`）と、予約名との衝突・`outside-repo` の扱いを足す。呼び出し元は今のまま（close C3.6・survey Step 5・update-knowledge）。`docs_layout.py` の行に code-knowledge の予約名と `constraints.md` を足す。
  - `/xddp-update-knowledge` の説明の `constraint` に「既存のエントリを置き換えるかを人が選ぶ」を足す。
  - 「開発時テストハーネス（make）」の `make lint` の行（検査A〜G を並べている）に検査H を足す。
- ADR-0037（追加）: 制約のエントリをスクリプトが書く理由、鍵の書式（元の文書の項目を指す・出典と分ける・接頭辞はスクリプトが付ける）、`--batch` の範囲と消さずに示す理由（7. の 2.）、`replace` で鍵を `manual:` にする理由と、直接書き直したエントリは鍵の行を消さないとやり直しで上書きされること、経路の名前空間（`cr:`・`survey:`・`manual:`）を固定の接頭辞で分ける理由、置き場所の入力（`targets`）と表示（`subjects`）を分ける理由、予約名との衝突を `fallback` に置く理由、受け入れる限界（3.1 (c)・(e)）、却下した案（6.）。
- ADR-0033: 「範囲外・限界」の「予約名と同じ名前のディレクトリ」と「既存の問題（upsert の鍵）」の2行を、ADR-0037 で扱ったと書き換える。
- `docs/adr/README.md` に ADR-0037 を足す。
- 監査の報告書の 8.2・8.3: P2 の名前を `PLAN-20261108-code-knowledge-writers` にする。
- `docs/document-flow.md`: C3.6 の行・ファイル構成の図・更新方式の表の3か所の「CK-NNN ID をキーに upsert」「ID 一致で置換」を、「鍵（元の文書の項目）で照合し、`knowledge_place.py upsert` が書く（`[CK-NNN]` は保つ）」にする。
- CLAUDE.md: 「ファイルの置き場所」の表の `skills/xddp-rules/` の行に「refcheck 検査H が、宛先ルーティング表のパスを他のファイルが書いていないかを見る」を足す（同じ表の `procedures/`・`reviewer-checklists/` の行が検査G・検査E を書いているのと同じ形）。
- `Makefile`: 先頭と `lint` のコメントが「検査A/B/C/D/E」のままなので、検査A〜H にする（検査F・G の分は前から古い）。

---

## 4. 影響範囲

- **影響するスキル・コマンド:** `/xddp-close`（Step C3.6・Step D）、`/xddp-survey`（Step 5）、`/xddp-update-knowledge`（constraint・callgraph・flow・structure）、`/xddp-04-specout`（`status`・`doc-targets` の出力のフィールドが減るだけ）。
- **影響する工程:** close・随時実行（survey・update-knowledge）。読む側（工程2・工程4a の下調べ・AI_INDEX）の読み方は変えない。
- **後方互換性:** 考慮しない（CLAUDE.md「後方互換性ポリシー」）。既存の `constraints.md` のエントリは鍵の行を持たないので、`upsert` は照合も削除もしない（足すだけ。手での登録で人が `replace` に選んだときだけ置き換える）。移行の手順は足さない。予約名と同じ名前のディレクトリに今までの規則で書かれた制約は、そのまま読まれない（人が移す。ADR-0037 に書く）。
- **今の動作から変わること（実装者が知っておくこと）:**
  - 手での登録で自動の経路のエントリを `replace` で置き換えると、鍵が `manual:` になるので、その CR のクローズ・その SURVEY の昇格をやり直すと、元の項目が別のエントリとしてもう一度足される（人の書き直しを上書きしないほうを選んだ。3.1 (a)）。
  - `/` を付けてリポジトリのルートからの意味で書いた、まだ無いディレクトリのパスは、`not-found` ではなく `outside-repo` になる（3.1 (c) の限界）。
  - close はやり直しで制約が0件の repo でも `upsert` を実行する。`not_written` が出るだけで、何も書かない。
- **エージェントの権限:** close-knowledge-agent・survey-promote-agent の Bash の用途（「`knowledge_place.py` の実行」）は変わらない（サブコマンドが増えるだけ）。`tools:` は変えない。
- **トークン:** エージェントが `constraints.md` を読んで採番・照合しなくなる分だけ減る。入力 JSON に本文を書く分は、今の Edit・Write と同程度。
- **他のプランとの関係:**
  - P5（project-rulebook）: `xddp-close-knowledge-agent.md` を P2（C3.6）と P5（C3.5）が直す。`xddp-close/SKILL.md` を P2（Step D の1行）と P5（A5-1 の順序）が直す。P5 は P2 の実装の後の状態を見て書く。
  - PLAN-20261102-cochange-knowledge・PLAN-20261102-impact-hypotheses: 監査の報告書の 8.3 のとおり、P2 の実装の後に書き換える（A1・A2 の指摘を割り当てた修正プランは P1 と P2）。cochange-knowledge は `_cochange/` を宛先ルーティング表と `docs_layout.SHARED_KNOWLEDGE_DIRS` に足すことになり、3.7 の表のテストと検査H が効く。
  - P1・P3・P4: 実装の後の状態を見て書いた。P3 が直した close-knowledge-agent の出典の1行（`（出典: {LL の ID}）`。C3.5）は変えない。P4 が直した survey の Step 2〜4・6〜8 は変えない。
  - 段階2b の候補（報告書の 6.）は、このプランで触らない。

---

## 5. 確認項目

- [x] 1.2 の18件と監査の外の2件それぞれに、直した箇所とテストがある（スクリプトで直したものは unittest がある。SKILL・agent・テンプレートの記述だけを直したもの〔A1-10・A1-11・A1-12・A1-15・`_structures/` の書き手〕は unittest が無く、下の同期の確認と refcheck で確かめる）
- [x] `make test` が緑（refcheck 検査F・検査H を含む）
- [x] 3.7 の 1. の書く側→読む側のテストが、実物のテンプレート・宛先ルーティング表を読み、`upsert` の出力を `list_places`・`applicable_places`・`domain_refs`・`ai_index` に通している
- [x] 3.7 の 2. の単一定義: `knowledge_place.py`・`ai_index.py`・`domain_refs.py` が code-knowledge の予約名と `constraints.md` を `docs_layout` から import し、自分で定義していない
- [x] スキルの同期: close-knowledge-agent・survey-promote-agent・update-knowledge が制約を `upsert` だけで書き、`constraints.md` を直接 Edit・Write する手順と「同一出典」「同じ 出典」の upsert が実行時ファイルに残っていない。鍵・出典の書式が code-knowledge-boundary.md の1か所にあり、各経路はそこを参照している
- [x] 3経路の鍵が、1回の実行の中で項目ごとに違う（SPO §5.6 の行・LL の ID・TRS のファイルと NG・SURVEY の項目）
- [x] close は `--batch-cr {CR_NUMBER}`、survey は `--batch-survey {SURVEY_FILE}` で呼び、鍵の接頭辞を LLM が書いていない。0件のときも（survey は §2.6 を選んだとき）空のリストで呼ぶ。`upsert` はどのエントリも消さない。`not_written`・`emptied` が close の Step D・survey の Step 9 に出る
- [x] CLAUDE.md・README・ADR が実装と一致する
- [x] 特定ドメイン（Web・業務・組み込み）への偏りがないか（CLAUDE.md「適用ドメインの中立性」参照。テンプレートの欄の説明・例）
- [x] 監査の報告書の 8.2・8.3 の表を直した
- [ ] 手での確認（実行はユーザー。smoke のシナリオが無い経路）: survey の (b) で §2.6 を昇格し、`constraints.md` に鍵の行と `**対象:**` のあるエントリが書かれ、同じ SURVEY でやり直すと置き換わる。update-knowledge の constraint で、プレビューに書き先と既存のエントリが出て、「置き換える」を選ぶと指定の `[CK-NNN]` が置き換わる

---

## 6. 却下した案

- **鍵を `[CK-NNN]`＋タイトルにする（A1 の監査者の修正案）:** タイトルは LLM が書くので、やり直すたびに言い回しが変わり、同じ項目が二重になる。元の文書の項目の位置は決定的に決まる。
- **鍵を出典の文字列のまま、出典を項目ごとに細かくする:** 出典は人が読む表示で、経路ごとの事情（TRS の実行回等）を足すと読みにくい。照合の値と表示を分け、鍵は人の読む表示に出さない。
- **LLM の手順に「項目ごとに別のエントリにする」と書き足すだけ（3経路それぞれ）:** 3か所の解釈がまたずれうる（A1-1〜A1-4 は、そうしてずれた結果）。採番・照合は決定的なのでスクリプトにする。
- **やり直しで今回書かなかった制約をスクリプトが消す（7. の 2. の案A）:** 書かなかった理由が LLM の判断の変化のときも消え、誤りではない知見が失われる。消した後に戻すのは人の手間が大きい。
- **鍵の接頭辞（CR 番号・SURVEY ファイルの相対パス）を LLM が入力の `key` に書く:** 相対パスの書き方（`./` の有無・絶対パスのまま等）が実行ごとに揺れると、やり直しで鍵が変わって重複し、`--batch` の接頭辞も変わるので `not_written` にも出ない。接頭辞はスクリプトが `--batch-cr`・`--batch-survey` から作る。
- **手での登録の自由記述の「対象」も `targets` に入れる:** 置き場所は `placed` の対象すべての共通の先頭で決まるので、「対象」に書かれたパスで、人が明示した置き場所が変わる。置き場所の入力と表示を分ける（`subjects`）。
- **upsert をやめて、毎回追記だけにする:** やり直し（close の再実行・同じモジュールの再調査）で同じ制約が増え続ける。
- **予約名と衝突したら置き場所に接頭辞を付ける（`_dir/_structures` 等。R1）:** 読む側（`applicable_places`・下調べの LLM の読み方・`domain_refs.py`）すべてに同じ変換が要る。衝突は第1階層に予約名と同じディレクトリがあるときだけなので、読まれる `fallback` に置いて人に示せば足りる（7. の 1.）。
- **予約名と衝突したら書かない（人に示すだけ）:** 知見が失われる。
- **SPO §4.5 の列を `定義場所（ファイル:行）` にする（A1-9）:** SPO を仕上げる document agent はソースコードを読まないので、行を書けない。工程4a の書く側を変えることになり、このプランの範囲（約束の食い違いを直す）を超える。
- **per-repo の `_structures/` をクローズで書く手順を足す:** per-repo の SPO には「落とし穴を伴う構造体依存関係」の節が無く、元が無い。工程4a の変更が要るので、要るなら別のプランにする。
- **A1-17 で、`place` に1行1対象の JSON でない入力を足す:** `upsert` の本文（人の自由な入力）は JSON で渡すので、対象だけ別の形にしても解決しない。制御文字を検出して止めれば、黙って誤らない。

---

## 7. 未決事項（人の判断 2026-11-08 で決着）

1. **予約名と衝突した制約の置き場所（3.1 (b)。R1）:**
   - 推奨: その知見の `fallback`（多くは `_general`）に置き、`reserved_collision` を true にして人に示す。理由: `_general` はすべての読む側が常に読むので、知見が失われない。読む側の変更が要らない。
   - 欠点: そのディレクトリのファイルに限った制約でも `_general` に入り、工程4a の観察 f では他の制約と並ぶ（`**対象:**` で照合されるので、関係の判定はできる）。
   - 他の案: 接頭辞を付ける（6.）。
   - **決定（2026-11-08・人）:** 推奨のとおり、`fallback` に置く。
2. **やり直しで、前回は書いたが今回は書かなかった制約をどうするか（3.1 (a) の 3.・3.2 の `--batch`）:** 同じ CR のクローズ・同じ SURVEY ファイルの昇格をやり直したときだけ起きる（1回だけの実行では出ない）。
   - 案A: 消して、人に示す。欠点: 今回書かなかった理由が LLM の判断の変化なら、誤りではない知見が消える。
   - 案B: 消さず、示さない。欠点: 人が誤りとして消した項目や、行の番号のずれでできた重複が黙って残る。
   - 案C: 消さず、一覧で人に示し、消すかは人が決める。欠点: やり直すたびに人が一覧を確かめる手間が増える（やり直しは多くない）。
   - **決定（2026-11-08・人）:** 案C。
3. **refcheck に検査H を足すか（3.7 の 3.）:**
   - 推奨: 足す。理由: A1-13・A1-14 は、宛先ルーティング表の「この表以外に定義してはならない」が文章だけで守られず、写しができた例。P1 が申し送った約束（ディレクトリ名）もここで守れる。検査は `CC/` の .md の検索なので、refcheck の他の検査と同じ形で書ける。
   - 足さない場合: 3.3・3.4 で今の写しを消すだけになり、再発は人のレビューで見つける。
   - **決定（2026-11-08・人）:** 推奨のとおり、足す。
4. **`doc_target_modules` も消すか（3.5。監査の外）:**
   - 推奨: 消す。理由: `confirmed_modules`（A1-16）と同じく、読む側がテストだけで、廃止した規則の値を出している。
   - 消さない場合: このプランでは A1-16 だけを直し、`doc_target_modules` は記録だけにする。
   - **決定（2026-11-08・人）:** 推奨のとおり、消す。

---

## 8. レビュー

AIレビュー結果: [plans/review/PLAN-20261108-code-knowledge-writers-review.md](review/PLAN-20261108-code-knowledge-writers-review.md)

---

## 9. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | tsuna44 |
| 承認日 | 2026-11-15 |
| 備考 | |
