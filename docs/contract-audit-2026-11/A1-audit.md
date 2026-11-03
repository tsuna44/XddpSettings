# 監査者 A1 の報告（原文。PLAN-20261103-contract-audit 段階2a）

> 監査者の最終報告をそのまま載せたもの（検証前）。検証結果と統合後の重大度は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。パスの `{W}` は監査用の worktree（ecb54c4。セッションのスクラッチのディレクトリに作り、監査の後に削除）。

# A1 code-knowledge 約束の監査 報告（ecb54c4）

パスは `{W}` からの相対パスです。`CC/` は `ClaudeCode/.claude/` の略です。行番号は ecb54c4 の値です。スクリプト・テストは実行していません。

## 1. 確認した約束の一覧

見つけた方法の略記:
- S1 = `grep -rlE 'code-knowledge' CC/skills CC/agents | grep -v /tests/`
- S2 = `grep -rlE 'DOMAIN_REF' …`
- S3 = `grep -rln 'CK-\|constraints\.md\|code-knowledge\|knowledge_place' CC | grep -v /tests/`

| # | 約束 | 書く側 | 読む側 | 見つけた方法 | 結果 |
|---|---|---|---|---|---|
| 1 | `{KNOW}`／`{XKNOW}` の略記の定義 | `CC/skills/xddp-rules/code-knowledge-boundary.md:73-74` | close-knowledge-agent:14-15、survey-promote-agent:14-15、update-knowledge SKILL:37-38（「## 宛先ルーティング表」を apply する） | 書く側・読む側とも S1 | なし |
| 2 | 制約の出力パス `{KNOW}/{MODULE}/constraints.md` | boundary:78,138 | close-agent:85、survey-promote-agent:39-40、update-knowledge:174,185 | S1 | なし |
| 3 | constraints.md の節の名前（3節） | boundary:78、`CC/skills/xddp-close/templates/code-knowledge-constraints-template.md:5,13,20` | close-agent:96,102,109,120 | S1／テンプレートは boundary:78 の参照をたどった | なし |
| 4 | constraints.md のエントリの書式（`[CK-NNN]`・`**対象:**`・`**出典:**`） | constraints テンプレート:7-25 | module-documentation.md:181（`**対象:**`、無ければ内容）・185-188（`[CK-NNN]`） | boundary:78 の参照をたどった／S3 | **あり A1-6** |
| 5 | 「対象」には拾った表記をすべて書く | boundary:120、close-agent:86、survey-promote:46 | module-documentation.md:181 | S1 | **あり A1-6** |
| 6 | upsert の鍵（survey の昇格） | survey-promote-agent:59-60,63 | 同じファイル（読み書きとも同じ constraints.md） | S1 | **あり A1-1** |
| 7 | upsert の鍵（手での登録） | update-knowledge:53,187-188 | 同上 | S1 | **あり A1-2** |
| 8 | upsert の鍵（クローズ。SPO §5.6・LL） | close-agent:85,96、テンプレート:3 | 同上 | S1 | **あり A1-3** |
| 9 | upsert の鍵（クローズ。TRS の NG） | close-agent:119-127 | 同上 | S1 | **あり A1-4** |
| 10 | 出典の書式 `CR-{CR_NUMBER} / NG-…` | close-agent:119,127 | テンプレート:11、spec-writer-agent:46（CR 番号の形） | S1／`grep -rn 'CR-{CR'` | **あり A1-5** |
| 11 | `place` の入力 JSON（id・targets・fallback） | close-agent:81-82、survey-promote:43-45、survey SKILL:265-267、update-knowledge:156-161 | `knowledge_place.py:215-229` | S3 | なし（エスケープの件は A1-17） |
| 12 | `place` の出力（module・status・reserved_collision）と終了コード | `knowledge_place.py:198-212,279-292`、boundary:113-117 | close-agent:83-89、survey-promote:46-47,68-70、survey SKILL:268-271、update-knowledge:162-167 | S3 | なし |
| 13 | 人に示すもの（placed 以外・collision・失敗） | boundary:118-119 | close-agent:87-89,215-217 → close SKILL:381-382、survey-promote:68-70 → survey SKILL:287,420、update-knowledge:162-167 | 書く側 S1／読む側は close-agent:25 と survey SKILL:287 をたどった | なし |
| 14 | `--repo-root` に渡す値（ワークスペースからの相対パス） | close-agent:82（`REPOS_MAP[repo]`）、survey SKILL:36（`REPO_PATH`=`REPOS_MAP`） | `knowledge_place.py:201-202,286-287`（ワークスペースからの相対として解決する） | S3 | なし |
| 15 | 予約名と列挙で除く第1要素 | boundary:121,130 | `knowledge_place.py:40-42,252` | S3 | なし |
| 16 | 読む側の「当てはまる置き場所」（`_general`・`_root`・祖先） | boundary:125-128 | `knowledge_place.py:258-271`、module-documentation.md:179-180、prelim-agent:168-169 | S3 | なし |
| 17 | 列挙（`list_places`） | boundary:130-132 | `knowledge_place.py:237-255`、`domain_refs.py:370`、prelim-agent:167 | S3 | なし |
| 18 | 下調べ・追加下調べ・依頼調査への `DOCS` の渡し方 | xddp-04-specout SKILL:256、specout-finish.md:79、investigate SKILL:172-174 | prelim-agent:31,68,105,167-170 | `grep -rn xddp-specout-prelim-agent CC/skills` | なし |
| 19 | `KNOWN_CONSTRAINTS` のキー（＝置き場所） | prelim-agent:167-170 | module-documentation.md:177-189 | S1 | なし |
| 20 | 制約照合の表の5列 | module-documentation.md:76-77 | summary テンプレート:267、document-agent:96-99 | S1 | なし |
| 21 | survey の「ディレクトリ」欄 → `MODULE_FALLBACK` | survey-agent:45-47、module テンプレート:17 | survey SKILL:261-271 | survey SKILL:261 からたどった | なし |
| 22 | survey の節番号（2.1/2.4/2.5/2.6/4.2/4.3/4.5） | module テンプレート:25,47,58,68,106,123,145（survey-agent:36 が全節を使う） | survey SKILL:248-254、survey-promote:39-57 | survey SKILL:247 からたどった | なし（topic の扱いは A1-15） |
| 23 | survey の昇格先パスの定義場所（単一情報源） | boundary:53-55 | survey SKILL:248-254、survey-promote:40-56 | S1 | **あり A1-14** |
| 24 | flow／callgraph のパスとテンプレートの定義場所 | boundary:81-83 | update-knowledge:193-204 | S1 | **あり A1-13** |
| 25 | callgraph のファイル名のベース | boundary:83 | update-knowledge:67-69,200-201、callgraph テンプレート:7 | S1 | **あり A1-12** |
| 26 | SPO §5.6 の列（ファイル/識別子・影響度） | summary テンプレート:236,254 | close-agent:79,95 | close-agent:93 からたどった | なし |
| 27 | SPO §3・§4.2・§4.5 の見出し・表の名前 | summary テンプレート:47,79,139,152,159 | close-agent:129-171 | close-agent からたどった | なし |
| 28 | SPO §4.5 共有定数の列 → `_constants` テンプレートの列 | summary テンプレート:154-156 | constants テンプレート:5-7 | close-agent:163 からたどった | **あり A1-9** |
| 29 | cross SPO の §3・§5・§6 の見出し | cross-repo テンプレート:35,77,88 | close-agent:173-195 | close-agent:175 からたどった | なし |
| 30 | TRS の NG の書式（`## 3. NG詳細`・`### NG-`・原因分析） | `CC/skills/xddp-10-test-run/templates/10_test-results-template.md:34,36,46` | close-agent:113-118 | `grep -rln 'NG詳細'` | なし（鍵は A1-4） |
| 31 | LL の `**repo：**` 欄とタグ | close SKILL:117-119、lessons-learned テンプレート:17,20 | close-agent:100,106,111 | `grep -rn '#リスク'` | なし |
| 32 | knowledge agent への入力（`CR_LESSONS_FILE`・`TRS_PATTERN`・`OUTPUT_FILE`・`REPOS_MAP`） | close SKILL:312-327 | close-agent:21-25 | close SKILL:312 | なし |
| 33 | PENDING-KNOWLEDGE の3節 → Step D での提示 | close-agent:201-218 | close SKILL:331-332,378-382 | close SKILL:331 | **あり A1-10** |
| 34 | `_domain名要確認一覧` に載せるもの | close-agent:156,170,197-199 | close SKILL:378-379 | 同上 | **あり A1-11** |
| 35 | `DOMAIN_REF_PATHS` の形（`{abs} \| {種別}` を ` ; ` で連結） | `domain_refs.py:415`、02-analysis SKILL:54,109,216,245 | analyst-agent:26-28,76-78 | S2 | なし |
| 36 | `DOMAIN_REF_PATHS` の要素が「ファイル」であること | `domain_refs.py:304-311` | analyst-agent:26,77-78 | S2 | **あり A1-7** |
| 37 | `DOMAIN_REF_MODE` の語彙（normal/degraded/none）と未指定時の意味 | `domain_refs.py:418-423` | analyst-agent:24-28,94,156-159、`artifact_lint.py:546-612` | S2 | なし |
| 38 | 種別の語彙（制約・共有構造体・共有定数・用語 等） | `domain_refs.py:35-38,269,290,317,372,375` | analyst-agent:84-86、ANA テンプレート:13-15 | S2 | なし |
| 39 | 制約の集め方（直接列挙・最後の要素・祖先・`_general`・`_root`） | `domain_refs.py:168-188,367-372` | ADR-0033:51-53（約束の根拠） | S2 | なし |
| 40 | `_structures`／`_constants` の集め方 | `domain_refs.py:292-311` | analyst-agent:84 | S2 | **あり A1-8**（ラベルの件は担当外 A2） |
| 41 | `specout_bfs.py status` の `confirmed_modules`（code-knowledge の参照用） | `specout_bfs.py:2989-2994` | なし | S3 | **あり A1-16** |

