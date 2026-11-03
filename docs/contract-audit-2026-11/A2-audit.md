# 監査者 A2 の報告（原文。PLAN-20261103-contract-audit 段階2a）

> 監査者の最終報告をそのまま載せたもの（検証前）。検証結果と統合後の重大度は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。パスの `{W}` は監査用の worktree（ecb54c4。セッションのスクラッチのディレクトリに作り、監査の後に削除）。

# A2 AI_INDEX.md 約束の監査 報告（対象 ecb54c4）

**ツールについて:** この環境には Grep・Glob ツールがありませんでした（呼び出すと「Grep is not available — use grep via Bash」と返りました）。そのため、検索と行の表示には Bash の読み取り専用コマンド（`grep -rn`・`sed -n`・`ls`・`wc`・`tail`・`git log -1`）を使いました。ファイルの書き換え・スクリプトやテストの実行はしていません。パスは `{W}` からの相対パスで、`CC=ClaudeCode/.claude` と略します。

## 1. 確認した約束の一覧

| # | 約束 | 書く側（ファイル:行・節） | 読む側（ファイル:行・節） | 見つけた検索語（パターンと範囲） | 結果 |
|---|---|---|---|---|---|
| 1 | progress.md の「## 工程11 AI_INDEX先行更新セクション」の見出しと `- {節}: 済` の行の書式 | CC/skills/xddp-11-specs/SKILL.md:604-619（Step DONE） | CC/skills/xddp-close/scripts/promote.py:234-250, 548-551（`read_ai_index_preupdated`・`_skip`） | `AI_INDEX`（CC/skills・agents） | なし（書式は一致）。ただし「済」でスキップした後の扱いで食い違いがある（指摘#2・#7） |
| 2 | 「ユースケース一覧」の列（ユースケース／目的（1行）／description／関連モジュール／最終更新CR）・リンク `system/specs/use-cases/{uc}/description.md`・フロントマター `related-modules`・`## 2. 目的・ゴール` | promote.py:354-356, 368-397, 557-559／01-init SKILL.md:143-147／11-specs:581-589／uc テンプレート CC/skills/xddp-11-specs/templates/11_system-use-case-description-template.md:6-8, 34 | domain_refs.py:239-269 | `ユースケース一覧`・`related-modules|目的・ゴール`（CC 全体） | 列とパスは一致。`related-modules: []` の扱いに 🔵（指摘#9） |
| 3 | 「モジュール別最新仕様」の列・キー（リポジトリ, モジュール）・リンク `{repo}/specs/{module}/spec.md`・行の範囲 | promote.py:362-364, 420-432, 568-574／11-specs:575-602／survey SKILL.md:390-393／01-init:155-159 | domain_refs.py:271-290 | `モジュール別最新仕様`（CC 全体） | 食い違いあり 指摘#3・#7・#8・#9 |
| 4 | 「リポジトリ別仕様書」の列・キー | promote.py:358-360, 400-417, 561-566／survey:394-400 | 機械的に読む側は無い（AI が読むことを想定） | `リポジトリ別仕様書` | 最終更新CR の付け方に食い違いあり 指摘#7 |
| 5 | 「クロスインタフェース一覧」の列・名前の列＝`latest-specs/cross/interfaces/{名前}` のディレクトリ名・「⚠️ 破壊的変更あり」の印 | promote.py:435-457, 576-582／11-specs:577, 289-296／project-rulebook-cross-template.md:61 | domain_refs.py:319-333 | `クロスインタフェース一覧`・`破壊的変更` | 食い違いあり 指摘#2 |
| 6 | cross の CHD のパス `06_design/cross/CHD-{CR}-cross.md`・見出し「インタフェース変更サマリ」・`breaking` 列・`インタフェース` 列（`detect_breaking_changes`） | 06-design SKILL.md:112, 126-130（Step A-cross） | promote.py:1022-1078 | `インタフェース変更サマリ`（CC 全体） | パス・見出し（正規表現）・列名は一致。インタフェース名と AI_INDEX のディレクトリ名との照合で食い違いあり（指摘#2） |
| 7 | 「code-knowledge インデックス」の列（知りたいこと／参照先）と行のラベル `{repo}/{place} 制約・注意事項`・`{repo} 構造体関連図`・`{repo} 共有定数`・`{repo} 機能間フロー` | promote.py:590-605 | domain_refs.py:34-38, 292-313（`_structures`→`共有構造体`、`_constants`→`共有定数`）／analyst-agent CC/agents/xddp-analyst-agent.md:84（種別 `共有構造体`） | `構造体関連図|共有構造体|共有定数|機能間フロー`（ClaudeCode・tools・docs/adr） | 食い違いあり 指摘#1（`_constants` と制約の行はなし） |
| 8 | 「変更要求仕様書（CRS）ナビゲーション」の行と、写し `{DOCS}/{repo}/crs/CRS-{CR}.md`（元は `03_change-requirements/CRS-{CR}.md`） | promote.py:476-485, 607-611（行）、929-947（写し） | AI が AI_INDEX から引く（機械的に読む側は無い） | `CRS-\{CR\}`・`crs/` | なし（行のリンクと写しの先が一致）。節の名前の記述が不整合（指摘#9） |
| 9 | 「テスト仕様（TSP）・テスト結果（TRS）」の行と写し（`09_test-spec/{repo}/TSP-{CR}.md`・`cross/TSP-{CR}-cross.md`・`10_test-results/{repo}/TRS-{CR}-*.md` → `{DOCS}/{repo}/test/`） | promote.py:488-502, 613-617, 950-979 | 09-test SKILL.md:35-41（Step 0「past TSP/TRS list」） | `TSP-\{CR\}|TRS-\{CR\}-`（09-test・10-test-run） | パスは 09-test:155,191／10-test-run:104,118 と一致。表のキーを repo にしているので過去の CR の行が残らない（指摘#5） |
| 10 | 過去の DSN／CHD の一覧（`{DOCS}/{repo}/design/`・「設計書ナビゲーション」・「リポジトリ別設計書・テスト仕様書」） | 11-specs:631-640／01-init:122, 167-171, 186-190 | 05-arch SKILL.md:109-113, 159／06-design SKILL.md:49-53, 114, 216／designer-agent:45 | `/design/|設計書ナビゲーション|リポジトリ別設計書`（CC 全体。`06_design/`・`05_architecture/` を除く） | 食い違いあり 指摘#4 |
| 11 | 「共通知識」の列 | 01-init:173-177（`ドキュメント | 説明`） | promote.py:524-536, 624-627（`リポジトリ | project-rulebook | 最終更新CR`） | `共通知識` | 食い違いあり 指摘#6 |
| 12 | 「用語集」の行 | promote.py:505-524, 619-622 | 機械的に読む側は無い（domain_refs.py:374-379 は直接列挙） | `## 用語集` | なし |
| 13 | 「知識参照ガイド」（初回だけ作る） | promote.py:334-347, 584-588（ADR-0005） | AI が読む | `知識参照ガイド` | 記述の不整合 🔵（指摘#9） |
| 14 | AI_INDEX のひな形（初期の内容） | 01-init:136-178／promote.py:349-365（`AI_INDEX_SKELETON`）／11-specs:51-60・survey:388-389（init を正本として作る） | — | `AI_INDEX`・`Initial file contents` | 食い違いあり 指摘#9 |
| 15 | `--force-full-ai-index` を付ける条件（`PULLED_FILES` に `AI_INDEX.md` が含まれる） | close SKILL.md:236-241（C0-4）、292-299 | promote.py:548-551, 1262 | `AI_INDEX`（close） | 🔶（指摘#11） |
| 16 | code-knowledge-boundary.md「## 知見の置き場所（MODULE）」に従う読む側として「AI_INDEX の更新」を挙げていること | code-knowledge-boundary.md:94-96 | promote.py:596-600（`list_places`） | `AI_INDEX`（xddp-rules） | なし（`list_places` を import している。promote.py:34-35） |

