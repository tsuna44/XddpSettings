# 監査者 A5 の報告（原文。PLAN-20261103-contract-audit 段階2a）

> 監査者の最終報告をそのまま載せたもの（検証前）。検証結果と統合後の重大度は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。パスの `{W}` は監査用の worktree（ecb54c4。セッションのスクラッチのディレクトリに作り、監査の後に削除）。

# A5 project-rulebook 監査報告（対象 ecb54c4。`CC/` = `ClaudeCode/.claude/`）

## 1. 確認した約束の一覧

見つけた方法の略記:
- G1 = `grep -rn 'project-rulebook' CC/skills CC/agents | grep -v /tests/`
- G2 = `grep -rn 'RULEBOOK_CONTEXT' CC/skills CC/agents | grep -v /tests/`
- G3 = `grep -rn -B3 -A3 'Load Steering Context\|load-steering-context\|Load Domain Constraints\|load-domain-constraints' CC/skills CC/agents`
- G4 = `grep -rn 'DOMAIN_CONSTRAINTS' CC/skills CC/agents`

| # | 約束 | 書く側 | 読む側 | 見つけた方法 | 結果 |
|---|---|---|---|---|---|
| 1 | 共通ファイルのパス `{XDDP_DIR}/project-rulebook.md` | init SKILL:221-223、fill-rulebook:51,64、02-analysis:279(B3) | load-steering-context.md:15、load-domain-constraints.md:16、05-arch:155、promote.py:984 | 両側とも G1 | なし |
| 2 | repo 別ファイルのパス `{XDDP_DIR}/project-rulebook-{repo}.md` | init:229-231、fill:53、close-knowledge-agent:63 | load-steering:16、promote.py:992 | G1 | なし |
| 3 | cross ファイルのパス `{XDDP_DIR}/project-rulebook-cross.md` | init:236-238、fill:52、knowledge-agent:64 | load-steering:17、05-arch:155、06-design:110、promote.py:1000 | G1 | なし |
| 4 | 共通ファイルの DOCS への写し `{DOCS}/project-rulebook.md` | promote.py:988 | init:222 | G1 | なし |
| 5 | repo 別の写し `{DOCS}/{repo}/project-rulebook.md` | promote.py:996 | init:230 | G1 | なし |
| 6 | cross の写し `{DOCS}/cross/project-rulebook.md` | promote.py:1004 | init:237 | G1 | なし |
| 7 | 生成条件（repo 別・cross は REPOS が2つ以上のときだけ） | init:226-227,234-235（条件あり）、knowledge-agent:63-64（条件なし） | fill:58-62（シングルでは拒否）、load-steering:16 | G1 | あり A5-2 |
| 8 | 共通テンプレートのプレースホルダー `YYYY-MM-DD`・`CR番号` | project-rulebook-template.md:104,191 | init:223（置き換える） | G1、テンプレートは init:223 から | あり A5-22 |
| 9 | repo テンプレートのプレースホルダー `{REPO_NAME}`・`YYYY-MM-DD`・`{CR}` | repo-template:1,17,161,187 | init:231 | G1 | あり A5-22 |
| 10 | cross テンプレートのプレースホルダー `YYYY-MM-DD`・`{CR}` | cross-template:155,177 | init:238 | G1 | あり A5-21 |
| 11 | fill-rulebook がテンプレートから作るときのプレースホルダー | 3つのテンプレート | fill:72-74 | G1 | あり A5-11 |
| 12 | §1.6 の見出し名 `## 1.6 ドメイン制約` | template:40、02 B3:301 | load-domain:16 | G1 | なし |
| 13 | §1.6 の表の列（種別/制約内容/根拠/影響する要求の観点）と6種別 | template:46-53 | 02 B3:341-346 | G1 | なし |
| 14 | §1.6 の「未記入」の判定 | template:46-53 | load-domain:19-20 | G1 | あり A5-23 |
| 15 | DOMAIN_CONSTRAINTS が空のとき渡さない | 02-analysis:110,217 | analyst-agent:29 | G4 | なし |
| 16 | 共通の §2・§3・§4・§5 の見出し名 | template:60,95,111,152 | 02 B3:296-300 | G1。テンプレートは B3 から | なし |
| 17 | §7 変更履歴の見出しと3列 | template:187-189、repo:183-185、cross:173-175 | 02 B3:284,348-351、knowledge-agent:69 | G1 | なし |
| 18 | B3 の冪等性の判定（§7 に {CR} の行がある） | init:223（初期行に {CR} を入れる） | 02 B3:284-285 | G1 | あり A5-3 |
| 19 | B3 の追記先のコードブロック | template §2・§4（どちらも複数のブロック） | 02 B3:333-336 | G1 | あり A5-19 |
| 20 | 禁止事項の行の書式 `# ❌`/`# ⚠️` | template:156-162、repo:172-177、02 B3:310-312 | knowledge-agent:55-58、verifier:76-78 | G1・G2 | あり A5-20 |
| 21 | B3 の repo 別の候補を C3.5 へ渡す | 02 B3:287 | knowledge-agent:29,62-65（LL だけを読む） | G1 | あり A5-18 |
| 22 | C3.5 の宛先: Section 5 の名前 | knowledge-agent:34 `ADR・設計判断記録` | repo-template:151 `アーキテクチャ決定記録（ADR）` | G1。テンプレートは agent:63 から | あり A5-13 |
| 23 | C3.5 の宛先: Section 4 の名前 | knowledge-agent:35 `既存パターン・慣習` | repo-template:116 `コーディング規約・既存パターン` | 同上 | あり A5-14 |
| 24 | C3.5 の宛先: Section 4 の `### テストパターン` | knowledge-agent:36 | repo-template:139 | 同上 | なし |
| 25 | C3.5 の宛先: Section 6 の名前とルール行 | knowledge-agent:37,55-58 | repo-template:168,172-177 | 同上 | なし |
| 26 | C3.5 の Section 4 のテーマ見出しを鍵にした upsert | knowledge-agent:49-52 | repo-template:120,130,139 | 同上 | あり A5-15 |
| 27 | C3.5 で cross へ追記する節 | knowledge-agent:40-42,64 | cross-template:1-177 | G1 | あり A5-12 |
| 28 | C3.5 でファイルが無いときテンプレートから作る | knowledge-agent:63-64 | repo・cross テンプレート | G1 | あり A5-16 |
| 29 | LL の `repo:` の値（repo名/cross/unknown） | close SKILL:119,134-137 | knowledge-agent:62-65 | `grep -n 'repo：\|repo:' CC/skills/xddp-close/SKILL.md` | なし |
| 30 | LL のタグと C3.5 の宛先の表 | lessons-learned-template.md:17 | knowledge-agent:33-38 | `find CC -name '*lessons*'` | あり A5-17 |
| 31 | RULEBOOK_CONTEXT の読み込み方（共通＋repo別、cross は INCLUDE_CROSS） | load-steering:9-19 | 05:189-192、06:197-200、07:126-129,158-161、08:112-115、09:109-112,174-177、10-test-run:208-210、feedback:208-210、sync-design:62-63 | G2・G3 | なし |
| 32 | RULEBOOK_CONTEXT の中身（agent の Inputs の説明） | load-steering:15-17 | architect:34、designer:46、coder:30、verifier:32、test-writer:32、design-sync:29、chd-sync:34 | G2 | なし |
| 33 | ファイルが無いときの RULEBOOK_CONTEXT（空で続ける） | load-steering:18 | 各 agent の `(optional)`。各スキルは空でも渡す（例 05:233） | G2 | なし |
| 34 | verifier が使う禁止事項の節番号（共通 §5／repo §6） | template:152、repo:168 | verifier:76-78 | G2 | なし |
| 35 | 禁止事項の節名 | template:152、repo:168 | test-writer:98-100 | G2 | なし |
| 36 | 05-arch cross が使う節番号（共通 §2 命名規約／cross §2・§3） | template:60、cross:42,68 | 05-arch:155-162 | G1 | なし |
| 37 | 06-design cross が使う節番号（cross §2・§6） | cross:42,150 | 06-design:110-117 | G1 | なし |
| 38 | arch・design ルールからの参照 | template（共通） | xddp.arch.rules.md:114、xddp.design.rules.md:125 | G1 | なし |
| 39 | fill の未記入判定に使うプレースホルダー（共通） | template:16-21,33,70,81,91,107,148,164,183 | fill:82-91 | G1 | なし |
| 40 | fill のプレースホルダー（repo の §2・§3） | repo-template:64,75,89,101,112 | fill:97 | G1 | あり A5-4 |
| 41 | fill のプレースホルダー（repo の §6 のモジュール構成） | repo-template（該当の文字列なし） | fill:101 | G1 | あり A5-5 |
| 42 | fill のプレースホルダー（repo の §1・§4・§5・§6 禁止事項） | repo-template:24,128,164,179 | fill:96,98-100 | G1 | なし |
| 43 | fill のプレースホルダー（cross §1〜§6） | cross-template:23,64,101,131,146,169 | fill:103-111 | G1 | なし |
| 44 | fill のドラフト規則 §5(ADR)・§3 | 共通 template:95(ADR),152(禁止事項) | fill:171-192 | G1 | あり A5-6 |
| 45 | fill のドラフト規則 §6 | 共通 template:168、repo:168 | fill:157-169,194-195 | G1 | あり A5-7 |
| 46 | fill のドラフト規則 §4（specout が書く） | 共通 template:111-148、repo:116-147 | fill:197-198 | G1。specout が書かないことは G1 の結果に xddp-04-specout が無いことで確認 | あり A5-8 |
| 47 | fill のドラフト規則（cross §2） | cross-template:42-64 | fill:134-135 | G1 | あり A5-9 |
| 48 | fill のドラフト規則（cross §3〜§6） | cross-template:68-169 | fill:117-198（cross 専用の規則なし） | G1 | あり A5-10 |
| 49 | promote の cross の写しの条件（`has_cross`） | knowledge-agent:64（条件なし） | promote.py:999-1006 | G1 | あり A5-24 |
| 50 | close Step D の昇格の報告 | promote.py:982-1006（ファイルがあるときだけ写す） | close SKILL:348,352 | G1 | あり A5-25 |
| 51 | cross テンプレート §6 が指す仕様書のパスと節名 | xddp-11-specs SKILL:298-302（`cross/interfaces/{interface-kebab}/spec.md`） | cross-template:165 | `grep -rn 'interfaces/\|移行ガイド' CC/skills CC/agents` | あり A5-26 |
| 52 | README の §1.5 の説明 | template:26-36 | README.md:355-356 | `grep -n 'rulebook' README.md` | あり A5-27 |
| 53 | DOCS の rulebook の上書き（同時に進む別の作業場所） | promote.py:988,996,1004（copy2） | close SKILL:187-277（C0 の競合の検出は latest-specs だけ） | close SKILL を通読 | あり A5-28 |
| 54 | 書く時期: C3.5 → C6 の写し | knowledge-agent（close:310-331） | promote.py:1216（close:299） | close SKILL を通読 | あり A5-1 |

