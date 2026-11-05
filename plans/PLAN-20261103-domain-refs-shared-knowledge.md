# PLAN-20261103-domain-refs-shared-knowledge

作成日: 2026-11-03（書き換え: 2026-11-04。PLAN-20261103-contract-audit の段階3 の P1）  
ステータス: 草案 / 承認待ち / 承認済み / **実装完了**

---

## 1. 背景・目的

### 1.1 起きていること

最初の版のこのプランは、工程2（要求分析）で code-knowledge の共有の知見（`_structures/`・`_constants/`）が集まらない不具合（同プランの旧 1.3 の4件）を直すものだった。
その後、約束の監査（[docs/xddp-contract-audit-2026-11.md](../docs/xddp-contract-audit-2026-11.md)）で、同じ `domain_refs.py`・`promote.py` の AI_INDEX の部分と、それに関わるスキルに、ほかの食い違いが見つかった。
監査の報告書の 8.2 は、それらを P1 としてこのプランに割り当てた（人の判断・2026-11-04）。

食い違いのもとは、次の3つにまとまる。
- **AI_INDEX を書く人が多い:** `promote.py`（close）・工程11 の先行更新（LLM）・01-init（LLM がひな形を書く）・survey（LLM が行を足す）の4か所が書き、表の定義も別々に持っている。
- **AI_INDEX を CR の差分から書き足している:** close のたびに latest-specs から行を足すので、触っていない行の「最終更新CR」がずれ、行が置き換わり、削除が伝わらない。
- **工程2 が AI_INDEX のラベルを通して `{DOCS}` を引く:** ラベル・パスの約束が、書く側と読む側で食い違う。

### 1.2 割り当てた指摘（P1。17件）

指摘の詳細は、監査の報告書の付録（各監査者の報告の「3. 指摘」と、検証者の報告）にある。

| # | 内容（要約） | 直す節 |
|---|---|---|
| A1-7 | `DOMAIN_REF_PATHS` に `_structures`・`_constants` の**ディレクトリ**が入る。analyst はファイルを Read する | 3.4 |
| A1-8 | `_structures`・`_constants` だけを AI_INDEX のラベル経由で集める。AI_INDEX が無い・クローズ直後・survey や手での登録の後は届かない（A2-10 を含む） | 3.2・3.4・3.5 |
| A2-1 | code-knowledge インデックスの `_structures` のラベルが、書く側 `構造体関連図`・読む側 `共有構造体` で違う | 3.4（約束を無くす） |
| A2-2 | クロスインタフェース一覧の「⚠️ 破壊的変更あり」が付かない（CHD の名前とケバブ形式のディレクトリ名を比べる）。付くとキー列が変わって行が増える | 3.2・3.6 |
| A2-4 | 過去の DSN／CHD を AI_INDEX から引く読む側（工程5・6・designer）に書く側が無い | 3.10 |
| A2-5 | TSP／TRS の表のキーが repo だけで、過去の CR の一覧にならない | 3.2 |
| A2-6 | 「共通知識」の列が init と promote で違い、共通の project-rulebook の行が消える | 3.2・3.7 |
| A2-7 | 「最終更新CR」を、今の CR が触っていない行にも付ける。11-specs が引用する promote.py の文は実在しない | 3.2・3.6 |
| A2-8 | 先行更新のモジュール名（SPO のディレクトリ名）と latest-specs のケバブ名がずれうる（検証は「判断できず」） | 3.6（仕組みを無くす） |
| A2-9 | ひな形が3つある・プレースホルダー行が残る・知識参照ガイドの表の名前と「上記」・`state` 列が常に `—`・`related-modules: []`・セルの `\|` | 3.1・3.2 |
| A2-11 | 11-specs がコミットせずに AI_INDEX を書き換えると close C0-2 の `git pull` が止まる（失敗時の扱いが無い）。`git diff --name-only` のパスの基準が DOCS と違う | 3.5・3.6 |
| A4-12 | AI_INDEX が無いとき、`domain_refs.py` が cross のインタフェース仕様を誤ったパスで探す | 3.4 |
| A4-13 | 01-init が `{DOCS}/{repo}/specs/` を必ず作るので、latest-specs へのフォールバックが働かない。11-specs の先行更新の目的も成り立たない（A2-3 を含む） | 3.4・3.6 |
| A4-15 | ユースケースの `related-modules` の値が latest-specs のディレクトリ名とずれうる | 3.4 |
| N1 | survey が書く最終更新CR `SURVEY-{TODAY}` が、アーカイブ候補の正規表現 `\bCR-…` に一致しない | 3.2 |
| N6 | 知識参照ガイドの早見表が、rulebook について `{XDDP_DIR}/…` だけを挙げる | 3.2 |
| N7 | 破壊的変更の印を付けた行が、クロスインタフェース一覧に重複して残る | 3.2 |

### 1.3 方針（人の判断・2026-11-04）

1. **工程11 の AI_INDEX の先行更新を廃止する。** AI_INDEX を書くのは 3.2 のスクリプトだけにする。先行更新の目的（close の前に次の CR の工程2 が最新仕様を参照できる）は、工程2 が `{DOCS}` に無いファイルを latest-specs から読むことで果たす（3.4）。
2. **AI_INDEX の定義をスクリプトに寄せる。** 節・列・ひな形・行の作り方を1つのスクリプトに定義し、01-init・close・survey・update-knowledge はそのスクリプトを呼ぶ。LLM は AI_INDEX を書かない。
3. **過去の DSN・CHD を読む側を消す。** CHD はその時点のコードに対する差分で、後の CR から参照すると古い Before と今の仕様が並ぶ。今の姿は最新仕様（`{DOCS}/{repo}/specs/`）、変更の理由は CRS の写し（`{DOCS}/{repo}/crs/`）、設計判断は project-rulebook の ADR（close の C3.5。`#方式検討`・`#設計` の知見）が受け持つ。元の DSN・CHD は CR のフォルダに残る。`{DOCS}/{repo}/design/` も作らない。
4. **AI_INDEX は「`{DOCS}` の中身の索引」とする。** 書くたびに `{DOCS}` を走査して、管理する節を作り直す。最終更新CR は各ファイルのフロントマター（`last-updated-cr`）かファイル名から取る。工程2 の `domain_refs.py` は AI_INDEX を読まず、`{DOCS}` と latest-specs を直接列挙する（制約〔ADR-0033〕と同じ考え方）。

### 1.4 目的

- 1.2 の17件を直す。
- 書く側と読む側の間の約束を減らし、残る約束は1つの定義を両側が import する形にする（3.13 の再発防止）。

---

## 2. 変更対象ファイル

パスの `CC/` は `ClaudeCode/.claude/` の略。

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `CC/skills/xddp-common/scripts/docs_layout.py` | 追加 | `{DOCS}`・latest-specs の配置（パス）・フロントマターの読み取り・ユースケースの目的と関連モジュールの読み取りの単一定義（3.1） |
| `CC/skills/xddp-common/scripts/ai_index.py` | 追加 | AI_INDEX の節・列・行の定義と、`{DOCS}` から作り直す `build`（3.2） |
| `CC/skills/xddp-common/scripts/tests/test_docs_layout.py`・`test_ai_index.py` | 追加 | 3.12 |
| `CC/skills/xddp-close/scripts/promote.py` | 修正 | AI_INDEX の部分（`update_ai_index` と行の関数・先行更新の読み取り・`--force-full-ai-index`・アーカイブ候補）を削除。パスとフロントマターは `docs_layout` を使う（3.3） |
| `CC/skills/xddp-close/scripts/tests/test_promote.py` | 修正 | AI_INDEX のテストを `test_ai_index.py` へ移す（3.12） |
| `CC/skills/xddp-02-analysis/scripts/domain_refs.py` | 修正 | AI_INDEX を読まず、`{DOCS}` と latest-specs を直接列挙する。`_structures/`・`_constants/` をファイル単位で集める（3.4） |
| `CC/skills/xddp-02-analysis/scripts/tests/test_domain_refs.py` | 修正 | 3.12 |
| `CC/skills/xddp-02-analysis/SKILL.md` | 修正 | Step 0 の「AI_INDEX.md 照合」の記述・`unresolved_related_modules` の受け取りと Step D の報告（3.11） |
| `CC/skills/xddp-close/SKILL.md` | 修正 | C0-2 の pull の失敗・C0-4 のパスの基準・C2 の `--force-full-ai-index` の削除・AI_INDEX の作り直しの Step（Step D2）と Step E・F の表示（3.5） |
| `CC/skills/xddp-11-specs/SKILL.md` | 修正 | 先行更新の削除・案内の文・cross のインタフェース仕様の `breaking:`（3.6） |
| `CC/skills/xddp-01-init/SKILL.md` | 修正 | AI_INDEX を `ai_index.py build` で作る。`design/` を作らない（3.7） |
| `CC/skills/xddp-survey/SKILL.md` | 修正 | (b)・(c) の後に `ai_index.py build`（3.8） |
| `CC/skills/xddp-update-knowledge/SKILL.md` | 修正 | Step 3 の後に `ai_index.py build`（3.9） |
| `CC/skills/xddp-05-arch/SKILL.md`・`CC/skills/xddp-06-design/SKILL.md`・`CC/agents/xddp-designer-agent.md`・`CC/agents/xddp-architect-agent.md` | 修正 | 過去の DSN・CHD を読む手順と `PAST_CROSS_DESIGN_DIR` の削除・現状仕様の参照の記録先（3.10） |
| `CC/skills/xddp-common/scripts/artifact_lint.py`（とテスト） | 修正 | cross のインタフェース仕様の `breaking:` の値を `true`／`false` に限る（語彙は `docs_layout` から import。3.6） |
| `CC/skills/xddp-rules/code-knowledge-boundary.md`・`CC/skills/xddp-common/templates/project-rulebook-cross-template.md` | 修正 | AI_INDEX の説明（3.11） |
| `test-fixtures/` の `baseline_docs/AI_INDEX.md`（4か所）と関連の記述（`scratch-workspace` の README・progress.md・PENDING-PROMOTE・`xddp/project-rulebook-cross.md`） | 修正 | `ai_index.py build` の出力で作り直す（3.12） |
| `CLAUDE.md`・`README.md` | 修正 | スクリプトの説明（3.14） |
| `docs/adr/ADR-0034-ai-index-docs-index.md` | 追加 | 1.3 の方針（3.14） |
| `docs/adr/ADR-0005-knowledge-guide-once.md`・`ADR-0013-close-promote-script.md`・`ADR-0033-constraints-module-key.md`・`docs/adr/README.md` | 修正 | 3.14 |
| `docs/xddp-contract-audit-2026-11.md` | 修正 | 6. の 2b-3 に、05・06 の部分をこのプランで直した旨を書き足す（3.14・4.） |

