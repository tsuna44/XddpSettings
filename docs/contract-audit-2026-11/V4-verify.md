# 検証者 V4 の報告（やり直しの監査の検証・原文。PLAN-20261103-contract-audit 段階2a）

> 検証者の最終報告をそのまま載せたもの。統合後の結果は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。

# V4 検証報告（やり直しの監査の検証。A3r・A5r の新しい指摘と追記、抜き取りは A3・A5）

`{W}` = audit-ecb54c4（ecb54c4）。`CC/` = `ClaudeCode/.claude/`。行番号は ecb54c4 の値です。再現はすべて `{V}` = verify-V4 の中で行いました。`{W}` の promote.py・collect_insights.py・knowledge_place.py を `{V}/lib` にコピーし、`PYTHONDONTWRITEBYTECODE=1 python3 -B` で動かしています。

## 1. 指摘の検証の表

| 指摘 | 判定 | 確度 | 重大度の案 | 根拠 | 重複 |
|---|---|---|---|---|---|
| A3-24 | 確認（条件が少し広い） | ✅ 再現 | 🔵 | promote.py:1081-1097 はファイルが無いと空のリストに警告だけを書きます（`_write_lines`:68-74 が親ディレクトリも作る）。promote.py:900-901 は空のときだけヘッダーを書きます。**再現**: 無い `docs/cross/knowledge/lessons-learned.md` に `append_breaking_warning` を呼ぶと、先頭行が `### 破壊的変更警告（CR-1）` になりました。その後に `promote_lessons_learned` で cross の LL を足しても、ヘッダーは付きません。条件の追加は表の後に書きます | V2 N3 を具体化したもの |
| A3-25 | 確認 | ✅ | 🔵 | coder-agent.md:47-56（Coding Memo の中身に気づき節が無い）、verifier-agent.md:131-175（見出しは A〜J・総合判定・NG事項一覧だけ）。07・08 にはテンプレートが無く（`ls`）、`気づき` で grep しても coder・verifier・07・08 SKILL は0件。読む側は collect_insights.py:3,164-169。どちらも `literal` で、ファイルは実在するので「存在しなかった想定ファイル数」には入りません。ただし収集サマリの「気づきメモ節ありファイル数」（collect_insights.py:339）が少なく出るので、人が見れば気付けます | — |
| A3-26 | 確認 | ✅ | 🔵 | SPO tpl:308 のコメントは「手で直さない（再実行で上書きされる）」で、同じ節の 312-313 は「自由に記録する」と書いています。specout_bfs.py:7627 は `[自動転記]`（4452）で始まらない行を残します。§5.5 には別の残す側のコメント（`WRITER_SCRIPT_KEEP_COMMENT`:4455、tpl:223）があるのに、§9 には使っていません（`_ensure_script_comment` の呼び出しは 7520,7564,7574,7597 だけ） | 関連: A3-14、新たに気付いた N1 |
| A3-27 | 確認 | ✅ 再現（Step D で LLM が示すかは🔶） | 🟡 | promote.py:1117-1121 は global_errors を「リポジトリ別処理結果一覧」の下に書きます。close SKILL.md:302-306 の出力の一覧には共通ファイルのエラーが無く、336（FAILED_REPOS は repo だけ）・345-352（repo ごとに示す）・409（Step E の ✅）にも表示の指示がありません。**再現**: `docs/improvement-backlog.md` を行き先の無いシンボリックリンクにして run を実行しました。exit 0 で `backlog_promoted: false` になり、エラーは出力ファイルの「共通ファイルの昇格エラー」にだけ出ました | 同じ根: A3 担当外1 |
| A3-28 | 一部確認 | ✅（区切りが決まっていない）／🔶（起きるか） | 監査者 🟡→🔵 | Entry Format の close SKILL.md:119 `{#タグ}` は区切りを示していません。読む側の 142 は「カンマ区切り」とし、148 は行の無いタグを飛ばします。違う点: 監査者が「空白区切りの書く側」として挙げた template:16-20 は「タグ一覧」（定義の並び）で、エントリの書式ではありません。update-knowledge SKILL.md:79 は Layer 2（インデックスなし）の入力の例です。Layer 1 のエントリで空白区切りを示す書く側は無く、エントリを書く手順とインデックスを更新する手順は同じ Step C の中にあります（そこに「カンマ区切り」と書いてある） | — |
| A3-29 | 確認（起きる条件は監査者の記述より広い） | ✅ 順序／🔶 LLM | 🟡 | close SKILL.md:72-139 に「今の CR のエントリがあれば足さない」の指示はありません（`再実行\|重複\|already` で grep しても Step B・C には無い）。284→299→312 は人の確認なしに続きます。再実行を案内する箇所は 362,370 のほかにもあります: 173（最終コミットの失敗）、287（extract-ll の失敗。Step B・C の後）、388（FAILED_REPOS があるとき）。どれも再実行で Step A・B・C を繰り返します | 関連: A3-1（重複判定が ID だけ） |
| A3-30 | 確認 | ✅ | 🔵 | SPEC.md:28,39、11-specs SKILL.md:374、survey SKILL.md:351。11-specs SKILL.md の見出し（`grep '^#'`）に「3-4」は無く、`ポリシー` は 374 だけです。実際の規則は各テンプレートの「このファイルには気づきメモセクションなし」（6つのテンプレートの 14-17 行目）と collect_insights.py:113-114 にあります | 同じ型: 新たに気付いた N2 |
| A3 担当外1（AI_INDEX・共通 rulebook の昇格エラー） | 確認 | ✅ 再現 | 🟡 | promote.py:1195（AI_INDEX）・990（C6 の共通 rulebook）・1221（C7）。**再現**: 3つとも行き先の無いシンボリックリンクにして run を実行しました。exit 0 で、3件とも global_errors と出力ファイルにだけ出ました。Step D・E の扱いは A3-27 と同じです | A3-27 と同じ根 |
| A5-29 | 確認 | ✅（定義が無い）／🔶（推測の結果） | 🔵（監査者 🔵〜🟡） | fill SKILL.md:42 は WORKSPACE_ROOT・XDDP_DIR・REPOS_KEYS だけを受け取ります。`{REPO_PATH}` を使うのは :172,174,178 です。REPOS_MAP は xddp_config.py:108,216 にあります。🔵 にした理由: fill:122 が `xddp.config.md` を読ませているので、LLM が `REPOS:` のパスを拾える余地がある | V2 N1 と同じ |
| A5-30 | 確認 | ✅ | 🔵 | `INCLUDE_CROSS` が出てくるのは CC と tools 全体で load-steering-context.md:12,17 だけです。呼び出し元（05:189、06:197、07:126,158、08:112、09:109,174、10:208、feedback:208、sync-design:62）は XDDP_DIR と REPO_NAME だけを渡します。cross の呼び出し（07 B-cross:196-210、08 A-cross:154-171、09 cross:142-161、10:113-119）は RULEBOOK_CONTEXT を渡しません | — |
| A5-31 | 確認（範囲が少し広い） | ✅ 再現 | 🟡 | promote.py:1006 は `repo_results["cross"]` に書きますが、:1111 の `write_output_file` は affected_repos しか回りません。AFFECTED_REPOS は REPOS_KEYS の写しです（xddp-common SKILL.md:131）。close:350-352 は条件なしで「昇格」と書きます。**再現**: `docs/cross` を通常のファイルにして run を実行しました。stdout の `repo_results.cross` には C2・C4・C5・C6 の失敗が出ましたが、出力ファイルの一覧には a・b の成功だけが出ました。範囲の追加: `system` の C2 の失敗（promote.py:325）も同じく出ません（再現。新たに気付いた N3） | 担当外3 と同じ仕組み |
| A5-32 | 確認 | 🔶 | 🔵 | `upstream\|downstream` で CC・tools・README・CLAUDE.md・docs を grep すると、該当は fill:135 だけです（他はレビュー文の英語の表現）。cross tpl:17-38 の表・依存関係のブロックに、この名前の欄はありません | — |
| A5-33 | 確認（漏れが1件ある） | ✅ 渡さない／🔶 影響 | 🔵 | `ARCH_CALL_SHARED`（05:51-53）にも `DESIGN_CALL_SHARED`（06:83-86）にも RULEBOOK_CONTEXT は含まれません。05:279-288・331-340・444-452、06:251-259・303-317・377-385・467-478 のブロックにも ありません。build-design-spec-params.md も `RULEBOOK` で0件です。漏れ: 監査者が読んでいない 06:358-368（A3 の a.。`SECTION4_ERRORS` の修正）も渡しません。修正の呼び出しは、規約を使って書いた既存の文書を最小限に直すだけなので、影響は 🔵 と見ます | — |
| A5-8 の追記（repo 別 §4） | 確認 | ✅／🔶（置き換え） | 🟡 | fill:99 は repo の §4 を未記入の判定の対象にします。:197-198 の §4 の規則は repo か共通かを区別しません。:234 は見出しから次の `---` までを丸ごと置き換えます。repo tpl:116-148（`### テストパターン`:139 を含み、`---` は 149）。knowledge-agent:52 は一致が無ければ新しいサブセクションを足します。補足（🔶）: :233 と :234 の2つの指示はどちらとも読めます。丸ごと置き換えると読むと、§4 のプレースホルダーが1つでも残っていれば、人が書いた他のサブセクションも注記に置き換わります | 同じ根: A5-4、A5-6、A5-7 |
| A5-18 の追記（シングル構成でも注記） | 確認 | ✅（条件が無い）／🔶（注記するか） | 🟡 | 02:287 に IS_MULTI／`len(REPOS_KEYS)` の条件はありません。01-init:226-232 は2つ以上のときだけ repo 別ファイルを作ります | 関連: A5-2 |
| A5 担当外2（AI_INDEX の早見表が `{XDDP_DIR}` を指す） | 確認 | ✅ | 🔵 | promote.py:344 は rulebook について `{XDDP_DIR}/…` だけを挙げ、`{DOCS_DIR}` の写し（988,996）を示しません。同じ表の :343 は lessons-learned について作業中（XDDP）とクローズ済み（DOCS）の両方を挙げているので、扱いがそろっていません。A2.md の #13・指摘#9 は同じ「知識参照ガイド」の別の点（表の名前・「上記」）で、この点は書いていません | 関連: A2 指摘#9（同じブロック） |
| A5 担当外3（cross の C2・C4・C5 の失敗） | 確認 | ✅ 再現 | 🟡 | 上の A5-31 の再現で、C2:309・C4:947・C5:979 の失敗がすべて出力ファイルに出ないことを確かめました。C2 の破壊的変更の警告（:1212）は読んで確かめただけで、実行していません | A5-31 と同じ仕組み。system は N3 |