## 2. 時期の約束の表

| 書く側（スキル・Step） | 読む側（スキル・Step） | 順序の根拠（ファイル:行） | 結果 |
|---|---|---|---|
| xddp-01-init Step 4.5（AI_INDEX を新規に作る） | 以降のすべての工程 | 01-init:109-118 | なし |
| xddp-11-specs Step DONE（AI_INDEX の先行更新と progress.md の「済」） | xddp-close Step C2（promote.py `read_ai_index_preupdated`） | close:31（工程11 が ✅ でなければ止まる）、11-specs:544（次に `/xddp-close`） | 順序はよい。ただし「済」でスキップした結果に食い違いがある（指摘#2・#7） |
| xddp-11-specs Step DONE（先行更新） | 次の CR の xddp-02-analysis Step 0（domain_refs.py。xddp-close より前） | 11-specs:578（先行更新の目的として書かれている） | 食い違いあり 指摘#3 |
| xddp-11-specs Step DONE（`{DOCS}/AI_INDEX.md` を書き換え、コミットしない） | xddp-close Step C0-2（`git -C {DOCS} pull`） | close:207-209 | 🔶 指摘#11 |
| xddp-close Step C2（promote.py の code-knowledge インデックスの行） | 同じ close の Step C3.6（xddp-close-knowledge-agent が code-knowledge を書く）→ 次の CR の工程2 | close:278-308（C2）→ 310-327（C3.5/C3.6）。promote.py:590-605 | 食い違いあり 指摘#10（制約については ADR-0033:80 が既知の限界として記録） |
| xddp-close Step C2（AI_INDEX の CRS・TSP の行） | 同じ実行の C4・C5（写し） | promote.py:1186-1192 で AI_INDEX を書いた後に 1214-1215 で写す（同じ実行の中） | なし（行の有無は写しの元の実在で決める） |
| xddp-survey Step 8③（(c) specs への昇格だけ） | 工程2 domain_refs.py | survey:383-401 | survey の (b) knowledge への昇格では AI_INDEX を更新しない（指摘#10） |
| 前の CR の xddp-close（AI_INDEX） | xddp-05-arch／06-design／09-test の Step 0 | 05-arch:111、06-design:51、09-test:38 | 書く側が無い・足りない（指摘#4・#5） |

