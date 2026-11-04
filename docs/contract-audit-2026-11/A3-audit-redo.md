# 監査者 A3 の報告（やり直し版・原文。PLAN-20261103-contract-audit 段階2a）

> 抜き取り確認の漏れを受けた人の判断で行ったやり直しの監査の最終報告をそのまま載せたもの（検証前）。前回の版は [A3-audit.md](A3-audit.md)。検証結果と統合後の重大度は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。

# A3 知見ログ・バックログ 監査報告（やり直し。前回の A3.md を置き換える）

対象 ecb54c4。`{W}` = audit-ecb54c4、`CC/` = `ClaudeCode/.claude/`。行番号は ecb54c4 の値。スクリプトとテストは実行していない（✅ は「両側を読んで確認した」）。

## 0. 使った探し方（「見つけた方法」の列の略号。範囲はすべて `CC/skills CC/agents`、tests を含めて検索し、テストは参考扱い）
- **S1**（種類1 パス）`grep -rn 'lessons-learned'`
- **S2**（種類3・4 変数・書式）`grep -rnE '知見ログ|LESSONS_FILE|LL-\{|LL-[0-9N]|lessons_learned|lessons|LL_ENTRY|extract.ll|CR_LESSONS'`（lessons-learned を除く）
- **S3**（種類1）`grep -rnE 'improvement-backlog|INSIGHTS'`
- **S4**（種類3・4）`grep -rnE 'バックログ|IDEA-|IDEA|backlog'`
- **S5**（種類2 節名）`grep -rnE '気づき・提案メモ'` と `grep -rnE '気づき'`
- **S6**（種類2・3）`grep -rnE '破壊的変更警告|append_breaking_warning|breaking_warning|タグ別インデックス|知見詳細|エントリ一覧|要確認LL|要確認 LL|pending-items'`
- **S7**（種類3）`grep -rn 'LESSONS'`
- **S8**（種類1・4）成果物パスの集計 `grep -rnoE '(02_analysis|…|10_test-results)/[^ ]*(ANA|CRS|SPO|DSN|CHD|CODING|VERIFY|TSP|TRS)-\{?CR[^ ]*\.md'`
- **S9**（種類1・4）`grep -rnE 'LL-\{CR|INSIGHTS-|PENDING-PROMOTE|improvement-backlog|lessons-learned-archive'`
- **S10**（種類2）`grep -rn 'UR別ファイル一覧'`
- **S11**（種類2）`grep -rn 'CR クローズ'`
- **S12**（種類1）テンプレートの参照 `grep -rn '10_test-results-template|09_test-specification-template|02_req-analysis-memo-template|03_change-req-spec-template|06_change-design-document-template.md|04_specout-summary-template'`
- **S13**（種類1）`grep -rln 'improvement-backlog-template|lessons-learned-template' ClaudeCode tools`
- **S14**（種類2）`grep -rn 'ポリシー|Section 3-4'`（11-specs・SPEC.md・survey）
- **S15**（種類4）`grep -rnoE 'sequences/[^ ]*\.md|-seq\.md'`
- **S16**（種類3）`grep -rnE 'AUTO_NOTE_PREFIX'`、`grep -n 'global_errors'`
- **R**: 参照のたどり（参照元 ファイル:行 を併記）

## 前回からの変更
- **新しく足した約束:** #16b（破壊的変更警告のマーカー）・#16c（Layer 2 のヘッダーを作る側）・#23 を成果物ごとに分割（#23-1〜#23-15）・#38〜#52。
- **新しく見つけた書く側・読む側:**
  - #16・#16b・#16c の書く側 `promote.py:1081-1097,1200-1212`（`append_breaking_warning`）。前回の抜き取りで漏れていたもの。
  - #26 の書く側 `CC/skills/xddp-survey/SKILL.md:291-338`（(c) で `xddp-specs-mod-agent` が latest-specs を書く。気づき節のあるテンプレート）。
  - #23-9・#23-10・#23-11 の書く側 `CC/agents/xddp-coder-agent.md:47-56`・`CC/agents/xddp-verifier-agent.md:131-175`（気づき節を書かない）。
  - #42 の書く側・読む側 `promote.py:1117-1121,1216-1221` と close `SKILL.md:302-306,336-351`。
  - #45 の読む側 `CC/skills/xddp-common/reviewer-checklists/SPEC.md:28,39`、`CC/skills/xddp-11-specs/SKILL.md:374`、`CC/skills/xddp-survey/SKILL.md:351`。
  - #47 の読む側 `CC/skills/xddp-status/SKILL.md:106-108`。
  - #49 の読む側 `CC/agents/xddp-close-knowledge-agent.md:33-38,99-111`（タグ）。#50 の書く側 `xddp-designer-agent.md:55`。#51 の書く側 `xddp-analyst-agent.md:92`。
  - 参考扱いの読む側: `crs_model.py:190,361-364`・`crs_md2excel.py:340`（CRS §6 を読む。A3 の範囲外）。
- **新しい指摘:** A3-24〜A3-30（7件）。
- **取り下げた指摘:** 前回の「担当外（A2）」（AI_INDEX のタグ検索例）。理由は §4 に書く。A3 の番号つきの指摘で取り下げたものは無い。
- **番号を変えずに内容を直した指摘:**
  - A3-7: 範囲を広げた。`repos_keys` 全体を走査すること（V2 N2）と、survey の書く側を足した。
  - A3-14: 🔶 を ✅ に上げた。HTML コメントが残ることは `xddp-specout-prelim-agent.md:187` で決まっている。
  - A3-21: 観点の名前は括弧の中にある（V2 の「一部確認」）ことを反映した。
  - A3-2: アーカイブ後もタグ別インデックスに ID が残ることを補足した。

## 1. 確認した約束の一覧