## 2. 時期の約束の表

| 書く側（スキル・Step） | 読む側（スキル・Step） | 順序の根拠（ファイル:行） | 結果 |
|---|---|---|---|
| close `promote.py extract-ll`（Step C2 の前） | close-knowledge-agent C3.5／C3.6（`CR_LESSONS_FILE`） | close SKILL:284（extract-ll）→ 310-324（agent） | なし |
| 工程10 の TRS（`TRS-{CR}-{RUN}.md`） | close C3.6 | xddp-10-test-run SKILL:104 が書き、クローズが後で読む。CR 内の順序 | なし |
| 工程4a の SPO §3・§4.2・§4.5・§5.6 | close C3.6 | 同上 | なし |
| close C3.6（constraints・`_structures`・`_constants`・`_flows`） | 次の CR の工程2 Step 0（`domain_refs.py`）・工程4a の下調べ | CR をまたぐ。制約は直接列挙（domain_refs.py:367-372、prelim:167） | 制約はなし |
| close Step C2〜C7（AI_INDEX の更新） → C3.6（code-knowledge を書く） | 工程2（`_structures`／`_constants` は AI_INDEX のラベルを経由） | close SKILL:278 → 310。ADR-0033:80 | **あり A1-8**（初回のクローズで作った `_constants` は次のクローズまで工程2 に届かない） |
| survey Step 5・update-knowledge Step 3（随時） | 工程2・工程4a | 随時。制約は直接列挙されるのですぐ届く。`_structures`／`_constants` は AI_INDEX が更新されるまで届かない | **あり A1-8** |
| survey Step 5 の `MODULE_FALLBACK` の決定 | survey-promote-agent | survey SKILL:261-272 → 274-285 | なし |
| update-knowledge Step 1.5（置き場所） | Step 2（プレビュー）・Step 3（書き込み） | update-knowledge:152 → 171 → 179 | なし |
| 02-analysis Step 0（domain_refs） | Step A／A-profile／B（analyst） | 02-analysis SKILL:22-58 → 100-109,205-216,225-245 | なし |
| prelim の `KNOWN_CONSTRAINTS` の用意 | 観察 f | prelim-agent:167-170 → 175 | なし |

