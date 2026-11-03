# 約束の監査の報告書（PLAN-20261103-contract-audit 段階2a）

作成日: 2026-11-03
**状態: 途中（A2 だけを実施。検証・統合の前）。** プラン 3.2.4 の段取りに従い、A2 を先に1体で行った結果と、トークンの実績・指摘の質を人に報告するための版。
残りの監査（A1・A3・A4・A5）・検証（3.2.3）・統合（重複の除去・重大度の確定）・「段階3 の割り当て」は、人の判断の後に行い、この文書を書き足す。

- 対象リビジョン: ecb54c4（`audit/contract-audit-2026-11` の、段階2a を始めた時点の HEAD。`ClaudeCode/`・`tools/` は fbf3956 と同一。`git diff --stat fbf3956 ecb54c4 -- ClaudeCode tools` の出力が空であることを確認した）
- 監査用の worktree: セッションのスクラッチのディレクトリに `git worktree add --detach {スクラッチ}/audit-ecb54c4 ecb54c4` で作成。監査の後、その worktree に変更が無いこと（`git status --short` が空）を確認した。
- 行番号: ecb54c4 の値。パスの `CC/` は `ClaudeCode/.claude/` の略。
- 段階1 の報告書: [review-fbf3956-2026-11.md](review-fbf3956-2026-11.md)

---

## 1. 実行の記録

| 項目 | 内容 |
|---|---|
| 実行日 | 2026-11-03 |
| エージェント | A2 の監査者 1体（`general-purpose`。モデル claude-opus-5-5） |
| 所要時間 | 397 秒（ハーネスの通知の `duration_ms` 397435） |
| ツールの呼び出し | 32回（ハーネスの通知）。内訳（記録ファイルの集計）: Bash 20・Read 10・Grep 1・報告 1 |
| トークン（ハーネスの通知） | `subagent_tokens` 245,008 |
| トークン（記録ファイルの API 応答の `usage` の合計。31回） | 出力 38,049・キャッシュ作成 229,975・キャッシュ読み 5,370,113・その他の入力 62 |
| A2 の後に手順を直したか | まだ決めていない（人の判断待ち。下の 2.3） |

**プランとの違い（ツール）:** プラン 3.2.4 は監査者のツールを Read・Grep・Glob だけとしている。監査者への指示もそのとおりにしたが、この環境のサブエージェントには Grep・Glob が無く（監査者の報告: 呼び出すと「Grep is not available — use grep via Bash」と返った。記録ファイルにも Grep の呼び出しが1回だけある）、監査者は検索と行の表示に Bash（`grep -rn`・`sed -n`・`ls`・`wc`・`tail`・`git log -1`）を使った。
メインのセッションで、記録ファイルの Bash の20回の呼び出しがすべて監査用の worktree に `cd` してから始まることと、監査の後の worktree に変更が無いことを確かめた。各コマンドの全文が読み取りだけかは、先頭160文字だけを見たので確認していません。

**トークンの数え方について:** ハーネスの `subagent_tokens`（245,008）と、記録ファイルの `usage` の合計（キャッシュ読みを含めると約564万）は、数えているものが違う。`subagent_tokens` が何を数えているかは確認していません。課金の量はキャッシュ読みの単価がほかと違うので、どちらの数からも直接は出していない。

---

## 2. A2 の結果の要約と、指摘の質の所見（人の判断の材料）

### 2.1 結果の要約

- 確認した約束: 16件（うち食い違いなし 4件〔#1・#8・#12・#16〕、食い違いあり・記述の不整合・推論を含むもの 12件）
- 時期の約束: 8件
- 指摘: 11件（監査者の重大度の案: 🔴1・🟡7〔#7 は「🔵寄り」〕・🔶推論2・🔵1）
- 担当外の指摘: なし
- 段階2b の候補: 1件

