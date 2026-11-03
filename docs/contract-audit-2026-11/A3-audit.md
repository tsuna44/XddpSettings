# 監査者 A3 の報告（原文。PLAN-20261103-contract-audit 段階2a）

> 監査者の最終報告をそのまま載せたもの（検証前）。検証結果と統合後の重大度は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。パスの `{W}` は監査用の worktree（ecb54c4。セッションのスクラッチのディレクトリに作り、監査の後に削除）。

# A3 知見ログ・バックログ 監査報告（対象 ecb54c4、`{W}` = audit-ecb54c4、`CC/` = `ClaudeCode/.claude/`）

## 1. 確認した約束の一覧

| # | 約束 | 書く側（ファイル:行・節） | 読む側（ファイル:行・節） | 見つけた方法 | 結果 |
|---|---|---|---|---|---|
| 1 | Layer 1 のパス `{XDDP_DIR}/lessons-learned.md` | CC/skills/xddp-close/SKILL.md:106（Step C） | CC/skills/xddp-02-analysis/SKILL.md:71、xddp-05-arch/SKILL.md:145、xddp-06-design/SKILL.md:96、xddp-09-test/SKILL.md:81（Step A0）、xddp-close/SKILL.md:284,299（extract-ll・run の `--lessons-file`） | 両側: `grep -rn 'lessons-learned' CC/skills CC/agents` | なし |
| 2 | LL の見出し `### LL-{NNN}：` | close SKILL.md:117（Entry Format） | promote.py:661 `LL_ENTRY_RE`、load-lessons-context.md:28 `### {id}：` | 書く側: 同上 grep。読む側: promote.py は SKILL.md:284 の参照、load-lessons は SKILL の apply から | なし |
| 3 | LL のメタ行 `**CR：** … ／ **工程：** … ／ **repo：** … ／ **タグ：** …`（全角・見出しから5行以内） | close SKILL.md:119 | promote.py:662-664,671,799-803；close-knowledge-agent.md:100,106,111（`**repo：**` 欄） | 書く側: grep `lessons-learned`。読む側: promote.py は参照、agent は SKILL.md:312 の参照 | なし |
| 4 | LL の `repo` 欄の値の語彙（`{repo}`／`cross`／`unknown`） | close SKILL.md:134-137 | promote.py:884-897（パスを作る）、close-knowledge-agent.md:63-65 | 同上 | 食い違いあり A3-8、A3-9 |
| 5 | LL の採番（NNN） | close SKILL.md:108-117（採番の規則なし）、xddp-update-knowledge/SKILL.md:209（Layer 2 の「next NNN」） | promote.py:905-908（Layer 2 の重複判定は ID だけ） | 書く側: grep `lessons-learned`。読む側: promote.py を読んで | 食い違いあり A3-1、A3-2、A3-3 |
| 6 | Layer 1 の「エントリ一覧」表の列 | lessons-learned-template.md:26-27；close SKILL.md:139 | 人（構造的な読み手なし） | grep `lessons-learned` | なし |
| 7 | Layer 1 の「タグ別インデックス」表（タグの行・カンマ区切りの ID） | lessons-learned-template.md:33-56；close SKILL.md:141-148 | load-lessons-context.md:19-28 | grep `lessons-learned` | なし |
| 8 | Load Lessons Context の TARGET_TAGS がタグ一覧にあること | 呼び出し側 02:72、05:146、06:97、09:82 | lessons-learned-template.md:16-20,37-56 | grep `LESSONS_FILE:` | なし |
| 9 | エントリの置き場所 `## 知見詳細` | lessons-learned-template.md:60-62（close Step C は節を明示しないが末尾追記で節内に入る） | load-lessons-context.md:21,27 | 参照をたどって | なし |
| 10 | `LESSONS_CONTEXT` の Inputs（エージェント側の宣言・使い方） | 02 SKILL.md:107,214；05:232；06:213；09:136 | xddp-analyst-agent.md:18-35（宣言なし）、xddp-architect-agent.md:17-60（宣言なし）、xddp-designer-agent.md:52,80（宣言あり）、xddp-test-writer-agent.md:19-45（宣言なし） | `grep -rn 'LESSONS_CONTEXT' CC/skills CC/agents` | 食い違いあり A3-10、A3-11、A3-12（designer はなし） |
| 11 | `extract-ll` の出力パス `{CR_PATH}/pending-items/LL-{CR}.md` | close SKILL.md:284 | close SKILL.md:324 `CR_LESSONS_FILE`、close-knowledge-agent.md:23,29 | 参照をたどって | なし |
| 12 | `extract-ll` の出力ファイルが無いことの意味（0件） | promote.py:847-860（0件ならファイルを書かず、前回のファイルを消す） | close-knowledge-agent.md:23,29,99,105（無ければ取り込まない） | 同上 | なし |
| 13 | `extract-ll` の stdout の JSON キー（`count`・`unparsed`・`dropped`） | promote.py:861,1242-1244、docstring 19-22 | close SKILL.md:290 | 同上 | なし |
| 14 | `unparsed` の reason の語彙（heading／no-meta／multi-meta） | promote.py:786-803 | close SKILL.md:358 | 同上 | なし |
| 15 | `dropped` の reason の語彙（cr-meta／cut） | promote.py:806-827 | close SKILL.md:366 | 同上 | なし |
| 16 | Layer 2 のパス `{DOCS}/{repo}/knowledge/lessons-learned.md`・`{DOCS}/cross/knowledge/lessons-learned.md` | promote.py:895-897；update-knowledge SKILL.md:207；01-init SKILL.md:121,128 | domain_refs.py:315-321,362-365 | grep `lessons-learned` | なし |
| 17 | Layer 2 の「エントリ一覧」表（01-init の初期内容） | 01-init SKILL.md:204-213 | promote.py:901-917（表を更新しない）、update-knowledge SKILL.md:209（末尾に追記） | grep `lessons-learned` | 食い違いあり A3-17 |
| 18 | Layer 2 の LL エントリの書式（update-knowledge の lesson） | update-knowledge SKILL.md:76-85,206-209 | promote.py:905-908（ID の重複判定）、読み手の LLM（domain_refs 経由） | grep `lessons-learned` | 食い違いあり A3-18 |
| 19 | PENDING-PROMOTE の「要確認LL一覧」節 | promote.py:1124-1129 | close SKILL.md:301-308,355 | 参照をたどって | なし |
| 20 | `INSIGHTS-{CR}.md` のパス | close SKILL.md:64（`--output-file`） | close SKILL.md:69 | grep `INSIGHTS` | なし |
| 21 | INSIGHTS の「収集サマリ」「抽出エントリ数」 | collect_insights.py:337-341 | close SKILL.md:70 | 参照をたどって | なし |
| 22 | 「気づき・提案メモ」の見出しの文字列（番号・レベル不問） | 各テンプレート（02 tpl:105、03 tpl:203、04 SPO tpl:307、05 comparison:65・approach:64、06 CHD tpl:228、09 tpl:137、10 tpl:59、11 tpl 8種） | collect_insights.py:199-236 | 書く側: grep `気づき・提案メモ`。読む側: SKILL.md:64 | なし |
| 23 | 対象ファイルのパス: ANA・CRS・SPO（repo／cross）・DSN（comparison・approach-A/B/C・cross）・CHD（内容ファイル・cross）・CODING・VERIFY（repo／cross）・TSP（repo）・TRS（repo／cross） | 各スキルの OUTPUT_FILE（例 09-test SKILL.md:155 ほか、grep で集計） | collect_insights.py:129-192 | 書く側: `grep -rhoE '[0-9]{2}_[a-z-]+/…(ANA|CRS|…)-\{?CR\}?…'`。読む側: SKILL.md:64 | TSP cross に食い違いあり A3-5、他はなし |
| 24 | approach-D 以降・CHD のインデックスに節が無いこと | architect-agent.md:211-217、approach tpl:54-56（2案以上は節を消す）、CHD index tpl（節なし） | collect_insights.py:147-148,152-162 | 参照をたどって | なし |
| 25 | latest-specs の節なしのファイル（schema・crud・dfd・*-seq） | 11 tpl（sequence:15、crud:17、dfd:15、schema:17 等「気づきメモセクションなし」） | collect_insights.py:113-126 | grep `気づき` | なし |
| 26 | latest-specs の範囲（どの CR の行か） | 11-specs SKILL.md:135,183（気づきメモに記録）、11 tpl | collect_insights.py:179-184 | 同上 | 食い違いあり A3-7 |
| 27 | progress.md の「## 気づき・提案メモ」 | 00_progress tpl:67-73；xddp-abort SKILL.md:97-104 | collect_insights.py（対象外） | grep `気づき・提案メモ` | 食い違いあり A3-6 |
| 28 | 空の節の表し方（未記入の判定） | analyst-agent.md:41-42,65-66（「なし」）；specout_bfs.py:7629-7631（`| 1 | — | なし | — |`）；SPO tpl:307-308（HTML コメント） | collect_insights.py:203,239-257 | grep `気づき・提案メモ` | 食い違いあり A3-13、A3-14 |
| 29 | 「対応方針」列の語彙（今回対応／次回CR／保留／却下） | 全テンプレートの4列表（例 06 tpl:233-235）；specout_bfs.py:7629（`保留`） | close SKILL.md:76（「今回対応」以外を IDEA に） | 同上 | なし |
| 30 | IDEA のエントリの書式 | close SKILL.md:84-90 | 10_improvement-backlog-template.md:41-67 | grep `improvement-backlog` | 食い違いあり A3-15 |
| 31 | バックログの表の更新 | close SKILL.md:92 | backlog tpl:16-34 | 同上 | 食い違いあり A3-16 |
| 32 | `improvement-backlog.md` の昇格（Layer 1 → DOCS） | promote.py:1009-1015 | DOCS の利用者 | 同上 | 食い違いあり A3-4 |
| 33 | テンプレートの所在と管理場所の記述 | close SKILL.md:74,106（テンプレートのパスなし）；lessons-learned-template.md:8 | — | grep `lessons-learned` | 食い違いあり A3-19、A3-20 |
| 34 | LL の抽出の観点 | close SKILL.md:110-112 | — | 同上 | 食い違いあり A3-21 |
| 35 | 中止した CR の気づきを後で登録する経路 | xddp-abort SKILL.md:105-107 | update-knowledge SKILL.md:15,32（種別） | grep `improvement-backlog` | 食い違いあり A3-22 |
| 36 | Layer 1 の読み手の記述 | close SKILL.md:96-104（コメント） | 02/05/06/09 Step A0 | grep `LESSONS_FILE:` | 食い違いあり A3-23 |
| 37 | cross の LL を rulebook-cross へ | close-knowledge-agent.md:64 | （A5 の担当。ここではルーティングの語彙だけ確認） | 参照をたどって | なし（A3-8 で関係） |