## 3. 指摘

### A1-1 survey の昇格：§2.6 の制約どうしが互いに置き換わる
- **約束:** constraints.md の upsert の鍵
- **書く側:** `CC/agents/xddp-survey-promote-agent.md:59-60`（「constraints.md は同一出典があれば置換」）、`:63`（出典 = `SURVEY-{TODAY}`）
- **読む側:** 同じ constraints.md を次に書くとき（同じ節）
- **食い違い:** 1回の昇格のすべての §2.6 の項目が同じ出典を持ちます。同じ `{MODULE}` に入る2件目以降は、前の項目を置き換えます（`[CK-NNN]` は増えません）。同じ日の別の survey の昇格とも衝突します。
- **起きること:** survey の knowledge 昇格で、同じ置き場所の制約が最後の1件しか残りません。知見が黙って失われます。module スコープの §2.6 は `MODULE_FALLBACK`（モジュールのディレクトリ）に集まりやすいので、よく起きます。
- **確度:** ✅ 文面どおり（survey-promote:59-60,63）。ADR-0033:82-83 は「既存の問題…別途扱う」と記録しています（受け入れた制限としては書かれていません）。
- **重大度の案:** 🔴
- **修正案（任意）:** 鍵を `[CK-NNN]`＋項目の同一性（タイトル等）にし、出典は鍵にしない。