## 3. 指摘（A2 の担当）

### 指摘#1 🔴 code-knowledge インデックスの `_structures` のラベルが書く側と読む側で違う
- **約束:** 「知りたいこと」列のラベル `{repo} {種類名}`
- **書く側:** CC/skills/xddp-close/scripts/promote.py:601 `("_structures", "構造体関連図")` → 行のラベルは `{repo} 構造体関連図`（:603）
- **読む側:** CC/skills/xddp-02-analysis/scripts/domain_refs.py:35-38 `"_structures": "共有構造体"`。:305-307 は `f"{repo} {type_name}"` がラベルとして AI_INDEX に無ければ `continue` する。:34 のコメントは「promote.py update_ai_index() と同一の対応」と書いているが、実際には違う。
- **食い違い:** `repo-a 構造体関連図` と `repo-a 共有構造体` が一致しない（`共有定数` は両側で一致する）。
- **起きること:** 工程2 の `DOMAIN_REF_PATHS` に `{DOCS}/{repo}/knowledge/code-knowledge/_structures/` が一度も入らない。analyst-agent（CC/agents/xddp-analyst-agent.md:84）が種別 `共有構造体` の参照先として期待している構造体関連図の知見が、警告なしに渡らない。AI_INDEX が無い場合の経路（domain_refs.py:334-365）も `_structures`・`_constants` を列挙しないので、どの経路でも読まれない。単体テスト（test_domain_refs.py）にこのラベルを確かめるケースは見当たらない（grep で 0 件）。
- **確度:** ✅ 両側の定数を読んで確認した。
- **修正案（決めない）:** ラベルの対応を1か所（例: knowledge_place.py か promote.py の定数）にまとめて両側で import する。または `_structures`・`_constants` も制約と同じように直接列挙する。

### 指摘#2 🟡 クロスインタフェース一覧の「⚠️ 破壊的変更あり」が付かない・付いた場合も表と工程2 の参照を壊す
- **約束:** cross の CHD「インタフェース変更サマリ」で `breaking: true` のインタフェースを、AI_INDEX のクロスインタフェース一覧で「⚠️ 破壊的変更あり」と示す（CC/skills/xddp-common/templates/project-rulebook-cross-template.md:61）。
- **書く側:**
  - 06-design SKILL.md:126-130 の「インタフェース」列（例 `POST /jobs`）
  - 11-specs:289-296 のディレクトリ名（ケバブ形式 `post-jobs` 等）
  - promote.py:446-447（`if name in breaking_interfaces` でディレクトリ名と CHD のインタフェース名を比べる）
  - promote.py:577（先行更新が「済」なら節ごと飛ばす）