| # | 重大度（監査者の案） | 内容 | 確度（監査者） |
|---|---|---|---|
| 1 | 🔴 | code-knowledge インデックスの `_structures` のラベルが書く側（`構造体関連図`）と読む側（`共有構造体`）で違い、工程2 に `_structures/` が届かない | ✅ |
| 2 | 🟡 | クロスインタフェース一覧の「⚠️ 破壊的変更あり」が付かない（CHD のインタフェース名とケバブ形式のディレクトリ名を変換せずに比べる）。付いた場合はキー列が変わり行が増え、工程2 のパスも壊れる | ✅（一部 🔶） |
| 3 | 🟡 | 11-specs の先行更新の目的（close の前に次の CR の工程2 が参照できる）が、`domain_refs.py` のフォールバックの条件のため達成されない | ✅ |
| 4 | 🟡 | 過去の DSN／CHD を AI_INDEX から引く読む側（工程5・6）に、書く側が無い | ✅ |
| 5 | 🟡 | TSP／TRS の表のキーが repo だけで、過去の CR の一覧にならない | ✅（影響は 🔶） |
| 6 | 🟡 | 「共通知識」の列が init と promote で違い、初回の close で共通の project-rulebook の行が消える | ✅ |
| 7 | 🟡（🔵寄り） | 「最終更新CR」を今の CR で触っていない行にも付ける。11-specs が引く promote.py の文が実在しない | ✅ |
| 8 | 🔶 | 先行更新のモジュール名（SPO のディレクトリ名）と latest-specs のディレクトリ名（ケバブ形式）が違いうる | 🔶 |
| 9 | 🔵 | ひな形が3つある・プレースホルダー行が残る・知識参照ガイドの参照先の名前・`state` 列・`related-modules: []`・セルの `|` | ✅（一部 確認していません） |
| 10 | 🟡 | 時期: code-knowledge インデックスを書くのが C3.6 の前。survey の knowledge への昇格では AI_INDEX を更新しない。`_structures`・`_constants` は AI_INDEX 経由でしか読まれない | ✅ |
| 11 | 🔶 | 11-specs の先行更新（コミットしない）と close C0-2 の `git pull`、`PULLED_FILES` の相対パスの照合 | 🔶 |

### 2.2 指摘の質の所見（メインのセッション）

**確かめたこと:**
- 指摘#1 は、既知の不具合（PLAN-20261103-domain-refs-shared-knowledge が扱う、プラン 1.1 の表の3行目）と同じもので、両側の定数をメインのセッションでも読んで一致しないことを確認した（`CC/skills/xddp-02-analysis/scripts/domain_refs.py:35-38` の `"_structures": "共有構造体"`、`CC/skills/xddp-close/scripts/promote.py:601` の `("_structures", "構造体関連図")`）。既知の不具合を独立に見つけたことは、手順が機能している材料になる。
- 指摘#2〜#11 は、まだ検証していない（プラン 3.2.3 の検証は、残りの監査の後にまとめて行う予定）。

**良い点（報告の内容から）:**
- 約束ごとに書く側・読む側のファイルと行番号があり、検証者が読み直せる粒度になっている。
- 「食い違いなし」の約束（#1・#8・#12・#16）も一覧にあり、何を見たかが分かる。
- 時期の約束を Step の順序の根拠（ファイル:行）付きで表にしている。
- 確度を ✅／🔶 で分け、推論の根拠（例: #2 (b) は 11-specs に breaking の判定の手順が無いこと）を書いている。「確認していないこと」も列挙している。
- ADR に受け入れた制限として書かれているもの（ADR-0033:51, 80）を区別している（#10）。

**気になる点（手順・入力を直すかの材料）:**
1. **約束の一覧の粒度が揃っていない。** #2・#3 は複数の小さな約束（列・キー・リンクの形・行の範囲）を1行にまとめ、#9 は6つの別々の不整合を1つの指摘にまとめている。統合と段階3 の割り当ては指摘の単位で行うので、#9 は分けたほうが割り当てやすい。
2. **「見つけた検索語」の列が粗い。** 多くの行が `AI_INDEX`（範囲 CC 全体）だけで、参照をたどって足した書く側・読む側（例: #10 の `design/README.md`、#9 の mod-agent）をどの検索で見つけたかが行ごとには分からない。抜き取り確認（3.2.3）で検証者が独立に検索し直すので致命的ではない。
3. **一部のファイルを部分的にしか読んでいない。** 01-init（95-214行）・survey（330-429行）・05-arch・06-design・09-test は Step 0 等の該当範囲だけ。手順 2.（すべての書く側・読む側を Read する）の「Read」を該当範囲で満たしたと解釈している。報告に読んだ範囲が明記されているので、検証者が補える。
4. **領域の境界に近い指摘がある。** #3・#8 は `latest-specs/`・`{DOCS}/{repo}/specs/`（A4）と AI_INDEX の行の両方に関わる。#11 は close C0 の git の扱い。境界の規則（AI_INDEX の行・節に関わる部分は A2）に照らせば A2 でよいが、A4 の監査者が同じ食い違いを報告する可能性があり、統合で重複を除く必要がある。
5. **ツールの違い**（1. の「プランとの違い」）。

### 2.3 人に決めてほしいこと

