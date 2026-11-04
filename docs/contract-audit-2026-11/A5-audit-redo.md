# 監査者 A5 の報告（やり直し版・原文。PLAN-20261103-contract-audit 段階2a）

> 抜き取り確認の漏れを受けた人の判断で行ったやり直しの監査の最終報告をそのまま載せたもの（検証前）。前回の版は [A5-audit.md](A5-audit.md)。検証結果と統合後の重大度は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。

# A5 project-rulebook 監査報告（やり直し。対象 ecb54c4。`CC/` = `ClaudeCode/.claude/`）

この報告は前回の `audit-reports/A5.md` を置き換えます。行番号は ecb54c4 の値です。読んだのは監査用の worktree の中だけです。書き込み・スクリプトの実行はしていません。

## 0. 前回からの変更
- **新しく足した約束:** #8（cross ファイルの生成条件を repo 別の #7 から分けた）、#13（C3.5 のテンプレートからの作成）、#17、#20、#22、#34、#36（INCLUDE_CROSS）、#38（RULEBOOK_CONTEXT を渡す呼び出し・渡さない呼び出し）、#39、#55（fill の repo パス）、#56（fill の upstream/downstream）、#57、#60（cross の C6 の失敗の報告）
- **新しく見つけた書く側・読む側:**
  - #1: fill:72（テンプレートからの作成）、02:348、arch.rules:114・design.rules:125（05:57・06:155 から渡される）
  - #3: fill:12,19,62,73、init:268（案内）、promote.py:534,535、knowledge-agent:41（説明）、test_promote.py:542（参考）。V3 が抜き取りで見つけた分を含む
  - #35: 07:110-111・08:108-109（説明の文）、xddp-templates/xddp.skill-template.md:35,44（開発用のひな形。説明のみ）。V3 が見つけた分を含む
  - #38: 05:279,331,444、06:251,303,377,467（RULEBOOK_CONTEXT を渡さない呼び出し）、07:200・08:159・09:151（cross の呼び出し）
  - Step D の説明: close:357-370（「rulebook に人が直接書く」の案内。説明のみ）
- **新しい指摘:** A5-29（V2 の N1 を取り込んだ。fill-rulebook が repo のパスを受け取らない）、A5-30（INCLUDE_CROSS を使う呼び出し元が無い）、A5-31（cross の rulebook の写しの失敗が報告されない）、A5-32（fill の `upstream-repos`/`downstream-repos` がどこにも定義されていない）、A5-33（designer・architect の修正・追加の呼び出しが RULEBOOK_CONTEXT を渡さない）
- **取り下げた指摘:** なし
- **番号を変えずに内容を直した指摘:**
  - A5-8: repo 別ファイルの §4 にも同じ置き換えが起きることを追記した。その結果、C3.5 の upsert 先のサブセクションも消える
  - A5-14: 同じ agent の :48 は正しい名前を書いている（V2 の補足）。ファイルの中でも名前が食い違っている
  - A5-18: シングル構成でも「→ project-rulebook-{repo}.md へ追記推奨」と注記する点を追記した
  - A5-19: 行番号を 02:333,338 に直した
  - A5-20: 行番号を 02:314 に直した
  - A5-26: 「移行ガイド」の節は存在する（V3 の訂正。`11_cross-interface-spec-template.md:115`）。残る食い違いはパスの形だけ
  - A5-27: 行番号を README.md:357 に直した
  - A5-4: 重大度の案を 🟡 にした（V2 の判断に揃えた）

## 1. 確認した約束の一覧

見つけた方法の略記（範囲はすべて `CC/skills CC/agents`。`tests/` も検索し、テストは参考として扱った）:
- S1 (1)(3) `grep -rnE 'project-rulebook|RULEBOOK_CONTEXT'`
- S2 (1) `grep -rniE 'rulebook|steering'`（S1 の行を除く）
- S3 (1) `grep -rn 'rulebook-cross\|cross/project-rulebook\|rulebook_cross\|cross_rb'`
- S4 (1) `grep -rn '}/project-rulebook\|docs / repo / "project-rulebook\|docs / "project-rulebook'`
- S5 (2) `grep -rnE 'ドメイン制約|禁止事項・注意事項|アーキテクチャ決定記録|既存パターン・慣習|インタフェース変更手順|API バージョニング|モジュール構成メモ|リポジトリ構成|コーディング規約・既存パターン|インタフェース命名規則'`
- S6 (3) `grep -rn 'INCLUDE_CROSS\|CROSS_RULEBOOK'`
- S7 (3)(5) `grep -rn -A4 'Load Steering Context'`
- S8 (3) `grep -rn 'DOMAIN_CONSTRAINTS'`
- S9 (4) `grep -rn 'ADR-NNN\|ADR-候補'`・`grep -rln '命名規約\|ADR-NNN\|# ❌'`
- S10 (3) promote.py の中で `grep -n 'promote_rulebooks\|_common_knowledge_rows\|def write_output_file\|def _record_failure\|"cross"'`
- S11 (5) 各スキルで `grep -n 'FIXER_AGENT\|subagent_type=xddp-(architect|designer|coder|verifier|test-writer|design-sync|chd-sync)'` を探し、呼び出しのブロックを読んだ
- S12 (2) `grep -n 'REPO_NAME: cross' CC/skills/*/SKILL.md`
- S13 (3) `grep -rn 'upstream-repos\|downstream-repos\|REPO_PATH\|REPOS_MAP'`（fill-rulebook・xddp_config.py・config テンプレート）
- S14 (4) `grep -rn 'YYYY-MM-DD\|CR番号\|{REPO_NAME}\|{CR}'`（3つのテンプレート）
- S15 (5) 参照のたどり（行は各セルに書いた）
- S16 (2) `grep -rn -i 'rulebook\|規約\|禁止事項' reviewer-checklists agents/xddp-reviewer.md`（0件。レビュアーは rulebook を読まない）