## 2. 時期の約束の表

| 書く側（スキル・Step） | 読む側（スキル・Step） | 順序の根拠 | 結果 |
|---|---|---|---|
| init Step 4.6（XDDP の rulebook を作る） | 02 Step A0.5（§1.6）、05〜10・feedback・sync-design（Load Steering Context） | init:251 で次のコマンドを `/xddp-02-analysis` にする。工程の番号順 | なし |
| 02 Step B3（共通 rulebook に追記） | 05〜10 の Load Steering Context | 02:353-357（工程2の完了後に次へ進む） | なし |
| 02 Step B3（§1.6 に追記） | 02 Step A0.5（§1.6 を読む） | 02:75 の A0.5 が 02:270 の B3 より前 | 食い違いではない。その CR の追記は次の CR から効く |
| close Step C（LL を書く） | close extract-ll → C3.5（`CR_LESSONS_FILE`） | close:94 → 284 → 310-324 | なし |
| close C3.5（rulebook-{repo}/cross に upsert） | close C6（promote.py が DOCS へ写す） | close:299 の promote.py run が close:312 の C3.5 より前。promote.py:1216 | **逆順 A5-1** |
| close C6（DOCS へ写す） | 次の CR の init Step 4.6（XDDP に無いとき DOCS から写す） | init:221-238 | repo 別はシングル構成で戻らない。A5-2 |
| close C6（DOCS を copy2 で上書き） | 別の作業場所の close C0（DOCS の pull） | close:207-277 | 競合を検出しない。A5-28 |