- **読む側:** domain_refs.py:322-331（名前の列のセルをそのまま `cross/specs/interfaces/{name}/spec.md` のパスにする）
- **食い違い:**
  - (a) CHD のインタフェース名とケバブ形式のディレクトリ名を、変換せずに完全一致で比べている。11-specs の命名規則では HTTP・イベント・CAN 等の名前が必ず変わるので、一致するのはもともとケバブ形式の名前だけになる。
  - (b) 11-specs が先行更新でクロスインタフェース一覧を「済」と記録すると（11-specs:577, 612）、promote.py は節を更新しない（:577）。11-specs の指示（:581-589）は「update_ai_index の定義に従う」だけで、CHD から breaking を判定する手順は書いていない。
  - (c) 印が付いた場合、キー列 [0]（:581-582）の値が `名前 ⚠️ 破壊的変更あり（CR: …）` に変わる。そのため既存の行と一致せずに行が増え、CR ごとにさらに増える。domain_refs は印の付いた文字列でパスを作るので、ファイルが無く、`add_docs` が何も言わずに飛ばす。
- **起きること:** AI_INDEX から破壊的変更の印が抜ける（PENDING-PROMOTE と知見ログの警告 promote.py:1132-1138, 1200-1212 には出るので、人が気付ける経路はある）。印が付いた CR では表に重複した行が残り、初めて追加されたインタフェースは工程2 で参照できない。
- **確度:** (a)(c) は ✅（コードと命名規則を読んだ）。(b) の「LLM が印を付けない」は 🔶（11-specs の指示に breaking の判定が無いことから推論）。「済」でスキップすること自体は ✅。
- **修正案（決めない）:** 印は名前の列ではなく別の列（例: 「破壊的変更」列）に書く。照合には interface spec のフロントマター `breaking:`（11_cross-interface-spec-template.md:7）を使う。先行更新ではこの節を「済」にしない。

### 指摘#3 🟡 先行更新の目的（close の前に次の CR の工程2 が参照できる）が達成されない
- **約束:** 11-specs:578「xddp-close 実行前に次 CR の xddp-02-analysis が参照できる状態にする」、11-specs:666「次の CR の xddp-02-analysis は `latest-specs/` から直接参照します」
- **書く側:** 11-specs Step DONE の先行更新（:575-602）。リンク先が close の前には無いことを認めている（:642-645）。
- **読む側:** domain_refs.py:288-290 は AI_INDEX で当たったモジュールを `{DOCS}/{repo}/specs/{mod}/spec.md` としてだけ追加する（ファイルが無ければ飛ばす。:233-236）。latest-specs へのフォールバックは `{DOCS}/{repo}/specs` ディレクトリ自体が無い場合だけ（:382-384）。ユースケースも `{DOCS}/system/specs` が無い場合だけ（:398）。01-init:120 が `{DOCS}/{repo}/specs/README.md` を作るので、通常このディレクトリはある。
- **起きること:** close の前に始めた次の CR の工程2 では、先行更新した行のモジュール・ユースケースが参照先から何も言わずに抜ける。`DOMAIN_REF_MODE` は `normal` のままになる（:420-423）。
- **確度:** ✅（両側のコードを読んで確認した）
- **修正案（任意）:** domain_refs で、DOCS 側のファイルが無いときにファイル単位で latest-specs へフォールバックする（`degraded`）。

### 指摘#4 🟡 過去の DSN／CHD を AI_INDEX から引く読む側に、書く側が無い
- **読む側:** 05-arch SKILL.md:109-113（`{DOCS}/{repo}/design/` があれば AI_INDEX から過去の DSN の一覧を探す）、06-design SKILL.md:49-53, 114、designer-agent:45（`{DOCS}/cross/design/`）
- **書く側（とされるもの）:**
  - 11-specs:631-640 が「設計書ナビゲーション」に `{DOCS}/{repo}/design/DSN-…` の行を足し、「リンク先は xddp-close Step C4 完了後に有効になる」と書いている。しかし close の C4 は CRS の写しだけ（promote.py:929-947）。
  - 01-init:167-171 の「リポジトリ別設計書・テスト仕様書」には「xddp-close Step C4/C5 が更新する」とあるが、promote.py にこの節を書く処理は無い。
  - 01-init:186-190 の `design/README.md` は「このディレクトリは本ツールでは使用されていません」と書いている。
  - `/design/` を grep した結果（CC 全体。`05_architecture/`・`06_design/` を除く）、DSN・CHD を `{DOCS}` に写す処理は見つからなかった。