| # | 約束 | 書く側（ファイル:行・節） | 読む側（ファイル:行・節） | 見つけた方法 | 結果 |
|---|---|---|---|---|---|
| 1 | Layer 1 のパス `{XDDP_DIR}/lessons-learned.md` | close SKILL.md:106（Step C） | 02 SKILL.md:71、05:145、06:96、09:81（Step A0）、close SKILL.md:284,299（`--lessons-file`） | 書く側 S1／S2。読む側 S1・S2・S7 | なし |
| 2 | LL の見出し `### LL-{NNN}：`（全角コロン） | close SKILL.md:117（Entry Format） | promote.py:661 `LL_ENTRY_RE`、load-lessons-context.md:28 `### {id}：`、close SKILL.md:150-151（`### LL-` を数える） | S2（`LL-\{`・`LL_ENTRY`）・S6（`知見詳細`）・R（SKILL.md:284→promote.py） | なし |
| 3 | LL のメタ行 `**CR：** … ／ **工程：** … ／ **repo：** … ／ **タグ：** …`（見出しから5行以内） | close SKILL.md:119 | promote.py:662-664,671,783-803；close-knowledge-agent.md:100,106,111；テスト test_promote.py:165 ほか（参考） | S2・S6（`要確認LL`）・R（SKILL.md:312→agent） | なし |
| 4 | LL の `repo` 欄の値の語彙（`{repo}`／`cross`／`unknown`） | close SKILL.md:119（例は `{repo名 or cross}` だけ）、134-137 | promote.py:884-897、close-knowledge-agent.md:63-65,111 | S2・S6・R | 食い違いあり A3-8、A3-9 |
| 5 | LL の採番（NNN）と Layer 2 の重複判定 | close SKILL.md:108（採番の規則なし）、update-knowledge SKILL.md:209 | promote.py:905-908 | S1・S2（`LL-[0-9N]`） | 食い違いあり A3-1、A3-2、A3-3 |
| 6 | Layer 1「エントリ一覧」表の列 `ID｜タイトル｜CR｜工程｜タグ`・`最終更新CR` | lessons-learned-template.md:10,24-29；close SKILL.md:139,160-161 | 人（構造的な読み手なし） | S1・S6（`エントリ一覧`） | なし |
| 7 | Layer 1「## タグ別インデックス」表（タグの行・カンマ区切りの ID・`—`） | template:33-56；close SKILL.md:141-148 | load-lessons-context.md:19-28 | S6（`タグ別インデックス`）・S1 | なし（区切りは #40） |
| 8 | TARGET_TAGS がタグ一覧にあること | 呼び出し側 02:72、05:146、06:97、09:82 | template:16-20,37-56 | S7・S2（`LESSONS_FILE`） | なし |
| 9 | エントリの置き場所 `## 知見詳細`（末尾追記） | template:60-62；close SKILL.md:106-139 | load-lessons-context.md:21,27 | S6（`知見詳細`）・R | なし |
| 10 | `LESSONS_CONTEXT` の Inputs の宣言と使い方 | 02 SKILL.md:107,214；05:232；06:213；09:136 | analyst-agent.md:18-35（無し）、architect-agent.md（無し）、designer-agent.md:52-58,80-84（あり）、test-writer-agent.md（無し） | S7・S2 | 食い違いあり A3-10、A3-11、A3-12 |
| 11 | `extract-ll` の出力パス `{CR_PATH}/pending-items/LL-{CR}.md` | close SKILL.md:284 | close SKILL.md:324、close-knowledge-agent.md:23,29 | S9（`LL-\{CR`）・S6（`pending-items`）・S2（`CR_LESSONS`） | なし |
| 12 | `extract-ll` の出力が無いことの意味（0件） | promote.py:830-863（書かない・前回を消す） | close-knowledge-agent.md:23,29,99,105 | S2・R | なし |
| 13 | `extract-ll` の stdout キー（`count`・`unparsed`・`dropped`） | promote.py:19-22,860-861,1242-1244 | close SKILL.md:290 | S2（`extract.ll`）・R | なし |
| 14 | `unparsed` の reason の語彙（heading／no-meta／multi-meta） | promote.py:786-803 | close SKILL.md:358 | S2・S6（`要確認 LL`） | なし |
| 15 | `dropped` の reason の語彙（cr-meta／cut） | promote.py:806-827 | close SKILL.md:366 | 同上 | なし |
| 16 | Layer 2 のパス `{DOCS}/{repo}/knowledge/lessons-learned.md`・`{DOCS}/cross/knowledge/lessons-learned.md` | promote.py:895-897（LL）、**promote.py:1203,1209（`append_breaking_warning`）**、update-knowledge SKILL.md:207、01-init SKILL.md:121,128 | domain_refs.py:315-321,361-365；説明のみ: close SKILL.md:101-103、code-knowledge-boundary.md:25、promote.py:343（A2） | S1・S2・S6（`append_breaking_warning`）・R | なし |
| 16b | 破壊的変更警告のマーカー `### 破壊的変更警告（{CR}）`（Layer 2 に足す） | promote.py:1081-1097 | promote.py:1085-1087（重複判定）、promote.py:905-907（`LL_ENTRY_RE` に当たらない）、LLM（domain_refs 経由） | S6・R（promote.py:1200） | なし |
| 16c | Layer 2 のファイルのヘッダーを作る側 | 01-init SKILL.md:204-213（repo だけ）、promote.py:901、update-knowledge SKILL.md:208、promote.py:1082-1088（ヘッダーなし） | 読み手 LLM | S2（`知見ログ`）・S6・S11 | 食い違いあり A3-17、A3-24 |
| 17 | Layer 2 の「エントリ一覧」表 | 01-init SKILL.md:204-213 | promote.py:899-917（更新しない）、update-knowledge SKILL.md:209 | S1・S6（`エントリ一覧`） | 食い違いあり A3-17 |
| 18 | Layer 2 の lesson エントリの書式（update-knowledge） | update-knowledge SKILL.md:76-85,206-209 | promote.py:905-908、LLM の読み手 | S1・S2 | 食い違いあり A3-18 |
| 19 | PENDING-PROMOTE の「## 要確認LL一覧（repo:unknown スキップ分）」 | promote.py:1124-1129 | close SKILL.md:303,355 | S9・S6 | なし |
| 20 | `INSIGHTS-{CR}.md` のパス | close SKILL.md:64（`--output-file`） | close SKILL.md:69 | S3・S9 | なし |
| 21 | INSIGHTS の「## 収集サマリ」「抽出エントリ数」 | collect_insights.py:337-341 | close SKILL.md:70 | S3・R | なし |
| 22 | 「気づき・提案メモ」見出しの文字列（番号・レベル不問） | 02 tpl:105、03 tpl:203、SPO tpl:307、05 comparison:65・approach:64、CHD tpl:228、09 tpl:137、10 tpl:59、11 tpl 8種（module-spec:104 ほか） | collect_insights.py:199-236 | S5・S12・R（SKILL.md:64） | なし |
| 23-1 | ANA `02_analysis/ANA-{CR}.md` | 02 SKILL.md:105 | collect_insights.py:138 | S8・S12 | なし |
| 23-2 | CRS `03_change-requirements/CRS-{CR}.md` | 03 SKILL.md:72、02 SKILL.md:133 | collect_insights.py:139 | S8・S12 | なし |
| 23-3 | SPO repo `04_specout/{repo}/SPO-{CR}.md` | 04 SKILL.md:259、specout-finish.md:83 | collect_insights.py:141-142 | S8・S12 | なし |
| 23-4 | SPO cross（テンプレートに節なし） | 04 SKILL.md:668（cross-repo tpl） | collect_insights.py:143-144 | S8・S5 | なし（節が無いので集める物も無い） |
| 23-5 | DSN comparison・approach-A/B/C | 05 SKILL.md:45-48,306-314；architect-agent.md:205-217 | collect_insights.py:146-148 | S8・S12 | なし |
| 23-6 | DSN cross（節なし）・DSN インデックス・rev（節なし） | 05 SKILL.md:157-168；05 index tpl（見出しに節なし） | collect_insights.py:149-150（インデックスは対象外） | S8・S5 | なし |
| 23-7 | CHD インデックスの「## 2. UR別ファイル一覧」とリンクの形 | CHD index tpl:21-27 | collect_insights.py:59-106（xddp-common SKILL.md:217 と同じ） | S10・R | なし |
| 23-8 | CHD 内容ファイル・CHD cross（cross は節なし） | CHD tpl:228；06 SKILL.md:111-130 | collect_insights.py:152-162 | S8・S12・S10 | なし |
| 23-9 | CODING `07_coding/CODING-{CR}-{repo}.md` の気づき節 | coder-agent.md:47-56（節を書かない） | collect_insights.py:3,164-165 | S8・R | 食い違いあり A3-25 |
| 23-10 | VERIFY repo の気づき節 | verifier-agent.md:131-175（節なし） | collect_insights.py:166-167 | S8・R | 食い違いあり A3-25 |
| 23-11 | VERIFY cross の気づき節 | 07 SKILL.md:204、08 SKILL.md:163（同じ書式） | collect_insights.py:168-169 | S8 | 食い違いあり A3-25 |
| 23-12 | TSP repo `09_test-spec/{repo}/TSP-{CR}.md` | 09 SKILL.md:93,133 | collect_insights.py:170-171 | S8・S12 | なし |
| 23-13 | TSP cross `09_test-spec/cross/TSP-{CR}-cross.md` | 09 SKILL.md:142-155 | collect_insights.py（列挙なし） | S8・S12 | 食い違いあり A3-5 |
| 23-14 | TRS repo・cross `10_test-results/{repo|cross}/TRS-{CR}-{RUN_NO}.md` | 10 SKILL.md:82（10 tpl:59） | collect_insights.py:173-177 | S8・S12 | なし |
| 23-15 | latest-specs の対象（repo・cross・system） | 11-specs、survey（#26） | collect_insights.py:179-184 | S8・S5 | A3-7 |
| 24 | approach-D 以降・2案以上の approach に節が無いこと | approach tpl:54-72、architect-agent.md:211-217 | collect_insights.py:147 | S5・R | なし |
| 25 | latest-specs の節なしファイル（schema・crud・dfd・`*-seq.md`） | 11 tpl（sequence:15-16、crud:17、dfd:15、schema:17）；名前は 11 SKILL.md:153-159、mod-agent.md:105-124 | collect_insights.py:113-126 | S5・S15 | なし |
| 26 | latest-specs の範囲（どの CR の行か） | 11-specs SKILL.md:135,183、11 tpl、**survey SKILL.md:291-338**、close SKILL.md:211-221（C0-3） | collect_insights.py:179-184,327-336 | S5・S1（survey は S5 の `気づき` から）・R | 食い違いあり A3-7 |
| 27 | progress.md の「## 気づき・提案メモ」 | 00_progress tpl:67-73；abort SKILL.md:96-107 | collect_insights.py（対象外） | S5・S4（`バックログ`） | 食い違いあり A3-6 |
| 28 | 空の節の表し方 | analyst-agent.md:41,65-66（「なし」）；specout_bfs.py:7625-7632；SPO tpl:308（HTML コメント）、prelim-agent.md:187 | collect_insights.py:203,239-257 | S5・S16 | 食い違いあり A3-13、A3-14 |
| 29 | 「対応方針」の語彙（今回対応／次回CR／保留／却下） | 全テンプレートの4列表；specout_bfs.py:7629（`保留`） | close SKILL.md:76 | S5・S4 | なし |
| 30 | IDEA のエントリの書式 | close SKILL.md:84-90 | backlog tpl:41-67 | S3・S4（`IDEA-`） | 食い違いあり A3-15 |
| 31 | バックログの表の更新 | close SKILL.md:92 | backlog tpl:16-34 | S4 | 食い違いあり A3-16 |
| 32 | `improvement-backlog.md` の昇格（Layer 1 → DOCS） | promote.py:1009-1015,1217-1221 | DOCS の利用者（スクリプト・スキルの読み手なし） | S3・S4（`backlog`） | 食い違いあり A3-4 |
| 33 | テンプレートの所在・管理場所の記述 | close SKILL.md:74,106；LL tpl:8 | 実体 CC/skills/xddp-close/templates/（setup.sh:93,96 だけが参照） | S1・S13 | 食い違いあり A3-19、A3-20 |
| 34 | LL の抽出の観点 | close SKILL.md:110-112 | — | S2・R | 食い違いあり A3-21 |
| 35 | 中止した CR の気づきを後で登録する経路 | abort SKILL.md:105-107 | update-knowledge SKILL.md:15,32 | S3・S5 | 食い違いあり A3-22 |
| 36 | Layer 1 の読み手の記述 | close SKILL.md:96-104 | 02/05/06/09 Step A0 | S2・S7 | 食い違いあり A3-23 |
| 37 | cross の LL を rulebook-cross へ（A5 の担当。振り分けの語彙だけ） | close-knowledge-agent.md:64 | — | S2・R | なし（A3-8 と関係） |
| 38 | LL の採番とアーカイブ後のタグ別インデックス | close SKILL.md:150-165 | load-lessons-context.md:23-28 | S9（`lessons-learned-archive`）・S6 | A3-2 に含む |
| 39 | 再実行時の Step B・C の追記と、同じ実行の中の昇格 | close SKILL.md:72-139 → 284 → 299 → 312 | promote.py:905-908 | S6・S9・R（SKILL.md:362,370） | 食い違いあり A3-29 |
| 40 | LL のタグの区切り | close SKILL.md:119（`{#タグ}`）、142；template:16-20；update-knowledge SKILL.md:79 | close SKILL.md:142-148、load-lessons-context.md:23-28 | S6（`タグ別インデックス`）・S2 | 食い違いあり A3-28 |
| 41 | `### 破壊的変更警告` の書き込みと Layer 2 のヘッダー | promote.py:1081-1097 | — | S6 | A3-24 |
| 42 | PENDING-PROMOTE の「共通ファイルの昇格エラー」（C7 backlog） | promote.py:1117-1121,1216-1221 | close SKILL.md:302-306,336-351,409 | S16（`global_errors`）・S9 | 食い違いあり A3-27 |
| 43 | SPO §9 の書き手の注記とスクリプトの保持 | SPO tpl:307-317；specout_bfs.py:4452,7625-7632；document-agent.md:94 | 人・collect_insights | S5・S16（`AUTO_NOTE_PREFIX`） | 食い違いあり A3-26 |
| 44 | latest-specs の気づき節の有無の規則（ポリシー） | 11 tpl の「このファイルには気づきメモセクションなし」 | SPEC.md:28,39；11 SKILL.md:374；survey SKILL.md:351 | S14・S5 | 食い違いあり A3-30 |
| 45 | close-knowledge-agent が読む LL のタグ（#リスク・#見落とし・#仕様定義・#方式検討 等） | template:16-20 | close-knowledge-agent.md:33-38,99-111 | S2・R | なし |
| 46 | designer が `#設計` の知見を CHD §8 に書く | designer-agent.md:55 | CHD tpl:228 → collect_insights | S5・S7 | なし |
| 47 | progress.md「## CR クローズ」の「改善バックログ追加」「知見ログ追加」行 | close SKILL.md:404-409 | xddp-status SKILL.md:106-108（読まないと明記） | S11・S2（`知見ログ`） | なし |
| 48 | analyst が ANA §7 に「用語集への追加候補」を書く | analyst-agent.md:92 | collect_insights | S5 | なし |
| 49 | abort が progress.md の表に追記する行の書式（`#` は既存行数+1） | abort SKILL.md:102-104 | 読み手なし（tpl:73 のプレースホルダー行も数える） | S5 | なし（読み手なし。A3-6 と関係） |
| 50 | run・extract-ll の stdout の残りのキー（`out`・`removed`・`backlog_promoted`・`unresolved_ll`） | promote.py:1229-1240,860-861 | close は使わない（出力ファイルを読む） | S2・S4 | なし |
| 51 | 参考: CRS §6 の4列表を Excel 変換が読む（A3 の範囲外） | 03 tpl:203-209 | crs_model.py:190,361-364、crs_md2excel.py:340 | S5 | なし |
| 52 | 説明のみ: xddp-11-specs SKILL.md:143「improvement-backlog に記録する」、02 SKILL.md:24-29、xddp-common SKILL.md:237 | — | — | S3・S2 | なし |