1. 残りの4体（A1・A3・A4・A5）を並列で行うか。
2. 行う場合、手順・入力を直すか。メインのセッションからの案（決めない）:
   - (a) ツール: 監査者は Bash の読み取りのコマンド（`grep`・`sed -n`・`ls`・`wc`）を使ってよいと明記する（この環境ではサブエージェントに Grep・Glob が無いため）。書き込み・実行をしないことは今までどおり指示する。
   - (b) 粒度: 「確認した約束の一覧」は、列・キー・リンクの形・行の範囲のように、食い違いの有無を別々に判断できる単位で1行にする。指摘は、別々に直せるものを別の指摘にする（#9 のようにまとめない）。
   - (c) 検索語: 参照をたどって足した書く側・読む側は、行ごとに、それを見つけた検索（パターンと範囲、または参照元のファイル:行）を書く。
3. (b)・(c) を直した場合、A2 をやり直すか（プラン 3.2.4。実行の記録に残す）。

### 2.4 残りのトークンの見積もり（計測ではない）

A2 の実績（`subagent_tokens` 245,008、検索語の和集合 19ファイル・7,112行）から、検索語の和集合の行数に比例すると仮定した粗い見積もり。監査者はファイルの全文を読むとは限らず、参照をたどって足すファイルの量も領域によって違うので、実際は外れうる。

| 領域 | 検索語の和集合（ファイル数・行数。ecb54c4） | 見積もり（`subagent_tokens` 相当） |
|---|---|---|
| A2（実績） | 19・7,112 | 245,008（実績） |
| A1 code-knowledge | 20・16,081 | 約55万 |
| A3 知見ログ・バックログ | 39・18,679 | 約64万 |
| A4 仕様・用語・カタログ | 35・21,102 | 約73万 |
| A5 project-rulebook | 32・8,856 | 約31万 |
| 残り4体の合計 | — | 約220万（A2 と同じ量なら約100万） |

ほかに検証者（1〜3体）の分がかかる。指摘の数と、再現にスクリプトを実行するかで変わるので、見積もっていない。
ファイル数・行数は `grep -rlE '{検索語}' ClaudeCode/.claude/skills ClaudeCode/.claude/agents | grep -v '/tests/'` の結果と、その `cat | wc -l`（ecb54c4 の worktree で実行）。

---

## 3. 段階1 から引き継いだ約束の食い違い

段階1（[review-fbf3956-2026-11.md](review-fbf3956-2026-11.md)）の指摘のうち、約束の食い違いであるもの（プラン 3.1）。担当の領域は A1（code-knowledge の置き場所）。A1 の監査の後に統合する。

| 段階1 の # | 内容 | 確度 |
|---|---|---|
| R1 | 予約名（`_structures` 等）と同じ名前のディレクトリにある対象の制約は、`knowledge_place.py place` の置き場所がその予約名になり、`list_places` が列挙から外すので読まれない | ✅ 実行して再現 |
| R4 | ワークスペースの外の絶対パスの `status` が `not-found` になり、`code-knowledge-boundary.md` と `xddp-update-knowledge` の `not-found` の説明（リポジトリに無い）と合わない | ✅ 実行して再現 |

---

## 4. A2 の監査者の報告（検証前）

以下は A2 の監査者の報告の内容を、表記（`CC/` の略・見出しの水準）だけ揃えて載せたもの。確度は監査者の判断で、検証（プラン 3.2.3）はまだ行っていない。

### 4.1 確認した約束の一覧（A2）