### A1-2 手での登録：同じ出典の別の制約を置き換える
- **書く側／読む側:** `CC/skills/xddp-update-knowledge/SKILL.md:187-188`（「if same 出典 exists → replace entry」）。出典の例は `:53`（`manual/2026-07-04`）。
- **食い違い:** 例にならって同じ日に同じ置き場所へ2件目を登録すると、1件目を置き換えます。Step 2 のプレビュー（`:173-175`）は置き換えを示しません。
- **起きること:** 人が登録した制約が黙って消えます。ADR-0033:82 は survey と SPO §5.6 だけを挙げ、この経路を挙げていません。
- **確度:** ✅（文面）
- **重大度の案:** 🟡（同じ出典の文字列を入れた場合だけ起きる）

### A1-3 クローズ：SPO §5.6・LL 由来の制約に upsert の鍵が無い
- **書く側:** `CC/agents/xddp-close-knowledge-agent.md:85`（「upsert する」）、`:96`（出典 `{CR_NUMBER}`）。LL 由来の出典は書いていません。
- **読む側:** テンプレート:3（「[CK-NNN] で識別」）
- **食い違い:** 鍵を定めているのは TRS（`:122-126`）だけです。SPO §5.6・LL の知見は元の文書に `[CK-NNN]` を持たないので、同一性の判断は LLM に任されます。ADR-0033:82 は、鍵が「同一出典 `{CR_NUMBER}`」になっているとしています。その解釈で動けば、同じ CR の §5.6 の複数の行が互いに置き換わります。
- **確度:** 🔶（LLM の解釈次第）
- **重大度の案:** 🟡

### A1-4 クローズ：TRS の upsert の鍵に TRS ファイル（実行回）・repo が入っていない
- **書く側:** close-agent:119（`UPSERT_KEY` = `CR-{CR_NUMBER} / NG-{NNN}`）、`:113-114`（`TRS_PATTERN` に一致するすべての TRS を処理する）
- **読む側:** 同じ constraints.md
- **食い違い:** TRS は実行回ごとのファイルです（`TRS-{CR}-{RUN_NO}.md`。xddp-10-test-run SKILL:104）。テンプレートは NG を `NG-001` から振ります（TRS テンプレート:36）。回をまたいだ連番の指示は見当たりません（test-runner-agent:27-28）。1回目の `NG-001`（不具合A）と2回目の `NG-001`（不具合B）が同じ置き場所に入ると、後のほうが前を置き換えます。
- **起きること:** 不具合由来の制約が黙って失われます。
- **確度:** 🔶（NG の採番が回ごとか、回をまたぐかは指示が無く、テンプレートからの推論です）
- **重大度の案:** 🟡

### A1-5 出典の `CR-{CR_NUMBER}` で接頭辞が二重になる
- **書く側:** close-agent:119,127（例は `CR-2026-002 / NG-001`）
- **読む側:** 出典の書式 `CR-NNN`（テンプレート:11）。CR 番号の形は spec-writer-agent:46 の例 `CR-2026-970-UR-001`（CR_NUMBER = `CR-2026-970`）。
- **食い違い:** CR フォルダ名が `CR-…` で始まる慣習では `CR-CR-2026-970 / NG-001` になります。同じエージェントの §5.6 の出典（`:96`）は `{CR_NUMBER}` で、書式が揃いません。
- **起きること:** 出典の表記が不揃いになります。鍵は自分の書いたものと照合するので、upsert は動きます。
- **確度:** 🔶（CR フォルダの命名次第。xddp-common SKILL:46-52 はフォルダ名をそのまま CR にします）
- **重大度の案:** 🔵