## 2. 時期の約束の表

| 書く側（スキル・Step） | 読む側（スキル・Step） | 順序の根拠（ファイル:行） | 結果 |
|---|---|---|---|
| 工程2〜11 の成果物（気づき・提案メモの節） | close Step A（collect_insights） | close SKILL.md:31（工程11 ✅ が前提）、11-specs SKILL.md:660（工程11の後に close を案内） | なし |
| close Step A（INSIGHTS） | close Step B・C | close SKILL.md:61-70 → 72 → 94 | なし |
| close Step B（Layer 1 の backlog） | close C7 `promote_backlog` | SKILL.md:72 → 299；promote.py:1217-1218 | なし |
| close Step C（Layer 1 LL） | close C2 前の `extract-ll` → C3 `promote_lessons_learned` | SKILL.md:94 → 284 → 299；promote.py:1197 | なし |
| `extract-ll`（LL-{CR}.md） | C3.5/C3.6 knowledge agent | SKILL.md:284 → 312-327 | なし |
| promote C3（Layer 2 への追記） | promote の破壊的変更警告の追記（同じファイル） | promote.py:1197 → 1200-1212 | なし |
| close Step C0-3（DOCS specs → latest-specs） | 次の CR の close Step A | SKILL.md:211-221 は Step A（61）の後。次回の close で集める | 関係あり A3-7 |
| close（Layer 1） | 後の CR の 02/05/06/09 Step A0 | 別の CR。Layer 1 が無ければ空（load-lessons-context.md:17） | なし |
| close C3（Layer 2） | 後の CR の 02 Step 0（domain_refs） | 別の CR。`add_docs` はファイルがあるときだけ（domain_refs.py:233-236） | なし |
| update-knowledge（Layer 2・随時） | 後の close C3 の重複判定 | 随時（順序の保証なし） | A3-1 |
| abort Step 3（progress.md の気づき） | （読み手なし。close は工程11 ✅ が前提なので中止した CR には走らない） | abort SKILL.md:105-107；close SKILL.md:31 | なし |