| # | 約束 | 書く側（ファイル:行・節） | 読む側（ファイル:行・節） | 見つけた検索語（パターンと範囲） | 結果 |
|---|---|---|---|---|---|
| 1 | progress.md の「## 工程11 AI_INDEX先行更新セクション」の見出しと `- {節}: 済` の行の書式 | CC/skills/xddp-11-specs/SKILL.md:604-619（Step DONE） | CC/skills/xddp-close/scripts/promote.py:234-250, 548-551（`read_ai_index_preupdated`・`_skip`） | `AI_INDEX`（CC/skills・agents） | なし（書式は一致）。ただし「済」でスキップした後の扱いで食い違いがある（指摘#2・#7） |
| 2 | 「ユースケース一覧」の列（ユースケース／目的（1行）／description／関連モジュール／最終更新CR）・リンク `system/specs/use-cases/{uc}/description.md`・フロントマター `related-modules`・`## 2. 目的・ゴール` | promote.py:354-356, 368-397, 557-559／01-init SKILL.md:143-147／11-specs:581-589／uc テンプレート CC/skills/xddp-11-specs/templates/11_system-use-case-description-template.md:6-8, 34 | domain_refs.py:239-269 | `ユースケース一覧`・`related-modules\|目的・ゴール`（CC 全体） | 列とパスは一致。`related-modules: []` の扱いに 🔵（指摘#9） |
| 3 | 「モジュール別最新仕様」の列・キー（リポジトリ, モジュール）・リンク `{repo}/specs/{module}/spec.md`・行の範囲 | promote.py:362-364, 420-432, 568-574／11-specs:575-602／survey SKILL.md:390-393／01-init:155-159 | domain_refs.py:271-290 | `モジュール別最新仕様`（CC 全体） | 食い違いあり 指摘#3・#7・#8・#9 |
| 4 | 「リポジトリ別仕様書」の列・キー | promote.py:358-360, 400-417, 561-566／survey:394-400 | 機械的に読む側は無い（AI が読むことを想定） | `リポジトリ別仕様書` | 最終更新CR の付け方に食い違いあり 指摘#7 |
| 5 | 「クロスインタフェース一覧」の列・名前の列＝`latest-specs/cross/interfaces/{名前}` のディレクトリ名・「⚠️ 破壊的変更あり」の印 | promote.py:435-457, 576-582／11-specs:577, 289-296／project-rulebook-cross-template.md:61 | domain_refs.py:319-333 | `クロスインタフェース一覧`・`破壊的変更` | 食い違いあり 指摘#2 |
| 6 | cross の CHD のパス `06_design/cross/CHD-{CR}-cross.md`・見出し「インタフェース変更サマリ」・`breaking` 列・`インタフェース` 列（`detect_breaking_changes`） | 06-design SKILL.md:112, 126-130（Step A-cross） | promote.py:1022-1078 | `インタフェース変更サマリ`（CC 全体） | パス・見出し（正規表現）・列名は一致。インタフェース名と AI_INDEX のディレクトリ名との照合で食い違いあり（指摘#2） |
| 7 | 「code-knowledge インデックス」の列（知りたいこと／参照先）と行のラベル `{repo}/{place} 制約・注意事項`・`{repo} 構造体関連図`・`{repo} 共有定数`・`{repo} 機能間フロー` | promote.py:590-605 | domain_refs.py:34-38, 292-313（`_structures`→`共有構造体`、`_constants`→`共有定数`）／analyst-agent CC/agents/xddp-analyst-agent.md:84（種別 `共有構造体`） | `構造体関連図\|共有構造体\|共有定数\|機能間フロー`（ClaudeCode・tools・docs/adr） | 食い違いあり 指摘#1（`_constants` と制約の行はなし） |
| 8 | 「変更要求仕様書（CRS）ナビゲーション」の行と、写し `{DOCS}/{repo}/crs/CRS-{CR}.md`（元は `03_change-requirements/CRS-{CR}.md`） | promote.py:476-485, 607-611（行）、929-947（写し） | AI が AI_INDEX から引く（機械的に読む側は無い） | `CRS-\{CR\}`・`crs/` | なし（行のリンクと写しの先が一致）。節の名前の記述が不整合（指摘#9） |
| 9 | 「テスト仕様（TSP）・テスト結果（TRS）」の行と写し（`09_test-spec/{repo}/TSP-{CR}.md`・`cross/TSP-{CR}-cross.md`・`10_test-results/{repo}/TRS-{CR}-*.md` → `{DOCS}/{repo}/test/`） | promote.py:488-502, 613-617, 950-979 | 09-test SKILL.md:35-41（Step 0「past TSP/TRS list」） | `TSP-\{CR\}\|TRS-\{CR\}-`（09-test・10-test-run） | パスは 09-test:155,191／10-test-run:104,118 と一致。表のキーを repo にしているので過去の CR の行が残らない（指摘#5） |
| 10 | 過去の DSN／CHD の一覧（`{DOCS}/{repo}/design/`・「設計書ナビゲーション」・「リポジトリ別設計書・テスト仕様書」） | 11-specs:631-640／01-init:122, 167-171, 186-190 | 05-arch SKILL.md:109-113, 159／06-design SKILL.md:49-53, 114, 216／designer-agent:45 | `/design/\|設計書ナビゲーション\|リポジトリ別設計書`（CC 全体。`06_design/`・`05_architecture/` を除く） | 食い違いあり 指摘#4 |
| 11 | 「共通知識」の列 | 01-init:173-177（`ドキュメント \| 説明`） | promote.py:524-536, 624-627（`リポジトリ \| project-rulebook \| 最終更新CR`） | `共通知識` | 食い違いあり 指摘#6 |
| 12 | 「用語集」の行 | promote.py:505-524, 619-622 | 機械的に読む側は無い（domain_refs.py:374-379 は直接列挙） | `## 用語集` | なし |
| 13 | 「知識参照ガイド」（初回だけ作る） | promote.py:334-347, 584-588（ADR-0005） | AI が読む | `知識参照ガイド` | 記述の不整合 🔵（指摘#9） |
| 14 | AI_INDEX のひな形（初期の内容） | 01-init:136-178／promote.py:349-365（`AI_INDEX_SKELETON`）／11-specs:51-60・survey:388-389（init を正本として作る） | — | `AI_INDEX`・`Initial file contents` | 食い違いあり 指摘#9 |
| 15 | `--force-full-ai-index` を付ける条件（`PULLED_FILES` に `AI_INDEX.md` が含まれる） | close SKILL.md:236-241（C0-4）、292-299 | promote.py:548-551, 1262 | `AI_INDEX`（close） | 🔶（指摘#11） |
| 16 | code-knowledge-boundary.md「## 知見の置き場所（MODULE）」に従う読む側として「AI_INDEX の更新」を挙げていること | code-knowledge-boundary.md:94-96 | promote.py:596-600（`list_places`） | `AI_INDEX`（xddp-rules） | なし（`list_places` を import している。promote.py:34-35） |