---

## 3. 変更内容

### 3.1 `docs_layout.py`（追加）

**変更前:** `{DOCS}` の配置（`{repo}/specs/{module}/spec.md`・`system/specs/use-cases/{uc}/description.md`・`cross/specs/interfaces/{name}/spec.md`・`{repo}/knowledge/code-knowledge/_structures/` 等）を、`promote.py`・`domain_refs.py`・各 SKILL.md が別々に書いている。フロントマターは `promote.py` の `_parse_frontmatter` だけが読み、`related-modules: []` を文字列 `"[]"` にする（A2-9）。

**変更後:** 次を1つのモジュールに定義し、`promote.py`・`domain_refs.py`・`ai_index.py` が import する。
- `{DOCS}` と latest-specs の配置（どちらも同じ相対の形。latest-specs の `{repo}/` は `{DOCS}` の `{repo}/specs/` に、`system/` は `system/specs/` に、`cross/` は `cross/specs/` に当たる）。
- フロントマターの読み取り。YAML のリスト（`[]`・`[a, b]`・`- a` の行）はリストとして返す。要素の引用符（`- "a"`・`["a", "b"]`・`'a'`）は外す（ユースケースのテンプレートは `related-modules` を `- "{module1}"` で書く）。
- ユースケースの目的（`目的・ゴール` の見出しの直後の最初の段落の1行）と関連モジュール（`related-modules`）の読み取り。
- code-knowledge の共有の知見のディレクトリ名と種別名（`_structures`→`共有構造体`、`_constants`→`共有定数`、`_flows`→`機能間フロー`）。
- cross のインタフェース仕様のフロントマター `breaking:` の語彙（`true`／`false`）と、破壊的変更かを決める関数。`artifact_lint.py`（検査）と `ai_index.py`（列の値）が import する。

**理由:** 配置とフロントマターの読み方は、書く側（promote の写し）と読む側（domain_refs・ai_index）で一致していなければならない。1か所に定義すれば、食い違いが起きない。

### 3.2 `ai_index.py`（追加）

**変更前:** AI_INDEX を `promote.py` の `update_ai_index` が latest-specs から書き足す。01-init・survey・11-specs も、LLM がそれぞれの定義で書く。

**変更後:**
- **サブコマンド `build --docs DOCS --repos-keys r1,r2 [--is-multi]`:** `{DOCS}` を走査して `{DOCS}/AI_INDEX.md` の管理する節を作り直す。`{DOCS}` が無ければ何もせず、その旨を JSON で返す。ファイルが無ければ作る（01-init の初回もこれで作る）。stdout に JSON（`ok`・`archive_candidates`・各節の行数）を出す。失敗は exit 非0 と stderr。
- **冪等:** 同じ `{DOCS}` に2回続けて実行しても、2回目は内容が変わらない。
- **管理する節と列（この順に並べる）:**

| 節 | 列 | 行のもと |
|---|---|---|
| `## ユースケース一覧` | ユースケース／目的（1行）／description／関連モジュール／最終更新CR | `{DOCS}/system/specs/use-cases/*/description.md`（目的・関連モジュールは 3.1） |
| `## リポジトリ別仕様書` | リポジトリ／バージョン／overview／モジュール数／最終更新CR | `--repos-keys` の各 repo の `{DOCS}/{repo}/specs/`（バージョン・最終更新CR は `overview/architecture.md` のフロントマター） |
| `## モジュール別最新仕様` | リポジトリ／モジュール／spec／structure／state／最終更新CR | `{DOCS}/{repo}/specs/*/spec.md`（`overview` を除く。`spec.md` の無いディレクトリは行にしない。工程2 も `spec.md` を読む）。最終更新CR は `spec.md` のフロントマター。`structure`・`state` は `structure.md`・`state-machine.md` があればリンク、無ければ `—`（A2-9） |
| `## クロスインタフェース一覧`（`--is-multi` または `{DOCS}/cross/specs/interfaces/` がある場合） | インタフェース／spec／schema／バージョン／最終更新の破壊的変更／最終更新CR | `{DOCS}/cross/specs/interfaces/*/spec.md`。「最終更新の破壊的変更」はフロントマター `breaking: true` なら `⚠️ あり`、それ以外は `—`（A2-2・N7。キー列は名前のまま）。意味は「最終更新CR の列の CR での更新が破壊的変更だった」で、後の CR がそのインタフェースを更新しない限り残る（3.6） |
| `## code-knowledge インデックス` | 知りたいこと／参照先 | 各 repo（`--is-multi` なら cross も）の `{DOCS}/{repo}/knowledge/code-knowledge/`。制約は `knowledge_place.list_places` の置き場所ごとに1行（`constraints.md` へのリンク）。共有の知見は 3.1 のディレクトリごとに1行（ディレクトリへのリンク。知りたいことは 3.1 の種別名〔`{repo} 共有構造体` 等〕）。ファイルごとの行にはしない（AI_INDEX は案内で、ファイル単位の列挙は工程2 の `domain_refs.py` が行う） |
| `## 変更要求仕様書（CRS）ナビゲーション` | リポジトリ／CR／CRS | `{DOCS}/{repo}/crs/CRS-*.md`・`{DOCS}/cross/crs/CRS-*.md`（CR ごとに1行） |
| `## テスト仕様（TSP）・テスト結果（TRS）` | リポジトリ／CR／TSP／TRS | `{DOCS}/{repo}/test/`・`{DOCS}/cross/test/` の `TSP-{CR}*.md`・`TRS-{CR}-*.md`（CR ごとに1行。A2-5） |
| `## 用語集` | 対象／参照先 | `{DOCS}/glossary.md`・`{DOCS}/{repo}/knowledge/glossary.md`・cross（用語数つき） |
| `## 共通知識` | 対象／project-rulebook | `{DOCS}/project-rulebook.md`（対象 `プロジェクト共通`）・`{DOCS}/{repo}/project-rulebook.md`・`{DOCS}/cross/project-rulebook.md`（A2-6） |
| `## 知識参照ガイド` | 知りたいこと／参照先パターン | 固定の文。表の名前は実際の見出しで書き、「上記」と書かない（A2-9）。rulebook は `{DOCS_DIR}` の写しを挙げる（N6） |

- **最終更新CR:** 行のもとのファイル（上の表の「行のもと」のファイル。モジュールは `spec.md`、リポジトリは `overview/architecture.md`）のフロントマター `last-updated-cr`（CRS・TSP・TRS はファイル名の CR）。無ければ `—`。今の CR を付けることはしない（A2-7）。
  - CR 番号はハイフンを含む（例 `CR-2026-970`）ので、`TRS-{CR}-{接尾辞}.md` のファイル名だけでは CR の境目が決まらない。TRS の CR は、同じディレクトリの `TSP-{CR}.md`・`TSP-{CR}-cross.md` と CRS の CR に前方一致する最長のものとし、どれにも一致しなければ TRS のフロントマターから取る。取り方の細部は実装時にテストで決める。