## 2. 時期の約束の表

| 書く側（スキル・Step） | 読む側（スキル・Step） | 順序の根拠（ファイル:行） | 結果 |
|---|---|---|---|
| 工程2〜11 の成果物（気づき・提案メモの節） | close Step A（collect_insights） | close SKILL.md:31（工程11 ✅ が前提）、11-specs SKILL.md:660 | なし |
| close Step A（INSIGHTS） | close Step B・C | SKILL.md:61-70 → 72 → 94 | なし |
| close Step B（Layer 1 backlog） | promote C7 `promote_backlog` | SKILL.md:72 → 299；promote.py:1217-1218 | なし |
| close Step C（Layer 1 LL） | `extract-ll` → promote C3 | SKILL.md:94 → 284 → 299；promote.py:1197 | なし |
| `extract-ll`（LL-{CR}.md） | C3.5/C3.6 knowledge agent | SKILL.md:284 → 312-327 | なし |
| promote C3（LL を Layer 2 に足す。ヘッダーを作る） | `append_breaking_warning`（同じファイル） | promote.py:1197 → 1200-1212 | なし（順序は正しい。cross は A3-24） |
| 再実行時の close Step B・C（追記の繰り返し） | 同じ実行の extract-ll・promote・knowledge agent | SKILL.md:362,370（重複は人が消すと案内）→ 284/299/312 は同じ実行で人の確認なしに続く | A3-29 |
| close Step C0-3（DOCS specs → latest-specs） | 次の CR の close Step A | SKILL.md:211-221 は Step A（61）の後 | A3-7 |
| survey (c)（latest-specs・DOCS specs、随時） | 次の CR の close Step A | survey SKILL.md:291-338,369-370。順序の保証なし | A3-7 |
| close（Layer 1） | 後の CR の 02/05/06/09 Step A0 | 別の CR。無ければ空（load-lessons-context.md:17） | なし |
| close C3（Layer 2） | 後の CR の 02 Step 0（domain_refs） | 別の CR。ファイルがあれば読む（domain_refs.py:233-236） | なし |
| update-knowledge（Layer 2、随時） | 後の close C3 の重複判定 | 順序の保証なし | A3-1 |
| abort Step 3（progress.md の気づき） | 読み手なし（close は工程11 ✅ が前提） | abort SKILL.md:105-107；close SKILL.md:31 | なし |