### 4.2 時期の約束の表（A2）

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

### 4.3 指摘（A2。検証前）

#### 指摘#1 🔴 code-knowledge インデックスの `_structures` のラベルが書く側と読む側で違う
- **約束:** 「知りたいこと」列のラベル `{repo} {種類名}`
- **書く側:** CC/skills/xddp-close/scripts/promote.py:601 `("_structures", "構造体関連図")` → 行のラベルは `{repo} 構造体関連図`（:603）
- **読む側:** CC/skills/xddp-02-analysis/scripts/domain_refs.py:35-38 `"_structures": "共有構造体"`。:305-307 は `f"{repo} {type_name}"` がラベルとして AI_INDEX に無ければ `continue` する。:34 のコメントは「promote.py update_ai_index() と同一の対応」と書いているが、実際には違う。
- **食い違い:** `repo-a 構造体関連図` と `repo-a 共有構造体` が一致しない（`共有定数` は両側で一致する）。
- **起きること:** 工程2 の `DOMAIN_REF_PATHS` に `{DOCS}/{repo}/knowledge/code-knowledge/_structures/` が一度も入らない。analyst-agent（CC/agents/xddp-analyst-agent.md:84）が種別 `共有構造体` の参照先として期待している構造体関連図の知見が、警告なしに渡らない。AI_INDEX が無い場合の経路（domain_refs.py:334-365）も `_structures`・`_constants` を列挙しないので、どの経路でも読まれない。単体テスト（test_domain_refs.py）にこのラベルを確かめるケースは見当たらない（grep で 0 件）。
- **確度:** ✅ 両側の定数を読んで確認した。（メインのセッションも両側の定数を読んで一致しないことを確認した。この不具合は PLAN-20261103-domain-refs-shared-knowledge が扱う既知のもの）
- **修正案（決めない）:** ラベルの対応を1か所（例: knowledge_place.py か promote.py の定数）にまとめて両側で import する。または `_structures`・`_constants` も制約と同じように直接列挙する。

#### 指摘#2 🟡 クロスインタフェース一覧の「⚠️ 破壊的変更あり」が付かない・付いた場合も表と工程2 の参照を壊す
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

#### 指摘#3 🟡 先行更新の目的（close の前に次の CR の工程2 が参照できる）が達成されない
- **約束:** 11-specs:578「xddp-close 実行前に次 CR の xddp-02-analysis が参照できる状態にする」、11-specs:666「次の CR の xddp-02-analysis は `latest-specs/` から直接参照します」
- **書く側:** 11-specs Step DONE の先行更新（:575-602）。リンク先が close の前には無いことを認めている（:642-645）。
- **読む側:** domain_refs.py:288-290 は AI_INDEX で当たったモジュールを `{DOCS}/{repo}/specs/{mod}/spec.md` としてだけ追加する（ファイルが無ければ飛ばす。:233-236）。latest-specs へのフォールバックは `{DOCS}/{repo}/specs` ディレクトリ自体が無い場合だけ（:382-384）。ユースケースも `{DOCS}/system/specs` が無い場合だけ（:398）。01-init:120 が `{DOCS}/{repo}/specs/README.md` を作るので、通常このディレクトリはある。
- **起きること:** close の前に始めた次の CR の工程2 では、先行更新した行のモジュール・ユースケースが参照先から何も言わずに抜ける。`DOMAIN_REF_MODE` は `normal` のままになる（:420-423）。
- **確度:** ✅（両側のコードを読んで確認した）
- **修正案（任意）:** domain_refs で、DOCS 側のファイルが無いときにファイル単位で latest-specs へフォールバックする（`degraded`）。