- **プレースホルダー行を書かない**（A2-9）。行が0件の節は、見出しとヘッダだけにする。
- **セルの `|` は `\|` にする**（A2-9）。
- **管理しない節**（人が足した節）は、内容を変えずに、管理する節の後ろに元の順で残す。冒頭のタイトルと説明の行はスクリプトが書く。
- **廃止した節**（`## 設計書ナビゲーション`・`## リポジトリ別設計書・テスト仕様書`・`## 工程11 AI_INDEX先行更新セクション`）は消す。
- **アーカイブ候補**（作り直した AI_INDEX が500行を超える場合。今の `detect_archive_candidates` と同じ閾値）:
  - 対象: CR の値を持つ節の行（「最終更新CR」の列を持つ ユースケース一覧・リポジトリ別仕様書・モジュール別最新仕様・クロスインタフェース一覧と、「CR」の列を持つ CRS ナビゲーション・TSP／TRS）。値が `CR-` または `SURVEY-` で始まる行（N1）。`—` の行と、CR の列を持たない節（code-knowledge インデックス・用語集・共通知識・知識参照ガイド）は対象外。
  - 返す内容: 節・キー（1列目）・CR の値・行のもとのファイルの `{DOCS}` からの相対パス。
  - 並び: `CR-` の行を値の文字列の昇順（今と同じ）に並べ、その後に `SURVEY-` の行を日付の昇順に並べる（`SURVEY-` の後の日付は `YYYYMMDD`・`YYYY-MM-DD` のどちらも日付として読む）。CR 番号と日付は比べられないので混ぜない。
  - 人の作業: AI_INDEX は `{DOCS}` から作り直すので、行だけを消しても次の build で戻る。行を減らすには、行のもとのファイルを build が走査しない場所（3.2 の表の「行のもと」の外。例 `{DOCS}/_archive/{元の相対パス}`）へ人が移す。移したファイルは工程2 の `domain_refs.py` も読まない。ただし仕様（モジュール・ユースケース・インタフェース）は latest-specs にも同じものが残るので、工程2 は latest-specs から `degraded` で読み、後の close で `{DOCS}` に戻りうる（latest-specs から消さないのは P4 の範囲。4. のデグレードのリスク）。行が増えるのは主に CR ごとの行（CRS・TSP／TRS）で、これらは latest-specs に無いので移せば消える。この案内は close の Step F の表示（3.5）と README（3.14）に書く。
  - 呼ぶ側の扱い: close は Step F で示す（3.5）。01-init・survey・update-knowledge は示さない（次の close で示される）。
- **ADR-0005 の「知識参照ガイドは初回だけ作る」をやめる。** ガイドは固定の文なので、毎回作り直しても差分は出ない。

**理由:** AI_INDEX を `{DOCS}` の中身から毎回作れば、書き足しによるずれ（最終更新CR・置き換わる行・重複する行・消えない行）が起きない。書く人が1つになるので、表の定義の食い違いも起きない。

### 3.3 `promote.py`（修正）

**変更前:** `run` が C2 で `update_ai_index` を呼び、progress.md の「工程11 AI_INDEX先行更新セクション」を読んで節を飛ばす（`read_ai_index_preupdated`・`--force-full-ai-index`）。アーカイブ候補を PENDING-PROMOTE に書く。

**変更後:**
- AI_INDEX を書かない。`update_ai_index`・行の関数（`_usecase_rows` 〜 `_common_knowledge_rows`）・`KNOWLEDGE_GUIDE_BLOCK`・`AI_INDEX_SKELETON`・`read_ai_index_preupdated`・`PREUPDATED_*`・`detect_archive_candidates`・`ARCHIVE_ROW_CR_RE`・`--force-full-ai-index` を削除する。
- 上の削除で使う側が無くなる表の補助関数（`_find_heading`・`_section_bounds`・`_find_table_bounds`・`_ensure_section`・`upsert_table`・`section_exists`・`_join_row`・`_glossary_term_count`）も削除する。`ai_index.py` は節を丸ごと作り直すので upsert を使わない。用語数の数え方（`_glossary_term_count`）は `ai_index.py` に移す。`_split_row`（`detect_breaking_changes` が使う）・`_read_lines`・`_write_lines` は残す。実装時に `grep` で使う側が無いことを確かめてから消す。
- `_parse_frontmatter`・`_read_frontmatter` は `docs_layout` に移す（promote.py に残る使う側は `docs_layout` を import する）。
- `from knowledge_place import list_places` を消す（AI_INDEX の制約の行だけが使っていた）。`xddp-common/scripts` を `sys.path` に足す行は、`docs_layout` の import のために残す。
- `write_output_file` のアーカイブ候補の節を削除する（close の Step F が示す。3.5）。
- `detect_breaking_changes`（知見ログへの警告と PENDING-PROMOTE への記載）は残す。
- `{DOCS}` の写し先のパスとフロントマターの読み取りは `docs_layout` を使う。
- docstring の Usage と説明を直す。

**理由:** AI_INDEX は close の Step D の後（Step D2）に作り直す（3.5）。C2 の時点で書くと、C3.6 が書く code-knowledge と C6 の rulebook の写しが載らない（A1-8・A2-6）。

### 3.4 `domain_refs.py`（修正）

**変更前:** AI_INDEX があれば、その表のラベル・行から `{DOCS}` のパスを作る（3-2）。無ければ `{DOCS}` を列挙する（3-1a）。latest-specs を読むのは、`{DOCS}/{repo}/specs/` のディレクトリ自体が無い場合だけ（3-4）。`_structures`・`_constants` はラベルが一致した場合だけディレクトリを渡す。

**変更後:** AI_INDEX を読まない。affected repos ごとに次を集める（並びは今と同じく種別ごと、名前の順）。
- **ユースケース:** `{DOCS}/system/specs/use-cases/` と latest-specs の `system/use-cases/` のディレクトリ名の和集合から、名前（`resolve_matches`）または目的（3.1。`text_contains_keyword`）でキーワードに当たるもの。
  - どれにも当たらず、`{DOCS}/system/specs/use-cases/` にユースケースのディレクトリが1つも無い場合は、latest-specs の更新日時の新しい順に `FALLBACK_TOP_N` 件（今の 3-4 の b と同じ）。
- **モジュールの仕様:** `{DOCS}/{repo}/specs/` と latest-specs の `{repo}/` のディレクトリ名（`overview` を除く）の和集合から、キーワードに当たるものと、当たったユースケースの関連モジュール。
  - 関連モジュールの値は、ディレクトリ名と `normalize_token` の完全一致で対応させる。対応しない値は `stats.unresolved_related_modules`（`{repo}`・ユースケース・値の組の一覧）に出す（A4-15）。02 の SKILL.md が人に示す（3.11）。
  - どれにも当たらず、`{DOCS}/{repo}/specs/` にモジュールのディレクトリが1つも無い場合は、latest-specs の更新日時の新しい順に `FALLBACK_TOP_N` 件（今の 3-4 の a と同じ）。
- **`stats.fallback_applied`:** 残す。値の意味を「上位 `FALLBACK_TOP_N` 件の代わりの読み方をした」に変える（`a:{repo}`＝モジュール、`b`＝ユースケース）。今の「`{DOCS}` 側のディレクトリ自体が無い」という意味は無くなる（latest-specs は常に和集合で見るため）。
- **cross のインタフェース仕様（`IS_MULTI`）:** `{DOCS}/cross/specs/interfaces/` と latest-specs の `cross/interfaces/` のディレクトリ名の和集合から、キーワードに当たるもの（A4-12）。
- **共有の知見:** `{DOCS}/{repo}/knowledge/code-knowledge/_structures/`・`_constants/` の直下の `*.md` をファイル単位で、種別 `共有構造体`・`共有定数` で（A1-7・A1-8）。`IS_MULTI` では `{DOCS}/cross/knowledge/code-knowledge/` も。キーワードでは絞らない。`_flows/` は集めない（7. の 1.・2.）。
- **制約・知見ログ・用語集:** 今と同じ。
- **ファイルの選び方:** 名前が決まったら、`{DOCS}` 側のファイルがあればそれ、無ければ latest-specs 側のファイル（`stats.latest_specs_sourced` に数える）。どちらにも無ければ入れない（A4-13・1.3 の 1.）。
- **`DOMAIN_REF_MODE`:** 今と同じ（latest-specs から1件でも入れば `degraded`）。
- `stats` から `ai_index_present`・`ai_index_malformed_sections` を消す（読むのはテストだけ）。
- 出力の形（`domain_ref_paths`・`domain_ref_mode`・種別名）は変えない。

**理由:** AI_INDEX のラベルを通す限り、書く側と読む側でラベルとパスの形を揃え続ける必要がある（A2-1・A4-12）。`{DOCS}` を直接列挙すれば、その約束が無くなる。`{DOCS}` に無いファイルを latest-specs から読めば、close の前に始めた次の CR の工程2 も、新しいモジュール・ユースケースを参照できる。

### 3.5 `xddp-close/SKILL.md`（修正）

