# 検証者 V2 の報告（原文。PLAN-20261103-contract-audit 段階2a）

> 検証者の最終報告をそのまま載せたもの。統合後の結果は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。`{W}` は監査用の worktree（ecb54c4）、`{V}` は検証者ごとのスクラッチのディレクトリ（どちらもセッションのスクラッチに作り、後で削除）。

# V2 検証報告（A3-1〜A3-23・A3 の担当外・A5-1〜A5-14、抜き取りは A3）

`{W}` = audit-ecb54c4。`CC/` = `ClaudeCode/.claude/`。行番号は ecb54c4 の値。再現はすべて `{V}` = verify-V2 の中で、`PYTHONDONTWRITEBYTECODE=1 python3 -B` を使って行いました。

## 1. 指摘の検証の表

| 指摘 | 判定 | 確度 | 重大度の案 | 根拠 | 重複 |
|---|---|---|---|---|---|
| A3-1 | 確認 | ✅ 再現（前提は🔶） | 🔴 | 書く側は CC/skills/xddp-update-knowledge/SKILL.md:206-209（Layer 2 の LL-NNN から次の番号を採る）。読む側は promote.py:904-908（`### {id}：` だけで重複を判定する）。**再現**: Layer 2 の repo-a に `### LL-004：`（CR 欄 —）を置き、Layer 1 に CR-2 の LL-004（repo-a）を置いて `promote_lessons_learned` を呼んだ。追記されず、unresolved も `[]` だった。前提は update-knowledge が全角コロンの `### LL-NNN：` で書くこと（書式は決まっていない。A3-18） | 関連: A3-18 |
| A3-2 | 確認 | ✅（規則が無いこと）／🔶（起きるか） | 🟡 | close SKILL.md:108（`Extract LL-{NNN}` だけで採番の規則が無い）、150-165（アーカイブ）。照合は promote.py:907 | A3-1 と同じ仕組み |
| A3-3 | 確認（前提は🔶） | ✅ 仕組み／🔶 運用 | 🔴（条件つき） | close SKILL.md:187-276。C0 は他の CR の昇格を `{DOCS}` の pull で取り込む前提になっている。番号の照合は promote.py:907 で、作業場所ごとに独立に採番すると重なる。`{XDDP_DIR}` を共有するかは確認していません | A3-1 |
| A3-4 | 確認（前提は🔶） | ✅ 読んで確認 | 🟡 | promote.py:1009-1015（`shutil.copy2` で丸ごと上書き） | 同じ型: A5-28（rulebook の copy2） |
| A3-5 | 確認 | ✅ 再現 | 🔴 | 書く側は 09-test SKILL.md:142-155（`09_test-spec/cross/TSP-{CR}-cross.md` を 09 tpl で書く。§5 は tpl:137）。読む側は collect_insights.py:170-171（repo だけを列挙）。**再現**: cross TSP に気づきを1行書いて collect を実行した。INSIGHTS に出なかった | — |
| A3-6 | 確認 | ✅ 再現 | 🔴（人が書いた場合だけ） | progress tpl:67-74 は「バックログの入力として活用する」と書く。collect_insights.py:129-192 は progress.md を対象にしない。**再現**: progress.md に書いた気づきが集まらなかった。abort（SKILL.md:105-107）は昇格しないと明記しているので、食い違いではない | — |
| A3-7 | 確認 | ✅ 再現（Step B が重複を除くかは🔶） | 🟡 | collect_insights.py:179-184 は **repos_keys の全部**（affected だけでない）・cross・system の latest-specs を走査する。11 の tpl の表に CR 列は無い（例: 11_module-spec-template.md:108-110）。specs-mod／uc の agent に気づき行の扱いの記述は無い（grep で0件）。**再現**: latest-specs に前の CR の「保留」行を置くと、INSIGHTS に出典の CR が分からない形で入った | — |
| A3-8 | 確認 | ✅ 再現 | 🟡 | promote.py:891-894（`has_cross` が偽なら continue し、unresolved にも足さない）。HAS_CROSS の定義は close SKILL.md:24。domain_refs.py:320-321,364-365 は IS_MULTI で cross の Layer 2 を読む。**再現**: `repo：cross`・has_cross=False で、ファイルが作られず unresolved も空だった | 同じ型: A5-24（rulebook の cross の写し） |
| A3-9 | 確認 | ✅ 再現 | 🟡 | promote.py:884,897（値を検証せずにパスにする）。IDEA は close SKILL.md:81,87 で `全リポジトリ`・判定根拠を許す。**再現**: `repo：全リポジトリ` で `docs/全リポジトリ/knowledge/lessons-learned.md` が作られた | — |
| A3-10 | 確認 | ✅（宣言が無い）／🔶（無視されるか） | 🟡 | 書く側は 02 SKILL.md:107,214。`grep LESSONS CC/agents` で当たるのは designer（52-53,80-84,142）だけで、analyst には一度も出てこない | — |
| A3-11 | 確認 | 同上 | 🟡 | 05 SKILL.md:232。architect-agent に言及は無い | — |
| A3-12 | 確認 | 同上 | 🟡 | 09 SKILL.md:136。test-writer-agent に言及は無い | — |
| A3-13 | 確認 | ✅ 再現 | 🔵 | analyst-agent.md:41,65-66（「なし」と明記させる）。collect_insights.py:203,239-257。**再現**: ANA §7 の「なし」が1件として集まった | — |
| A3-14 | 確認（HTML コメントも ✅ に上げる） | ✅ 再現 | 🔵 | specout_bfs.py:7625-7632（`| 1 | — | なし | — |`）。§9 には `_ensure_script_comment` を使わないが、prelim-agent.md:187 が「§9 はテンプレートのまま残す」としているので、tpl:308 の HTML コメントは残る。**再現**: (a) 「なし」の行の SPO、(b) テンプレートのままの §9（HTML コメントと `{内容}` の行）。どちらも1件として集まった（`_is_placeholder_or_empty` が `<!--` の行を本文とみなす） | — |
| A3-15 | 確認 | ✅ | 🔵 | close SKILL.md:84-90 と backlog tpl:43-51 | — |
| A3-16 | 確認 | ✅ | 🔵 | close SKILL.md:92。backlog tpl の §1 サマリは 16-25、§2 一覧は 29-34 | — |
| A3-17 | 確認 | ✅ | 🔵 | 01-init SKILL.md:204-213。promote.py:899-917（一覧を更新しない。ヘッダーは 901） | — |
| A3-18 | 確認 | 🔶 | 🔵 | update-knowledge SKILL.md:76-85,206-209。見出しとメタ行の書式が決まっていない | A3-1 の前提 |
| A3-19 | 確認 | ✅ | 🔵 | lessons-learned-template.md:8 | — |
| A3-20 | 確認 | ✅ | 🔵 | close SKILL.md:74,106。2つのテンプレートのパスはリポジトリのどこからも参照されていない（grep で0件） | — |
| A3-21 | 一部確認 | ✅ | 🔵 | close SKILL.md:112。「same as before」は前の版の内容を指している。ただし括弧の中に観点の名前4つ（要求分析・方式設計・実装テスト・プロセス）は書いてある。「何から抽出するか」が書かれていない点はそのとおり | 関連: A5-18 |
| A3-22 | 確認 | ✅ | 🔵 | abort SKILL.md:99,105-107。update-knowledge SKILL.md:15,32,207（backlog の種別が無く、lesson の書き先は Layer 2） | — |
| A3-23 | 確認 | ✅ | 🔵 | close SKILL.md:99 は 02・05 だけを挙げる。実際は 06 SKILL.md:96 と 09 SKILL.md:81 も Layer 1 を読む | — |
| A3 担当外（A2: AI_INDEX のタグ検索例） | 否定 | ✅ | — | promote.py:343 | — |
| A5-1 | 確認 | ✅ | 🟡 | close SKILL.md:299（promote.py run。中の :1216 で rulebook を写す）が SKILL.md:312（C3.5 の agent）より前にある。agent は 63-64 で rulebook を書く。AI_INDEX の行（promote.py:527-536）も run の時点のファイルの有無で決まる | — |
| A5-2 | 確認 | ✅ | 🟡 | knowledge-agent.md:63 に IS_MULTI の条件が無い。init SKILL.md:226-232（2つ以上のときだけ写す）、fill SKILL.md:58-62（「生成されません」と言って止まる）、promote.py:991-998（条件なしで写す）、load-steering-context.md:16 | — |
| A5-3 | 確認 | ✅ | 🟡 | init SKILL.md:223 が `CR番号` を {CR} に置き換え、共通 tpl:191 の行に CR が入る。02 SKILL.md:284-285 はその行があればスキップする。起きるのは XDDP にも DOCS にも共通 rulebook が無い最初の CR だけ | — |
| A5-4 | 確認 | ✅（対応のずれ）／🔶（上書きが起きるか） | 監査者 🔴→🟡 | fill SKILL.md:97 の §2 の文字列は repo tpl の §3（89,101,112）のもの。§2 の文字列（64,75）は表に無い。§3 の行も無い。fill:148-155 と 232-234 | 同じ根: A5-6、A5-7 |
| A5-5 | 確認 | ✅ | 🔵 | fill:101。その文字列は repo tpl に無い（モジュールの文字列は tpl:43 の §1） | — |
| A5-6 | 確認 | ✅／🔶 | 🟡 | 共通 tpl の ADR は §3（95）、§5 は禁止事項（152）。fill:88,90,171-192。読む側は verifier:76-78 | — |
| A5-7 | 確認 | ✅／🔶 | 🟡 | fill:157-169 と 194-195 で同じ §6 に2つの規則がある。repo tpl:168 の §6 は禁止事項、cross tpl:150 の §6 はインタフェース変更手順。読む側は verifier:76-78 | — |
| A5-8 | 確認 | ✅／🔶 | 🟡 | fill:197-198,234。工程4 のスキル・agent は rulebook を書かない（xddp-04-specout と specout agent を grep して0件）。共通 tpl:115-128 の既定の原則が消える | — |
| A5-9 | 確認 | ✅／🔶 | 🟡 | fill:134-135。cross tpl の §2 は 42-64、§1 の表と依存関係は 17-38。読む側は 05 SKILL.md:159-161、06 SKILL.md:114-116 | — |
| A5-10 | 確認 | ✅／🔶 | 🟡 | fill:117-198 に cross 専用の規則が無い（§3 の規則はどのファイル用にも無い）。cross tpl:68-169 | — |
| A5-11 | 確認 | ✅ | 🔵 | fill:72-74（`{REPO_NAME}` だけを置き換える）。共通 tpl:104,191、repo tpl:161,187、cross tpl:155,177 | — |
| A5-12 | 確認 | 🔶 | 🟡 | knowledge-agent.md:40-42,64。宛先の表 33-38 は repo tpl の節番号。cross tpl:9 は「末尾に追記」 | — |
| A5-13 | 確認 | ✅ | 🔵 | knowledge-agent.md:34 と repo tpl:151 | — |
| A5-14 | 確認 | ✅ | 🔵 | knowledge-agent.md:35 と repo tpl:116。ただし同じ agent の :48 は正しい名前「コーディング規約・既存パターン」で書いている（ファイルの中でも食い違っている） | — |

