# 検証者 V1 の報告（原文。PLAN-20261103-contract-audit 段階2a）

> 検証者の最終報告をそのまま載せたもの。統合後の結果は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。`{W}` は監査用の worktree（ecb54c4）、`{V}` は検証者ごとのスクラッチのディレクトリ（どちらもセッションのスクラッチに作り、後で削除）。

# V1 検証報告（対象 ecb54c4。`{W}` = audit-ecb54c4、`CC/` = `ClaudeCode/.claude/`）

## 1. 指摘の検証の表

| 指摘 | 判定 | 確度 | 重大度の案 | 根拠 | 重複 |
|---|---|---|---|---|---|
| A1-1 | 確認 | ✅ | 🔴 | CC/agents/xddp-survey-promote-agent.md:59-60（同じ出典なら置き換え）、:63（出典は `SURVEY-{TODAY}`）。1回の昇格のすべての §2.6 の項目が同じ出典になる。docs/adr/ADR-0033-constraints-module-key.md:82-83 は「既存の問題…別途扱う」と書いており、受け入れた制限として書いたものではない | ADR-0033:82 の既知の問題（A1-3 と同じ根） |
| A1-2 | 確認 | ✅ | 🟡 | CC/skills/xddp-update-knowledge/SKILL.md:187-188（同じ出典なら replace）、:53（出典の例 `manual/2026-07-04`）。:173-175 のプレビューは置き換えを示さない | A1-1・A1-3 と同じ根 |
| A1-3 | 確認 | 鍵が無いことは ✅、置き換わるかは 🔶 | 🟡 | close-knowledge-agent.md:85,96（§5.6 の出典は `{CR_NUMBER}`）。:98-109 の LL 由来には出典の指示が無い。鍵を定めているのは TRS（:122-126）だけ。テンプレート code-knowledge-constraints-template.md:3 は「[CK-NNN] で識別」。ADR-0033:82 は鍵を「同一出典」と書いている | A1-1 |
| A1-4 | 一部確認 | 🔶 | 🟡 | close-agent:119（鍵）、:113-114。xddp-10-test-run/SKILL.md:104（TRS は回ごとのファイル）。TRS テンプレート 10_test-results-template.md:36（`NG-001`）。test-runner-agent に回をまたいだ連番の指示は無い（grep で確認）。違う点は下に書く | — |
| A1-5 | 確認 | 🔶（CR の名前の付け方による） | 🔵 | close-agent:119,127（`CR-{CR_NUMBER}`）。CR の形は spec-writer-agent.md:46 が `CR-2026-970`、README.md:54 が `REQ-2026-001`。xddp-common/SKILL.md:46-52 はフォルダ名をそのまま CR にする | — |
| A1-6 | 一部確認 | 文面の食い違いは ✅、影響は 🔶 | 監査者 🟡→🔵 | テンプレート:13-25 の2つの節に `**対象:**` が無い。一方 boundary:120 と close-agent:86 は対象を書けと指示している。理由は下に書く | — |
| A1-7 | 確認（再現） | ✅ | 🟡 | domain_refs.py:308-311 は**ディレクトリ**を `col.add` に渡す。analyst-agent.md:26 は「ファイルの絶対パス」を期待し、:77-78 は開けないパスを失敗として扱う。再現: promote の AI_INDEX と domain_refs.resolve を実行すると、`domain_ref_paths` = `…/code-knowledge/_constants \| 共有定数` になった | A2-1 と組みになる |
| A1-8 | 確認（再現） | ✅ | 🟡 | domain_refs.py:292-311（AI_INDEX のラベルがある場合だけ）・:334-365（索引が無い経路では列挙しない）。xddp-close/SKILL.md:278（C2）→:310（C3.6）。再現: AI_INDEX を外して resolve を実行すると、`_structures`・`_constants` があっても `domain_ref_paths` が空になった | A2-10 |
| A1-9 | 確認 | ✅ | 🔵 | summary テンプレート:155-157（`定義モジュール`）と constants テンプレート:5-7（`定義場所`=`{ファイルパス:行}`） | — |
| A1-10 | 確認 | ✅ | 🔵 | close-agent:143-144,160-161,184-185,211-213 が書く。close/SKILL.md:378-382 は「昇格見送り一覧」を示さない | — |
| A1-11 | 一部確認 | ✅ | 🔵 | 「Add」と明示しているのは close-agent:156,170 だけ。違う点は下に書く | — |
| A1-12 | 確認 | ✅ | 🔵 | update-knowledge:69（フロー名の入力を求める）。:200-201 はファイル名を `{DOMAIN}-{VAR_NAME}` にしていて、入力したフロー名を使わない | — |
| A1-13 | 確認 | ✅ | 🔵 | boundary:53-55（「この表以外に定義してはならない」）と update-knowledge:193-197,201-204。値は今は一致している | A1-14 と同じ種類 |
| A1-14 | 確認 | ✅ | 🔵 | survey/SKILL.md:248-254、survey-promote-agent.md:40-56 | A1-13 と同じ種類 |
| A1-15 | 確認 | ✅ | 🔵 | survey/SKILL.md:272 と :252（§2.6 は「常に」）。survey-agent.md:36（テンプレートの全節を使う）、module テンプレート:68（§2.6） | — |
| A1-16 | 確認 | ✅ | 🔵 | specout_bfs.py:2989-2994。値は :1395-1409 の第1階層。`grep -rn confirmed_modules ClaudeCode tools docs/adr` で、読む側はテスト（test_specout_bfs.py:1675-1697）だけだった。SKILL が呼ぶのは `status --brief` だけ（04-specout/SKILL.md:172） | — |
| A1-17 | 確認（再現） | 再現は ✅、LLM がエスケープするかは 🔶 | 🔵 | knowledge_place.py が `src\auth\x.c` を受けると「Invalid \escape」で exit 2 になった。追加で分かったことは下に書く | — |
| A1 担当外（構造体のラベル） | 確認（再現） | ✅ | 🟡 | A2-1 と同じ | A2-1 |
| A2-1 | 確認（再現） | ✅ | 監査者 🔴→🟡 | promote.py:601（`構造体関連図`）と domain_refs.py:35-38,305-307（`共有構造体`）。再現: promote が書いた行は `repo-a 構造体関連図` で、domain_refs は `_structures` を集めなかった | A1 担当外。A1-7 と組み |
| A2-2 | 確認（(a)(c) は再現） | (a)(c) は ✅、(b) は 🔶 | 🟡 | (a) promote.py:446 は名前を完全一致で比べる。06-design/SKILL.md:128-130 の名前は `POST /jobs`、11-specs/SKILL.md:290 はケバブ形式。(c) upsert のキー [0]（promote.py:581-582、upsert_table:206-218）。(b) 11-specs:577,612 と promote.py:577 | — |
| A2-3 | 確認（再現） | ✅ | 🟡 | domain_refs.py:233-236,288-290,382-384。01-init:120 が `{DOCS}/{repo}/specs/README.md` を作る。再現: AI_INDEX に先行更新の行があり latest-specs にだけ spec.md がある状態で、参照先が空、`DOMAIN_REF_MODE` は `none` になった。11-specs:665-667 の「latest-specs から直接参照します」は事実と違う | — |
| A2-4 | 確認 | ✅（書く側が無いことを grep で確認） | 🟡 | 読む側は 05-arch:108-113、06-design:46-53、designer-agent:45。`design/` を書くのは 01-init（README だけ。:186-190「使用されていません」）と 11-specs:631-640（AI_INDEX の行だけ）。promote.py に DSN・CHD を写す処理は無い | — |
| A2-5 | 確認 | 置き換わることは ✅、影響は 🔶 | 🟡 | promote.py:488-502,616-617（キーは repo）、09-test/SKILL.md:35-40 | — |
| A2-6 | 一部確認（再現） | ✅ | 🟡 | promote.py:200-202（ヘッダが違えば行を捨てる）、:527-536、:627。01-init:173-177。再現: 共通の rulebook の行が消え、repo の行だけになった。条件の違いは下に書く | — |
| A2-7 | 確認 | ✅ | 🔵寄りの 🟡 | promote.py:420-432,400-417。close/SKILL.md:21-23 と xddp-common/SKILL.md:131-132（FILTER_BY_SPO=false は全 repo）。11-specs:595-597,624-626 の引用文は promote.py に無い（grep で 0 件）。specs-mod-agent.md:50-51 | — |
| A2-8 | 判断できず | 🔶 | 🟡 | 11-specs:120,594 は SPECOUT_MODULES をディレクトリ名とする。mod-agent:159-161 はケバブ形式に変える。module-documentation.md「## モジュールの決め方」は `_` を許す。先行更新の LLM が名前を変換するかに依存する（下記「新たに気付いた食い違い」1 も参照） | — |
| A2-9 | 確認 | ✅（`related-modules: []` と `\|` は再現） | 🔵 | `_parse_frontmatter` が `'[]'` を文字列で返す。uc テンプレート:20 が `[]` を指示している。`_join_row(['a\|b'])` は `\|` をエスケープしない。KNOWLEDGE_GUIDE_BLOCK（promote.py:334-347）は末尾に足され（:585-588）、その後に CRS・TSP の節が作られる。11-specs:57-58 の「テーブル形式ではない」は promote.py:605,611 と食い違う | — |
| A2-10 | 確認 | ✅ | 🟡 | A1-8 と同じ。survey の (b) は AI_INDEX を書かない（survey:383 の ③ は (c) の手順。survey-promote-agent に AI_INDEX は出てこない） | A1-8 |
| A2-11 | 確認（git の振る舞いを再現） | git の振る舞いは ✅、LLM の扱いは 🔶 | 🟡 | close/SKILL.md:207-209（pull が失敗したときの扱いが無い）、:236-241,293。再現は {V} の git で行った。結果は下に書く | — |
| R1 | 確認（再現） | ✅ | 🟡 | knowledge_place.py:195,40,42,252。再現: `place` は `{"module":"_structures","reserved_collision":true}` を返し、`list_places` は `['_general']`（`_structures` を除く）、`applicable_places('_structures/x.c')` は `['_general','_structures']` を返した | — |
| R4 | 確認（再現） | ✅ | 🔵 | knowledge_place.py:131-132,169。`/usr/include/stdio.h` と `/nonexistent_zz/foo.h` は、どちらも `not-found` で置き場所 `_general` になった。boundary:115、update-knowledge:165-166 と食い違う | — |