**変更前:**
- C0-2 は `git -C {DOCS} pull` を実行し、失敗したときの扱いが無い（A2-11）。
- C0-4 は `git -C {DOCS} diff --name-only ORIG_HEAD HEAD` の結果を DOCS からの相対パスとして照合する。DOCS が上位のリポジトリの一部だと、git はリポジトリのルートからのパスを返すので一致しない（A2-11）。
- C2 は `PULLED_FILES` に `AI_INDEX.md` があれば `--force-full-ai-index` を付ける。

**変更後:**
- C0-2: pull が失敗したら stderr を示す。続けて `git -C {DOCS} rev-parse --show-prefix`（`PREFIX`。`{DOCS}` のリポジトリのルートからの位置）を実行し、`{DOCS}` の状態で次の3つに分ける。git のパスはリポジトリのルートからなので `{PREFIX}AI_INDEX.md` と比べる。パスの一覧は `-z` で取る（`core.quotePath` によって日本語等のパスが引用符つきになるのを避ける）。
  - **(a) merge の途中で止まった**（`git -C {DOCS} rev-parse -q --verify MERGE_HEAD` が成功する。pull が merge で衝突した）: `git -C {DOCS} diff --name-only --diff-filter=U -z` で衝突したファイルを取る。
    - 衝突したのが `{PREFIX}AI_INDEX.md` だけなら、次を尋ねる。
      > ⚠️ `{DOCS}` の pull で `AI_INDEX.md` が衝突し、merge の途中で止まりました。
      > AI_INDEX は close の最後に `{DOCS}` から作り直すので、どちらの内容を採ってもかまいません。
      > 1. 取り込む側の AI_INDEX.md を採って merge を終える（推奨。`{DOCS}` に merge のコミットを作る）
      > 2. merge を取り消して（pull の前に戻して）続行する（C0-4 の競合検出を行わない）
      > 3. merge を取り消して中止する
      - 1.: `git -C {DOCS} checkout --theirs -- AI_INDEX.md`・`git -C {DOCS} add -- AI_INDEX.md`・`git -C {DOCS} commit --no-edit`。pull が済んだので、C0-4 は今までどおり行う（`ORIG_HEAD` は pull の前を指す）。どれかが失敗したら（取り込む側が AI_INDEX.md を消した `UD` では `checkout --theirs` が失敗する。commit のフック等で commit が失敗する）、stderr を示し、`git -C {DOCS} merge --abort` で pull の前に戻してから「続行／中止」を尋ねる。
      - 2.・3.: `git -C {DOCS} merge --abort` の後に続行・中止する。
    - 衝突したのが `AI_INDEX.md` 以外にもあるか、衝突したファイルが無い（フックの失敗等で merge の途中で止まった）なら、stderr と衝突したファイルを示し、`git -C {DOCS} merge --abort` で pull の前に戻してから「続行／中止」を尋ねる（衝突は人が解消する。merge の途中のまま続行しない）。
  - **(b) rebase の途中で止まった**（`git -C {DOCS} rev-parse --absolute-git-dir` が返すディレクトリの下に `rebase-merge` か `rebase-apply` がある。`pull.rebase` の設定で pull が rebase した）: `git -C {DOCS} diff --name-only --diff-filter=U -z` で衝突したファイルを取り、`{PREFIX}AI_INDEX.md` と比べる（`rebase --abort` の後は取れないので、先に取る）。その後に `git -C {DOCS} rebase --abort` で pull の前に戻し、衝突したファイルを示して「続行／中止」を尋ねる。衝突が `{PREFIX}AI_INDEX.md` だけなら「どちらの内容を採ってもかまいません（close が作り直す）」と添え、衝突したファイルが無ければ stderr だけを示す（rebase の途中の解消は手順が多いので、人が行う）。
  - **(c) merge・rebase の途中ではない**（pull が始まる前に止まった）: `git -C {DOCS} status --porcelain -z -- .`（`-- .` で `{DOCS}` の配下に限る）で分ける。
    - `{DOCS}` の配下の未コミットの変更が `{PREFIX}AI_INDEX.md` の1つだけ（状態の2文字は問わない。` M`・`M `・`MM`・`A `・`??` 等）なら、次を尋ねる。
      > ⚠️ `{DOCS}` の pull に失敗しました（stderr: …）。
      > `{DOCS}` の配下の未コミットの変更は `AI_INDEX.md` だけです。AI_INDEX は close の最後に `{DOCS}` から作り直すので、手元の変更を捨ててかまいません。
      > 1. AI_INDEX.md の手元の変更を捨てて pull し直す（推奨）
      > 2. pull せずに続行する（C0-4 の競合検出を行わない）
      > 3. 中止する
      - 1. の捨て方: `git -C {DOCS} cat-file -e HEAD:./AI_INDEX.md` が成功する（HEAD にある）なら `git -C {DOCS} checkout HEAD -- AI_INDEX.md`（`HEAD` を付けて、索引に載せた変更〔`M `・`MM`〕も戻す）。HEAD に無い（`??`・`A `）なら `git -C {DOCS} rm -q --cached --ignore-unmatch -- AI_INDEX.md` の後に `{DOCS}/AI_INDEX.md` を消す。その後に pull し直す。pull し直した結果は、成功なら C0-3 へ進み、失敗ならもう一度この C0-2 の分け方に戻る（2回目は (c) の 1. を示さない。(a) に入ったら (a) の 1. は示す）。
    - 未コミットの変更が無い（ネットワーク・upstream の未設定等）か、`AI_INDEX.md` 以外の変更もあれば、「続行／中止」を尋ねる。
  - (a) の `merge --abort`・(b) の `rebase --abort` が失敗したら（merge・rebase の前に未コミットの変更があった場合等）、「続行／中止」を尋ねずに stderr を示して中止する（人が `{DOCS}` を直す。merge・rebase の途中のまま昇格を書き込まない）。
  - どの場合も、続行したときは（(a) の 1. で merge のコミットを作った場合を除き）C0-4 の競合検出を行わず、その旨を Step D に「⚠️ `{DOCS}` の pull に失敗したため、並行 CR の昇格との競合を確かめていません」と出す。
  - 上の git の動きは、`{DOCS}` を日本語の名前のサブディレクトリに置いた一時リポジトリで確かめた〔2026-11-05〕: 2つのクローンが AI_INDEX.md を別々にコミットすると pull が衝突して `UU`・`MERGE_HEAD` の状態で残り、`checkout HEAD --` の後の pull は `Exiting because of unfinished merge` で失敗する。(a) の 1. で merge のコミットを作った後の `diff --name-only --relative ORIG_HEAD HEAD` は pull で入ったファイルを返す。`pull.rebase=true` では `rebase-merge` ができ `MERGE_HEAD` は無く、`rebase --abort` で pull の前に戻る。(c) の捨て方で変更が消える。git 2.54 で追加で確かめた〔2026-11-05〕: rebase の途中では `diff --name-only --diff-filter=U -z` が `{PREFIX}AI_INDEX.md` を返し、`rebase --abort` の後は何も返さない。`rev-parse --absolute-git-dir` の下に `rebase-merge` がある。取り込む側が AI_INDEX.md を消した merge（`UD`）では `checkout --theirs -- AI_INDEX.md` が失敗し、その後の `merge --abort` は成功する。