#### 指摘#4 🟡 過去の DSN／CHD を AI_INDEX から引く読む側に、書く側が無い
- **読む側:** 05-arch SKILL.md:109-113（`{DOCS}/{repo}/design/` があれば AI_INDEX から過去の DSN の一覧を探す）、06-design SKILL.md:49-53, 114、designer-agent:45（`{DOCS}/cross/design/`）
- **書く側（とされるもの）:**
  - 11-specs:631-640 が「設計書ナビゲーション」に `{DOCS}/{repo}/design/DSN-…` の行を足し、「リンク先は xddp-close Step C4 完了後に有効になる」と書いている。しかし close の C4 は CRS の写しだけ（promote.py:929-947）。
  - 01-init:167-171 の「リポジトリ別設計書・テスト仕様書」には「xddp-close Step C4/C5 が更新する」とあるが、promote.py にこの節を書く処理は無い。
  - 01-init:186-190 の `design/README.md` は「このディレクトリは本ツールでは使用されていません」と書いている。
  - `/design/` を grep した結果（CC 全体。`05_architecture/`・`06_design/` を除く）、DSN・CHD を `{DOCS}` に写す処理は見つからなかった。
- **起きること:** 05・06 の Step 0 は過去の設計を見つけられない（`design/` はあるので手順には入るが、一覧が無い）。11-specs が足すリンクはずっと壊れたまま。CHD の行はどこにも無い。
- **確度:** ✅（書く側が無いことを grep で確認した）
- **修正案（決めない）:** DSN・CHD を昇格させるか、読む側の手順と 11-specs の設計書ナビゲーション、init のひな形の節を消すかを決める。

#### 指摘#5 🟡 TSP／TRS の表が repo ごとに1行で、過去の CR の一覧にならない
- **書く側:** promote.py:616-617（キー列 [0]＝repo）。CR ごとに同じ行を置き換える。
- **読む側:** 09-test SKILL.md:38-40（「past TSP/TRS list」から最大3件の TSP・2件の TRS を読む）
- **起きること:** AI_INDEX には各 repo の最新の CR の TSP・TRS しか残らない。写しは `{DOCS}/{repo}/test/` に溜まるので、LLM がディレクトリを列挙すれば補える。
- **確度:** キーで置き換わることは ✅。影響の大きさは 🔶（LLM がディレクトリを見るかどうか次第）。
- **修正案（任意）:** キーを (repo, 最終更新CR) にする。CRS ナビゲーションと同じく CR ごとの行にする。

#### 指摘#6 🟡 「共通知識」の列が init と promote で違い、初回の close で共通の project-rulebook の行が消える
- **書く側1:** 01-init:173-177（`ドキュメント | 説明`、`[project-rulebook.md](project-rulebook.md)` の行）
- **書く側2:** promote.py:627（`リポジトリ | project-rulebook | 最終更新CR`）。`upsert_table` はヘッダが違えばデータ行を捨てる（:200-202）。
- **起きること:** 共通の `project-rulebook.md` は `{DOCS}` に写される（:984-990）が、AI_INDEX の行は消え、promote.py には共通の rulebook の行を作る処理が無い。`_common_knowledge_rows` は rulebook が変わっていなくても、全 repo の最終更新CR を今の CR にする（:530-535）。
- **確度:** ✅

#### 指摘#7 🟡（🔵寄り）「最終更新CR」を今の CR で触っていない行にまで付ける。11-specs の「同じ行集合」という説明は事実と違う
- **書く側:**
  - promote.py `_module_spec_rows`（:420-432）は latest-specs の全モジュールディレクトリ（C0-3 で DOCS から取り込んだ他の CR・survey のモジュールを含む）に今の CR を付ける。
  - `_repo_spec_rows`（:561-566）は常に更新する。close の AFFECTED_REPOS は FILTER_BY_SPO=false で REPOS_KEYS 全部（close:21-23、xddp-common SKILL.md:131-132）なので、今の CR が触っていない repo にも付く。
- **11-specs の説明:** :591-598 は、先行更新の行を SPECOUT_MODULES に限り「promote.py の『今回 CR で生成・更新した全モジュールの行を upsert』と同一の集合」と書いている。しかしその文は promote.py に無い（grep で 0 件）。:624-626 が引く「IS_MULTI への移行対応…」も無い。
- **逆向き:** 先行更新が「済」の場合、MOD が更新した「SPO なし・CHD あり」のモジュール（CC/agents/xddp-specs-mod-agent.md:50-51）は SPECOUT_MODULES に入らないので、行が更新されない。
- **起きること:** 最終更新CR がずれる。これを使うアーカイブ候補の判定（promote.py:639-654）も、実際には古い行を新しいと見る。
- **確度:** ✅（コードと文の有無を確認した）