- **起きること:** 05・06 の Step 0 は過去の設計を見つけられない（`design/` はあるので手順には入るが、一覧が無い）。11-specs が足すリンクはずっと壊れたまま。CHD の行はどこにも無い。
- **確度:** ✅（書く側が無いことを grep で確認した）
- **修正案（決めない）:** DSN・CHD を昇格させるか、読む側の手順と 11-specs の設計書ナビゲーション、init のひな形の節を消すかを決める。

### 指摘#5 🟡 TSP／TRS の表が repo ごとに1行で、過去の CR の一覧にならない
- **書く側:** promote.py:616-617（キー列 [0]＝repo）。CR ごとに同じ行を置き換える。
- **読む側:** 09-test SKILL.md:38-40（「past TSP/TRS list」から最大3件の TSP・2件の TRS を読む）
- **起きること:** AI_INDEX には各 repo の最新の CR の TSP・TRS しか残らない。写しは `{DOCS}/{repo}/test/` に溜まるので、LLM がディレクトリを列挙すれば補える。
- **確度:** キーで置き換わることは ✅。影響の大きさは 🔶（LLM がディレクトリを見るかどうか次第）。
- **修正案（任意）:** キーを (repo, 最終更新CR) にする。CRS ナビゲーションと同じく CR ごとの行にする。

### 指摘#6 🟡 「共通知識」の列が init と promote で違い、初回の close で共通の project-rulebook の行が消える
- **書く側1:** 01-init:173-177（`ドキュメント | 説明`、`[project-rulebook.md](project-rulebook.md)` の行）
- **書く側2:** promote.py:627（`リポジトリ | project-rulebook | 最終更新CR`）。`upsert_table` はヘッダが違えばデータ行を捨てる（:200-202）。
- **起きること:** 共通の `project-rulebook.md` は `{DOCS}` に写される（:984-990）が、AI_INDEX の行は消え、promote.py には共通の rulebook の行を作る処理が無い。`_common_knowledge_rows` は rulebook が変わっていなくても、全 repo の最終更新CR を今の CR にする（:530-535）。
- **確度:** ✅

### 指摘#7 🟡（🔵寄り）「最終更新CR」を今の CR で触っていない行にまで付ける。11-specs の「同じ行集合」という説明は事実と違う
- **書く側:**
  - promote.py `_module_spec_rows`（:420-432）は latest-specs の全モジュールディレクトリ（C0-3 で DOCS から取り込んだ他の CR・survey のモジュールを含む）に今の CR を付ける。
  - `_repo_spec_rows`（:561-566）は常に更新する。close の AFFECTED_REPOS は FILTER_BY_SPO=false で REPOS_KEYS 全部（close:21-23、xddp-common SKILL.md:131-132）なので、今の CR が触っていない repo にも付く。
- **11-specs の説明:** :591-598 は、先行更新の行を SPECOUT_MODULES に限り「promote.py の『今回 CR で生成・更新した全モジュールの行を upsert』と同一の集合」と書いている。しかしその文は promote.py に無い（grep で 0 件）。:624-626 が引く「IS_MULTI への移行対応…」も無い。
- **逆向き:** 先行更新が「済」の場合、MOD が更新した「SPO なし・CHD あり」のモジュール（CC/agents/xddp-specs-mod-agent.md:50-51）は SPECOUT_MODULES に入らないので、行が更新されない。
- **起きること:** 最終更新CR がずれる。これを使うアーカイブ候補の判定（promote.py:639-654）も、実際には古い行を新しいと見る。
- **確度:** ✅（コードと文の有無を確認した）