- C0-4: `git -C {DOCS} diff --name-only --relative ORIG_HEAD HEAD` にする（`--relative` で DOCS からの相対パスが返ることを、DOCS をサブディレクトリに置いたリポジトリで確かめた〔2026-11-04〕）。
- C2: `--force-full-ai-index` の段落と引数を消す。
- 新しい Step「## Step D2: Rebuild AI_INDEX.md」を Step D と Step E の間に置く。Step D で人が「クローズ完了」と入力し、オーケストレーターが削除候補のディレクトリを消した**後**に実行する（Step D で人が `{DOCS}` を直接直した分と、削除を AI_INDEX に入れるため）。
  - 実行する: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/ai_index.py build --docs {DOCS} --repos-keys {REPOS_KEYS をカンマ区切り} {IS_MULTI の場合のみ}--is-multi`（`REPOS_KEYS`・`IS_MULTI` は close の冒頭で「## CR Resolution」から再利用している値。affected repos ではなく全 repo を渡す）。
  - 結果を `AI_INDEX_RESULT`（成功／失敗と stderr の1行目）・`ARCHIVE_CANDIDATES`（成功時の `archive_candidates`）とする。失敗しても close は止めない（AI_INDEX は `{DOCS}` から作り直せるので、次の close か `ai_index.py build` の再実行で直る）。
- Step E の記録に1行足す: `- **AI_INDEX.md：** {成功なら "作り直し済み"／失敗なら "⚠️ 作り直しに失敗（{stderr の1行目}）。\`ai_index.py build\` を再実行してください"}`。
- Step F の報告に足す:
  - `AI_INDEX_RESULT` が失敗なら、stderr と再実行のコマンド（Step D2 と同じ）。
  - `ARCHIVE_CANDIDATES` が空でなければ、次を示す（今 PENDING-PROMOTE に書いている内容の置き換え）。
    > **AI_INDEX.md が500行を超えています（アーカイブ候補）:**
    > {節・キー・CR・ファイルの相対パスの表。並びは 3.2}
    > AI_INDEX は `{DOCS}` から作り直すので、行だけを消しても戻ります。行を減らすには、該当するファイルを `{DOCS}/_archive/{元の相対パス}` 等の、AI_INDEX と工程2 が読まない場所へ移してから `ai_index.py build` を再実行してください（自動では移しません）。

**理由:** 1.3 の 4.・3.3。Step D の削除と人の直接編集の後に作り直さないと、close の直後の AI_INDEX に消したモジュールの行が残る。C0-2 の案内は、01-init・survey・update-knowledge が AI_INDEX をコミットせずに作り直すようになり（3.7〜3.9）、AI_INDEX だけの未コミットの変更で pull が止まる場合が増えるため。また close のたびに AI_INDEX を丸ごと作り直すので、別々のワークスペースで close してコミットした AI_INDEX.md は、ふつうの使い方でも pull で衝突する。その場合に効かない手順を勧めたり、merge の途中のまま `{DOCS}` に昇格を書き込んだりしないようにする（4.）。

### 3.6 `xddp-11-specs/SKILL.md`・`artifact_lint.py`（修正）

**変更前:**
- Step 0 の 5. が先行更新のために `{DOCS}/AI_INDEX.md` を確かめ、無ければ 01-init のひな形で作る。
- Step DONE が先行更新（「モジュール別最新仕様」「ユースケース一覧」「クロスインタフェース一覧」「設計書ナビゲーション」）を行い、progress.md に「工程11 AI_INDEX先行更新セクション」を書く。
- 完了の案内に「AI_INDEX.md の全リンクは機能しません」「AI_INDEX.md の競合更新リスク」と書く。
- cross のインタフェース仕様のフロントマター `breaking:` を、CHD の値から書く指示が無い（テンプレートの既定は `false`）。

**変更後:**
- Step 0 の 5.、Step DONE の先行更新の段落（「AI_INDEX.md 先行更新」から「先行更新時の注意（broken リンク許容）」まで）、progress.md のセクションの記録を削除する。
- 完了の案内: 「次の CR の工程2 は、`{DOCS}` に無い最新仕様を `latest-specs/` から読む（degraded）。xddp-close を実施してから次の CR を開始することを推奨する」にする。並行 CR の注意は overview の共有ファイルの同時更新だけにする（Step GATE の注意も同じ）。
- cross のインタフェース仕様の生成・更新: 今回の CHD の「インタフェース変更サマリ」にあるインタフェースだけ、フロントマター `breaking:` をその行の `breaking` の値（`true`／`false`）にする。サマリに無いインタフェースの仕様は `breaking:` を変えない（更新しない仕様は `last-updated-cr` も変わらないので、`breaking:` は常に `last-updated-cr` の CR での更新を表す。3.2）。
- `artifact_lint.py`: latest-specs の cross のインタフェース仕様の `breaking:` が `true`／`false` 以外なら指摘する。

**理由:** 1.3 の 1.。先行更新は、リンク先が close まで存在せず、読む側も使っていなかった（A4-13）。破壊的変更の印は、名前の照合（A2-2）をやめ、11-specs が CHD から書くフロントマターで決める。LLM が書く値なので、lint で語彙を検査する（3.13 の 2.）。

### 3.7 `xddp-01-init/SKILL.md`（修正）

**変更前:** 「Initial file contents」に `{DOCS}/AI_INDEX.md` の全文（6節・プレースホルダー行つき）を持ち、LLM がそれを書く。`{DOCS}/{repo}/design/README.md` を作る。

**変更後:**
- Step 4.5 の 3.・4. の作るファイルの一覧から `{DOCS}/AI_INDEX.md` と `{DOCS}/{repo}/design/README.md` を消す。「Initial file contents」から AI_INDEX の全文と `design/README.md` の節を削除する（1.3 の 3.）。
- Step 4.5 に 6. を足す（変更後の文）:
  > 6. If 3. or 4. created anything, or `{DOCS}/AI_INDEX.md` does not exist → run:
  > `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/ai_index.py build --docs {DOCS} --repos-keys {REPOS_KEYS をカンマ区切り} {REPOS_KEYS が2件以上の場合のみ}--is-multi`
  > If it fails, show stderr and continue（AI_INDEX は後の close・survey・update-knowledge か `ai_index.py build` の再実行で作られる）.
  - 5.（すべてあればスキップ）で AI_INDEX.md もある場合は build しない（`{DOCS}` に不要な未コミットの変更を作らないため）。
  - `REPOS_KEYS` は Step 4.5 の 2. で取得済み。2. で `REPOS:` が無く Step 4.5 をスキップした場合は 6. も行わない。

**理由:** 1.3 の 2.・3.。

### 3.8 `xddp-survey/SKILL.md`（修正）

**変更前:** Step 8 の ③ で、LLM が AI_INDEX の「モジュール別最新仕様」「リポジトリ別仕様書」に行を足す（最終更新CR は `SURVEY-{TODAY}`）。Step 5（(b) knowledge への昇格）は AI_INDEX を更新しない（A1-8）。

**変更後:**
- Step 8 の ③ を「`ai_index.py build` を実行する」にする（`{DOCS}` が無い場合の警告は残す）。列構成・リンクパス形式の記述と、AI_INDEX.md が無い場合に 01-init のひな形で作る段落は消す（build が作る）。
- Step 5 の昇格の後にも `ai_index.py build` を実行する。
- コマンドは 3.7 の 6. と同じ形: `... ai_index.py build --docs {DOCS} --repos-keys {REPOS_KEYS をカンマ区切り} {IS_MULTI の場合のみ}--is-multi`（`DOCS`・`REPOS_KEYS`・`IS_MULTI` は Step 0 の「## Load Config」で取得済み。調べた repo だけでなく全 repo を渡す）。
- 失敗したら stderr を Step 9 のサマリーに「⚠️ AI_INDEX.md の作り直しに失敗しました（{stderr の1行目}）。昇格は済んでいます。`ai_index.py build` を再実行してください」と示す（昇格は取り消さない）。`archive_candidates` は示さない（3.2）。

**理由:** 1.3 の 2.。survey で昇格した知見も、その場で AI_INDEX に載る。

### 3.9 `xddp-update-knowledge/SKILL.md`（修正）

**変更前:** `{DOCS}` に知見・用語を書くが、AI_INDEX は更新しない。

**変更後:** Step 3 で書いた後に、3.8 と同じ形のコマンド（`DOCS`・`REPOS_KEYS`・`IS_MULTI` は Step 0 の「## Load Config」で取得済み）で `ai_index.py build` を実行する。失敗したら Step 4 の報告に「⚠️ AI_INDEX.md の作り直しに失敗しました（{stderr の1行目}）。登録は済んでいます。`ai_index.py build` を再実行してください」と示す。`archive_candidates` は示さない（3.2）。

**理由:** 手で登録した知見・用語も、その場で AI_INDEX に載る（A1-8）。

### 3.10 `xddp-05-arch/SKILL.md`・`xddp-06-design/SKILL.md`・`xddp-designer-agent.md`・`xddp-architect-agent.md`（修正）

**変更前:**
- 05 の Step 0 は、`{DOCS}/{repo}/design/` があれば AI_INDEX から過去の DSN を探し、`{DOCS}/cross/design/` の DSN-*-cross.md を読む。cross の手順にも `Read {DOCS}/cross/design/` がある。
- 06 の Step 0 も同じく過去の CHD を探す。cross の手順に `Read {DOCS}/cross/design/` があり、designer に `PAST_CROSS_DESIGN_DIR` を渡す。
- designer エージェントの Optional Inputs に `PAST_CROSS_DESIGN_DIR` がある。

**変更後:**
- 05・06 の Step 0 から、過去の設計を探す手順（1.〜3.。`DESIGN_DIR` と `{DOCS}/cross/design/`）と、最後の記録の手順（5.）を消す。現状仕様の読み込み（4.。SPO・latest-specs）だけを残す。
  - 今の 5. が書かせる節（"referenced past design documents" 等）は DSN・CHD のテンプレートに無い。しかも Step 0 の時点では書く先の文書がまだ無い（DSN のインデックスは Step A で architect エージェントが、CHD のインデックスは Step A の 2. でスキルが書く）。そこで記録は、それぞれのインデックスを書く者が、テンプレートにある冒頭の表の「参照資料」の行に書く（下の2つ）。
  - 残す手順の変更後の文（05・06 共通。repo ごとの値にする。今は1つの変数を repo ごとに上書きしていて、最後の repo の値だけが Step A に渡る）:
    > For each `{repo}` in `AFFECTED_REPOS`:
    > Let `SPO_SUMMARY` = `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`.
    > If `SPO_SUMMARY` does not exist: let `CURRENT_SPECS_REFS[{repo}]` = [] (note "SPO 未存在のためスキップ") and continue with the next repo.
    > （モジュールごとの `SPEC_FILE_PATHS` の求め方は今と同じ）
    > Let `CURRENT_SPECS_REFS[{repo}]` = `SPEC_FILE_PATHS` (may be empty).
  - 今の 4. の「skip to Step 5」は、上の「continue with the next repo」に置き換わる（行き先の 5. が無くなるため）。
  - Step A でエージェントに渡す行は `CURRENT_SPECS_REFS: {CURRENT_SPECS_REFS[repo]}`（`CURRENT_SPECS_REFS[repo]` が空でない場合のみ追加）にする。
- Step 0 の見出し: 05・06 とも `## Step 0: Reference Current Specs` にする。
- 05 の記録: `xddp-architect-agent.md` の INDEX_FILE を生成する手順（`INDEX_FILE (DSN-{CR_NUMBER}.md) を生成` の項）に、「`CURRENT_SPECS_REFS` が渡された場合は、冒頭の表の「参照資料」の行の既存の SPO・CRS の後にそのパスを足す」を足す。
- 06 の記録: Step A の「2. Write index skeleton」に、「冒頭の表の「参照資料」の行の既存の CRS・SPO・DSN の後に `CURRENT_SPECS_REFS[{repo}]` のパスを足す（空なら足さない）」を足す。
- 05・06 の cross の手順の `Read {DOCS}/cross/design/` の行を消す。
- 06 から designer への `PAST_CROSS_DESIGN_DIR` を消し、designer エージェントの `PAST_CROSS_DESIGN_DIR` を消す。