## 3. 指摘

### A5-1 close で C3.5 の upsert が DOCS への写し（C6）の後に行われる
- 約束: close で更新した rulebook を `{DOCS}` へ昇格する。
- 書く側: `CC/agents/xddp-close-knowledge-agent.md:27-69`（Step C3.5）。`CC/skills/xddp-close/SKILL.md:310-331` で呼ぶ。
- 読む側: `CC/skills/xddp-close/scripts/promote.py:982-1006` の `promote_rulebooks`（`run` の中の :1216 で呼ぶ）。`CC/skills/xddp-close/SKILL.md:299` の Step C2〜C7 で実行する。同じ時点で AI_INDEX の行も promote.py:527-536 で作る。
- 食い違い: SKILL は C2〜C7（promote.py。C6 の写しを含む）を先に実行し、その後に C3.5 の agent を起動する。C3.5 が今の CR の LL から書いた内容は、その close では `{DOCS}` に写されない。Step D は close:348,352 で「昇格」と報告する。
- 起きること: `{DOCS}` の rulebook が1つ前の CR の内容のまま残る。最後の CR の C3.5 の内容は、次の close が来るまで `{DOCS}` に届かない。`{XDDP_DIR}` が引き継がれない場合（新しく clone して init:221-238 で DOCS から写す等）は失われる。C3.5 が初めて作った repo 別・cross のファイルは、写しも AI_INDEX の行も作られない。
- 確度: ✅ SKILL の順序と promote.py の呼び出しを読んで確認した。この順序を受け入れた制限とする ADR は見つからない（`grep -rn 'C3\.5' docs/adr/`）。
- 重大度の案: 🟡（失われるのは `{XDDP_DIR}` が引き継がれない場合だけ。ただし Step D の報告が実態と合わない）
- 修正案: C3.5 の後に rulebook の写しだけを再実行する。または C3.5 を promote.py run の前へ移す。