#### 指摘#8 🔶 先行更新のモジュール名（SPECOUT_MODULES）と latest-specs のディレクトリ名（ケバブ形式）が違う場合がある
- **書く側:** 11-specs:591-598（`04_specout/{repo}/modules/` のディレクトリ名）。promote.py:426-431 と domain_refs.py:290 が前提にするのは latest-specs のディレクトリ名。
- **変換規則:** mod-agent:159-161 では `AuthService` → `auth-service` に変える。
- **起きること:** 先行更新の LLM が SPO のディレクトリ名をそのまま書くと、domain_refs が存在しないパスを作って何も言わずに飛ばし、close で行が重複しうる。
- **確度:** 🔶（11-specs は「列・リンクは promote に従う」とも書いており、LLM が変換するかどうかで決まる）

#### 指摘#9 🔵 ひな形・説明の不整合（動作への影響は小さい）
- **ひな形が3つある:** 01-init:136-178（6節・プレースホルダー行あり）、promote.py:349-365（3節）、11-specs:53-59・survey:388（init を正本とする）。11-specs:57-59 は「code-knowledge インデックス・CRS ナビゲーションはテーブル形式ではない」と書くが、promote.py:605, 611 は表で書く。
- **プレースホルダー行が残り続ける:** init の `（… 実行後に自動追記） | — |…`（01-init:147,153,159,165,171）。ヘッダが一致すると upsert で残り続ける（promote.py:204-218）。domain_refs は `（` で始まる行を除外する（:249）ので、実害は表示だけ。
- **知識参照ガイドの参照先の名前と位置:** promote.py:342, 345 は「変更要求仕様書」テーブル・「上記『テスト仕様（TSP）』テーブル」を指すが、実際の見出しは「変更要求仕様書（CRS）ナビゲーション」「テスト仕様（TSP）・テスト結果（TRS）」（:611, 616）。しかもガイドの後に末尾へ足すので「上記」ではない。
- **`state` 列が常に `—`:** promote.py:431、survey:393。mod-agent:97 は `state-machine.md` を作るのに、リンクにならない。
- **`related-modules: []` の扱い:** フロントマターの `related-modules: []`（テンプレート:20 の指示）は `_parse_frontmatter` で文字列 `"[]"` になる（promote.py:118, 387-389）。関連モジュールの列に `[]` と出て、domain_refs は `[]` をモジュール名として扱う（:259-264。パスが無いので飛ばされるだけ）。
- **`|` のエスケープ:** promote の `_join_row`（:58-59）はセル内の `|` をエスケープしない。domain_refs の分割（:124-126）は `\|` を扱わない（目的の列に `|` があると列がずれる。実例は確認していません）。

#### 指摘#10 🟡 時期: code-knowledge インデックスを書くのが C3.6 の前。survey の knowledge への昇格では AI_INDEX を更新しない。`_structures`・`_constants` は AI_INDEX 経由でしか読まれない
- **書く側:** promote.py:590-605（close C2）。code-knowledge を書くのは C3.6（close:310-327）で、その後になる。survey の (b)（survey:383 の③は (c) だけ）。
- **読む側:** domain_refs.py:292-311（`_structures`・`_constants` は AI_INDEX のラベルがある場合だけ集める）
- **起きること:** 制約は直接列挙するので影響を受けない（ADR-0033:51, 80 に記録済み）。しかし `_structures`・`_constants` は、作られた CR の close では載らず、同じ repo の次の close まで工程2 に届かない。survey で昇格したものは、その repo が次の close の AFFECTED_REPOS に入るまで届かない（指摘#1 があるので `_structures` はいつまでも届かない）。
- **確度:** ✅（Step の順序とコードから）

#### 指摘#11 🔶 11-specs の先行更新と close の `git pull`・`PULLED_FILES` の照合
- 11-specs Step DONE は git 管理の `{DOCS}/AI_INDEX.md` を書き換えてコミットしない（11-specs:575-579）。close C0-2 の `git -C {DOCS} pull`（close:208）で、リモート側も AI_INDEX.md を変えていると、git は作業ツリーの変更を理由に pull を止める。C0-2 には pull が失敗したときの扱いが書かれていない（close:207-209）。
- close:236-241, 293 は `git -C {DOCS} diff --name-only` の結果を「DOCS ルートからの相対パス」として `AI_INDEX.md` と比べる。しかし git はリポジトリのルートからの相対パスを返すので、DOCS が上位のリポジトリの一部（例: `baseline_docs/` がワークスペースのリポジトリの中）のときは `baseline_docs/AI_INDEX.md` になり、一致せず `--force-full-ai-index` が付かない。
- **確度:** 🔶（git の振る舞いと LLM の解釈に依存する。実行で確かめていない）