### 「一部確認」「判断できず」と、重大度を変えた理由
- **A1-4:** 回ごとに NG 番号を振り直す場合に、回をまたいで置き換わることは文面どおりです（🔶）。見出しの「repo が鍵に入っていない」は問題になりません。置き場所 `{KNOW}` = `{DOCS}/{repo}/…` は repo ごとに別のファイルで、TRS_PATTERN も repo ごとだからです（close-agent:24,114）。
- **A1-6:** 読む側の module-documentation.md:181 は、`**対象:**` の無い制約（「仕様上の暗黙の前提等」）を内容で照合すると明示しており、この場合を想定した作りです。食い違いは書く側の中にあります（boundary:120・close-agent:86 は「対象を書け」、テンプレートの2つの節には欄が無い）。LLM が欄を足すかで結果が変わり、影響は限られるので 🔵 にしました。
- **A1-11:** `_flows` の sequence・DFD は、close-agent:197-199 の「_flows/ 昇格時の共通注意事項」（暫定のドメイン名を OUTPUT_FILE に記録する）で覆われています。漏れが確かなのは、cross の `_constants`・`_structures`（:173-188）と cross の `_flows`（:190-195 は :197 の共通注意の範囲内とも読める）です。per-repo の `_structures` を昇格する手順は close-agent にありません。
- **A1-17:** 監査者の報告に加えて、エラーにならない形も再現しました。`src\network\foo.c` は JSON として正しく読めてしまい、`\n` と `\f` が制御文字に変わります。結果は exit 0・`no-path`・`_general` です。update-knowledge は no-path を人に示しますが、survey の MODULE_FALLBACK はそのまま `_general` になり、Step 9 に何も出ません（survey:269-271）。ただし survey-agent.md:45-47 は `/` 区切りで書くよう指示しているので、起きにくいです。
- **A2-1（🔴→🟡）:** ラベルを合わせても、A1-7 のとおりディレクトリのパスが渡るので、analyst は Read に失敗して §0 に記録します。人が気付ける形になるのは A1-7 と組にした場合です。知見は DOCS と AI_INDEX の行には残っています。
- **A2-6:** 共通の rulebook の行が消えるのは、C2 の時点で `project-rulebook-{repo}.md` が1つでもある場合だけです。`_common_knowledge_rows` が空なら upsert を呼ばないからです（promote.py:626）。具体的には、マルチリポジトリでは初回の close から消えます（01-init が作る）。シングルリポジトリでは、前回の close の C3.5 が rulebook を作った（close-agent:63「create if absent」）後の close から消えます。監査者の「初回の close で」は、シングルリポジトリには当てはまりません。
- **A2-8:** 先行更新の LLM がディレクトリ名をケバブ形式に変えるかで決まります。11-specs の先行更新を実際に動かしたときの AI_INDEX の行（または取得の手順を明示した記述）が分かれば判断できます。
- **A2-11:** {V} で作ったリポジトリ（DOCS をサブディレクトリ `baseline_docs/` に置いた）で、次の2点を再現しました。
  - ローカルで AI_INDEX.md を変えたまま `git -C baseline_docs pull` を実行すると、「Please commit your changes or stash them… Aborting」で exit 1 になる。
  - `git -C baseline_docs diff --name-only ORIG_HEAD HEAD` は `baseline_docs/AI_INDEX.md` を返す（DOCS からの相対パスではない）。
  - 監査者の報告に加えて、同じ理由で C0-4 の PROTECTED_FILES の照合（close:244-249。DOCS からの相対パスと比べる）も一致せず、競合を検出できなくなります（🔶。git の出力からの推論）。