## 3. 指摘

### A3-1 Layer 2 の重複判定が ID だけで、update-knowledge が Layer 2 の中で別に採番する
- 約束: Layer 2 に足す LL の ID が、既にある LL と重ならないこと。
- 書く側: update-knowledge SKILL.md:206-209（Layer 2 の LL-NNN の次の番号）。Layer 1 の採番は close SKILL.md:108-117 で、Layer 2 と無関係に採る。
- 読む側: promote.py:905-908（`### {entry_id}：` が既にあれば足さない）。
- 食い違い: Layer 2 は Layer 1 の一部の写しなので、update-knowledge が採った番号を、後で Layer 1 が使いうる。
- 起きること: その CR の LL が Layer 2 に入らない。Step D の一覧にも出ない（黙って失われる）。工程2 の参照から抜ける。
- 確度: ✅（V2 が再現）。前提として、update-knowledge が `### LL-NNN：` で書く（書式は決まっていない。A3-18）。
- 重大度の案: 🔴
- 修正案（決めない）: 重複判定の鍵を (ID, CR) にする。または update-knowledge に別の接頭辞を使わせる。

### A3-2 Layer 1 の LL の採番規則が無い（アーカイブの後に番号が重なりうる）
- 書く側: close SKILL.md:108（採番の規則なし）、150-165（アーカイブで `### LL-` を移す。タグ別インデックスの ID は消さない：159-161）。
- 読む側: promote.py:905-908、load-lessons-context.md:23-28。
- 食い違い: アーカイブ後に件数や一覧から番号を採ると、Layer 2 の既存 ID と重なって昇格しない。インデックスに残った古い ID と新しいエントリが同じ ID になると、load-lessons が別のエントリを返す。
- 確度: ✅（規則が無いこと）／🔶（起きるか）
- 重大度の案: 🟡
- 修正案: 「Layer 1・アーカイブ・Layer 2 の最大の番号 + 1」を書く。アーカイブ手順にインデックスの更新を足す。