### 理由の補足
- **A3 担当外を否定した理由**: promote.py:343 の行は「タグ検索例」を挙げているだけで、タグ別インデックスがあるとは書いていません。同じ行は Layer 1（インデックスあり）も並べて挙げています。Layer 2 のエントリは Layer 1 のエントリを丸ごと写したもので（promote.py:911 `target_lines.extend(entry)`）、`**タグ：** #…` のメタ行を含みます。そのため、タグの文字列での検索はインデックスが無くても成り立ちます。残る弱点は、update-knowledge の lesson にタグの行の書式が無いこと（A3-18）だけです。
- **A3-21 を一部確認とした理由**: 「参照先が無い」はそのとおりです。ただし観点の名前は括弧の中に書いてあり、まったく無いわけではありません。履歴の記述が混ざっている点（「same as before」）は、CLAUDE.md の規則に当たります。
- **A5-4 の重大度を下げた理由**: 起きるのは「人が §2 を書いた」「§3 は未記入」「LLM が節番号で書き込む先を決める」の3つが揃ったときだけです。また Step 5 で人がドラフトを確認し、Step 6 の後に確認を促します。同じ根の A5-6・A5-7 を監査者は 🟡 としているので、それに揃えました。
- **A3-14**: 監査者が 🔶 とした HTML コメントの残りは、prelim-agent.md:187 で残ると決まっています。テンプレートのままの §9 でも1件として集まることを再現したので、✅ に上げます。