## 3. 指摘

### A3-1 Layer 2 の重複判定が ID だけで、update-knowledge が Layer 2 で別に採番する
- 約束: Layer 2 に足す LL の ID が既存の LL と重ならないこと。
- 書く側: `CC/skills/xddp-update-knowledge/SKILL.md:206-209`（lesson は `{KNOW_DIR}/lessons-learned.md` の既存の LL-NNN から次の番号を採る）。Layer 1 の採番は close Step C（`CC/skills/xddp-close/SKILL.md:108-117`）で、Layer 2 とは関係なく採る。
- 読む側: `CC/skills/xddp-close/scripts/promote.py:905-908`（`### {entry_id}：` が Layer 2 にあれば追記しない）。
- 食い違い: Layer 2（repo ごとの一部の写し）で update-knowledge が「次の番号」を採ると、Layer 1 が後で同じ番号を使える。例: Layer 2 の repo-a に LL-001・LL-003 があり、update-knowledge が LL-004 を追加する。次の CR の Layer 1 の LL-004（repo-a）は、promote が「既にある」と判定して追記しない。
- 起きること: その CR の LL が Layer 2 に入らない。Step D の一覧（unparsed・dropped・要確認LL）にも出ないので、黙って失われる。工程2 の domain_refs が渡す確定した知見から抜ける。
- 確度: ✅ 振り分けの仕組みは両側を読んで確認した。update-knowledge が `### LL-NNN：` の見出しで書くかは書式が決まっていないので 🔶（A3-18）。
- 重大度の案: 🔴
- 修正案（決めない）: 重複判定の鍵を（ID, CR）にする。または update-knowledge の lesson に別の接頭辞（例 `LL-M{NNN}`）を使わせる。