### 4.4 担当外の指摘（A2）

なし（監査者の報告）。`{DOCS}/{repo}/design/README.md` の文言は、AI_INDEX の設計書の行に関わるので指摘#4 に含めた。

### 4.5 段階2b の候補（A2。検証しない〔プラン 3.2.3〕）

- **段階2b:** cross の CHD「インタフェース変更サマリ」の列。書く側 06-design SKILL.md:126-130（`インタフェース | 変更種別 | breaking` の3列）。読む側 xddp-common SKILL.md:138-141（Resolve Affected Repos の FILTER_BY_SPO=true が「影響リポジトリ」を読む）と xddp-common/reviewer-checklists/SPEC.md:31（「CHD cross の影響リポジトリ」と照合する）。CHD のひな形に「影響リポジトリ」列が無いので、11-specs の AFFECTED_REPOS の追加条件と SPEC レビューの照合の拠り所が無い。確度 ✅（ひな形の表とプロシージャの文を読んだ。LLM が別の表〔実装依存関係の消費リポジトリ〕から読み替える可能性は 🔶）。
- verifier-agent:86-92・07-code:207-212・coder-agent:31 が読む「新規追加／変更／削除」は、06-design の「変更種別」列と矛盾しない（ひな形の例は「新規追加」だけ）。食い違いはなし。

### 4.6 監査者が読んだファイルと、確認していないこと

**読んだファイル（監査者の報告）:**
- 全文: CC/skills/xddp-close/scripts/promote.py、CC/skills/xddp-02-analysis/scripts/domain_refs.py、CC/skills/xddp-11-specs/SKILL.md、CC/skills/xddp-close/SKILL.md、docs/adr/ADR-0005-knowledge-guide-once.md
- 範囲: CC/skills/xddp-01-init/SKILL.md:95-214、CC/skills/xddp-survey/SKILL.md:330-429、CC/skills/xddp-05-arch/SKILL.md:100-130、CC/skills/xddp-06-design/SKILL.md:40-70, 95-164、CC/skills/xddp-09-test/SKILL.md:28-60、CC/skills/xddp-02-analysis/SKILL.md:30-60、CC/skills/xddp-common/SKILL.md:120-150、CC/skills/xddp-common/templates/project-rulebook-cross-template.md:50-66、CC/skills/xddp-rules/code-knowledge-boundary.md:85-110、CC/skills/xddp-11-specs/templates/11_system-use-case-description-template.md:1-40、CC/skills/xddp-11-specs/templates/11_cross-interface-spec-template.md:1-15、CC/agents/xddp-specs-uc-agent.md:50-75、CC/agents/xddp-specs-mod-agent.md:45-64, 150-161、CC/agents/xddp-verifier-agent.md:84-92、CC/skills/xddp-07-code/SKILL.md:204-212、CC/skills/xddp-02-analysis/scripts/tests/test_domain_refs.py:140-225、docs/adr/ADR-0033-constraints-module-key.md:45-85
- grep の該当行だけ: coder-agent、designer-agent、test-writer-agent、xddp-08-verify、10-test-run、analyst-agent、close-knowledge-agent、survey-promote-agent、reviewer-checklists/SPEC.md、test_promote.py

**確認していないこと（監査者の報告）:**
- スクリプト・テストの実行による再現（指摘はすべてコードを読んだ結果）
- CC/agents/xddp-close-knowledge-agent.md・xddp-survey-promote-agent.md の全文（AI_INDEX を書かないことは grep で確認しただけ）
- test_promote.py の全文（grep の該当行だけ）
- 05-arch・06-design・09-test の Step 0 以外の節
- 04-specout の `modules/` のディレクトリ名がケバブ形式かどうか（指摘#8 の前提）
- xddp-status・xddp-abort・xddp-update-knowledge が AI_INDEX に触れるか（`AI_INDEX` の grep には出なかったので、触れていないと判断した）
- `.claude/` 以外の README.md・CLAUDE.md の記述と実装との整合

---

## 5. まだ書いていない節（残りの監査・検証・統合の後に書く）

- 指摘の一覧（統合後。#・重大度・領域・内容・確度・検証結果）
- A1・A3・A4・A5 の「確認した約束の一覧」と時期の約束の表
- 抜き取り確認の結果
- 段階2b の候補（統合後）
- 段階3 の割り当て（段階1 の R1〜R5 を含む。PLAN-20261102-cochange-knowledge・PLAN-20261102-impact-hypotheses・PLAN-20260730-specout-recall-crosscheck を書き換える予定を含む）