### A3-3 ワークスペースが別だと Layer 1 の番号が独立で、共有の Layer 2 で重なる
- 書く側: 各ワークスペースの close Step C（SKILL.md:106-117）。読む側: promote.py:905-908（共有 `{DOCS}`）。前提は close C0（SKILL.md:187-276）の `{DOCS}` の pull。
- 確度: ✅ 仕組み／🔶 運用（`{XDDP_DIR}` を共有するかは確認していません）。重大度の案: 🔴（条件つき）。修正案: A3-1 と同じ。

### A3-4 improvement-backlog.md を DOCS に丸ごと上書きする
- 書く側: promote.py:1009-1015（`shutil.copy2`）。読む側: DOCS の利用者。
- 起きること: 別のワークスペースから昇格すると、DOCS の backlog は最後にクローズした側だけになる。
- 確度: ✅ 読んで確認／前提は 🔶。重大度の案: 🟡。修正案: IDEA の ID で upsert する。

### A3-5 cross の TSP の気づき・提案メモを集めない
- 書く側: 09 SKILL.md:142-155（`09_test-spec/cross/TSP-{CR}-cross.md` を 09 tpl で書く。節は tpl:137）。
- 読む側: collect_insights.py:170-171（repo だけ。SPO・DSN・CHD・VERIFY・TRS の cross は列挙している：143-144,149-150,159-162,168-169,176-177）。
- 起きること: cross 統合テストの気づきが INSIGHTS・IDEA・LL のどこにも入らない（close SKILL.md:69 は INSIGHTS だけを読む）。黙って失われる。
- 確度: ✅（V2 が再現）。重大度の案: 🔴。修正案: `if has_cross: literal.append(… "09_test-spec"/"cross"/f"TSP-{cr}-cross.md")`。

### A3-6 progress.md の「## 気づき・提案メモ」を集めない
- 書く側: 00_progress tpl:67-73（「バックログの入力として活用する」）。読む側: collect_insights.py:129-192（対象外）、close SKILL.md:69。
- 起きること: 人が CR の途中で progress.md に書いた気づきが失われる。abort が書く分（SKILL.md:105-107）は「昇格しない」と明記しているので、食い違いではない。
- 確度: ✅（V2 が再現）。重大度の案: 🔴（人が書いた場合）。修正案: progress.md を対象に足す。またはテンプレートの節を消す。

### A3-7 latest-specs の節を CR で絞らず毎回集める（内容を直した）
- 書く側: 11-specs（SKILL.md:135,183。11 tpl の表に CR 列なし：例 module-spec tpl:104-110）。**xddp-survey (c)**（SKILL.md:291-338。`xddp-specs-mod-agent` が同じテンプレートで latest-specs を書き、369-370 で DOCS に写す）。close C0-3（SKILL.md:211-221）は DOCS specs を latest-specs に戻す。specs-mod・uc の agent に、気づきの行の扱いの記述は無い（S5 で0件）。
- 読む側: collect_insights.py:179-184（**`repos_keys` の全部**。`affected_repos` ではない）・cross・system。出典は相対パスだけで CR を書かない（327-336）。
- 起きること: 前の CR・survey・今の CR が触れていない repo の気づきが毎回 INSIGHTS に入る。Step B（SKILL.md:76。重複の確認の指示は無い）が、同じ IDEA を今の CR を発生源として繰り返し足しうる。
- 確度: ✅（V2 が再現）／Step B が重複を除くかは 🔶。重大度の案: 🟡。
- 修正案: progress.md の「工程11 更新仕様書ファイル一覧」に載ったファイルに限る。または表に CR 列を足す。