| # | 約束 | 書く側（ファイル:行・節） | 読む側（ファイル:行・節） | 見つけた方法 | 結果 |
|---|---|---|---|---|---|
| 1 | 共通ファイルのパス `{XDDP_DIR}/project-rulebook.md` | init:221-223（4.6）、fill:51,64,72、02:279,348（B3） | load-steering:15、load-domain:16、05:155、promote.py:984。arch.rules:114・design.rules:125（05:57・06:155 から渡る）。説明のみ: init:266、common SKILL:239、fill:3,7,10,17、promote.py:4,344 | S1・S4・S15 | なし |
| 2 | repo 別ファイルのパス `{XDDP_DIR}/project-rulebook-{repo}.md` | init:229-231、fill:53,74、knowledge-agent:63 | load-steering:16、promote.py:531,992。説明のみ: init:267、fill:11,18、close:348 | S1・S4 | なし |
| 3 | cross ファイルのパス `{XDDP_DIR}/project-rulebook-cross.md` | init:236-238、fill:12,52,73、knowledge-agent:64 | load-steering:17、05:155、06:110、promote.py:534,1000。説明のみ: init:268、fill:19,62、close:352、knowledge-agent:41。参考: test_promote.py:542 | S1・S3・S6 | なし |
| 4 | 共通ファイルの DOCS の写し `{DOCS}/project-rulebook.md` | promote.py:988 | init:222 | S4・S10 | なし |
| 5 | repo 別の写し `{DOCS}/{repo}/project-rulebook.md` | promote.py:996 | init:230。AI_INDEX のリンク promote.py:533 は A2 | S4・S10 | なし |
| 6 | cross の写し `{DOCS}/cross/project-rulebook.md` | promote.py:1004 | init:237。AI_INDEX のリンク promote.py:535 は A2 | S3・S10 | なし |
| 7 | repo 別ファイルの生成条件（REPOS が2つ以上） | init:226-227、fill:58-60（条件あり）、knowledge-agent:63（条件なし） | load-steering:16、promote.py:991-998（条件なし）、init:226-232（DOCS から戻す） | S1・S15 | あり A5-2 |
| 8 | cross ファイルの生成条件（REPOS が2つ以上） | init:234-235、fill:54,61-62 | knowledge-agent:64（条件なし）、load-steering:17 | S1・S3 | なし（🔶 knowledge-agent に条件は無いが、シングル構成で `repo: cross` の LL が付く根拠は close:134-136 から読めない） |
| 9 | 共通テンプレートのプレースホルダー `YYYY-MM-DD`・`CR番号` | 共通 tpl:104,191 | init:223（置き換える） | S1・S14 | あり A5-22、A5-3 |
| 10 | repo テンプレートのプレースホルダー `{REPO_NAME}`・`YYYY-MM-DD`・`{CR}` | repo tpl:1,17,161,187 | init:231 | S14 | あり A5-22 |
| 11 | cross テンプレートのプレースホルダー `YYYY-MM-DD`・`{CR}` | cross tpl:155,177 | init:238 | S14 | あり A5-21 |
| 12 | fill がテンプレートから作るときのプレースホルダー | 3つのテンプレート | fill:72-74 | S1・S14 | あり A5-11 |
| 13 | C3.5 がテンプレートから作るとき | repo・cross テンプレート | knowledge-agent:63-64 | S1・S14 | あり A5-16 |
| 14 | §1.6 の見出し名 `## 1.6 ドメイン制約` | 共通 tpl:40、02:300,324,341 | load-domain:16-17、analyst:29 | S5・S8 | なし |
| 15 | §1.6 の表の4列と6種別 | 共通 tpl:46-53 | 02:341-346（B3 の追記） | S5 | なし |
| 16 | §1.6 の「未記入」の判定 | 共通 tpl:48-53 | load-domain:19-20 | S5 | あり A5-23 |
| 17 | DOMAIN_CONSTRAINTS が空なら渡さない | 02:77-79,110,217 | analyst:29,124,130 | S8 | なし |
| 18 | B3 の追記先の見出し（共通 §2・§3・§4・§5） | 共通 tpl:60,95,111,152 | 02:296-299,312,338-339 | S5・S15 | なし |
| 19 | B3 の追記先のコードブロック | 共通 tpl §2（:63-89）・§4（:119-146） | 02:333,338 | S5 | あり A5-19 |
| 20 | B3 の ADR の書式 `### ADR-NNN:`（最大＋1） | 共通 tpl:99-105 | 02:339-340 | S9 | なし |
| 21 | §7 の見出し `## 7. 変更履歴` | 共通 tpl:187、repo:183、cross:173 | 02:284,348、knowledge-agent:69 | S1・S15 | なし |
| 22 | §7 の列と行の書式 | 共通 tpl:189（`更新者`）、repo:185・cross:175（`更新CR`） | 02:349-351（`{TODAY}\|{CR}\|…`）、knowledge-agent:69（書式の指定なし） | S15 | なし（列名は違うが、どの読む側も列名を使わない） |
| 23 | B3 の冪等性の判定（§7 に {CR} の行がある） | init:223（初期行に {CR} を入れる）、共通 tpl:191 | 02:284-285 | S1・S14 | あり A5-3 |
| 24 | 禁止事項の行の書式 `# ❌`/`# ⚠️` | 共通 tpl:156-161、repo:172-177、02:314 | knowledge-agent:55-57、verifier:76-78 | S9・S5 | あり A5-20 |
| 25 | B3 の repo 別の候補を C3.5 へ渡す | 02:287 | knowledge-agent:23,29（LL だけを読む） | S1 | あり A5-18 |
| 26 | C3.5 の宛先の Section 5 の名前 | knowledge-agent:34 | repo tpl:151 | S5 | あり A5-13 |
| 27 | C3.5 の宛先の Section 4 の名前 | knowledge-agent:35（:48 は正しい名前） | repo tpl:116 | S5 | あり A5-14 |
| 28 | C3.5 の宛先 `### テストパターン` | knowledge-agent:36 | repo tpl:139 | S15 | なし |
| 29 | C3.5 の宛先の Section 6 の名前とルール行 | knowledge-agent:37,54-58 | repo tpl:168,172-177 | S5 | なし |
| 30 | C3.5 の Section 4 のテーマ見出しを鍵にした upsert | knowledge-agent:49-52 | repo tpl:120,130,139 | S15 | あり A5-15 |
| 31 | C3.5 で cross へ追記する節 | knowledge-agent:40-42,64 | cross tpl:9,17-177 | S3 | あり A5-12 |
| 32 | LL の `repo:` の値（repo名/cross/unknown）による振り分け | close:120,134-136 | knowledge-agent:62-65 | S15（knowledge-agent:63 から close を参照） | なし |
| 33 | LL のタグと C3.5 の宛先の表 | LL tpl:17,20 | knowledge-agent:33-38 | S15（`find CC -name '*lessons*'`） | あり A5-17 |
| 34 | C3.5 の入力 `CR_LESSONS_FILE`（パス。無ければ取り込まない） | close:284（extract-ll `--out`）、:324 | knowledge-agent:23,29 | S15 | なし |
| 35 | RULEBOOK_CONTEXT の読み込み方（共通＋repo 別を repo ごとに読む） | load-steering:9-19 | 05:189-192、06:197-200、07:126-129,158-161、08:112-115、09:109-112,174-177、10:208-210、feedback:208-210、sync-design:62-63。説明のみ: 07:110-111、08:108-109、skill-template:35,44 | S1・S2・S7 | なし |
| 36 | `INCLUDE_CROSS`（cross も読む） | load-steering:12,17 | 呼び出し元なし（S6 で0件） | S6・S7 | あり A5-30 |
| 37 | RULEBOOK_CONTEXT の中身（agent の Inputs の説明） | load-steering:15-17 | architect:34、designer:46、coder:30、verifier:32、test-writer:32-34、design-sync:29-30、chd-sync:34-35 | S1 | なし |
| 38 | RULEBOOK_CONTEXT を agent に渡す | 渡す: 05:233、06:214、07:142,185、08:148、09:135,199、10:236、feedback:238、sync-design:90 | 渡さない: 05:279(A-ripple),331(B の修正),444(B3)、06:251(A2),303(A2.5),377(A3),467(B の修正) | S11 | あり A5-33 |
| 39 | RULEBOOK_CONTEXT が空のとき（空で続ける） | load-steering:18 | 5つの agent は `(optional)`。design-sync:29・chd-sync:34 は印が無いが、呼び出し元は常に渡す（sync-design:90、feedback:238） | S1 | なし |
| 40 | verifier が使う禁止事項の節番号（共通 §5／repo §6） | 共通 tpl:152、repo:168 | verifier:76-78 | S5 | なし |
| 41 | test-writer が使う節名「禁止事項・注意事項」 | 共通 tpl:152、repo:168 | test-writer:98-100 | S5 | なし |
| 42 | 05 cross が使う節（共通 §2 命名規約／cross §2・§3） | 共通 tpl:60、cross:42,68 | 05:155-162 | S5・S6 | なし |
| 43 | 06 cross が使う節（cross §2・§6） | cross:42,150 | 06:110-117 | S5・S6 | なし |
| 44 | arch・design のルールからの参照 | 共通 tpl | arch.rules:114、design.rules:125 | S1・S15（05:57、06:155、architect:47、designer:50） | なし |
| 45 | fill の未記入判定のプレースホルダー（共通） | 共通 tpl:16-21,33,70,81,91,107,148,164,183 | fill:82-91 | S1・S5 | なし |
| 46 | fill のプレースホルダー（repo §2） | repo tpl:64,75（§2）／:89,101,112（§3） | fill:97 | S1・S15 | あり A5-4 |
| 47 | fill のプレースホルダー（repo §6 のモジュール構成） | repo tpl（該当の文字列なし。モジュールは :43） | fill:101 | S1 | あり A5-5 |
| 48 | fill のプレースホルダー（repo §1・§4・§5・§6 禁止事項） | repo tpl:24,128,164,179 | fill:96,98-100 | S1 | なし |
| 49 | fill のプレースホルダー（cross §1〜§6） | cross tpl:23,64,101,131,146,169 | fill:103-111 | S1・S3 | なし |
| 50 | fill のドラフト規則 §5(ADR)・共通 §3 | 共通 tpl:95,152 | fill:88,171-192 | S9・S5 | あり A5-6 |
| 51 | fill のドラフト規則 §6（2つある） | 共通 tpl:168、repo:168、cross:150 | fill:157-169,194-195 | S5 | あり A5-7 |
| 52 | fill のドラフト規則 §4（specout が書く） | 共通 tpl:111-148、repo:116-147 | fill:197-198,234 | S1（specout 側に rulebook の記述が無いことも S1 で確認） | あり A5-8 |
| 53 | fill のドラフト規則（cross §1/§2） | cross tpl:17-64 | fill:134-135 | S3・S5 | あり A5-9 |
| 54 | fill のドラフト規則（cross §3〜§6） | cross tpl:68-169 | fill:117-198 | S3 | あり A5-10 |
| 55 | fill が調べる repo のパス | Load Config の出力（xddp_config.py:108,216 `REPOS_MAP`） | fill:42（WORKSPACE_ROOT・XDDP_DIR・REPOS_KEYS だけを受け取る）、:131-132,137-142,148-149,172-178（`{REPO_PATH}`） | S13 | あり A5-29 |
| 56 | fill の cross §1 の `upstream-repos`/`downstream-repos` | 定義なし（xddp_config.py・config tpl・CC 全体で0件） | fill:135 | S13 | あり A5-32 |
| 57 | fill の書き込みの範囲（見出しから次の `---` まで） | 3つのテンプレート（節の間に `---`） | fill:234 | S15 | なし |
| 58 | promote の cross の写しの条件（`has_cross`） | knowledge-agent:64、fill:52（cross の成果物によらず更新） | promote.py:999-1006、close:23（HAS_CROSS の定義） | S3・S10 | あり A5-24 |
| 59 | close Step D の昇格の報告 | promote.py:982-1006（ファイルがあるときだけ写す） | close:348,352 | S1・S10 | あり A5-25 |
| 60 | cross の C6 の失敗の報告 | promote.py:1006（`repo_results["cross"]`） | promote.py:1111（affected_repos だけを出力）、close:20-22（AFFECTED_REPOS は REPOS_KEYS）、close:335-352 | S10 | あり A5-31 |
| 61 | 書く時期: C3.5 → C6 の写し | knowledge-agent（close:310-331） | promote.py:1216（close:299） | S2・S10・close を通読 | あり A5-1 |
| 62 | DOCS の rulebook の上書き（同時に進む別の作業場所） | promote.py:988,996,1004（copy2） | close:207-277（C0。latest-specs だけを扱う） | S4・close を通読 | あり A5-28 |
| 63 | cross テンプレート §6 が指す仕様書のパス | 11-specs:298-300（`cross/interfaces/{interface-kebab}/spec.md`）、11_cross-interface-spec-template.md:115（`## 6. 移行ガイド`） | cross tpl:165 | `grep -rn '移行ガイド\|interfaces/' CC/skills` | あり A5-26 |
| 64 | README の §1.5 の説明 | 共通 tpl:26-36 | README.md:357（:302 も） | `grep -n rulebook README.md` | あり A5-27 |