### A3-2 Layer 1 の LL の採番規則が無い（アーカイブの後に番号が重なりうる）
- 書く側: `CC/skills/xddp-close/SKILL.md:108-117`（`LL-{NNN}` の採り方を書いていない）、150-165（古いエントリを `lessons-learned-archive-{YYYY}.md` に移し、エントリ一覧の行も消す）。
- 読む側: `promote.py:905-908`。
- 食い違い: アーカイブの後に LLM が残りの件数や一覧表から番号を採ると、Layer 2 に既にある ID を再び使い、A3-1 と同じく追記されない。
- 確度: 🔶（LLM の採番の仕方による）。
- 重大度の案: 🟡
- 修正案: Step C に「Layer 1・アーカイブ・Layer 2 の最大の番号 + 1」を書く。A3-1 の鍵の変更でも防げる。

### A3-3 ワークスペースが別だと Layer 1 の番号が独立していて、共有の Layer 2 で重なる
- 書く側: 各ワークスペースの close Step C（`SKILL.md:106-117`。`{XDDP_DIR}` はワークスペースごと）。
- 読む側: `promote.py:905-908`（共有の `{DOCS}`）。
- 食い違い: close Step C0（`SKILL.md:187-276`「Parallel-CR Support」）は `{DOCS}` を git pull し、他の CR の昇格を取り込む前提になっている。ワークスペースごとに LL-001 から番号を振ると、後からクローズした側の同じ番号の LL は追記されない。
- 確度: 🔶（`{XDDP_DIR}` をワークスペースの間で共有するかはファイルに書かれていない。確認していません）。
- 重大度の案: 🔴（起きる場合は黙って失われる）
- 修正案: A3-1 と同じ。

### A3-4 improvement-backlog.md を DOCS に丸ごと上書きする
- 書く側: `promote.py:1009-1015`（`shutil.copy2` で上書き）。
- 読む側: `{DOCS}/improvement-backlog.md` の利用者。
- 食い違い: A3-3 と同じく別のワークスペースから昇格すると、DOCS の backlog は最後にクローズした側の Layer 1 の内容だけになり、他の側の IDEA が DOCS から消える（各ワークスペースの Layer 1 には残る）。
- 確度: 🔶（前提は A3-3 と同じ）。
- 重大度の案: 🟡
- 修正案: IDEA の ID で upsert する。