## 2. 抜き取り確認の表

| 領域 | 約束（一覧の #） | 使った検索（パターンと範囲） | 漏れ | 漏れの書く側・読む側と食い違いの有無 |
|---|---|---|---|---|
| A1 | #17 列挙（`list_places`）と読む側 | `constraints\.md\|code-knowledge/\*\*\|knowledge/code-knowledge`（ClaudeCode・tools/harness の .md/.py。既知の書く側を除く）と `list_places\|applicable_places`（skills・agents） | なし | 読む側は prelim-agent:167、promote.py:596、domain_refs.py:184,370 だけ。architect-agent:143,197 は SPO §5.7 を読む（A1 の結論どおり） |
| A1 | #11 `place` の入力 JSON | `knowledge_place\.py\b`（ClaudeCode・tools）と `"targets"\|"fallback"`（skills・agents） | なし | 呼び出しは boundary・close-agent・survey-promote・update-knowledge:158・survey:265 だけ。specout_bfs.py:3039 と specout_slice.py:4928 の `targets` は別の JSON（関係なし） |
| A2 | #1 progress.md の「工程11 AI_INDEX先行更新セクション」 | `先行更新\|先行 upsert\|PREUPDATED\|preupdated`（ClaudeCode・tools） | なし | 書く側は 11-specs:604-619、読む側は promote.py:234-250,548-551,1184-1188 だけ。xddp-common:181 と xddp_progress.py:163,195 は ARTIFACT_LINK の「先行更新」で別のもの |
| A2 | #8 CRS ナビゲーションと写し | `/crs/\|crs/CRS\|"crs"`（skills・agents）と CRS の元のパス（03-req） | なし | 写しの元 `03_change-requirements/CRS-{CR}.md` は 03-req:25,71,91 と一致する。機械的に読む側は無い |
| A2 | #12 用語集 | `glossary\.md\|## 用語集`（skills・agents）と `_glossary_term_count` の見出し | なし | promote.py:461-473 が数える `## 用語一覧` は、glossary-template.md:9 と update-knowledge:224 に一致する |