### 指摘#8 🔶 先行更新のモジュール名（SPECOUT_MODULES）と latest-specs のディレクトリ名（ケバブ形式）が違う場合がある
- **書く側:** 11-specs:591-598（`04_specout/{repo}/modules/` のディレクトリ名）。promote.py:426-431 と domain_refs.py:290 が前提にするのは latest-specs のディレクトリ名。
- **変換規則:** mod-agent:159-161 では `AuthService` → `auth-service` に変える。
- **起きること:** 先行更新の LLM が SPO のディレクトリ名をそのまま書くと、domain_refs が存在しないパスを作って何も言わずに飛ばし、close で行が重複しうる。
- **確度:** 🔶（11-specs は「列・リンクは promote に従う」とも書いており、LLM が変換するかどうかで決まる）

### 指摘#9 🔵 ひな形・説明の不整合（動作への影響は小さい）
- **ひな形が3つある:** 01-init:136-178（6節・プレースホルダー行あり）、promote.py:349-365（3節）、11-specs:53-59・survey:388（init を正本とする）。11-specs:57-59 は「code-knowledge インデックス・CRS ナビゲーションはテーブル形式ではない」と書くが、promote.py:605, 611 は表で書く。
- **プレースホルダー行が残り続ける:** init の `（… 実行後に自動追記） | — |…`（01-init:147,153,159,165,171）。ヘッダが一致すると upsert で残り続ける（promote.py:204-218）。domain_refs は `（` で始まる行を除外する（:249）ので、実害は表示だけ。
- **知識参照ガイドの参照先の名前と位置:** promote.py:342, 345 は「変更要求仕様書」テーブル・「上記『テスト仕様（TSP）』テーブル」を指すが、実際の見出しは「変更要求仕様書（CRS）ナビゲーション」「テスト仕様（TSP）・テスト結果（TRS）」（:611, 616）。しかもガイドの後に末尾へ足すので「上記」ではない。
- **`state` 列が常に `—`:** promote.py:431、survey:393。mod-agent:97 は `state-machine.md` を作るのに、リンクにならない。
- **`related-modules: []` の扱い:** フロントマターの `related-modules: []`（テンプレート:20 の指示）は `_parse_frontmatter` で文字列 `"[]"` になる（promote.py:118, 387-389）。関連モジュールの列に `[]` と出て、domain_refs は `[]` をモジュール名として扱う（:259-264。パスが無いので飛ばされるだけ）。
- **`|` のエスケープ:** promote の `_join_row`（:58-59）はセル内の `|` をエスケープしない。domain_refs の分割（:124-126）は `\|` を扱わない（目的の列に `|` があると列がずれる。実例は確認していません）。

### 指摘#10 🟡 時期: code-knowledge インデックスを書くのが C3.6 の前。survey の knowledge への昇格では AI_INDEX を更新しない。`_structures`・`_constants` は AI_INDEX 経由でしか読まれない
- **書く側:** promote.py:590-605（close C2）。code-knowledge を書くのは C3.6（close:310-327）で、その後になる。survey の (b)（survey:383 の③は (c) だけ）。
- **読む側:** domain_refs.py:292-311（`_structures`・`_constants` は AI_INDEX のラベルがある場合だけ集める）
- **起きること:** 制約は直接列挙するので影響を受けない（ADR-0033:51, 80 に記録済み）。しかし `_structures`・`_constants` は、作られた CR の close では載らず、同じ repo の次の close まで工程2 に届かない。survey で昇格したものは、その repo が次の close の AFFECTED_REPOS に入るまで届かない（指摘#1 があるので `_structures` はいつまでも届かない）。
- **確度:** ✅（Step の順序とコードから）

### 指摘#11 🔶 11-specs の先行更新と close の `git pull`・`PULLED_FILES` の照合
- 11-specs Step DONE は git 管理の `{DOCS}/AI_INDEX.md` を書き換えてコミットしない（11-specs:575-579）。close C0-2 の `git -C {DOCS} pull`（close:208）で、リモート側も AI_INDEX.md を変えていると、git は作業ツリーの変更を理由に pull を止める。C0-2 には pull が失敗したときの扱いが書かれていない（close:207-209）。
- close:236-241, 293 は `git -C {DOCS} diff --name-only` の結果を「DOCS ルートからの相対パス」として `AI_INDEX.md` と比べる。しかし git はリポジトリのルートからの相対パスを返すので、DOCS が上位のリポジトリの一部（例: `baseline_docs/` がワークスペースのリポジトリの中）のときは `baseline_docs/AI_INDEX.md` になり、一致せず `--force-full-ai-index` が付かない。
- **確度:** 🔶（git の振る舞いと LLM の解釈に依存する。実行で確かめていない）