## 2. 時期の約束の表

| 書く側（スキル・Step） | 読む側（スキル・Step） | 順序の根拠（ファイル:行） | 結果 |
|---|---|---|---|
| init Step 4.6（XDDP の rulebook を作る） | 02 A0.5・B3、05〜10・feedback・sync-design（Load Steering） | init:251（次のコマンドは `/xddp-02-analysis`）。工程の番号順 | なし |
| fill-rulebook（随時） | 02・05〜10 の読み込み | fill:247（specout の前を案内）。順序の制約は無い | なし（シングル構成で repo 別・cross を拒否する点は A5-2） |
| 02 B3（共通に追記） | 05〜10 の Load Steering | 02:270（B3）→ 02:353-357（Step C。次は `/xddp-03-req`） | なし |
| 02 B3（§1.6 に追記） | 02 A0.5（§1.6 を読む） | 02:75（A0.5）が 02:270（B3）より前 | 食い違いではない（その CR の追記は次の CR から効く） |
| 02 B3（repo 別の候補） | close C3.5 | 受け渡しの手段が無い（02:287） | A5-18 |
| close Step C（LL を書く） | extract-ll → C3.5（CR_LESSONS_FILE） | close:94-165 → :284 → :312,324 | なし |
| close C3.5（repo 別・cross に upsert） | close C6（promote.py が DOCS へ写す） | close:299 の promote.py run が close:312 の C3.5 より前。promote.py:1216 | **逆順 A5-1** |
| close C6（DOCS へ写す） | 次の CR の init 4.6（XDDP に無ければ DOCS から写す） | init:221-238 | repo 別はシングル構成で戻らない（A5-2） |
| close C6（DOCS を copy2 で上書き） | 別の作業場所の close C0（DOCS の pull） | close:207-277 | 競合を検出しない（A5-28） |
| close C3.5 | 同じ作業場所の次の CR の Load Steering | 同じ `{XDDP_DIR}` を読む（load-steering:15-17） | なし |