### A1-6 「対象」を書く約束とテンプレートの節が合わない
- **書く側:** boundary:120、close-agent:86、survey-promote:46（「内容の『対象』に拾った対象の表記をすべて書く」）
- **読む側:** constraints テンプレート:13-25（「仕様上の暗黙の前提」「パフォーマンス・非機能特性」の節には `**対象:**` 欄がありません）、module-documentation.md:181（`**対象:**` が無ければ内容で照合する）
- **食い違い:** SPO §5.6 由来（パフォーマンスの節）と LL `#仕様定義` 由来（暗黙の前提の節）の制約では、テンプレートどおりに書くと「ファイル/識別子」が欄として残りません。
- **起きること:** 工程4a の観察 f は内容の文章で照合するしかなくなります。関係を確かめにくくなり、「照合せず」に回りやすくなります。
- **確度:** ✅（両側の文面）。影響の程度は 🔶。
- **重大度の案:** 🟡
- **修正案（任意）:** 3つの節すべてに `**対象:**` を置く。

### A1-7 `DOMAIN_REF_PATHS` にディレクトリが入る
- **書く側:** `CC/skills/xddp-02-analysis/scripts/domain_refs.py:308-311`（`col.add(special_path, …)` の `special_path` は `code-knowledge/_structures`・`_constants` のディレクトリ）
- **読む側:** `CC/agents/xddp-analyst-agent.md:26`（「参照先ファイルの**絶対パス**一覧」）、`:77-78`（各パスを Read し、開けなければ §0 に失敗を記録する）
- **食い違い:** 渡す側はファイルを約束していますが、ディレクトリを渡しています。
- **起きること:** ANA §0 に「読み取り失敗」の行が出て、共有定数（と構造体）の知見が工程2 で使われません。テストも見当たりません（`test_domain_refs.py` に `_structures`・`_constants` の検査はありません）。
- **確度:** ✅（両側の文面。エージェントが Glob で補うかは 🔶）
- **重大度の案:** 🟡

### A1-8 `_structures`／`_constants` だけが AI_INDEX のラベルを経由して集められる
- **書く側（knowledge）:** close C3.6、survey Step 5、update-knowledge
- **読む側:** `domain_refs.py:292-311`（AI_INDEX があり、ラベルの行がある場合だけ集める）。AI_INDEX が無い経路（`:334-365`）では集めません。制約だけは直接列挙です（`:367-372`）。
- **食い違い:** ADR-0033:51 が制約を直接列挙にした理由（「AI_INDEX を更新するのはクローズだけ…AI_INDEX の有無で結果が変わる」）が、`_structures`・`_constants` にもそのまま当てはまります。しかもクローズでは AI_INDEX の更新（close SKILL:278）が C3.6（`:310`）より先に走ります。
- **起きること:** 次の場合に、`_structures`・`_constants` の知見が工程2 に届きません。
  - 初回のクローズで作った `_constants`
  - survey・手で登録したもの（次のクローズまで）
  - AI_INDEX が無い環境（常に）
- **確度:** ✅
- **重大度の案:** 🟡

### A1-9 SPO §4.5 の共有定数の列と `_constants` テンプレートの列が合わない
- **書く側の元:** summary テンプレート:154-156（`定義モジュール`）
- **読む側（書き出し先）:** constants テンプレート:5-7（`定義場所` = `{ファイルパス:行}`）
- **起きること:** クローズの昇格で「定義場所」にモジュール名が入るか、空になります。survey 由来（module テンプレート:53 の `定義場所（ファイル:行）`）とは中身が揃いません。
- **確度:** ✅
- **重大度の案:** 🔵

### A1-10 「## 昇格見送り一覧」を Step D で示さない
- **書く側:** close-agent:143-144,160-161,184-185,211-213
- **読む側:** close SKILL:331-332（`KNOWLEDGE_RESULT` に保持する）、`:378-382`（示すのはドメイン名と置き場所の2つだけ）
- **起きること:** 見送った DFD・callgraph・構造の一覧は PENDING ファイルに残りますが、人に提示されません。
- **確度:** ✅
- **重大度の案:** 🔵