### A5-2 シングルリポジトリでも C3.5 が `project-rulebook-{repo}.md` を作る
- 約束: repo 別のファイルは REPOS が2つ以上のときだけ作る（CLAUDE.md の project-rulebook 節。init:226-227、fill:58-60）。
- 書く側: `xddp-close-knowledge-agent.md:63`「`repo: {repo-name}` → append to `project-rulebook-{repo}.md` (create if absent from template)」。IS_MULTI の条件が無い。close:134-135 はシングル構成でも LL に `repo: {repo-name}` を付ける。
- 読む側: `xddp-01-init/SKILL.md:226-232`（2つ以上のときだけ `{DOCS}/{repo}/project-rulebook.md` から写す）、`xddp-fill-rulebook/SKILL.md:58-60`（「シングルリポジトリ構成では project-rulebook-{repo}.md は生成されません」と言って止まる）、`load-steering-context.md:16`（ファイルがあれば読む）。
- 食い違い: シングル構成では、C3.5 だけがファイルを作る。init と fill-rulebook は、そのファイルが無い前提で動く。
- 起きること: 同じ作業場所では load-steering が読むので、知見は届く。しかし (a) 新しい作業場所の init は `{DOCS}/{repo}/project-rulebook.md` を写さない（promote.py:992-998 は条件なしで写している）。そのため LL 由来の repo の規約が RULEBOOK_CONTEXT から黙って消える。(b) fill-rulebook は、実在するファイルについて「生成されません」と案内する。
- 確度: ✅
- 重大度の案: 🟡
- 修正案: シングル構成では共通 rulebook（§3 ADR／§4／§5 禁止事項）に送ると決める。または init の復元の条件を外す。どちらにするかは決めない。

### A5-3 最初の CR では 02 Step B3 が必ずスキップされる
- 約束: B3 の冪等性の判定は「§7 変更履歴に {CR} を含む行がある」。
- 書く側: `xddp-01-init/SKILL.md:223` がテンプレートの `CR番号` を `{CR}` に置き換える。その結果 `project-rulebook-template.md:191` が `| {today} | {CR} | 初期作成 |` になる。
- 読む側: `xddp-02-analysis/SKILL.md:284-285`（その行があれば「Step B3 をスキップします」）。
- 食い違い: XDDP にも DOCS にも共通 rulebook が無い最初の CR では、init が作った初期行に {CR} が入る。そのため B3 は「抽出済み」と判定する。
- 起きること: その CR の要求書の命名規約・ADR・禁止事項・ドメイン制約の候補が、提示されないまま失われる。人には「エントリが見つかったのでスキップ」と表示されるので、処理済みと誤解しやすい。quick（02:183-186）でも同じ。
- 確度: ✅
- 重大度の案: 🟡（人に表示はされるが、理由を誤解させる）
- 修正案: B3 が書く行を印（例「（req より抽出）」）で照合する。または init の初期行に {CR} を入れない。