**理由:** 1.3 の 3.（A2-4）。記録の手順は、読まなくなった過去の設計を書かせないため、テンプレートに無い節を書かせないため、また書く先の文書を書く者に書かせるため。

### 3.11 説明の文（修正）

- `xddp-02-analysis/SKILL.md` Step 0 の 3.: 「AI_INDEX.md 照合・フォールバック・…」を「`{DOCS}` と latest-specs の直接列挙・…」にする。
- `xddp-02-analysis/SKILL.md` Step 0 の 3-2: JSON から `stats.unresolved_related_modules` も `UNRESOLVED_RELATED_MODULES` として得る。Step D の報告に、空でなければ次を足す（analyst には渡さない）。
  > ⚠️ ユースケースの関連モジュール（`related-modules`）のうち、仕様のディレクトリに対応しない値があります。参照先に入っていません。
  > {repo・ユースケース・値の一覧}
  > 値がモジュールのディレクトリ名とずれていれば、ユースケースの description.md を直してください。
- `xddp-rules/code-knowledge-boundary.md`: 読む側の「AI_INDEX の更新」を「AI_INDEX の作り直し（`ai_index.py`）」にする。
- `project-rulebook-cross-template.md`（と fixture の `test-fixtures/scratch-workspace/xddp/project-rulebook-cross.md`）: 「xddp-close 時に AI_INDEX.md に『⚠️ 破壊的変更あり』として記録される」を「工程11 がインタフェース仕様の `breaking:` に書き、AI_INDEX の『最終更新の破壊的変更』列に出る」にする。

**理由:** 1.3 の 2.（AI_INDEX を書くのは `ai_index.py` だけ）・1.3 の 4.（工程2 は AI_INDEX を読まない）・3.6（破壊的変更の印は `breaking:` で決める）に、説明の文を合わせる。`unresolved_related_modules` は、ずれ（A4-15）をテストだけでなく人に見えるようにするため。

### 3.12 テスト・fixture

- `test_docs_layout.py`: フロントマターのリスト（`[]`・`[a, b]`・`- a`・`- "a"`・`["a", "b"]`。引用符が外れる）、ユースケースの目的と関連モジュール（テンプレートの形 `- "{module1}"`）、`breaking:` の判定（`true`／`false`／`"true"`／キーなし）。
- `test_ai_index.py`:
  - 各節の行が `{DOCS}` の中身と一致する。最終更新CR がフロントマター・ファイル名の値になる（モジュールは `spec.md` の値。`spec.md` の無いモジュールのディレクトリは行にならない）。
  - 冪等（2回続けて実行しても変わらない）。
  - 管理しない節は残り、廃止した節は消える。プレースホルダー行が無い。セルの `|` が `\|` になる。
  - 最終更新の破壊的変更の列（`breaking: true`／`false`／キーなし）。同じインタフェースの行は1つだけ（N7）。
  - モジュール・ユースケースのディレクトリを消してから build すると、その行が消える（3.5 の Step D2）。
  - TSP・TRS・CRS が CR ごとの行になる（A2-5）。共通知識に `プロジェクト共通` の行がある（A2-6）。
  - アーカイブ候補（500行を超える `{DOCS}`）: `SURVEY-` の行が入る（N1）。`—` の行・CR の列を持たない節の行は入らない。`CR-` の行の後に `SURVEY-` の行が日付の順に並ぶ（`YYYYMMDD`・`YYYY-MM-DD` の両方）。ファイルの相対パスが入る。
  - code-knowledge インデックスの共有の知見がディレクトリごとに1行（ファイルごとではない）。
  - `{DOCS}` が無ければ何もしない。
- `test_domain_refs.py`: AI_INDEX を前提にしたテストを直接列挙の前提に直し、次を足す。
  - `_structures/`・`_constants/` の `.md` がファイル単位で入り、ディレクトリ・`.md` 以外は入らない。`IS_MULTI` で cross の分が入る。`_flows/` は入らない。
  - AI_INDEX があっても無くても結果が同じ。
  - `{DOCS}` に無いモジュール・ユースケース・インタフェースが latest-specs から入り、`degraded` になる。`{DOCS}/{repo}/specs/README.md` だけがある場合も同じ（A4-13）。
  - 上位 `FALLBACK_TOP_N` 件の代わりの読み方が、モジュール（`{DOCS}/{repo}/specs/` にモジュールが無い）とユースケース（`{DOCS}/system/specs/use-cases/` にユースケースが無い）の両方で働き、`fallback_applied` に `a:{repo}`・`b` が入る。`{DOCS}` に1つでもあれば働かない。
  - cross のインタフェース仕様のパスが `cross/specs/interfaces/{name}/spec.md`（A4-12）。
  - 関連モジュールの値の正規化と `unresolved_related_modules`（A4-15）。
- `test_promote.py`: AI_INDEX のテストを `test_ai_index.py` へ移し、先行更新・`--force-full-ai-index` のテストを消す。
- `artifact_lint.py` のテスト: `breaking:` の値の検査。
- 3.6 の「サマリに無いインタフェースの `breaking:` を変えない」は LLM の手順なので unittest にしない（5. の smoke で確かめる）。
- 3.13 の 1. の書く側→読む側のテスト。
- `test-fixtures/` の `baseline_docs/AI_INDEX.md` の4つ（`scratch-workspace/`・`scratch-workspace-p4-new-mode/`・`scratch-workspace-min/seeds/phase02-single/`・`scratch-workspace-min/seeds/phase02-single-quick/`）を、それぞれの fixture の `baseline_docs/` に対する `ai_index.py build` の出力で作り直す。
- `scratch-workspace` の `README.md`（AI_INDEX・先行更新のフラグの記述）・`xddp/CR-2026-903/progress.md`（先行更新のセクション）・`xddp/CR-2026-900/pending-items/PENDING-PROMOTE-CR-2026-900.md`（アーカイブ候補の節）・`xddp/project-rulebook-cross.md`（3.11）は、実装時に読んで、今の形に合わせる。

### 3.13 再発防止（PLAN-20261103-contract-audit 3.3）

1. **書く側→読む側のテスト:** 一時ディレクトリの latest-specs（モジュール・ユースケース・cross のインタフェース）と code-knowledge（`_structures/`・`_constants/`・制約）から、`promote.promote_specs` で `{DOCS}` に写し、そのまま
   - `domain_refs.resolve` に通して、モジュールの仕様・ユースケース・関連モジュール・インタフェース仕様・共有の知見のファイルが集まることを確かめる。
   - `ai_index.build` に通して、同じものが AI_INDEX の行になることを確かめる（共有の知見はディレクトリごとの行。3.2）。インタフェース仕様の `breaking: true` が「破壊的変更」の列に出ることも確かめる。
2. **共有の値の単一定義:**
   - `{DOCS}` と latest-specs の配置・フロントマターの読み方・ユースケースの目的と関連モジュール・共有の知見のディレクトリ名と種別名は `docs_layout.py` に定義し、`promote.py`・`domain_refs.py`・`ai_index.py` が import する。
   - AI_INDEX の節・列は `ai_index.py` だけが持つ。AI_INDEX を書くのは `ai_index.py` だけで、01-init・close・survey・update-knowledge はそれを呼ぶ。SKILL.md に AI_INDEX の表の定義を書かない。
   - LLM が書く値（cross のインタフェース仕様の `breaking:`）は `artifact_lint.py` で語彙を検査する。語彙は `docs_layout.py` に置き、`artifact_lint.py` と `ai_index.py` が import する。
   - **残る約束（このプランでは守れない）:** code-knowledge を書くのは LLM（`xddp-close-knowledge-agent`・`xddp-survey-promote-agent`・`xddp-update-knowledge`）で、置き場所は `code-knowledge-boundary.md` の宛先のルーティング表（`_structures/{DOMAIN}-relations.md` 等）が決める。`promote.promote_specs` は code-knowledge を写さないので、1. のテストも code-knowledge を一時ディレクトリに直接置く。ルーティング表と `docs_layout.py` のディレクトリ名・「直下の `*.md`」の約束は、import でもテストでも守られない。code-knowledge の書く側を直す P2 へ申し送る（4.）。