## 3. 指摘

### A5-1 close で C3.5 の upsert が DOCS への写し（C6）の後に行われる
- 約束: close で更新した rulebook を `{DOCS}` へ昇格する。
- 書く側: `CC/agents/xddp-close-knowledge-agent.md:27-69`（C3.5）。`CC/skills/xddp-close/SKILL.md:310-331` で呼ぶ。
- 読む側: `promote.py:982-1006`（`promote_rulebooks`。`run` の中の :1216 で呼ぶ）。close:299 で実行する。AI_INDEX の行（promote.py:527-536）も同じ時点で作る。
- 食い違い: C2〜C7（C6 の写しを含む）を先に実行し、その後に C3.5 を起動する。C3.5 が今の CR の LL から書いた内容は、その close では DOCS に写されない。close:348,352 は「昇格」と報告する。
- 起きること: DOCS の rulebook は、1つ前の CR の内容のまま残る。`{XDDP_DIR}` が引き継がれない場合（新しい作業場所が init:221-238 で DOCS から写す場合）、その内容は失われる。C3.5 が初めて作った repo 別・cross のファイルは、DOCS への写しも AI_INDEX の行も作られない。close を再実行すると前回の C3.5 の分は写る。
- 確度: ✅（V2 も確認）。受け入れた制限とする ADR は無い（`grep -rn 'C3\.5' docs/adr/` で当たるのは ADR-0013:36 の extract-ll の説明だけ）。
- 重大度の案: 🟡
- 修正案: C3.5 の後に rulebook の写しだけを再実行する。または C3.5 を promote.py run の前に移す。