### A5-4 fill-rulebook の repo 別ファイルの §2 の判定に §3 のプレースホルダーを使っている
- 約束: fill-rulebook の未記入の判定（節番号とプレースホルダー）。
- 書く側: `project-rulebook-repo-template.md`。§2 アーキテクチャ概要のプレースホルダーは :64 と :75。`（このリポジトリ固有の命名規約…）` と `（…DB・API 命名規約…）` は §3 命名規約にある（:89,101,112）。
- 読む側: `xddp-fill-rulebook/SKILL.md:97`（§2 として §3 の文字列を挙げる）、:148-155（「§2 Naming conventions」のドラフト）、:234（見出しから次の `---` までを置き換える）。repo の §3 の行は無い。
- 食い違い: §3 が未記入だと §2 と判定する。命名規約のドラフトを `## 2. アーキテクチャ概要` の本文に書き込み、§3 は未記入のまま残る。§2 のプレースホルダーは検出しない。
- 起きること: 人が §2 に書いたアーキテクチャの記述が、命名規約のドラフトで置き換わって失われることがある。§3 はいつまでも埋まらない。工程5〜10 の RULEBOOK_CONTEXT に、誤った節の内容が渡る。
- 確度: 節の対応がずれていることは ✅。置き換えが実際に起きるかは LLM が手順どおりに動くか次第なので 🔶。
- 重大度の案: 🔴（人が書いた内容が黙って失われうる）
- 修正案: repo の表を §2（:64,:75）・§3（:89,:101,:112）に分け、ドラフト規則も repo 用に分ける。

### A5-5 fill-rulebook の repo 別ファイルの §6 の行に、テンプレートに無いプレースホルダーがある
- 書く側: `repo-template`。`（このリポジトリ固有のモジュール構成…）` は無い。モジュールの役割は §1 の :43 にある。
- 読む側: `fill:101`
- 食い違い: 照合しても一致しない行がある。
- 起きること: 動作への影響は無い。
- 確度: ✅
- 重大度の案: 🔵

### A5-6 fill-rulebook の「§5 (ADR)」の規則が、共通ファイルでは §5 禁止事項に当たる
- 書く側: 共通 `project-rulebook-template.md` は :95 が §3 ADR、:152 が §5 禁止事項。
- 読む側: `fill:171-192` は「§5 (ADR)」の規則で git log から ADR の候補を作る（`{REPO_PATH}` は共通では決まらない）。共通の §3（fill:88 で未記入と判定する）にはドラフト規則が無い。
- 食い違い: 共通の §5 禁止事項に、ADR の候補を書く。共通の §3 ADR は扱いが決まっていない。
- 起きること: 共通の禁止事項の節が ADR の候補で置き換わる。その節は verifier（verifier:76-78 は共通 Section 5 を禁止事項として読む）や test-writer が読む。
- 確度: 規則と節の不一致は ✅。結果は 🔶。
- 重大度の案: 🟡（人がドラフトを確認する）

### A5-7 fill-rulebook に §6 の規則が2つあり、repo 別ファイルの §6 禁止事項にモジュール構成を書く
- 読む側: `fill:157-169`「§6 Module structure」、:194-195「§6 (not applicable)」
- 書く側: 共通 template:168 は §6 モジュール構成。repo:168 と cross:150 の §6 は別の内容（禁止事項、インタフェース変更手順）。
- 食い違い: 同じ節番号に、互いに矛盾する規則が2つある。repo 別では禁止事項の節が、モジュール構成か「手動記入してください」の注記で置き換わる。
- 起きること: verifier（verifier:77 は repo の Section 6 を読む）に禁止事項が渡らなくなる。
- 確度: ✅（結果は 🔶）
- 重大度の案: 🟡

### A5-8 fill-rulebook の §4 の注記「スペックアウトで記入される」に対応する処理が無く、§4 を置き換える
- 読む側: `fill:197-198` は §4 に `（スペックアウト（工程4a）で調査・記入されます）` を入れる。:234 は節の本文をまるごと置き換える。
- 書く側: 工程4 のスキル・エージェントは rulebook を書かない（G1 の結果に xddp-04-specout とその agent が無い）。共通 template:117-128 の「デフォルト原則」は、この置き換えで消える。
- 起きること: §4 は以後だれも埋めない。デフォルトのエラーハンドリングの原則が、工程5〜10 の RULEBOOK_CONTEXT から消える。
- 確度: ✅（置き換えは 🔶）
- 重大度の案: 🟡