3. **refcheck の検査は足さない。** 理由: AI_INDEX の表の定義は SKILL.md から無くなり、AI_INDEX と工程2 の間の約束はスクリプトの import とテストで守られる。2. の「残る約束」（LLM が書く code-knowledge の置き場所）は書く側の約束なので、検査の要否も P2 で決める。

### 3.14 ドキュメント・ADR

- `CLAUDE.md` のファイル構成の表:
  - `xddp-02-analysis/scripts/`: `domain_refs.py` の説明を「AI_INDEX を読まず、`{DOCS}` と latest-specs を直接列挙する（`{DOCS}` に無いファイルは latest-specs から読み `degraded`。`_structures/`・`_constants/` は `.md` をファイル単位で、`IS_MULTI` では cross も）」にする。
  - `xddp-close/scripts/`: `promote.py` の説明から「AI_INDEX.md 全7セクションupsert（code-knowledge インデックスの制約の行は `knowledge_place.list_places` の列挙）」を消す。
  - `xddp-common/scripts/`: `docs_layout.py`・`ai_index.py` を足す。`knowledge_place.py` の説明の「読む側の関数 `list_places`・`applicable_places`（`promote.py`・`domain_refs.py` が `sys.path` 経由で import する」を「（`ai_index.py`・`domain_refs.py` が `sys.path` 経由で import する」にする。`xddp-close/scripts/` の `promote.py` の説明の「code-knowledge インデックスの制約の行は `knowledge_place.list_places` の列挙」も消す（上の項目）。
- `README.md`:
  - `/xddp-close` の行・`promote.py` の行・スクリプトの一覧を直す（AI_INDEX は Step D2 の `ai_index.py build`）。
  - AI_INDEX の作り直しの説明を足す: 01-init・close（Step D2）・survey・update-knowledge が作り直す。人が `{DOCS}` のファイルを直接編集した場合は、次にそれらを実行したときに反映される。すぐに反映するには `python3 ~/.claude/skills/xddp-common/scripts/ai_index.py build --docs {DOCS} --repos-keys {REPOS} [--is-multi]` を手で実行する（実例を書く）。
  - 01-init・survey・update-knowledge が作り直した AI_INDEX は `{DOCS}` の未コミットの変更になる。close の C0-2 で pull が止まったら、AI_INDEX.md の手元の変更は捨ててよい。pull が AI_INDEX.md で衝突したら、どちらの内容を採ってもよい（close が作り直す。3.5）。
  - アーカイブ候補の扱い（3.2）: 行を減らすには行のもとのファイルを `{DOCS}/_archive/` 等へ移す。
  - 工程11 の説明に先行更新の記述があれば消す。
- `docs/adr/ADR-0034-ai-index-docs-index.md`（追加）: 1.3 の方針（AI_INDEX は `{DOCS}` の索引で `ai_index.py` だけが書く・工程2 は AI_INDEX を読まない・先行更新の廃止・過去の DSN・CHD を読まない）と理由、却下した案（6.）。
- `ADR-0005`: Status を Superseded（ADR-0034）にし、知識参照ガイドも毎回作り直す旨を追記する。
- `ADR-0013`: AI_INDEX の更新は `promote.py` から `ai_index.py`（close の Step D2）へ移した旨を追記する。
- `ADR-0033`: Consequences に「工程2 は `_structures/`・`_constants/` も同じ理由で直接列挙し、ファイル単位で渡す」を1段落足す。「クローズの Step C2〜C7（AI_INDEX の更新）は Step C3.6 より前に走るので、クローズで書いた制約が AI_INDEX に載るのは次のクローズの後になる」の段落を「ADR-0034 で、AI_INDEX は close の Step D2（C3.6 と Step D の後）で作り直すようにしたので、クローズで書いた制約はそのクローズで AI_INDEX に載る」に直す。
- `docs/adr/README.md`: ADR-0034 の行を足し、ADR-0005 の状態を直す。
- `docs/xddp-contract-audit-2026-11.md` の 6. の 2b-3: 「05・06 の部分は PLAN-20261103-domain-refs-shared-knowledge で直した。09 の部分が残る。09 は過去の TSP・TRS をオーケストレーターが読むがテスト設計エージェントに渡していないので、記録先だけでなく受け渡しから決める必要がある」を書き足す（4.）。

---

## 4. 影響範囲

- 影響するスキル・コマンド: `/xddp-01-init`（AI_INDEX の作り方・`design/` を作らない）、`/xddp-02-analysis`（Step 0 の参照先）、`/xddp-05-arch`・`/xddp-06-design`（Step 0 で過去の設計を読まない）、`/xddp-11-specs`（先行更新が無くなる・`breaking:`）、`/xddp-close`（C0-2・C0-4・Step D2・Step E・F）、`/xddp-survey`・`/xddp-update-knowledge`（AI_INDEX を作り直す）。`/xddp-09-test` は変えない（AI_INDEX の TSP・TRS の表が CR ごとの行になるだけ）。
- 影響する工程: 工程2（`_structures/`・`_constants/` のファイルが参照先に入る。close の前の次の CR では latest-specs から読んで `degraded` になる）、工程5・6（過去の DSN・CHD を読まない）、工程11、close。
- トークン:
  - 工程2: analyst が読むファイルが、`_structures/`・`_constants/` の `.md` の数（ドメインの数に比例）と、latest-specs から入るファイルの分だけ増える。
  - 工程5・6: 過去の DSN（最大3件＋cross 2件）・CHD（最大3件＋cross）を読まなくなる分だけ減る（今は書く側が無いので、実際には読んでいない場合が多い。確認していません）。
  - 工程11: 先行更新の手順を読まなくなる分だけ減る。
- 後方互換性: 考慮しない。既存の AI_INDEX は、次に `ai_index.py build` を実行したときに管理する節が作り直され、廃止した節は消える。既存の `{DOCS}/{repo}/design/` は残るが、どこからも読まれない（消すかは人が決める）。
- 他のプラン:
  - P3（PLAN-{作成日}-lessons-backlog）・P5（PLAN-{作成日}-project-rulebook-contracts）は `promote.py` の `write_output_file` を直す。このプランの実装（アーカイブ候補の節の削除）の後の状態を見て書く。
  - P3 の A3-27（共通ファイルの昇格エラーが Step D・E に出ない）のうち、AI_INDEX の更新エラーの部分は、このプランの Step D2・E・F（3.5）で直る。P3 は backlog（C7）と共通の rulebook（C6）の部分だけを直す。
  - P5 の A5-1（close の C3.5 と C6 の順序）は close の Step の並びを変えうる。このプランの Step D2 は Step D の後に置くので、C2〜C7・C3.5・C3.6 の並びが変わっても位置は変わらない。
  - P2（PLAN-{作成日}-code-knowledge-writers）は survey・update-knowledge を直す。このプランが足す `ai_index.py build` の呼び出しを前提にする。
  - P2 への申し送り: code-knowledge の置き場所の約束（`code-knowledge-boundary.md` のルーティング表と `docs_layout.py` の共有の知見のディレクトリ名・「直下の `*.md`」）は、このプランでは守れない（3.13 の 2.）。P2 で書く側を直すときに、`docs_layout.py` の定義に揃える方法（と refcheck の検査の要否）を決める。
  - P4（PLAN-{作成日}-latest-specs-contracts）は 11-specs を直す。このプランが先行更新を削除した後の状態を見て書く。
  - P4 は「05／06 の latest-specs の参照」（A4-14）も直す。このプランの 3.10 が同じ 05・06 の Step 0 を書き換える（過去の設計の手順を消し、`CURRENT_SPECS_REFS[{repo}]` を repo ごとの値にする）ので、P4 はその後の形を前提に書く。
  - P4 への申し送り: 工程2 が latest-specs にだけある仕様を読むようになる（3.4）ので、latest-specs に古い仕様が残る問題（A4-43・A4-44 と、別のワークスペースの close が `{DOCS}` から消したモジュールを C0-3 が latest-specs から消さないこと）は工程2 にも効く。P4 で latest-specs から消す仕組みを決めるときは、工程2 の読み方（3.4）も前提にする。
  - PLAN-20261102-cochange-knowledge は AI_INDEX の code-knowledge インデックスに `_cochange/` を足す。書き換えるときは `ai_index.py`・`docs_layout.py` の定義に足す。