### A5-2 シングルリポジトリでも C3.5 が `project-rulebook-{repo}.md` を作る
- 書く側: knowledge-agent:63（IS_MULTI の条件が無い）。close:134-135 はシングル構成でも `repo: {repo-name}` を付ける。
- 読む側: init:226-232（2つ以上のときだけ DOCS から戻す）、fill:58-60（「生成されません」と言って止まる）、load-steering:16（ファイルがあれば読む）、promote.py:991-998（条件なしで写す）。
- 起きること: 新しい作業場所では、LL から入れた repo の規約が RULEBOOK_CONTEXT から黙って消える。fill-rulebook は、実在するファイルについて「生成されません」と案内する。
- 確度: ✅
- 重大度の案: 🟡
- 修正案（決めない）: シングル構成では共通 rulebook へ送る。または init の戻す条件を外す。

### A5-3 最初の CR では 02 Step B3 が必ずスキップされる
- 書く側: init:223 が `CR番号` を `{CR}` に置き換える。その結果、共通 tpl:191 が `| {today} | {CR} | 初期作成 |` になる。
- 読む側: 02:284-285（その行があれば「Step B3 をスキップします」）。quick（02:183-186）も同じ。
- 起きること: XDDP にも DOCS にも共通 rulebook が無い CR では、要求書から出した規約・ADR・禁止事項・ドメイン制約の候補が、提示されないまま失われる。表示される理由が実態と合わないので、人は処理済みと誤解しやすい。
- 確度: ✅
- 重大度の案: 🟡
- 修正案: 印（例「（req より抽出）」、02:350）で照合する。または初期行に {CR} を入れない。

### A5-4 fill-rulebook が repo 別の §2 の判定に、§3 のプレースホルダーを使っている
- 書く側: repo tpl。§2 のプレースホルダーは :64,:75、§3 のものは :89,:101,:112。
- 読む側: fill:97（§2 として §3 の文字列を挙げる。§3 の行は無い）、:148-155（§2 命名規約のドラフト）、:234（節の本文を丸ごと置き換える）。
- 起きること: §3 が未記入だと §2 と判定する。命名規約のドラフトで §2（アーキテクチャ概要）を置き換えることがあり、§3 はいつまでも埋まらない。
- 確度: 節の対応がずれていることは ✅。置き換えが実際に起きるかは 🔶。
- 重大度の案: 🟡（V2 に揃えた）

### A5-5 fill の repo §6 の行に、テンプレートに無いプレースホルダーがある
- fill:101。repo tpl にこの文字列は無い（モジュールの記述は §1 の :43）。動作への影響は無い。✅ 🔵

### A5-6 fill の「§5 (ADR)」の規則が、共通ファイルでは §5 禁止事項に当たる
- 共通 tpl では、ADR は §3（:95）、§5 は禁止事項（:152）。fill:171-192 は §5 に ADR の候補を書く。共通 §3（fill:88 で未記入と判定する）にはドラフト規則が無い。
- 起きること: 共通の禁止事項の節が ADR の候補で置き換わる。この節は verifier:76-78 と test-writer:98-100 が読む。
- 確度: ✅／🔶。重大度の案: 🟡

### A5-7 fill に §6 の規則が2つあり、repo 別の §6 禁止事項がモジュール構成か注記で置き換わる
- fill:157-169（§6 モジュール構成）と :194-195（§6 該当なし）。repo tpl:168 の §6 は禁止事項、cross:150 の §6 はインタフェース変更手順。
- 起きること: verifier:77 が読む repo の §6 から禁止事項が消える。
- 確度: ✅／🔶。重大度の案: 🟡

### A5-8 fill の §4 の注記「スペックアウトで記入される」に対応する処理が無く、§4 を置き換える
- fill:197-198 が注記を入れ、:234 で節を丸ごと置き換える。工程4 のスキルと agent は rulebook を書かない（S1 で0件）。
- 起きること: 共通 tpl:115-128 の既定のエラーハンドリングの原則が消える。§4 は以後だれも埋めない。**（追記）** repo 別の §4（repo tpl:116-147）にも同じ規則が当たる。C3.5 が upsert の先にする `### テストパターン` 等のサブセクションも消えるので、C3.5 は新しいサブセクションを足すことになる（knowledge-agent:52）。
- 確度: ✅（置き換えは 🔶）。重大度の案: 🟡

### A5-9 fill の「§1 / §2 Cross-repo overview」が、cross の §2 API バージョニング規約に当たる
- fill:134-135。cross tpl の §2 は :42-64（SemVer の表を含む）、リポジトリの表と依存関係は §1（:17-38）。
- 起きること: cross §2 が、リポジトリの一覧と依存関係で置き換わる。05:161 と 06:116 は cross §2 を breaking の判定に使う。
- ✅／🔶 🟡

### A5-10 fill に cross §3〜§6 用のドラフト規則が無い
- fill:117-198 の規則は節番号だけで当てる。そのため cross §4 には specout の注記、§5 には ADR の候補、§6 にはモジュール構成か注記が入る。06:116 が読む §6 インタフェース変更手順が、無関係の内容になる。
- ✅／🔶 🟡

### A5-11 fill がテンプレートから作るとき、日付と CR のプレースホルダーを置き換えない
- fill:72-74（repo は `{REPO_NAME}` だけを置き換える）。共通 tpl:191、repo:187、cross:177。✅ 🔵