### A5-9 fill-rulebook の「§1 / §2 Cross-repo overview」が cross の §2 API バージョニング規約に当たる
- 書く側: `cross-template:42-64`（§2 API バージョニング規約。既定の SemVer の表を含む）。対象リポジトリの表と依存関係のブロックは §1（:17-38）にある。
- 読む側: `fill:134-135`
- 起きること: cross の §2 が、リポジトリの一覧と依存関係で置き換わる。05-arch:161-162 と 06-design:116 は cross の §2 を API バージョニング規約として読み、breaking の判定に使う。
- 確度: ✅（結果は 🔶）
- 重大度の案: 🟡

### A5-10 fill-rulebook に cross §3〜§6 用のドラフト規則が無い
- 読む側: `fill:117-198` の規則は節番号だけで当てる。そのため cross の §4 には specout の注記（A5-8）、§5 には ADR の候補（A5-6）、§6 にはモジュール構成か注記（A5-7）が入る。
- 書く側: `cross-template:68-169`（命名規則、エラーコード、認証方式、インタフェース変更手順。既定の手順を含む）
- 起きること: 06-design:116 が読む cross の §6 インタフェース変更手順が、無関係の内容に置き換わる。
- 確度: ✅（結果は 🔶）
- 重大度の案: 🟡

### A5-11 fill-rulebook がテンプレートからファイルを作るとき、日付と CR のプレースホルダーを置き換えない
- 読む側: `fill:72-74`（repo は `{REPO_NAME}` だけを置き換える）
- 書く側: template:191（`YYYY-MM-DD`・`CR番号`）、repo:187、cross:177（`{CR}`）
- 起きること: §7 にプレースホルダーのままの行が残る。
- 確度: ✅
- 重大度の案: 🔵

### A5-12 C3.5 で cross に追記する節が決まっていない
- 書く側: `knowledge-agent:40-42`（「cross 宛ては Append を維持」）、:64
- 読む側: `cross-template` の節の構成は §5 認証方式・§4 エラーコード・§6 変更手順で、宛先の表（agent:33-38 の Section 4/5/6）の意味と合わない。cross:9 の更新ルールは「末尾に追記」。
- 食い違い: どの節に追記するかが書かれていない。宛先の表を節番号で当てると、別の意味の節に入る。末尾に入れると §7 の表の後ろになる。
- 起きること: 05-arch・06-design の cross の手順が読む §2・§3・§6 に入らないか、無関係の節に混ざる。
- 確度: 🔶（LLM の解釈による）
- 重大度の案: 🟡

### A5-13 C3.5 の宛先の表の Section 5 の名前が、テンプレートの見出しと違う
- 書く側（宛先の表）: `knowledge-agent:34`「Section 5 (ADR・設計判断記録)」
- 読む側（テンプレートの見出し）: repo:151「アーキテクチャ決定記録（ADR）」
- 確度: ✅
- 重大度の案: 🔵（節番号は合っている）

### A5-14 C3.5 の宛先の表の Section 4 の名前が、テンプレートの見出しと違う
- 書く側（宛先の表）: `knowledge-agent:35`「Section 4 (既存パターン・慣習)」。これは共通テンプレートの名前。
- 読む側（テンプレートの見出し）: repo:116「コーディング規約・既存パターン」
- 確度: ✅
- 重大度の案: 🔵

### A5-15 C3.5 の Section 4 のテーマ見出しの例が、テンプレートの見出しと一致しない
- `knowledge-agent:50` は例として鍵 `エラーハンドリング` を挙げる。repo:120 の見出しは `### このリポジトリ固有のエラーハンドリング`、:130 は `### 非同期処理パターン`。完全一致で照合すると、同じテーマの節が重複して足される。
- 確度: 🔶
- 重大度の案: 🔵

### A5-16 C3.5 がテンプレートからファイルを作るとき、どのテンプレートを使い何を置き換えるかが決まっていない
- `knowledge-agent:63-64`「create if absent from template」。対象は repo:1,17,187 の `{REPO_NAME}`・`{CR}` と、cross:177。
- 確度: ✅
- 重大度の案: 🔵

### A5-17 LL のタグ `#レビュー` が C3.5 の宛先の表に無い
- `lessons-learned-template.md:17` に `#レビュー` がある。`knowledge-agent:33-38` には、宛先の行にも「Not mapped」の行にも無い。
- 確度: ✅
- 重大度の案: 🔵