**表の後の理由**
- **A3-24（条件の追加）:** repo の側でも起きる余地があります（🔶）。01-init:124-130 は、`{DOCS}/{repo}/` が無いときだけ `knowledge/lessons-learned.md` を作ります。一方、codemap SKILL.md:135 は `{DOCS}/{repo}/` を `mkdir -p` で作ります。codemap を init より先に実行すると repo の Layer 2 ができず、その repo の LL が無い CR で破壊的変更があると、ヘッダーの無いファイルができます。
- **A3-28（一部確認）:** 食い違い（区切りが決まっていない）はあります。ただし監査者が挙げた「空白区切りの書く側」は Layer 1 のエントリの書き方ではありません。また書き込みとインデックスの更新は同じ手順の中にあり、そこにカンマ区切りと書かれています。このため起きる見込みは監査者の記述より低いと見て、🔵 にしました。起きた場合に黙って漏れることは監査者の記述のとおりです。
- **A3-29（条件が広い）:** 再実行は LL の書式を直す場合に限りません。最終コミットの失敗、extract-ll の失敗、昇格の失敗でも案内されます。どの再実行でも Step B・C の追記が繰り返されるので、重複が起きる機会は監査者の記述より多くなります。

## 2. 抜き取り確認の表

前回の抜き取り（V2: A3 #1・#16・#22〜24・#29、V3: A5 #3・#35〔旧 #31〕・#40〔旧 #34〕）とは別の約束を選びました。