## 3. 新たに気付いた食い違い

1. **工程11 は SPO のモジュールを `modules/` の下の「ディレクトリ」として読むが、工程4a は「ファイル」として書く**
   - 書く側: CC/skills/xddp-04-specout/module-documentation.md:220,270（`modules/{モジュール名}-spo.md` のファイル）、:269（統合パスでは `modules/` を作らない）。ディレクトリになるのはサブディレクトリ分割のとき（:295-296）だけ。
   - 読む側:
     - 11-specs/SKILL.md:120,594（`SPECOUT_MODULES` = `modules/` 配下のディレクトリ名）
     - specs-mod-agent.md:49,125,171（`modules/*/`。廃止候補の判定にも使う）
   - 起きること（🔶。LLM が `modules/*/` をファイルとして読み替えるか次第）:
     - 統合パスと、分割パスのうちサブディレクトリ分割していないモジュールは、SPECOUT_MODULES に入らない。
     - その結果、AI_INDEX の先行更新の対象から漏れる。
     - Step MOD では、今回の CR のモジュールが「SPO あり」と判定されず、latest-specs の既存モジュールが廃止候補として出る。
   - 確度: 文面の食い違いは ✅、起きることは 🔶。担当外（11-specs・specout の領域）。重大度の案は 🟡（廃止候補は人の確認待ちで、削除はしない。mod-agent:178）。