### A5-18 02 B3 の「repo 別は C3.5 で行う」に、受け渡しの仕組みが無い
- 書く側: `02-analysis:287`。repo 別の候補は提示の一覧に「→ project-rulebook-{repo}.md へ追記推奨」と注記するだけで、どこにも保存しない。
- 読む側: `knowledge-agent:29,62-65`。C3.5 が読むのは `CR_LESSONS_FILE`（今の CR の LL）だけ。
- 起きること: 要求書から見つけた repo 別の規約は、人が手で書くか、close の Step C で LL に偶然拾われない限り、repo 別ファイルに入らない。
- 確度: 🔶（Step C の LL の抽出元が close:107-112 で具体化されていないため、LL に拾われるかは確定できない）
- 重大度の案: 🟡

### A5-19 02 B3 の「既存のコードブロックの末尾に追記」で、どのブロックかが決まらない
- `02-analysis:333-334`。共通の §2 にはコードブロックが3つ（template:63,73,84）、§4 にも3つ（:119,133,140）ある。
- 確度: ✅
- 重大度の案: 🔵

### A5-20 禁止事項の行の書式が書く側どうしで違う
- `02-analysis:312` の追記案は `❌ …`（`# ` なし）。template:158-161 と knowledge-agent:55,57（`# ❌/⚠️` の行を鍵にする）は `# ❌`。
- 共通ファイルは C3.5 の対象外なので、今は upsert の鍵としては衝突しない。
- 確度: ✅
- 重大度の案: 🔵

### A5-21 init の `{CR}` の置き換えで、cross テンプレート §6 の一般的な手順の文に CR 番号が入る
- `init:238` は `{CR}` を置き換える（何か所を置き換えるかの指定は無い）。`cross-template:155`「変更する CR の CRS-{CR}.md に…」が、初期化した CR の番号に固定される。06-design:116 はこの §6 を読む。
- 確度: ✅（全部の出現を置き換えるかは 🔶）
- 重大度の案: 🔵

### A5-22 init の置き換えで、ADR の書式のコメントに日付と CR が入る
- `init:223,231` は `YYYY-MM-DD`・`{CR}` を置き換える。共通 template:104 と repo:161 の ADR の書式のコメントにも同じ文字列がある。
- 確度: ✅（全部の出現を置き換えるかは 🔶）
- 重大度の案: 🔵

### A5-23 load-domain-constraints の「未記入」の判定が、テンプレートの §1.6 の行の形に合わない
- 読む側: `load-domain:19-20`「全行がプレースホルダー `{...}` のみ」
- 書く側: template:48-53。各行の種別の列には文言が入っていて、`{...}` だけの行は無い。B3（02:340）は行を追加するだけで、プレースホルダーの行は残る。
- 起きること: 未記入のテンプレートでも空と判定されず、analyst に渡るおそれがある。
- 確度: 🔶
- 重大度の案: 🔵

### A5-24 cross の写しが今の CR の cross の成果物の有無（`has_cross`）で決まる
- 読む側: `promote.py:999-1006`
- 書く側: `knowledge-agent:64` と fill-rulebook cross は、cross の成果物の有無によらず cross ファイルを更新する。
- 起きること: cross の成果物を持たない CR の close では、cross ファイルが写されない。
- 確度: ✅
- 重大度の案: 🔵

### A5-25 close Step D が、写していない rulebook も「昇格」と報告する
- 読む側: `close SKILL:348,352`。成功した repo には、常に「`project-rulebook-{repo}.md` を…に昇格」と書く。
- 書く側: `promote.py:992-1006` は、ファイルがあるときだけ写す。シングル構成では通常そのファイルが無い。
- 確度: ✅
- 重大度の案: 🔵

### A5-26 cross テンプレート §6 が、存在しないパスと節を指す
- `cross-template:165`「`cross/interfaces/{name}-spec.md` の「移行ガイド」セクション」。xddp-11-specs:298 が作るのは `cross/interfaces/{interface-kebab}/spec.md`。「移行ガイド」という節は、`grep -rn 移行ガイド CC` で他に見つからない。仕様書の側は A4 の担当。
- 確度: ✅
- 重大度の案: 🔵