### A3-8 IS_MULTI で cross の成果物が無い CR の `repo: cross` の LL を、黙って Layer 2 に入れない
- 書く側: close SKILL.md:136。読む側: promote.py:891-894（`has_cross` が偽なら continue し、unresolved にも足さない）。HAS_CROSS の定義は SKILL.md:24。domain_refs.py:320-321,364-365 は IS_MULTI なら cross の Layer 2 を読む。
- 確度: ✅（V2 が再現）。重大度の案: 🟡。修正案: cross の Layer 2 に書く。または unresolved に出す。

### A3-9 LL の `repo` 欄の値を検証せずにパスにする
- 書く側: close SKILL.md:134-137（IDEA は `全リポジトリ`・判定根拠つきを許す：79-82,87）。読む側: promote.py:884,897。
- 起きること: `docs/全リポジトリ/knowledge/…` のように、domain_refs から見えない場所に書く。
- 確度: ✅（V2 が再現。LLM が書き違えたときに起きる）。重大度の案: 🟡。修正案: REPOS_KEYS・cross・unknown 以外は unresolved に回す。

### A3-10 xddp-analyst-agent が LESSONS_CONTEXT を Inputs に持たない
- 書く側: 02 SKILL.md:107,214。読む側: analyst-agent.md:18-35（宣言なし。S7 で analyst に0件）。refcheck 検査B は条件つきのキーを照合しない（tools/harness/refcheck.py:374-389）。
- 確度: ✅（宣言が無い）／🔶（実際に無視されるか）。重大度の案: 🟡。修正案: designer（designer-agent.md:52-58,80-84）にそろえる。

### A3-11 xddp-architect-agent が LESSONS_CONTEXT を Inputs に持たない
- 書く側: 05 SKILL.md:144-147,232。読む側: architect-agent.md（S7 で0件）。確度・重大度・修正案は A3-10 と同じ。

### A3-12 xddp-test-writer-agent が LESSONS_CONTEXT を Inputs に持たない
- 書く側: 09 SKILL.md:80-83,136。読む側: test-writer-agent.md（S7 で0件）。同上。

### A3-13 analyst の「なし」を未記入と判定しない
- 書く側: analyst-agent.md:41,65-66。読む側: collect_insights.py:203,239-257（`（なし）`／`(なし)` だけ）。
- 起きること: ANA §7 の「なし」が1件として集まり、close SKILL.md:70 の「0件なら確認」が働かない。
- 確度: ✅（V2 が再現）。重大度の案: 🔵。

### A3-14 SPO §9 の「なし」の行と HTML コメントを未記入と判定しない（確度を ✅ に上げた）
- 書く側: specout_bfs.py:7625-7632（`| 1 | — | なし | — |`）。SPO tpl:308 の `<!-- 書き手: … -->` は prelim-agent.md:187（§9 はテンプレートのまま）で残る。
- 読む側: collect_insights.py:239-257（`<!--` の行を本文とみなす）。
- 確度: ✅（V2 が両方を再現）。重大度の案: 🔵。

### A3-15 IDEA のエントリの書式がテンプレートと違う
- close SKILL.md:84-90（半角コロンの太字の行・`repo` あり）と backlog tpl:43-51（`| 項目 | 内容 |` の表・repo なし）。確度 ✅。重大度の案 🔵。

### A3-16 Step B の「summary table」がどの表か不明で、一覧表への追記の指示が無い
- close SKILL.md:92 と backlog tpl:16-25（§1）・29-34（§2）。確度 ✅。重大度の案 🔵。

### A3-17 Layer 2 の「エントリ一覧」表を誰も更新しない（ヘッダーも書く側によって違う）
- 書く側: 01-init SKILL.md:204-213（表と「xddp-close 実行後に追記」）。追記する側: promote.py:899-917（表を更新しない。ヘッダーは901の2行）、update-knowledge SKILL.md:208-209。
- 確度 ✅。重大度の案 🔵。

### A3-18 update-knowledge の lesson のエントリの書式が決まっていない
- update-knowledge SKILL.md:76-85,206-209（見出し・メタ行・出典の行の形なし）。読む側: promote.py:905-908、LLM。確度 🔶。重大度の案 🔵。修正案: close の Entry Format（CR は `—`）にそろえる。

### A3-19 LL テンプレートの「管理場所」が実際のパスと違う
- LL tpl:8（「プロジェクトルート」）と close SKILL.md:106（`{XDDP_DIR}/`）。✅。🔵。

### A3-20 Step B・C の「create from template」がテンプレートのパスを示さない
- close SKILL.md:74,106。実体 CC/skills/xddp-close/templates/ の2ファイルを参照するのは setup.sh:93,96 だけ（S13）。✅。🔵。

### A3-21 Step C の抽出の観点が「(same as before …)」で、参照先と抽出元が無い（内容を直した）
- close SKILL.md:110-112。括弧の中に観点の名前4つはあるが、「same as before」の前の版の内容がファイルに無い。LL を何から抽出するか（INSIGHTS か）も書いていない（Step A は INSIGHTS だけを読む：69）。✅。🔵。CLAUDE.md の「実行時ファイルへの履歴の混入禁止」にも当たりうる。

### A3-22 abort が「update-knowledge 等で backlog に手で登録」と案内するが、update-knowledge に backlog の種別が無い
- abort SKILL.md:99,105-107。update-knowledge SKILL.md:15,32（種別に backlog は無い。lesson は Layer 2 に書く：207）。✅。🔵。