## 4. 担当外の指摘
なし。`{DOCS}/{repo}/design/README.md` の文言は、AI_INDEX の設計書の行に関わるので指摘#4 に含めた。

## 5. 段階2b の候補
- **段階2b:** cross の CHD「インタフェース変更サマリ」の列。書く側 06-design SKILL.md:126-130（`インタフェース | 変更種別 | breaking` の3列）。読む側 xddp-common SKILL.md:138-141（Resolve Affected Repos の FILTER_BY_SPO=true が「影響リポジトリ」を読む）と xddp-common/reviewer-checklists/SPEC.md:31（「CHD cross の影響リポジトリ」と照合する）。CHD のひな形に「影響リポジトリ」列が無いので、11-specs の AFFECTED_REPOS の追加条件と SPEC レビューの照合の拠り所が無い。確度 ✅（ひな形の表とプロシージャの文を読んだ。LLM が別の表（実装依存関係の消費リポジトリ）から読み替える可能性は 🔶）。
- verifier-agent:86-92・07-code:207-212・coder-agent:31 が読む「新規追加／変更／削除」は、06-design の「変更種別」列と矛盾しない（ひな形の例は「新規追加」だけ）。食い違いはなし。

## 6. 読んだファイルの一覧
- CC/skills/xddp-close/scripts/promote.py（全文）
- CC/skills/xddp-02-analysis/scripts/domain_refs.py（全文）
- CC/skills/xddp-11-specs/SKILL.md（全文）
- CC/skills/xddp-close/SKILL.md（全文）
- CC/skills/xddp-01-init/SKILL.md:95-214
- CC/skills/xddp-survey/SKILL.md:330-429
- CC/skills/xddp-05-arch/SKILL.md:100-130（と grep の該当行）
- CC/skills/xddp-06-design/SKILL.md:40-70, 95-164
- CC/skills/xddp-09-test/SKILL.md:28-60
- CC/skills/xddp-02-analysis/SKILL.md:30-60
- CC/skills/xddp-common/SKILL.md:120-150
- CC/skills/xddp-common/templates/project-rulebook-cross-template.md:50-66
- CC/skills/xddp-rules/code-knowledge-boundary.md:85-110
- CC/skills/xddp-11-specs/templates/11_system-use-case-description-template.md:1-40
- CC/skills/xddp-11-specs/templates/11_cross-interface-spec-template.md:1-15
- CC/agents/xddp-specs-uc-agent.md:50-75
- CC/agents/xddp-specs-mod-agent.md:45-64, 150-161（と tail）
- CC/agents/xddp-verifier-agent.md:84-92
- CC/skills/xddp-07-code/SKILL.md:204-212
- CC/skills/xddp-02-analysis/scripts/tests/test_domain_refs.py:140-225
- docs/adr/ADR-0033-constraints-module-key.md:45-85
- docs/adr/ADR-0005-knowledge-guide-once.md（全文）
- 上のほか、grep の該当行だけ見たファイル: coder-agent、designer-agent、test-writer-agent、xddp-08-verify、10-test-run、analyst-agent、close-knowledge-agent、survey-promote-agent、reviewer-checklists/SPEC.md、test_promote.py

## 確認していないこと
- スクリプト・テストの実行による再現（指摘はすべてコードを読んだ結果）
- CC/agents/xddp-close-knowledge-agent.md・xddp-survey-promote-agent.md の全文（AI_INDEX を書かないことは grep で確認しただけ）
- test_promote.py の全文（grep の該当行だけ）
- 05-arch・06-design・09-test の Step 0 以外の節
- 04-specout の `modules/` のディレクトリ名がケバブ形式かどうか（指摘#8 の前提。確認していません）
- xddp-status・xddp-abort・xddp-update-knowledge が AI_INDEX に触れるか（`AI_INDEX` の grep には出なかったので、触れていないと判断した）
- `.claude/` 以外の README.md・CLAUDE.md の記述と実装との整合