## 2. 抜き取り確認の表

| 領域 | 約束（一覧の #） | 使った検索（パターンと範囲） | 漏れ | 漏れの書く側・読む側と食い違いの有無 |
|---|---|---|---|---|
| A3 | #1・#16（Layer 1・Layer 2 のパス） | `grep -rnE "知見ログ\|LESSONS_FILE\|LL-\{\|LL-[0-9N]"` と、`lessons`（lessons-learned・LESSONS_CONTEXT 等を除く）を CC/ 全体で。close・promote・テンプレートは除外 | あり（1件） | promote.py:1081-1097 `append_breaking_warning` が Layer 2 に書く。#16 の書く側の一覧に無い（時期の表には出ている）。食い違いは無い。マーカー `### 破壊的変更警告（{CR}）` は `LL_ENTRY_RE` に当たらず、run の中では promote_lessons_learned（:1197）の後に呼ばれる（:1200-1212）。ほかに xddp-status SKILL.md:106-108 が progress.md の「知見ログ追加」行を読まないと明記しているが、食い違いではない |
| A3 | #22・#23・#24（「気づき・提案メモ」の見出しと対象ファイル） | `grep -rnE "^#{1,6} .*(気づき\|提案メモ)"` を CC/ 全体で。全 agent で `気づき\|提案` を検索。sync-design の rev ファイル（`DSN-{CR}-rev*.md`）の元の作り方 | なし（食い違いのある漏れはない） | architect-agent.md:213 は 1案のときの節を「気づきメモ」と略して書くが、テンプレートの見出し（approach tpl:64 `## 気づき・提案メモ`）が正しいので食い違いではない。sync-design の rev は DSN のインデックス（`DSN-{CR}.md`。節なし）を構造の元にするので、集める対象の外で問題ない |
| A3 | #29（「対応方針」の語彙） | `grep -rnE "今回対応\|次回CR\|\"保留\""` を CC/ 全体で（templates を除く）。SPO §9 の書く側を document・prelim agent で | なし | specout_bfs.py:7628（`保留`）は監査者の一覧にある。document-agent.md:94 は §9 に転記するが、対応方針の値を決めていない（「今回対応」以外として IDEA になるので、Step B の振り分けとは食い違わない） |