### A3-23 close のコメントにある Layer 1 の読み手の一覧が足りない
- close SKILL.md:99（02・05 だけ）。実際は 06 SKILL.md:95-98、09 SKILL.md:80-83 も読む。✅。🔵。

### A3-24（新）`append_breaking_warning` が Layer 2 をヘッダーなしで作る（cross で起きる）
- 約束: Layer 2 のファイルは `# 知見ログ: {repo}` のヘッダーで始まること（#16c）。
- 書く側: promote.py:1082-1088（ファイルが無いと空のリストに警告だけを書く）。他の書く側はヘッダーを書く（promote.py:901、01-init SKILL.md:204-207）。
- 起きる条件: 01-init は repo の Layer 2 だけを作り、cross は作らない（SKILL.md:117-128）。cross の Layer 2 は、その CR に cross の LL が無く（promote.py:891-899 を通らない）、cross に破壊的変更がある（1208-1210）と、ヘッダーなしで作られる。後の CR の LL は、ファイルが空でないのでヘッダーを足さない（900-901）。
- 起きること: cross の知見ログが見出しの無いファイルになる。読み手は LLM（domain_refs.py:321,365）なので、動作への影響は小さい。
- 確度: ✅（両側を読んで確認。V2 N3 を具体化）。重大度の案: 🔵。
- 修正案: ファイルが無ければ promote.py:901 と同じヘッダーを書く。

### A3-25（新）collect_insights が CODING・VERIFY の気づき節を集めるが、書く側に節が無い
- 書く側: coder-agent.md:47-56（コーディングメモの内容に気づき節なし）、verifier-agent.md:131-175（出力書式は A〜J・総合判定・NG事項一覧だけ）。07 SKILL.md:140,183,204・08 SKILL.md:145,163 はこれらの agent に書かせる。
- 読む側: collect_insights.py:3（docstring に CODING/VERIFY を挙げる）、164-169。
- 起きること: 工程7・8 で気づいたことを書く場所が無い。気づきが INSIGHTS に届かない（集める側は「存在しなかった想定ファイル数」にも数えず、黙って0件になる）。
- 確度: ✅。重大度の案: 🔵（工程7・8 の気づきの置き場所が無い、という設計上の空白）。
- 修正案: coder・verifier の出力に「気づき・提案メモ」の4列表を足す。または collect_insights と docstring から外す。

### A3-26（新）SPO §9 のテンプレートが「書き手: スクリプト。手で直さない（再実行で上書きされる）」と書くが、スクリプトは人が書いた行を残す
- 書く側（テンプレート）: SPO tpl:307-313（308 の HTML コメントは「手で直さない（再実行で上書きされる）」。312-313 は「自由に記録する」）。
- 書く側（スクリプト）: specout_bfs.py:7625-7627（`[自動転記]`〔4452〕で始まらない行は残す）。document-agent.md:94 も §9 に書く。
- 起きること: 人が「上書きされる」と読み、SPO に気づきを書かなくなりうる（その気づきは INSIGHTS に届かない）。記述が実際の動作と合わない。
- 確度: ✅（記述の不整合）／🔶（人がそれで書かなくなるか）。重大度の案: 🔵。
- 修正案: コメントを「表の `[自動転記]` の行はスクリプトが作り直す。それ以外の行は残る」に直す。

### A3-27（新）C7（improvement-backlog の昇格）の失敗が Step D・Step E に出ない
- 書く側: promote.py:1217-1221（失敗は `global_errors`）、1117-1121（出力ファイルの「リポジトリ別処理結果一覧」の中に「共通ファイルの昇格エラー」として書く）。stdout の `backlog_promoted`・`global_errors`（1236-1237）を close は読まない。
- 読む側: close SKILL.md:302-306（出力の内容の一覧に共通ファイルのエラーが無い）、336-351（Step D は repo ごとの成功・失敗だけを示す）、340-341・409（`FAILED_REPOS` は repo だけ。Step E は ✅ 完了と書く）。
- 起きること: DOCS の backlog が更新されなくても、人に示されず ✅ でクローズする。Layer 1 は残るので、次の close でまた写る（後で取り戻せる）。
- 確度: ✅（Step D に指示が無い）／🔶（LLM が出力ファイルを読んで示すか）。重大度の案: 🟡。
- 修正案: Step D に「共通ファイルの昇格エラー」の表示を足す。同じ節の AI_INDEX（A2）・共通 rulebook（A5）のエラーも同じ扱い（§4 を参照）。

### A3-28（新）LL のタグの区切りが決まっておらず、タグ別インデックスから漏れうる
- 書く側: close SKILL.md:119（`**タグ：** {#タグ}`。区切りを示さない）。template:16-20 はタグを空白区切りで並べ、update-knowledge SKILL.md:79 の例も空白区切り（`#リスク #見落とし #コーディング`）。
- 読む側: close SKILL.md:142-148（「カンマ区切り」として分ける。行が無いタグは足さずに飛ばす）、load-lessons-context.md:23-28（インデックスのどれかの行に ID があれば、本文の全体からは探さない）。
- 起きること: 空白区切りで書くと、`#設計 #リスク` を1つのタグとみなして行が見つからず、インデックスに載らない。インデックスが他の LL で埋まっていると、工程2・5・6・9 の LESSONS_CONTEXT にその LL が黙って入らない。
- 確度: 🔶（LLM の書き方による）。重大度の案: 🟡。
- 修正案: Entry Format に区切り（例 `#設計, #リスク`）を書く。または Step C で空白とカンマの両方で分ける。