| 領域 | 約束（一覧の #） | 使った検索（パターンと範囲） | 漏れ | 漏れの書く側・読む側と食い違いの有無 |
|---|---|---|---|---|
| A3 | #2（LL の見出し `### LL-{NNN}：`） | `grep -rn 'LL-'` を CC の .md・.py で（tests、`lessons-learned` を含む行、close SKILL、promote.py は除く）。domain_refs.py と xddp-common/scripts で `LL\b\|LL-\|LL_` | あり（軽い） | close-knowledge-agent.md:60 が見出しの ID を使って `（出典: LL-{NNN}, {CR}）` を付けます（読む側）。見出しは extract-ll がそのまま写すので、食い違いはありません。domain_refs は見出しを解析しません |
| A3 | #21（INSIGHTS の「## 収集サマリ」「抽出エントリ数」） | `grep -rnE '収集サマリ\|抽出エントリ\|走査ファイル数\|節ありファイル数\|存在しなかった想定\|気づきメモ集約\|pending-items/INS'` を CC・tools・README・docs/adr で | なし | — |
| A3 | #19（PENDING-PROMOTE の要確認LL一覧） | `grep -rnE 'unresolved\|repo: ?unknown\|repo：unknown\|昇格スキップ'` を CC で（tests は除く） | なし（食い違いのある漏れは無い） | knowledge-agent.md:65（unknown は飛ばす）は A5 #32 にあり、promote.py:884-887 と一致します |
| A5 | #14（`## 1.6 ドメイン制約`） | `grep -rnE '1\.6\|[Dd]omain [Cc]onstraint\|domain_constraint\|load-domain'` を CC と tools/harness で。fill の節の置き換えの範囲と、共通 tpl の `---` の位置も確かめた | あり（説明だけ） | xddp-common SKILL.md:240（索引の説明）。共通 tpl:38,58 で §1.6 は `---` に挟まれていて、fill（:85-91 に §1.6 の行が無い）が §1・§1.5 を置き換えても §1.6 は消えません。食い違いはありません |
| A5 | #21（`## 7. 変更履歴`） | `grep -rnE '変更履歴\|Change History\|history'` を rulebook を書く全員（02・fill・knowledge-agent・01-init・close・3つのテンプレート・update-knowledge・survey・survey-promote）で | あり（書く側） | fill-rulebook は rulebook を書いても §7 に行を足しません（repo tpl:12 は「追加型で更新」と書く）。読む側の 02:284 は {CR} の行だけを見るので、食い違いはありません。update-knowledge:203,228 の「変更履歴」は callgraph と glossary のもので、rulebook とは無関係です |
| A5 | #1（共通ファイルのパス。補助） | `grep -rniE 'プロジェクト規約\|規約ファイル\|steering'` を CC で（`Load Steering Context` を含む行は除く） | あり（軽い） | sync-design SKILL.md:55,62-63（`STEERING_MAP`。手順を「xddp-common の ## Load Steering Context」と書く）は A5 #35 の読む側にあり、索引 SKILL.md:239 から手順をたどれます。promote.py:344 は担当外2 と同じものです。新しい食い違いはありません |