## 3. 新たに気付いた食い違い
- **N1（fill-rulebook の `{REPO_PATH}` が未定義）**: CC/skills/xddp-fill-rulebook/SKILL.md:172,174,178 で `{REPO_PATH}` を使っているが、Step 1（:40-42）の Load Config で受け取るのは `WORKSPACE_ROOT`・`XDDP_DIR`・`REPOS_KEYS` だけで、REPOS_MAP も REPO_PATH もどこにも定義が無い。A5-6 は「共通では決まらない」と書いているが、実際は repo 別を含め、どのファイルでも決まらない。ADR 候補の git log は LLM がパスを推測して実行することになる。確度 ✅、重大度の案 🔵〜🟡。
- **N2（A3-7 の範囲が広い）**: collect_insights.py:180 は `affected_repos` ではなく `repos_keys` で回るので、今の CR が触れていない repo の latest-specs の気づきも毎回集める。✅ 再現。A3-7 に含めて扱ってよい。
- **N3（Layer 2 にヘッダーの無いファイルができる）**: `append_breaking_warning`（promote.py:1082-1088）はファイルが無いときに `# 知見ログ` のヘッダーなしで作る。init は通常 Layer 2 を作るので、起きる条件は限られる。🔵、確度 🔶。

## 4. 実行したこと
- 読んだもの: 指示書、A3・A5 の報告、close SKILL（1-30,55-186,187-277,278-414）、promote.py（650-930,975-1020,1081-1097,1185-1225,1251-1270,335-350,520-540）、collect_insights.py（100-345）、update-knowledge SKILL、01-init SKILL（115-132,198-245）、fill-rulebook SKILL（1-250）、close-knowledge-agent（1-115）、load-steering-context、3つの rulebook テンプレート（見出しとプレースホルダー）、backlog・LL テンプレート、progress テンプレート、abort SKILL（92-110）、09-test SKILL（140-160）、05・06・09・02 の agent 呼び出し部分、verifier-agent（72-80）、specout_bfs.py（6680-6745,7600-7635）、SPO tpl（300-312）、domain_refs.py（300-370）、architect-agent（205-220）、sync-design SKILL と agent の該当部分。
- 再現（すべて `{V}` の中）:
  - `{V}/a31`: `promote.promote_lessons_learned` を import して呼び、A3-1・A3-8・A3-9 を再現した。
  - `{V}/ci`・`{V}/ci2`: `collect_insights.py collect` を実行し、A3-5・A3-6・A3-7・A3-13・A3-14（なしの行と、テンプレートのままの §9）を再現した。
- `cd {W} && git status --short` の結果は空（終了コード 0）。`__pycache__` も作られていない。
- 確認していないこと:
  - LLM の実際の振る舞い（採番・節の当て方・置き換えの範囲）。
  - `{XDDP_DIR}` を作業場所の間で共有する運用かどうか（A3-3・A3-4）。
  - A5-15〜A5-28（割り当て外）。
  - promote.py の `run` 全体の通しの実行（関数を直接呼んだだけ）。