### A3-5 cross の TSP の「気づき・提案メモ」を集めない
- 書く側: `CC/skills/xddp-09-test/SKILL.md:148-155`（`{CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md` を `09_test-specification-template.md` で書く。節は `09 tpl:137`）。
- 読む側: `collect_insights.py:170-171`（TSP は affected_repos だけ。cross の TSP は列挙していない。SPO・DSN・CHD・VERIFY・TRS の cross は列挙している：143-144,149-150,159-162,168-169,176-177）。
- 起きること: cross の統合テストの設計で得た気づきが、INSIGHTS にも IDEA にも LL にも入らない。close SKILL.md:69 は INSIGHTS だけを読むので、黙って失われる。
- 確度: ✅
- 重大度の案: 🔴
- 修正案: `if has_cross: literal.append(cr_path / "09_test-spec" / "cross" / f"TSP-{cr}-cross.md")`。

### A3-6 progress.md の「## 気づき・提案メモ」を集めない
- 書く側: `CC/skills/xddp-01-init/templates/00_progress-management-template.md:67-73`（「各工程で気づいた…次のCR起票・バックログの入力として活用する」）。
- 読む側: `collect_insights.py:129-192`（progress.md は対象にない）、close SKILL.md:69（INSIGHTS だけを読み「個々の成果物は読まない」）。
- 起きること: 人が CR の途中で progress.md に書いた気づきが、バックログにも知見ログにも入らない（黙って失われる）。xddp-abort（SKILL.md:105-107）がここに書くのは「昇格しない」と明記されているので、abort は食い違いではない。
- 確度: ✅（人が書いた場合に起きる）
- 重大度の案: 🔴（条件は人が書いたとき）
- 修正案: progress.md を literal に足す。またはテンプレートの節を消す。

### A3-7 latest-specs の節を CR で絞らず毎回集める（前の CR の気づきを繰り返し集める）
- 書く側: 11-specs（`SKILL.md:135,183` で気づきメモに書く。11 のテンプレート8種の節）。更新のときに前の行を消すかは決まっていない。close Step C0-3（`SKILL.md:211-221`）は DOCS の specs を latest-specs に写すので、他の CR の行も入る。
- 読む側: `collect_insights.py:179-184`（repos_keys の全 repo・cross・system の latest-specs をすべて走査）。INSIGHTS の出典は相対パスだけで、CR は書かない（327-336）。
- 起きること: 前の CR（他のワークスペースの CR を含む）の気づきが毎回の close で INSIGHTS に入り、Step B（`SKILL.md:76`。重複の確認の指示はない）が同じ IDEA を繰り返し足し、発生源を今の CR として書きうる。
- 確度: 🔶（Step B の LLM が既存の backlog と照合するか、11 の agent が古い行を残すかによる）
- 重大度の案: 🟡
- 修正案: latest-specs は工程11 で今の CR が更新したファイル（progress.md「工程11 更新仕様書ファイル一覧」）に限る。または表に CR 列を足す。

### A3-8 multi-repo で cross の成果物が無い CR の `repo: cross` の LL を、黙って Layer 2 に入れない
- 書く側: close SKILL.md:136（リポジトリ間のインタフェース・フローは `repo: cross`）。
- 読む側: `promote.py:892-894`（`has_cross` が偽なら `continue`。unresolved にも足さない）。`HAS_CROSS` は「IS_MULTI かつ cross/ の成果物がある」（SKILL.md:24）。一方 knowledge agent は HAS_CROSS によらず `project-rulebook-cross.md` に書く（close-knowledge-agent.md:64）。domain_refs は IS_MULTI なら cross の Layer 2 を読む（domain_refs.py:320-321,364-365）。
- 起きること: IS_MULTI で cross の成果物が無い CR の cross の LL が Layer 2 に入らない。Step D にも出ない。
- 確度: ✅
- 重大度の案: 🟡（条件が限られる）
- 修正案: has_cross でなくても cross の Layer 2 に書く。または unresolved に「cross 成果物なし」として出す。