### A3-29（新）close の再実行で重複した LL・IDEA が、人が消す前に同じ実行で昇格する
- 書く側: close Step B・C（SKILL.md:72-139）。今の CR のエントリが既にあるかを確かめる指示が無い。
- 読む側: 同じ実行の extract-ll（284）、promote run（299。Layer 2 の重複判定は ID だけ：promote.py:905-908）、knowledge agent（312）。
- 食い違い: Step D は「再実行は Step B・C の知見の追記も繰り返すので、重複した LL は人が消す」と案内する（SKILL.md:361-362,370）。しかし再実行では Step C の後に人が確認する場所が無く（アーカイブの警告 151-163 は100件を超えたときだけ）、そのまま昇格まで進む。
- 起きること: 新しい ID で足した重複は Layer 2 に入る。knowledge agent も、重複を rulebook・code-knowledge に取り込みうる。Layer 1 で人が消しても Layer 2 には残る（DOCS の backlog は次の close で上書きされる）。
- 確度: ✅（順序と案内）／🔶（LLM が新しい ID で足し直すか）。重大度の案: 🟡。
- 修正案: Step B・C に「今の CR のエントリが既にあれば足さない」と書く。または案内を「再実行の前に消す」に直す。

### A3-30（新）latest-specs の「気づきメモポリシー」が参照先に無い
- 読む側: SPEC.md:28（「テンプレートポリシーで気づきメモあり（✅）のファイル」）、39（自動修正の対象）、11-specs SKILL.md:374（「Section 3-4 の気づきメモポリシー」）、survey SKILL.md:351。
- 書く側（実際の規則）: 11 tpl ごとの「このファイルには気づきメモセクションなし」（sequence tpl:15 ほか）と collect_insights.py:113-114。どのファイルに節があるかを一覧にした「ポリシー」や「Section 3-4」は、11-specs SKILL.md の中に無い（S14 で `ポリシー` は 374 行目だけ）。
- 起きること: レビューと自動修正が、テンプレートから推し量ることになる。節の無いファイル（`*-seq.md` 等）に節を足すと、そこに書いた気づきは collect_insights が除外する（113-126）ので届かない。
- 確度: ✅（参照先が無い）／🔶（起きるか）。重大度の案: 🔵。
- 修正案: ポリシーの表を SPEC.md に置く（collect_insights の除外と一致させる）。

## 4. 担当外の指摘
- **担当外（A2・A5）（A3-27 と同じ根）:** 「共通ファイルの昇格エラー」には AI_INDEX.md の更新失敗（promote.py:1195）と共通 project-rulebook.md の昇格失敗（promote.py:990）も入るが、close Step D（SKILL.md:336-351）に表示の指示が無く、Step E は ✅ と書く。確度 ✅／🔶。重大度の案 🟡。
- **前回の担当外（A2）を取り下げる:** promote.py:343 の行は「タグ検索例」を挙げているだけで、インデックスがあるとは書いていない。Layer 2 のエントリは Layer 1 のエントリを丸ごと写したもの（promote.py:911）で、`**タグ：**` 行を含む。そのため文字列での検索は成り立つ（V2 の否定に同意する）。

## 5. 段階2b の候補
なし

## 6. 読んだファイルの一覧と、確認していないこと

**読んだファイル（`{W}` からの相対パス）:**
- `{W}` 外: 指示 common.md・redo.md（全文）、前回の A3.md・V2.md（全文）。
- 全文: CC/skills/xddp-close/SKILL.md、xddp-close/templates/lessons-learned-template.md・10_improvement-backlog-template.md、xddp-common/procedures/load-lessons-context.md、xddp-close/scripts/collect_insights.py、xddp-update-knowledge/SKILL.md。
- 範囲:
  - promote.py 1-40, 330-352, 650-930, 975-1020, 1075-1140, 1150-1290
  - close-knowledge-agent.md 1-120
  - analyst-agent.md 16-45, 60-95
  - designer-agent.md 45-60, 78-86
  - architect-agent.md 143-152, 205-220
  - coder-agent.md 44-70（見出しの grep も）
  - verifier-agent.md 128-185（見出しの grep も）
  - 02 SKILL 18-120、05 SKILL 140-200（grep も）、06 SKILL 92-135、09 SKILL 78-84, 125-160
  - 01-init SKILL 105-140, 190-250、00_progress tpl 60-76、abort SKILL 92-115
  - domain_refs.py 225-240, 300-370（grep も）
  - specout_bfs.py 7600-7640（`AUTO_NOTE_PREFIX` の grep も）、SPO tpl 300-317
  - document-agent.md 50-58, 88-98、prelim-agent.md（grep の187行目）
  - 03 tpl 200-215、approach tpl 50-72、05 index tpl（見出し）、CHD index tpl 15-40、11 tpl 8種（節の前後）
  - xddp-common/SKILL.md 205-230、crs_model.py 175-215（grep も）
  - xddp-status SKILL 95-115、xddp_progress.py 315-420
  - xddp-survey SKILL 286-356（grep も）、xddp-11-specs SKILL 125-140, 178-186, 330-378（grep も）
  - reviewer-checklists/SPEC.md 1-42、xddp-rules/code-knowledge-boundary.md 1-60
  - tools/harness/refcheck.py 370-392、docs/adr/ADR-0013-close-promote-script.md 25-45（docs/adr の grep も）
  - test_promote.py（grep だけ）
- grep だけ: S1〜S16 の結果の行。

**確認していないこと:**
- スクリプトとテストは実行していません（再現は V2 のもの）。
- LLM の実際の振る舞いは確認していません: 採番・タグの区切り・再実行時の重複の扱い・Step B の重複除去・Step D で共通ファイルのエラーを示すか・レビューの自動修正で節を足すか（A3-1・2・7・18・27〜30 の 🔶 の部分）。
- `{XDDP_DIR}` をワークスペースの間で共有する運用かは確認していません（A3-3・A3-4）。
- xddp-specs-mod-agent・xddp-specs-uc-agent・xddp-revise・xddp-feedback・xddp-sync-design について: 「気づき」で grep して0件だったので、手順に節の扱いは書かれていません。ただし実際に LLM が節の行を残すか消すかは確認していません。
- test-writer-agent・test-runner-agent の全文は読んでいません（テンプレートを渡していることだけを確認）。
- close-knowledge-agent.md の 120 行目以降（A1 の担当）は読んでいません。