## 3. 新たに気付いた食い違い

- **N1（SPO §9 の「なし」の行が再実行で残る）:** specout_bfs.py:7629-7630 は、§9 に行が無いと `| 1 | — | なし | — |` を書きます。しかし :7627 の残す条件は `[自動転記]` と `{内容}` しか除かないので、次の assemble-spo でこの「なし」の行が残ります。その後に自動の注記が出ると、表に「なし」と注記が並びます（collect_insights はこの「なし」も1件として集めます。A3-14）。確度 ✅（読んで確認。実行はしていません）、🔵。
- **N2（もう1つの「Section 3-4」も参照先が無い）:** xddp-specs-uc-agent.md:76「機械的先決基準（Section 3-4 参照）」。11-specs SKILL.md にも、この agent にも「3-4」の節はありません。A3-30 と同じ型（バージョンの規則）です。確度 ✅、🔵。担当は A4 か A3 です。
- **N3（system の昇格の失敗も報告されない）:** promote.py:325 は `repo_results["system"]` に失敗を書きますが、:1111 は affected_repos しか出力しません。close Step D にも system の行はありません。**再現**: `docs/system` を通常のファイルにすると、stdout には `system: C2` の失敗が出ましたが、出力ファイルには出ませんでした。確度 ✅、🟡。A5-31・担当外3 と同じ仕組みです。