### A3-9 LL の `repo` 欄の値を検証せずパスにする
- 書く側: close SKILL.md:134-137（値は `{repo}`／`cross`／`unknown` だけ）。同じ Step B の IDEA は `全リポジトリ`・`（判定根拠）` 付きの値を許す（SKILL.md:79-82,87）。
- 読む側: `promote.py:884,897`（`repo` の文字列をそのまま `docs/{repo}/knowledge/` にする。REPOS_KEYS との照合はない）。
- 起きること: LLM が IDEA と同じ書き方（`全リポジトリ`・`repo-a（…）`）をすると、存在しないディレクトリに Layer 2 が作られ、domain_refs（affected_repos のパスだけを読む）から見えない。
- 確度: 🔶（LLM が書式を取り違えたときに起きる）
- 重大度の案: 🟡
- 修正案: promote が REPOS_KEYS・`cross`・`unknown` 以外を unresolved に回す。

### A3-10 xddp-analyst-agent が LESSONS_CONTEXT を Inputs に持たない
- 書く側: `CC/skills/xddp-02-analysis/SKILL.md:107,214`（空でなければ渡す）。
- 読む側: `CC/agents/xddp-analyst-agent.md:18-35`（Inputs に無い）。本文にも使い方が無い（81 の「過去の知見」は DOMAIN_REF_PATHS の手順の中）。
- 起きること: タグで選んだ Layer 1 の知見を渡しても、エージェントの手順に使い方が無く、使われない場合がある。refcheck 検査B は条件つきのキーを照合しない（tools/harness/refcheck.py:375-387。passed_req だけ）。
- 確度: ✅（宣言が無いこと）／🔶（実際に無視するか）
- 重大度の案: 🟡
- 修正案: designer（`xddp-designer-agent.md:52,80`）と同じく Inputs と使う手順を足す。

### A3-11 xddp-architect-agent が LESSONS_CONTEXT を Inputs に持たない
- 書く側: `CC/skills/xddp-05-arch/SKILL.md:145-147,232`。
- 読む側: `CC/agents/xddp-architect-agent.md:17-60`（宣言・言及なし）。
- 確度・重大度・修正案: A3-10 と同じ（✅／🔶、🟡）。

### A3-12 xddp-test-writer-agent が LESSONS_CONTEXT を Inputs に持たない
- 書く側: `CC/skills/xddp-09-test/SKILL.md:81-83,136`。
- 読む側: `CC/agents/xddp-test-writer-agent.md:19-45`（宣言・言及なし）。
- 確度・重大度・修正案: A3-10 と同じ。

### A3-13 analyst の「なし」を未記入と判定しない
- 書く側: `xddp-analyst-agent.md:41-42,65-66`（§7 は「なければ『なし』と明記」）。
- 読む側: `collect_insights.py:203`（未記入として扱うのは `（なし）`／`(なし)` の行だけ）、239-257。
- 起きること: 本文が「なし」だけの ANA §7 を1件の気づきとして集める。close SKILL.md:70 の「抽出エントリ数が 0 なら人に確認」が働かなくなる。Step B の LLM は IDEA にしないと推測する。
- 確度: ✅
- 重大度の案: 🔵
- 修正案: 判定する語に `なし` を足す。または analyst に `（なし）` と書かせる。

### A3-14 SPO §9 の「なし」の行（と HTML コメント）を未記入と判定しない
- 書く側: `CC/skills/xddp-04-specout/scripts/specout_bfs.py:7629-7631`（行が無ければ `| 1 | — | なし | — |`）。SPO テンプレートの §9 の直後の `<!-- 書き手: … -->`（`04_specout-summary-template.md:308`）は `_replace_table`（specout_bfs.py:6700-6724）で消えない。
- 読む側: `collect_insights.py:239-257`（`{…}` を含まないデータ行や、`>`・`|` で始まらない行があれば未記入としない）。
- 起きること: 気づきの無い SPO でも、毎回 SPO §9 を1件として集める（影響は A3-13 と同じ）。
- 確度: ✅（「なし」の行）／🔶（HTML コメントが実際の SPO に残るかは prelim agent による）
- 重大度の案: 🔵

### A3-15 IDEA のエントリの書式がテンプレートと違う
- 書く側: close SKILL.md:84-90（`### IDEA-{NNN}：` の後に `**repo:**`・`**カテゴリ:**`… 半角コロンの太字の行）。
- 読む側: `10_improvement-backlog-template.md:43-51`（`| 項目 | 内容 |` の表。カテゴリ・優先度・発生源・ステータス・対応CR。repo の欄は無い）。
- 起きること: バックログの中でエントリの形が混ざる。スクリプトの読み手は無い（promote はファイルを丸ごと写す）ので、動作への影響は無い。
- 確度: ✅
- 重大度の案: 🔵