2. **A2-11 の拡張:** C0-4 の PROTECTED_FILES の照合も、git が返すパスの基準の違いで一致しなくなります（上記。🔶）。
3. **survey が AI_INDEX に書く「最終更新CR」の値がアーカイブ候補の判定に合わない（参考・🔵）:** survey が書く `SURVEY-{TODAY}`（survey/SKILL.md:393,397）は、アーカイブ候補の正規表現 `\bCR-…`（promote.py:636）に一致しません。survey の行はアーカイブ候補に出ません。影響は小さいです。

## 4. 実行したこと
- 読み取り: `sed -n`・`grep -rn`・`cat -n`（{W} の CC/ 配下、ADR-0033、README）。
- 再現（すべて {V} = verify-V1 の中。`PYTHONDONTWRITEBYTECODE=1 python3 -B`。{W} のスクリプトは sys.path で import し、引数で {V} のファイルを渡した）:
  - r1: promote.update_ai_index → domain_refs.resolve（A2-1・A1-7）。AI_INDEX を外した場合（A1-8）。
  - kp: knowledge_place.py place（A1-17 の2形・R1・R4）、list_places・applicable_places（R1）。
  - r2: detect_breaking_changes・_cross_interface_rows・upsert_table（A2-2 (a)(c)）。
  - r3: 先行更新の行だけがある DOCS で domain_refs.resolve（A2-3）。
  - r4: 01-init の共通知識の表に update_ai_index を当てた（A2-6）。
  - _parse_frontmatter・_join_row（A2-9）。
  - g: {V} の中に作った git リポジトリで pull の拒否と diff のパスの基準（A2-11）。
- `cd {W} && git status --short` は空でした（exit 0）。{W} に新しい `__pycache__` はありません。
- 確認していないこと:
  - LLM の振る舞いに依存する部分（A1-3・A1-4 の採番、A2-2(b)、A2-5 の影響、A2-8、A2-11 で LLM が pull の失敗をどう扱うか）。
  - 11-specs の先行更新と Step MOD の実際の出力。
  - 単体テスト（make test）は実行していません。