### A1-11 `_domain名要確認一覧` に載せる対象が一部だけ
- **書く側:** close-agent:156（callgraph）・`:170`（per-repo の定数）だけが明示的に「Add」しています。シーケンス（`:129-134`）・DFD（`:136-141`）・cross の定数・構造・シーケンス（`:173-195`）には指示がありません。
- **読む側:** `:197-199`（「_flows/ 昇格時…OUTPUT_FILE に暫定ドメイン名を記録する」）、close SKILL:378（_flows/_constants/_structures）
- **起きること:** 暫定のドメイン名 `shared` で作った sequence・dfd・relations のファイルが、人の命名確認から漏れる可能性があります。
- **確度:** 🔶
- **重大度の案:** 🔵

### A1-12 update-knowledge の callgraph：「フロー名（ファイル名のベース）」がファイル名に使われない
- **書く側:** update-knowledge:69（入力を求める）
- **読む側:** `:200-201`（ファイル名は `{DOMAIN}-{VAR_NAME}`）、boundary:83
- **起きること:** 人が指定したつもりの名前と違うファイル名になります。
- **確度:** ✅
- **重大度の案:** 🔵

### A1-13 update-knowledge が flow・callgraph のパスとテンプレートを自分で定義している
- **書く側（規約）:** boundary:53-55（ルーティング表以外に定義しない）
- **読む側:** update-knowledge:193-197,201-204
- **食い違い:** 今は値が一致しているので、動作への影響はありません。単一情報源の規則に反しています。
- **確度:** ✅
- **重大度の案:** 🔵

### A1-14 survey が昇格先のパスを自分で定義している
- **該当箇所:** survey SKILL:248-254（昇格先の表）、survey-promote:40-56
- **食い違い:** A1-13 と同じです（boundary:53-55）。
- **確度:** ✅
- **重大度の案:** 🔵

### A1-15 survey の topic スコープで §2.6 の昇格は「発生しない」という記述が誤り
- **該当箇所:** survey SKILL:272
- **食い違い:** topic の SURVEY もテンプレートの全節（§2.6 を含む）を使います（survey-agent:36-37,52-55）。昇格の表も §2.6 を「常に」とします（survey SKILL:252）。
- **起きること:** 動作は `_general` を fallback にして正しく進みます。記述だけが不整合です。
- **確度:** ✅
- **重大度の案:** 🔵

### A1-16 `specout_bfs.py status` の `confirmed_modules` に読む側が無い
- **書く側:** `CC/skills/xddp-04-specout/scripts/specout_bfs.py:2989-2994`（code-knowledge の参照用と注記）。値は第1階層のディレクトリと `_root` です（`:1397-1411`）。
- **読む側:** S3 と `grep -rn confirmed_modules` の範囲では見つかりません。
- **食い違い:** 廃止された置き場所の規則（第1階層）で値を出し続けています。将来誰かが読むと、ADR-0033 の規則と食い違います。
- **確度:** ✅（読む側が無いこと）
- **重大度の案:** 🔵

### A1-17 ヒアドキュメントに人の入力をそのまま JSON 文字列として埋め込む
- **書く側:** update-knowledge:158-160、survey SKILL:265-267
- **読む側:** `knowledge_place.py:281-285`（JSON の誤りは exit 2）
- **食い違い:** スクリプトは `\` を `/` に揃えます（`:57-58`、ADR-0033:34）。しかし `src\auth\x.c` や `"` を含む入力は、JSON として壊れて、スクリプトに届く前に exit 2 になります。
- **起きること:**
  - update-knowledge では stderr を示して停止します（人が気付けます）。
  - survey の「ディレクトリ」欄では `MODULE_FALLBACK` が `_general` になります。
- **確度:** 🔶（LLM がエスケープするかに依存します）
- **重大度の案:** 🔵

## 4. 担当外の指摘

### 担当外（A2）：AI_INDEX の構造体のラベルの食い違い
- **書く側:** `CC/skills/xddp-close/scripts/promote.py:601`（`{repo} 構造体関連図`）
- **読む側:** `domain_refs.py:35-37,305-307`（`{repo} 共有構造体` を探す。`:34` のコメントは「promote.py と同一の対応」と書いています）
- **起きること:** `_structures` は工程2 の参照先に決して入りません（A1-7・A1-8 とは別に直せる原因です）。
- **確度:** ✅
- **重大度の案:** 🟡