### A5-12 C3.5 で cross に追記する節が決まっていない
- knowledge-agent:40-42 は「Append を維持」とだけ書く（:64 も同じ）。宛先の表（:33-38）は repo の節番号で書かれていて、cross tpl の節の意味と合わない。cross tpl:9 は「末尾に追記」と書く。
- 起きること: 05・06 の cross の処理が読む §2・§3・§6 に入らないか、別の意味の節に混ざる。
- 🔶 🟡

### A5-13 C3.5 の宛先の表の Section 5 の名前がテンプレートと違う
- knowledge-agent:34「ADR・設計判断記録」、repo tpl:151「アーキテクチャ決定記録（ADR）」。✅ 🔵

### A5-14 C3.5 の宛先の表の Section 4 の名前がテンプレートと違う
- knowledge-agent:35「既存パターン・慣習」（共通 tpl の名前）、repo tpl:116「コーディング規約・既存パターン」。同じ agent の :48 は正しい名前で書いている。✅ 🔵

### A5-15 C3.5 の Section 4 のテーマ見出しの例が、テンプレートの見出しと一致しない
- knowledge-agent:50 の例は `エラーハンドリング`。repo tpl:120 の見出しは `### このリポジトリ固有のエラーハンドリング`、:130 は `### 非同期処理パターン`。完全一致で照合すると、同じテーマの節が重ねて足される。🔶 🔵

### A5-16 C3.5 がテンプレートから作るとき、どのテンプレートを使い何を置き換えるかが決まっていない
- knowledge-agent:63-64「create if absent from template」。置き換える対象は repo tpl:1,17,161,187、cross tpl:155,177。✅ 🔵

### A5-17 LL のタグ `#レビュー` が C3.5 の宛先の表に無い
- LL tpl:17 にある。knowledge-agent:33-38 には、宛先の行にも Not mapped の行にも無い。✅ 🔵

### A5-18 02 B3 の「repo 別は C3.5 で行う」に、受け渡しの仕組みが無い
- 書く側: 02:287。提示の一覧に「→ project-rulebook-{repo}.md へ追記推奨」と注記するだけで、どこにも保存しない。シングル構成でもそう注記する（init はそのファイルを作らない。A5-2 と関係）。
- 読む側: knowledge-agent:23,29。読むのは `CR_LESSONS_FILE` だけ。
- 起きること: 要求書から見つけた repo 別の規約は、人が手で書くか、close Step C の LL に拾われない限り、repo 別ファイルに入らない。
- 確度: 🔶（close:110-112 は LL をどこから抜き出すかを具体的に書いていない）。重大度の案: 🟡

### A5-19 02 B3 の「既存のコードブロックの末尾に追記」で、どのブロックかが決まらない
- 02:333,338。共通 §2 にはコードブロックが3つ（tpl:63-68,73-79,84-89）、§4 にも3つ（:119-128,133-137,140-146）ある。✅ 🔵

### A5-20 禁止事項の行の書式が、書く側どうしで違う
- 02:314 の追記案は `❌ …`（`# ` なし）。共通 tpl:157-161 と knowledge-agent:55-57（`# ❌/⚠️` の行を鍵にする）は `# ❌`。共通ファイルは C3.5 の対象外なので、今は upsert の鍵としては衝突しない。✅ 🔵

### A5-21 init の `{CR}` の置き換えで、cross tpl §6 の一般的な手順の文に CR 番号が入る
- init:238。cross tpl:155「変更する CR の CRS-{CR}.md に…」が、初期化した CR の番号で固定される。06:116 はこの §6 を読む。✅（すべての出現を置き換えるかは 🔶） 🔵

### A5-22 init の置き換えで、ADR の書式のコメントに日付と CR が入る
- init:223,231。共通 tpl:104、repo tpl:161。✅（同上） 🔵

### A5-23 load-domain-constraints の「未記入」の判定が、テンプレートの §1.6 の行の形に合わない
- load-domain:19-20 は「全行がプレースホルダー `{...}` のみ」なら空とする。共通 tpl:48-53 の各行は種別の列に文言が入っている。B3（02:341）は行を足すだけなので、プレースホルダーの行は残る。
- 起きること: 未記入のテンプレートでも空と判定されず、analyst に渡るおそれがある。🔶 🔵

### A5-24 cross の写しが、今の CR の cross の成果物の有無（`has_cross`）で決まる
- promote.py:999-1006。HAS_CROSS は「IS_MULTI かつ CR に cross の成果物がある」（close:23）。一方、knowledge-agent:64 と fill:52 は、cross の成果物によらず cross ファイルを更新する。AI_INDEX の cross の行（promote.py:534）も同じ条件。
- 起きること: cross の成果物を持たない CR の close では、更新した cross ファイルが写されない。✅ 🔵

### A5-25 close Step D が、写していない rulebook も「昇格」と報告する
- close:348,352 は条件なしで「昇格」と書く。promote.py:992-1006 はファイルがあるときだけ写す。✅ 🔵

### A5-26 cross テンプレート §6 が、存在しないパスの形を指す
- cross tpl:165 は `cross/interfaces/{name}-spec.md`。11-specs:298 が作るのは `cross/interfaces/{interface-kebab}/spec.md`。「移行ガイド」の節は `11_cross-interface-spec-template.md:115` に**ある**（前回の「節が無い」は誤り）。仕様書の側は A4 の担当。✅ 🔵