### A3-16 Step B の「summary table」がどの表を指すか不明で、一覧表への追記の指示が無い
- 書く側: close SKILL.md:92（「Update summary table」）。
- 読む側: backlog tpl:16-25（§1 サマリ＝ステータス別件数）、29-34（§2 バックログ一覧＝ID ごとの行。repo 列なし）。
- 確度: ✅
- 重大度の案: 🔵

### A3-17 Layer 2 の「エントリ一覧」表を誰も更新しない（ヘッダーも書く側で違う）
- 書く側: `CC/skills/xddp-01-init/SKILL.md:204-213`（初期内容に `## エントリ一覧`。列 `ID | タイトル | タグ | CR | 日付`。「（xddp-close 実行後に追記）」）。
- 読む側・追記する側: `promote.py:899-917`（末尾にエントリを足すだけ。表は更新しない。ファイルが無いときのヘッダーは `# 知見ログ: {repo}` の2行だけ：901）。update-knowledge SKILL.md:208-209（「create with header」の中身は決まっていない・末尾に追記）。
- 起きること: Layer 2 の一覧は空のまま残り、「close が追記する」という記述と食い違う。読み手は LLM が全文を読むので、動作への影響は小さい。
- 確度: ✅
- 重大度の案: 🔵

### A3-18 update-knowledge の lesson のエントリの書式が決まっていない
- 書く側: update-knowledge SKILL.md:76-85（工程・タグ・タイトル・発生状況・学んだこと・次回への適用・出典を聞く）、206-209（書式は書いていない。`**CR：**` のメタ行・見出しの形も無い）。
- 読む側: Layer 2 の LLM の読み手。`promote.py:905-908`（見出しが `### LL-NNN：` なら A3-1 の重なりになる）。
- 確度: 🔶
- 重大度の案: 🔵
- 修正案: close Step C の Entry Format（CR 欄は `—`）に揃え、出典の行を決める。

### A3-19 LL テンプレートの「管理場所」が実際のパスと違う
- 書く側: `lessons-learned-template.md:8`（「プロジェクトルート `lessons-learned.md`」）。
- 読む側: 実際のパス `{XDDP_DIR}/lessons-learned.md`（close SKILL.md:106 ほか）。
- 確度: ✅ / 重大度の案: 🔵

### A3-20 Step B・C の「create from template」がテンプレートのパスを示さない
- 書く側: close SKILL.md:74,106。
- テンプレートの実体: `CC/skills/xddp-close/templates/10_improvement-backlog-template.md`、`lessons-learned-template.md`。
- 確度: ✅ / 重大度の案: 🔵（LLM が探すことになる）

### A3-21 Step C の抽出の観点が「(same as before …)」で、参照先が無い
- 書く側: close SKILL.md:110-112（「same as before」の前の版の内容はファイルに無い）。LL を何から抽出するかも書いていない（Step A は INSIGHTS だけを読む：69）。
- 確度: ✅ / 重大度の案: 🔵（CLAUDE.md の「実行時ファイルへの履歴の混入禁止」にも当たる可能性がある）

### A3-22 abort が「update-knowledge 等で backlog に手で登録」と案内するが、update-knowledge に backlog の種別が無い
- 書く側: `CC/skills/xddp-abort/SKILL.md:105-107`。
- 読む側: update-knowledge SKILL.md:15,32（種別は constraint|flow|callgraph|lesson|note|glossary|structure。improvement-backlog は無い。lesson の書き先は Layer 2 で Layer 1 ではない）。
- 確度: ✅ / 重大度の案: 🔵

### A3-23 close のコメントにある Layer 1 の読み手の一覧が足りない
- 書く側: close SKILL.md:96-104（Layer 1 の読み手は 02・05 Step A0）。
- 実際: 06 SKILL.md:95-98、09 SKILL.md:80-83 も Layer 1 を読む。
- 確度: ✅ / 重大度の案: 🔵