## 4. 実行したこと

- 読んだ箇所: 指示書 verifier.md、A3r・A5r（全文）、V2・V3 の §1・§2。
  - close SKILL.md（15-30、28-165、278-414）
  - promote.py（62-75、267-330、330-356、520-540、655-672、870-920、940-1016、1075-1135、1185-1250）
  - collect_insights.py（1-10、105-192、290-345）
  - coder-agent.md:40-60、verifier-agent.md（見出し）、07 SKILL:138-206、08・09・10 の cross の呼び出し
  - SPO tpl（300-320 と「書き手」の行）、specout_bfs.py（4452-4455、7590-7632 と grep）、document-agent.md:90-96
  - SPEC.md:25-40、11-specs SKILL（374 と見出し）、survey SKILL:349-352、11 tpl（grep）、specs-uc-agent.md:70-80、lessons-learned-template.md:1-62、load-lessons-context.md、update-knowledge SKILL（74-86、196-229）
  - fill-rulebook SKILL.md:36-248、load-steering-context.md、05 SKILL（51-62、276-345、440-460）、06 SKILL（83-90、196-262、300-318、355-386、460-480）、architect-agent.md:28-40、designer-agent.md:40-50
  - 3つの rulebook テンプレート（共通 1-62、repo 112-170、cross 15-40）、01-init SKILL（110-135、198-240）、02 SKILL:268-300、xddp-common SKILL（120-140、230-240）、sync-design SKILL:58-64、knowledge-agent.md:28-53、xddp_config.py（grep）、A2.md（grep）
- 再現（すべて `{V}` の中）:
  - `{V}/r24`: `append_breaking_warning` → `promote_lessons_learned` で A3-24 を再現しました。
  - `{V}/r31`: `promote.py run` を2回実行しました。1回目は `docs/cross`・`docs/system` を通常のファイルにして、A5-31・担当外3・N3 を再現しました。2回目は AI_INDEX・共通 rulebook・backlog を行き先の無いシンボリックリンクにして、A3-27・A3 担当外1 を再現しました。
- `cd {W} && git status --short` の結果は空でした（rc=0）。`{W}` の中に新しい `__pycache__` もありません。
- 確認していないこと:
  - LLM の振る舞い: タグの区切り方、再実行で足し直すか、Step D で global_errors を示すか、fill の置き換えの範囲、RULEBOOK_CONTEXT を省いたときの出力。
  - C2 の破壊的変更の警告の cross の失敗（promote.py:1212）は実行していません。
  - N1 は実行していません。
  - codemap を init より先に実行する運用があるか（A3-24 の追加の条件）は確認していません。

## やり直しの監査の質の所見

- **約束の一覧の網羅は改善しています。** A3r は #23 を成果物ごとに15行に分け、#38〜#52 を足しました。前回の抜き取りで漏れていた `append_breaking_warning`、survey (c)、coder・verifier を書く側として取り込んでいます。A5r も #8・#36・#38・#55〜#60 を足し、V2・V3 の発見（N1、#3・#35 の漏れ）を反映しました。今回の抜き取り（A3 3件・A5 3件）では、結論を変える書く側・読む側の漏れは見つかりませんでした。漏れたのは説明の行と、食い違いの無い読み手だけです。
- **書く側と読む側の洗い出しも改善しています。** 見つけた方法の略号（S1〜S16）が約束ごとに付き、追跡しやすくなりました。
- **残っている弱点:**
  - 根拠の性格の取り違えがあります。A3-28 では、タグ一覧（定義）と Layer 2 の入力の例を、Layer 1 のエントリの書き方の根拠にしていました。
  - 起きる条件の洗い出しが狭いところがあります。A3-29 は再実行の契機を LL の書式の修正しか挙げておらず、A3-24 は repo の側の条件を挙げていません。
  - 同じ仕組みの横展開が途中で止まっています。A5-31 と担当外3 は cross まで追いましたが、同じ関数の `system` を見落としました。A5-33 では、読んでいない 06:358 の呼び出しを一覧から外しています（ただし報告の「確認していないこと」に明記されています）。