### A5-27 README の §1.5 の説明がテンプレートと合わない
- README.md:357 は「1.5 にリポジトリ一覧・依存関係・共有インタフェースを記入」と書く（:302 も同じ趣旨）。共通 tpl:26-36 の §1.5 は「リポジトリ名・役割・主要技術」の表だけで、依存関係と提供・消費インタフェースは cross tpl:17-38 にある。✅ 🔵

### A5-28 DOCS の rulebook を、競合を検出せずに丸ごと上書きする
- promote.py:988,996,1004（`shutil.copy2`）。close C0（:207-277）は DOCS を pull するが、rulebook を XDDP へ取り込まない。競合の検出（C0-4）は latest-specs だけを対象にする。
- 起きること: 同じ DOCS を共有する別の作業場所が先に昇格させた rulebook の更新を、後から close した側が上書きして消す。
- 🔶（複数の作業場所で1つの DOCS を共有する運用が前提。init:222「knowledge hub priority」がその運用を示唆する）。🟡

### A5-29（新）fill-rulebook が repo のパスを受け取らず、`{REPO_PATH}` が未定義
- 約束: fill-rulebook が各 repo を調べてドラフトを作る。
- 書く側: `## Load Config` の出力に `REPOS_MAP` はある（xddp_config.py:108,216）。
- 読む側: fill:42 は「→ let WORKSPACE_ROOT, XDDP_DIR, REPOS_KEYS（他の戻り値は本スキルでは未使用）」と書く。それなのに :172,174,178 で `{REPO_PATH}` を使い、:131-132（repo の root files）、:137-142（§1.5 の各 repo）、:148-149（各 repo のファイル）でも repo の場所を前提にしている。REPO_PATH の定義はどこにも無い。
- 起きること: ADR の候補を出す git log と、コード調査の対象のディレクトリを、LLM が推測で決める。別の場所（作業場所のルート等）を調べたドラフトを人に示すことがある。
- 確度: ✅（未定義であること）／🔶（推測の結果）。重大度の案: 🔵〜🟡
- 修正案: Load Config から `REPOS_MAP` を受け取り、`REPO_PATH = REPOS_MAP[repo]` とする（shared・cross のときにどの repo を調べるかも決める）。

### A5-30（新）`INCLUDE_CROSS` を使う呼び出し元が無い
- 書く側（手順）: load-steering:12,17（`INCLUDE_CROSS` が true なら cross も読む）。
- 読む側（呼び出し元）: S6・S7 で、`INCLUDE_CROSS` を渡す呼び出しは0件。cross の工程の呼び出し（07:196-200 B-cross verifier、08:156-159 A-cross verifier、09:148-160 cross TSP、10:115）は RULEBOOK_CONTEXT 自体を渡さない。cross ファイルを読むのは 05:155 と 06:110 の直読みだけ。
- 起きること: cross tpl:11 の「インタフェース変更時は必ず §6 に従う」や §3 命名規則・§4 エラーコードは、工程7〜10 の cross の検証とテスト設計に届かない。手順の入力は使われないまま残っている。
- 確度: ✅（呼び出しが無いこと）／🔶（cross の検証に必要か）。重大度の案: 🔵

### A5-31（新）cross の rulebook の写しの失敗が報告されず、Step D が「昇格」と言う
- 書く側: promote.py:1006（失敗を `repo_results["cross"]` に記録する）。
- 読む側: promote.py:1111（`write_output_file` は `affected_repos` だけを出力する）。close:20-22 で AFFECTED_REPOS は REPOS_KEYS の写しなので、`cross` を含まない。close:352 は HAS_CROSS なら条件なしで「cross: project-rulebook-cross.md を…昇格」と書く。
- 起きること: cross の rulebook の写しが I/O のエラー等で失敗すると、PENDING-PROMOTE にも Step D にも出ず、成功と報告される。DOCS の cross の rulebook は古いまま残る。同じ仕組みで、cross の C2（promote.py:309）・C4（:947）・C5（:979）・C2 の破壊的変更の警告（:1212）の失敗も出力されない（担当外の部分は下の「担当外」に記載）。
- 確度: ✅（両側を読んだ。実行はしていない）。重大度の案: 🟡（起きるのは写しが失敗したときだけ。起きても人に見えない）
- 修正案: `write_output_file` の出力の対象に `cross` を足す（`repo_results` に `cross` があれば出す）。

### A5-32（新）fill の cross §1 の `upstream-repos`/`downstream-repos` がどこにも定義されていない
- 読む側: fill:135「investigate the `upstream-repos` / `downstream-repos` relationships」。
- 書く側: 該当なし（S13: CC と tools の全体で、この語は fill:135 だけ。xddp_config.py にも config tpl にも無い）。
- 起きること: 設定キーのように書いてあるが存在しないので、LLM が依存関係の調べ方を推測で決める。
- 🔶 🔵

### A5-33（新）designer・architect の修正・追加の呼び出しの一部が RULEBOOK_CONTEXT を渡さない
- 書く側（渡す）: 05:233、06:214、09:199（TSP の修正の呼び出しでも渡す）。
- 渡さない呼び出し: 05:279（A-ripple で DSN を更新）、05:331-341（Step B の修正）、05:444（B3）、06:303-317（A2.5 で §4 に変更を足す）、06:377-385（A3）、06:467-478（Step B の修正）。06:251（A2 の補完）は「既存パラメータは…そのまま渡し」（06:244-245）とあるが、RULEBOOK_CONTEXT を含むかは書かれていない。
- 読む側: architect:34・designer:46（`(optional)`。渡されなければ規約なしで書く）。
- 起きること: A2.5 で足す変更や、レビューの指摘で直した設計は、命名規約・禁止事項を見ずに書かれる。レビュアーは rulebook を読まない（S16 で0件）ので、規約違反は工程8 の verifier まで見つからない。A2 で `RULEBOOK_CONTEXT` を含めた場合、Step A のループの最後の repo の値が残っていて、別の repo の規約になるおそれがある（🔶）。
- 確度: 渡さないことは ✅、影響は 🔶。重大度の案: 🔵〜🟡
- 修正案: 修正・追加の呼び出しにも、その repo の RULEBOOK_CONTEXT を渡す。