### A5-27 README の §1.5 の説明がテンプレートと合わない
- `README.md:355-356` は「1.5 にリポジトリ一覧・依存関係・共有インタフェースを記入」と書く。template:26-36 の §1.5 は「リポジトリ名・役割・主要技術」の表だけで、依存関係と共有インタフェースは cross:17-38 にある。
- 確度: ✅
- 重大度の案: 🔵

### A5-28 DOCS の rulebook を、競合を検出せずに丸ごと上書きする
- 書く側: `promote.py:988,996,1004`（`shutil.copy2`）
- 読む側: `close SKILL:207-277`。C0 は DOCS を pull するが、rulebook を XDDP へ取り込まない。競合の検出（C0-4）は latest-specs の保護ファイルだけを対象にする。
- 起きること: 同じ DOCS を共有する別の作業場所が先に昇格させた rulebook の更新を、後から close した側が上書きして消す。
- 確度: 🔶（複数の作業場所で1つの DOCS を共有する運用が前提。init:222 の「knowledge hub priority」がその運用を示唆する）
- 重大度の案: 🟡

## 4. 担当外の指摘

### 担当外（A2）: AI_INDEX「## 共通知識」の表
- 書く側: init SKILL:173-177 の骨組みは、列 `ドキュメント | 説明` と共通 `project-rulebook.md` の行。promote.py:624-627 の upsert は、列 `リポジトリ | project-rulebook | 最終更新CR` と、repo・cross の行だけ（promote.py:527-536）。
- 食い違い: upsert_table（promote.py:199-202）は、列が一致しないと既存の行を捨てる。そのため共通 rulebook の行は最初の upsert で消え、その後も足されない。
- 確度: ✅（両側を読んだ）
- 重大度の案: 🔵〜🟡。A2 で報告済みかは確認していません。

## 5. 段階2b の候補
なし。

## 6. 読んだファイルの一覧と、確認していないこと

全文を読んだファイル:
- `CC/skills/xddp-common/templates/project-rulebook-template.md`
- `CC/skills/xddp-common/templates/project-rulebook-repo-template.md`
- `CC/skills/xddp-common/templates/project-rulebook-cross-template.md`
- `CC/agents/xddp-close-knowledge-agent.md`
- `CC/skills/xddp-fill-rulebook/SKILL.md`
- `CC/skills/xddp-common/procedures/load-steering-context.md`
- `CC/skills/xddp-common/procedures/load-domain-constraints.md`

範囲を読んだファイル:
- `CC/skills/xddp-close/SKILL.md`:1-30、94-186、187-400
- `CC/skills/xddp-close/scripts/promote.py`:176-216、335-350、520-540、615-630、960-1006、1180-1240
- `CC/skills/xddp-01-init/SKILL.md`:165-275
- `CC/skills/xddp-02-analysis/SKILL.md`:170-195、265-365（ほかは grep の行）
- `CC/skills/xddp-05-arch/SKILL.md`:145-240
- `CC/skills/xddp-06-design/SKILL.md`:106-120 と G2 の行
- `CC/skills/xddp-sync-design/SKILL.md`:55-95
- `CC/skills/xddp-feedback/SKILL.md`:225-240 と G3 の行
- `CC/skills/xddp-10-test-run/SKILL.md`:196-240
- `CC/skills/xddp-close/templates/lessons-learned-template.md`:10-50
- `CC/skills/xddp-common/SKILL.md`:230-245 と「## Resolve Affected Repos」
- xddp.arch.rules.md:108-116、xddp.design.rules.md:118-128
- test-writer:95-102、architect:155-163
- README.md:192、203、300-306、355-380
- 07・08・09 SKILL と各 agent は、G1〜G4 の grep の行とその前後だけ
- `docs/adr/` は grep だけ
- test_promote.py:539-563 は grep の行だけ

確認していないこと:
- 07・08・09 の agent の呼び出しブロックの全体（RULEBOOK_CONTEXT の行以外）は確認していません。
- close Step C で LL をどの成果物から抽出するか（A5-18 に関係する）は具体的に確認していません（SKILL に「same as before」とだけある）。
- fill-rulebook・init・C3.5 が LLM として実際にどう置き換えるか（全部の出現か等）は、実行していないので確認していません。
- A2 で AI_INDEX の共通知識の件が報告済みかは確認していません。
- `{XDDP_DIR}` が作業場所の間でどう引き継がれるか（VCS に入れるか等）の運用は確認していません（A5-1・A5-28 の重さに関わる）。