- デグレードのリスク:
  - 工程2 で `_constants/` のディレクトリの読み込みの失敗が §0 に記録されなくなる（意図した変化）。
  - 人が AI_INDEX の管理する節を手で直していた場合、その直しは消える（管理しない節は残る）。
  - 工程2 が latest-specs にだけある仕様を毎回読むようになる。今は `{DOCS}/{repo}/specs/` が無いときにしか読まず、01-init がそれを作るので実際には読んでいない（A4-13）。7.3 の進行中の CR の新しいモジュールのほかに、次の古い仕様も `degraded` で入る。(a) 工程11 の後に abort した CR の仕様（A4-43）。(b) survey の (c) で承認されなかった仕様（A4-44）。(c) 別のワークスペースの close が `{DOCS}` から消したモジュール（C0-3 は `{DOCS}`→latest-specs の写しだけで消さない）。
    - 扱い: P4 で直すまで受け入れる。これらは今も後の CR の close で `{DOCS}` に昇格しうる問題で、工程2 で読むことで新しく生じる問題ではない。ANA §0 の出典に latest-specs のパスが出て、`degraded` の注記が付くので、人がレビューで見分けられる。元の原因は P4 へ申し送る（上の「他のプラン」）。
  - 01-init・survey・update-knowledge が `{DOCS}/AI_INDEX.md` をコミットせずに作り直すようになる（今は 11-specs の先行更新と survey の ③ だけ）。並行する close も AI_INDEX を作り直すので、`{DOCS}` の pull が AI_INDEX.md の未コミットの変更で止まる場合が増える。AI_INDEX.md を別々にコミットした2つのワークスペースでは、pull が AI_INDEX.md で衝突する（今も close のたびに書き足すので起きうるが、丸ごと作り直すので起きやすくなる）。close の C0-2 で、未コミットの変更が AI_INDEX.md だけなら捨てて pull し直す案を、AI_INDEX.md だけの衝突なら取り込む側を採って merge を終える案を示す（3.5）。README にも書く（3.14）。
- 監査の報告書の段階2b の候補 2b-3（[docs/xddp-contract-audit-2026-11.md](../docs/xddp-contract-audit-2026-11.md) の 6.。工程5・6 の Step 0 がテンプレートに無い節に記録させる。09 も同じ型）との関係:
  - 05・06 の部分は、このプランの 3.10 で直る（記録を「参照資料」の行に移す）。実装の後に、報告書の 2b-3 にその旨を書き足す（3.14）。
  - 09 の部分（Step 0 の 3.「Record in TSP "referenced past test specs" section」）は、このプランでは直さない。09 は過去の TSP・TRS をオーケストレーターが読むがテスト設計エージェントに渡していないので、直すにはエージェントへの受け渡しから決める必要があり、P1 の範囲を超える。2b-3 に残る（段階2b を行うかの判断に従う）。

---

## 5. 確認項目

- [ ] `make test`（refcheck・全 unittest）が緑
- [ ] 3.12 の各テスト
- [ ] 3.13 の 1. の書く側→読む側のテストがある
- [ ] 3.13 の 2. の単一定義: `promote.py`・`domain_refs.py`・`ai_index.py` が `docs_layout.py` を import し、配置・フロントマターの読み取りを自分で定義していない。CC 配下の SKILL.md・エージェントに AI_INDEX の表のヘッダ行が無い（`grep` で確かめる）
- [ ] CC 配下に「先行更新」（AI_INDEX の）・`--force-full-ai-index`・`PAST_CROSS_DESIGN_DIR`・`{DOCS}/{repo}/design/`・`{DOCS}/cross/design/` の参照が残っていない（`grep` で確かめる）
- [ ] fixture の AI_INDEX が `ai_index.py build` の出力と一致する
- [ ] CLAUDE.md・README.md・ADR の記述と整合（3.14。README に `ai_index.py build` を手で実行する実例がある）
- [ ] 実行時ファイルに設計根拠・プランへの参照を書いていない（スクリプトの docstring・コメントを含む）
- [ ] 特定ドメインへの偏りがない（配置と表の定義だけで、ドメインに依存する記述は無い）
- [ ] 監査の報告書 8.2 の P1 の17件が、それぞれ 3. のどこで直るかが 1.2 にある
- [ ] smoke（人が実施）: 工程2（`_structures/`・`_constants/` のファイルと latest-specs だけにあるモジュールが ANA §0 に出る）・工程11（cross のインタフェース仕様の `breaking:`。サマリに無いものは変わらない）・close（Step D で削除した後の AI_INDEX に行が残らない。C0-2 の (a)〜(c) を、`{DOCS}` を git で管理したワークスペースで1回ずつ）・survey

---

## 6. 却下した案

- **今の書き足す仕組みを残し、指摘を1つずつ直す:** ラベル・最終更新CR・キー列・ひな形の食い違いを、書く人（4か所）ごとに直し続ける必要がある。人の判断（2026-11-04）で採らなかった。
- **先行更新を残し、スクリプトにする:** リンクが close まで壊れたままで、`{DOCS}` をコミットせずに書き換えるので close の `git pull` が止まりうる（A2-11）。人の判断で採らなかった。
- **close で DSN・CHD を `{DOCS}/{repo}/design/` に写す:** CHD は差分で、後の CR から読むと古い Before と今の仕様が並ぶ。設計判断の再利用は rulebook の ADR が受け持つ。人の判断で採らなかった。
- **`CODE_KNOWLEDGE_SPECIAL_DIRS` のラベルを `構造体関連図` に直すだけ（最初の版の却下案）:** ディレクトリのパスを渡す問題と、AI_INDEX に行の無い知見が見えない問題が残る。
- **ディレクトリのパスを渡したまま、analyst に配下を Glob させる:** 決定的な列挙を LLM に任せることになる（CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」）。

---

## 7. 未決事項（レビューで確認したい点）

1. **共有の知見をキーワードで絞るか:** ファイル名の `{DOMAIN}` にキーワードを当てて絞る案もある。`{DOMAIN}` はクローズで暫定に付けた名前（推定できなければ `shared`）が多く、照合の当たりにくさは確認できていない。本プランは絞らない（全件）。件数が問題になったら、`stats` に件数を出して計測してから決める。
   - **扱い:** 承認をもって決定とする。
2. **`_flows/`（機能間フロー・DFD・callgraph）を工程2 で集めるか:** analyst の Constraint check の種別に `_flows` は無く、工程2 で使う根拠を確認できていない。本プランでは集めない（PLAN-20261102-impact-hypotheses が読む側を足す予定）。
   - **扱い:** 承認をもって決定とする。
3. **同じモジュールが `{DOCS}` と latest-specs の両方にある場合、`{DOCS}`（承認済み）を選ぶ。latest-specs にだけあるものは渡す（`degraded`）:** latest-specs はワークスペースに1つで、同じワークスペースのすべての CR が共有する（close が `{DOCS}` から取り込んだ仕様・close していない CR が工程11 で書いた仕様・survey の (c) で書いた仕様が入る）。
   - 例: CR-A の工程11 まで進めて close していないときに、同じワークスペースで CR-B の工程2 を実行する。CR-A が既存のモジュールを変えていれば、CR-B は変える前（`{DOCS}`）の仕様を読む。CR-A が足した新しいモジュールは latest-specs から読み、ANA §0 に `degraded` と注記される。
   - latest-specs を選ぶ案は、承認前の内容を正として渡すことになるので採らない。latest-specs にだけあるものを渡さない案は、今の `degraded` の仕組み（analyst・lint・reviewer）を消すことになり、close 前の CR の新しいモジュールも見えなくなるので採らない。
   - **決定（2026-11-04・人）:** このとおりとする。
   - この決定の例（進行中の CR）のほかに、latest-specs にだけ古い仕様が残る場合（abort した CR・承認されなかった survey・別のワークスペースで消したモジュール）も `degraded` で入る。本プランでは受け入れ、P4 へ申し送る（4. のデグレードのリスク）。承認をもって決定とする。
4. **close で AI_INDEX を作り直すのは Step D2（Step D の「クローズ完了」と削除の後）だけにし、promote.py の `run` からは外す:** C2 で作ると C3.6 の code-knowledge と C6 の rulebook が載らず、Step D の前に作ると Step D で消したモジュールと人の直接編集が載らないため。結果とアーカイブ候補は PENDING-PROMOTE ではなく Step E・F で示す。
   - **扱い:** 承認をもって決定とする。
5. **`共通知識` の表に最終更新CR の列を持たない:** rulebook にはフロントマターの `last-updated-cr` が無く、今の値（close のたびに今の CR）は意味が無いため（A2-6）。
   - **扱い:** 承認をもって決定とする。

---

## 8. レビュー

AIレビュー結果: [plans/review/PLAN-20261103-domain-refs-shared-knowledge-review.md](review/PLAN-20261103-domain-refs-shared-knowledge-review.md)

---

## 9. 承認