## 4. 担当外の指摘

### 担当外（A2）: AI_INDEX「## 共通知識」の表（A2 指摘#6 と同じ）
- init:173-177（`ドキュメント | 説明`、共通の行）と promote.py:627（`リポジトリ | project-rulebook | 最終更新CR`）。upsert_table（promote.py:199-202）が共通の行を捨てる。V3 が再現済み。✅ 🔵

### 担当外（A2）（新）: AI_INDEX の早見表が rulebook の場所として `{XDDP_DIR}` を指す
- 書く側: promote.py:344（早見表「プロジェクト規約・禁止事項 | `{XDDP_DIR}/project-rulebook.md` / `{XDDP_DIR}/project-rulebook-{repo}.md`」）。
- 実際に昇格する先: `{DOCS}/project-rulebook.md`・`{DOCS}/{repo}/project-rulebook.md`（promote.py:988,996）。AI_INDEX は DOCS に置かれ、「clone してこのファイルを AI に注入」する前提（promote.py:351）。
- 起きること: DOCS だけを clone した AI は、指されたパスにたどり着けない。repo 別のファイル名の形も違う。A2 の報告に記載は無い（`grep -n '344\|rulebook' A2.md` で確認）。✅ 🔵

### 担当外（cross の昇格全般。A4 等）: cross の C2・C4・C5 の失敗が報告されない
- A5-31 と同じ仕組み（promote.py:309,947,979,1212 → :1111）。✅ 🟡

## 5. 段階2b の候補
なし。

## 6. 読んだファイルの一覧と、確認していないこと

全文を読んだファイル:
- `CC/skills/xddp-common/templates/project-rulebook-template.md`・`project-rulebook-repo-template.md`・`project-rulebook-cross-template.md`
- `CC/agents/xddp-close-knowledge-agent.md`
- `CC/skills/xddp-fill-rulebook/SKILL.md`
- `CC/skills/xddp-common/procedures/load-steering-context.md`・`load-domain-constraints.md`

範囲を読んだファイル:
- `CC/skills/xddp-close/SKILL.md`: 1-30、94-186、187-225、278-400
- `CC/skills/xddp-close/scripts/promote.py`: 1-12、267-271、335-350、515-540、615-630、975-1010、1105-1125、1185-1225、grep の `"cross"` の行
- `CC/skills/xddp-close/scripts/tests/test_promote.py`: 525-600 の grep の行（参考）
- `CC/skills/xddp-close/templates/lessons-learned-template.md`: 1-45
- `CC/skills/xddp-01-init/SKILL.md`: 160-275
- `CC/skills/xddp-02-analysis/SKILL.md`: 22-125、175-222、265-360
- `CC/skills/xddp-05-arch/SKILL.md`: 51-61、145-240、270-300・320-350・430-470（grep の行）
- `CC/skills/xddp-06-design/SKILL.md`: 83-91、104-135、190-220、238-262、296-318、370-395、460-480
- `CC/skills/xddp-07-code/SKILL.md`: 105-200
- `CC/skills/xddp-08-verify/SKILL.md`: 105-165
- `CC/skills/xddp-09-test/SKILL.md`: 100-205
- `CC/skills/xddp-10-test-run/SKILL.md`: 200-240、:115 の行
- `CC/skills/xddp-feedback/SKILL.md`: 200-242
- `CC/skills/xddp-sync-design/SKILL.md`: 50-95
- `CC/skills/xddp-common/SKILL.md`: 9-53、96-145、225-245
- `CC/skills/xddp-common/procedures/resolve-vcs-target-repos.md`: 1-40 の grep の行
- `CC/skills/xddp-common/scripts/xddp_config.py`: :108,:216 の行
- agents: design-sync 25-40、chd-sync 28-40、test-writer 95-102、verifier 72-80、analyst 25-32（各 agent の RULEBOOK の grep の行も）
- `CC/skills/xddp-rules/xddp.arch.rules.md`: 110-116 と見出し、`xddp.design.rules.md`: 120-127 と見出し
- `CC/skills/xddp-11-specs/SKILL.md`: 296-300、`templates/11_cross-interface-spec-template.md`: :115 の行
- `README.md`: 300-306、353-362 と grep の行
- `docs/adr/`: grep だけ（README.md・ADR-0013）
- 前回の報告 A5.md、検証 V2.md・V3.md、A2.md の grep の行

確認していないこと:
- LLM（fill-rulebook・init・knowledge-agent・designer）が実際にどう解釈するかは確認していません（置き換える範囲、節の当て方、RULEBOOK_CONTEXT を省いたときの出力）。
- close Step C で LL をどの成果物から抜き出すか（A5-18 に関係）は確認していません（close:110-112 に具体的な記述が無い）。
- `{XDDP_DIR}` を作業場所の間で引き継ぐ運用（VCS に入れるか等）は確認していません（A5-1・A5-2・A5-28 の重さに関わる）。
- promote.py は実行していません。A5-31 は両側のコードを読んで確かめただけです。
- 06:358 の designer の呼び出し（A3 の 3.a）のブロック全体は読んでいません（A5-33 の一覧には含めていません）。
- 05・06 の他の呼び出し（Step C の spec-writer 等）が rulebook を必要とするかは確認していません。