## 5. 段階2b の候補

なし。SPO §5.7 の転記（document-agent:96-101）とアーキテクトの読み方（architect-agent:143-145,197-200）は整合していました。

## 6. 読んだファイルの一覧と確認していないこと

### 全文を読んだもの
- `CC/skills/xddp-rules/code-knowledge-boundary.md`
- `CC/skills/xddp-common/scripts/knowledge_place.py`
- `CC/agents/xddp-close-knowledge-agent.md`
- `CC/agents/xddp-survey-promote-agent.md`
- `CC/skills/xddp-update-knowledge/SKILL.md`
- `CC/skills/xddp-02-analysis/scripts/domain_refs.py`
- `docs/adr/ADR-0033-constraints-module-key.md`
- `CC/skills/xddp-close/templates/code-knowledge-*.md`（5件）
- `CC/skills/xddp-update-knowledge/templates/*.md`（3件）

### 範囲を読んだもの
- `CC/skills/xddp-survey/SKILL.md`: 40-60, 220-292, 405-434
- `CC/agents/xddp-survey-agent.md`: 30-62
- `CC/skills/xddp-04-specout/templates/04_specout-module-template.md`: 1-75 と見出し
- `CC/agents/xddp-specout-prelim-agent.md`: 20-40, 60-70, 100-108, 160-180
- `CC/skills/xddp-04-specout/module-documentation.md`: 60-90, 170-195, 395-406
- `CC/skills/xddp-04-specout/SKILL.md`: 240-275
- `CC/skills/xddp-common/procedures/specout-finish.md`: 66-100
- `CC/skills/xddp-investigate/SKILL.md`: 165-185
- `CC/skills/xddp-02-analysis/SKILL.md`: 22-112, 205-248
- `CC/agents/xddp-analyst-agent.md`: 20-32, 72-96, 153-170
- `CC/skills/xddp-02-analysis/templates/02_req-analysis-memo-template.md`: 1-40
- `CC/skills/xddp-04-specout/templates/04_specout-summary-template.md`: 140-170, 244-272 と見出し
- `CC/agents/xddp-specout-document-agent.md`: 64-72, 92-102
- `CC/agents/xddp-architect-agent.md`: 140-146, 195-201
- `CC/skills/xddp-close/SKILL.md`: 110-135, 278-396
- `CC/skills/xddp-close/scripts/promote.py`: 580-610
- `CC/skills/xddp-common/SKILL.md`: 42-75, 120-144
- `CC/skills/xddp-04-specout/templates/04_specout-cross-repo-template.md`: 見出し
- `CC/skills/xddp-10-test-run/templates/10_test-results-template.md`: 30-52
- `CC/skills/xddp-close/templates/lessons-learned-template.md`: 14-22
- `CC/skills/xddp-04-specout/scripts/specout_bfs.py`: 1397-1412, 2985-2995
- `CC/skills/xddp-11-specs/SKILL.md`: 50-62
- `CC/skills/xddp-common/scripts/artifact_lint.py`: grep の結果の行のみ

### grep の結果だけを見たもの
`test_domain_refs.py`、test-runner-agent、xddp-10-test-run SKILL、spec-writer-agent、README.md

### 確認していないこと
- Write ツールが、入れ子の `{KNOW}/{MODULE}/` の親ディレクトリを自動で作るか。close-knowledge-agent・survey-promote-agent は、Bash の `mkdir` を制約のディレクトリには使わない規定です（close-agent:17、survey-promote:17）。
- 工程10 の NG 番号が、実際に回ごとか回をまたいだ連番か（A1-4）。
- Glob の `**/constraints.md` が、`{KNOW}` 直下に一致するかを含む実際の挙動。
- `xddp-investigate` の依頼調査の入力のうち、上記の範囲より外。
- `promote.py` の AI_INDEX の他の節（A2 の担当）。
- 参考（食い違いではありません）:
  - cross の `{XKNOW}`（`_structures`・`_constants`・`_flows`）は close が書きますが、AI_INDEX の行（promote.py:592）を除き、工程2・工程4a の自動の読む側は見つかりませんでした。
  - 予約名 `_cochange` を書く側は見つかりませんでした（boundary:121、`knowledge_place.py:40-42`）。