## 4. 担当外の指摘
- **担当外（A2）**: promote.py:343 の AI_INDEX「共通ナビゲーション」の行は、Layer 2（`{DOCS_DIR}/{repo}/knowledge/lessons-learned.md`）と並べて「タグ検索例」を示すが、Layer 2 にはタグ別インデックスが無い（promote.py:901 のヘッダー・01-init SKILL.md:204-213）。確度 ✅、重大度の案 🔵。

## 5. 段階2b の候補
なし

## 6. 読んだファイルの一覧と、確認していないこと

**読んだファイル（`{W}` からの相対パス）:**
- `{W}` 外: 指示ファイル common.md（全文）
- 全文: CC/skills/xddp-close/SKILL.md、CC/skills/xddp-close/templates/lessons-learned-template.md、CC/skills/xddp-close/templates/10_improvement-backlog-template.md、CC/skills/xddp-common/procedures/load-lessons-context.md、CC/skills/xddp-close/scripts/collect_insights.py、CC/skills/xddp-update-knowledge/SKILL.md、docs/adr/ADR-0013-close-promote-script.md
- 範囲:
  - promote.py:1-40,630-929,1000-1288（336-350 は grep で）
  - CC/skills/xddp-abort/SKILL.md:85-147
  - CC/agents/xddp-close-knowledge-agent.md:15-114
  - CC/agents/xddp-analyst-agent.md:18-44,60-84
  - CC/agents/xddp-architect-agent.md（grep の結果と 205-218）
  - CC/agents/xddp-test-writer-agent.md:19-45
  - CC/agents/xddp-designer-agent.md（grep の結果）
  - CC/agents/xddp-design-sync-agent.md:17-50
  - CC/skills/xddp-02-analysis/SKILL.md:20-32,68-110（grep の結果も）
  - CC/skills/xddp-05-arch/SKILL.md:142-147,220-236
  - CC/skills/xddp-06-design/SKILL.md:93-104
  - CC/skills/xddp-09-test/SKILL.md:78-83,125-160
  - CC/skills/xddp-01-init/SKILL.md:110-135,195-213
  - CC/skills/xddp-02-analysis/scripts/domain_refs.py:233-236,300-370
  - CC/skills/xddp-04-specout/scripts/specout_bfs.py:6700-6725,7600-7632
  - CC/skills/xddp-04-specout/templates/04_specout-summary-template.md:300-317
  - CC/skills/xddp-05-arch/templates/05_design-approach-memo-approach-template.md:1-75
  - CC/skills/xddp-01-init/templates/00_progress-management-template.md:55-73
  - 各テンプレートの「気づき・提案メモ」節の前後（02・03・06・09・10・05 comparison・11 の8種）
  - CC/skills/xddp-11-specs/SKILL.md:125-190,360-380（grep の結果も）
  - CC/skills/xddp-common/SKILL.md:198-219
  - CC/skills/xddp-rules/code-knowledge-boundary.md:1-60
  - tools/harness/refcheck.py:320-393
  - CC/skills/xddp-close/scripts/tests/test_collect_insights.py:105-200
  - test_promote.py（grep の結果）
  - CC/skills/xddp-common/scripts/crs_model.py:180-200
- grep だけ: パターン `lessons-learned`、`improvement-backlog|INSIGHTS`、`気づき`、`LESSONS_CONTEXT`、成果物のパスの集計、`DSN-{CR}\.md|DSN-{CR}-rev`。

**確認していないこと:**
- スクリプトとテストは実行していない（✅ は両側を読んで確認した、という意味）。
- update-knowledge の lesson、close Step C の採番、Step B の重複の扱いを LLM が実際にどうするかは確認していません（A3-1・A3-2・A3-7・A3-18 の 🔶 の部分）。
- `{XDDP_DIR}` をワークスペースの間で共有する運用かは確認していません（A3-3・A3-4）。
- xddp-specs-mod-agent・xddp-specs-uc-agent が latest-specs を更新するときに、気づきの節の前の行をどう扱うかは確認していません（A3-7）。
- prelim agent が SPO §9 の HTML コメントを残すかは確認していません（A3-14）。
- coder・verifier の出力（CODING・VERIFY）に「気づき・提案メモ」節を書く指示があるかは確認していません（テンプレートは無い）。
- xddp-revise・xddp-feedback・xddp-survey が「気づき・提案メモ」節を書く・消すかは確認していません。
- close-knowledge-agent.md の 114 行目以降（TRS・フロー等。A1 の担当）は読んでいません。
