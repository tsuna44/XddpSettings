# 検証者 V5 の報告（やり直しの監査の検証・原文。PLAN-20261103-contract-audit 段階2a）

> 検証者の最終報告をそのまま載せたもの。統合後の結果は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。

# V5 検証報告（A4 やり直し版: A4-32〜A4-47・A4-16/A4-21 の補足・担当外1件目の補足）

`{W}` = `.../scratchpad/audit-ecb54c4`（ecb54c4）。`CC/` = `ClaudeCode/.claude/`。再現は `{V}` = `.../scratchpad/verify-V5` の中だけで行いました。

**要点:**
- 割り当ての18件のうち、確認が15件、一部確認が3件（A4-38、A4-47、担当外の補足）です。否定・判断できずはありません。
- 抜き取り確認（#14・#16・#24）では、#14 で読む側の漏れが見つかりました。ただし監査者自身が「段階2b・確認していない」と明記している範囲で、値の形の食い違いはありません。
- 新たな食い違いが2件あります。
  - 破壊的変更の印を付けた行が AI_INDEX に重複して残ります（再現済み）。
  - 工程5・6 の「参照した資料を記録する節」がテンプレートにありません。

## 1. 指摘の検証の表

| 指摘 | 判定 | 確度 | 重大度の案 | 根拠 | 重複 |
|---|---|---|---|---|---|
| A4-32 | 確認 | ✅ | 🔵 | 読む側: `CC/skills/xddp-11-specs/SKILL.md:194-196`・`11_overview-deployment-template.md:15-17`。書く側の候補を探した: SPO サマリーのテンプレートの見出し（`04_specout-summary-template.md:11-332`）にその節は無い。`grep -rln 'ハードウェア\|メモリマップ\|タスク配置' CC` の結果は verifier・code-knowledge-boundary・11-specs・close のテンプレートだけで、SPO を書く prelim・document・specout の各 agent には無い | — |
| A4-33 | 確認 | 🔶 | 🔵 | `module-catalog-template.md:26-27`（ディレクトリと主要シンボルだけ）。`xddp-survey/SKILL.md:98`（「主要ファイル・ディレクトリ」）。codemap Step 1c〜1f（`xddp-codemap/SKILL.md:77-136`）も主要ファイルを書かない。`grep '主要ファイル'` は survey:98 と 11・04 のテンプレートだけ。LLM はディレクトリで代用できる | — |
| A4-34 | 確認 | ✅ | 🔵 | 説明: `xddp-04-specout/SKILL.md:519-520`。実際の動作: `specout_bfs.py:2680-2686`（catalog 不在なら `simple` モード）・`:1987-1998`（`simple` では一覧に無いディレクトリを LOW とし、後の波に回す）。LOW のエントリは波数上限で打ち切り記録に残る（`:1914-1918`）ので、失われるものは無いことも確認した | — |
| A4-35 | 確認 | ✅ | 🔵 | `11_system-use-case-sequence-template.md:28`（`../../{repo}/overview/...`）。置き場所は `latest-specs/system/use-cases/{uc}/sequences/`（`SKILL.md:570`）。そこからの `../../` は `use-cases/` を指す。DOCS では `system/specs/…` と `{repo}/specs/…`（`promote.py:289,313`）で深さが違う。uc-agent（`:102`）にリンクの書き方の別の指示は無い | — |
| A4-36 | 確認 | 🔶 | 🔵 | 書く側: `04_specout-cross-repo-template.md:38,41,54`（`### 3.1 {レベル名}レベルのシーケンス図`）・`04-specout/SKILL.md:670`。読む側: `11-specs/SKILL.md:276-278,305-307` | A4-23（ケバブ変換が決まっていない点） |
| A4-37 | 確認 | ✅ | 🔵 | CHD テンプレートの見出し（`06_change-design-document-template.md:17-239`）に「変更対象モジュール」は無い。§2（`:33`）の列は リポジトリ／ファイルパス／変更種別／対応SP番号。`grep '変更対象モジュール'` の結果は mod-agent `:50,53` と architect `:119`（無関係）だけ。mod-agent に CHD のパスは渡されない（`SKILL.md:234-246`）。ただし CR_PATH から探すことはできる | — |
| A4-38 | 一部確認 | 🔶 | 🔵 | 材料の取り方が書かれていない点は確認した（`11-specs/SKILL.md:284-303`。lint が必須とする: `artifact_lint.py:106-107`）。ただし Step CROSS は cross SPO を全部読み（`SKILL.md:274`）、その §4 には「提供リポジトリ」「消費リポジトリ」の列がある（`04_specout-cross-repo-template.md:71`・`04-specout/SKILL.md:671`）。既存のインタフェースの材料は読む範囲に入っている。材料が無いのは、SPO に無い新しいインタフェースだけ | 関連: A4-20 |
| A4-39 | 確認 | ✅（文面） | 🟡 | 書く側: `11-specs/SKILL.md:525`。読む側: `:47`（処理済みモジュールに限定する）。UR は未処理の一覧で継続する（`:48,527`）。マーカーがあるとコンテキスト圧迫チェックをしない（`:210`）ので、残りのモジュールを選び直す機会も無い。xddp-status も「処理済みモジュール」だけを表示する（`xddp-status/SKILL.md:60`） | — |
| A4-40 | 確認 | ✅ | 🔵 | progress テンプレートの見出しは `00_progress-management-template.md:1,11,31,46,53,61,67` で、番号付きの節は無い。補足: 「§15」は `SKILL.md:546`（更新ファイル一覧の記録）でも使われ、同じ番号が別の2つの節を指している | — |
| A4-41 | 確認 | 🔶 | 🔵 | `SKILL.md:84-86,97`（UR）と `:526-527`（URケバブ名）が揺れている。`uc-agent.md:17,25` は UR のリストとして扱う | — |
| A4-42 | 確認 | ✅ | 🟡 | `uc-agent.md:66-67`（複数の CR の UR が蓄積する）と `:89-91`（今回の CRS に同じケバブ名の UR が無ければ廃止候補）が衝突する。前の CR はクローズ済みなので、並行 CR 保護（`:92-97`）にも当たらない。GATE（`SKILL.md:454-457`）。`status: orphaned` を読む側は無い（`grep orphaned` の結果は `SKILL.md:512` だけ） | 関連: A4-4（モジュール側で同じ「毎回廃止候補」） |
| A4-43 | 確認 | ✅（両側の文面） | 🟡 | abort は latest-specs に触れない（`xddp-abort/SKILL.md:64-143`。revert は母体のリポジトリだけ: `:90`）。後の CR の close は AFFECTED_REPOS = REPOS_KEYS 全部（`xddp-common/SKILL.md:131-132`・`close/SKILL.md:21-23`）。C0-3 は DOCS にあるファイルだけを写し戻す（`close/SKILL.md:215`）。C2 は latest-specs/{repo} を全部写す（`promote.py:287-292`）。中止した CR の progress.md には「## CR 中止」しか無い（`abort:138`）ので、`mod-agent.md:129-133,176-178`・`uc-agent.md:92-97` で進行中とみなされ続ける | — |
| A4-44 | 確認 | 🔶 | 🟡 | Step 6 で latest-specs に書く（`survey/SKILL.md:318-332`）。Step 8 は承認を待つだけで、却下の分岐が無い（`:362`。「承認前は DOCS 側に一切書き込まない」）。後の CR の C0-3 と C2 は A4-43 と同じ経路 | 同じ経路: A4-43 |
| A4-45 | 確認 | ✅ | 🔵 | `survey/SKILL.md:338-339`（Step 7）と `:374-381`（Step 8②。承認の後）。V3 の新たな食い違い1（✅・🔵）と同じ内容・同じ結論 | V3 新1 |
| A4-46 | 確認 | ✅（V3 の再現） | 🔵 | `spec_version_delta.py:203-237`（spec.md 全体と SPO の §2 を比べる。`:228-234`）。spec テンプレートは §1〜§9 を持つ（`11_module-spec-template.md:23,33,…,114`）。V3 の新たな食い違い3（46.15% を再現・🔵）と同じ内容・同じ結論。補足: Mermaid のノード数・辺の数も spec.md 全体と比べている（`:228-233`） | V3 新3 |
| A4-47 | 一部確認 | ✅（文面）／🔶（条件） | 🟡 | 判定は latest-specs だけを見る（`survey/SKILL.md:295-304`）。写し先は DOCS（`:366-371`）。survey は DOCS を pull しない（`grep pull` は該当なし）。init も latest-specs に DOCS を取り込まない（`xddp-01-init/SKILL.md:81-91`）。条件は監査者の記述のとおり。「CR 検証済みの仕様を上書きする」のは、写す先に同じ名前のファイルがある場合 | — |
| A4-16（補足） | 確認 | 🔶 | 補足 🔵（指摘全体は 🟡 のまま） | `survey/SKILL.md:130-142` の規則は項番1「ディレクトリ一致で解決した場合」（Step 1 の catalog 不在時の Glob: `:79-85`）と項番2「ファイル名一致」だけ。catalog から解決したとき（`:78,98`）の規則は書かれていない。mod-agent `:156` も「catalog 不在時」の話だけ | — |
| A4-21（補足） | 確認 | ✅（再現） | 🔵 | `specout_bfs.py:1328` の正規表現。再現: `### src/auth/` と `### src/db/` の catalog を `_parse_module_catalog` に渡した結果、`dir_of` は `src` 1件（値 `src/db`）になり、all_dirs は `{'src/db'}`、auth の依存は消えた。`_compute_module_priority` の結果は `{'src/db': 'LOW'}`。ファイルのモジュールは `src`（`:1408-1411`）なので、マップに一致せず全部 HIGH。相対か絶対かが決まっていない点は `codemap/SKILL.md:54-55,104,131` で確認（Glob は `{REPO_PATH}/**/*`） | — |
| 担当外1件目の補足（印の付いた値をパスに使う） | 一部確認 | ✅（再現） | 🔵 | `promote.py:445-447` で印の付いた名前がセルになる。`domain_refs.py:328-331` はその値をパスに使い、`add_docs`（`:233-235`）はファイルが無ければ黙って飛ばす。再現: `resolve_matches(['job-completed ⚠️ 破壊的変更あり（CR: CR-1）','post-api-jobs'], ['job-completed'])` は印付きの値を返した（部分一致）。ただし `upsert_table` は印の無い既存の行を消さない（下の新たな食い違い1）。そのため以前の CR の行がある既存のインタフェースは、完全一致で印の無い行が先に選ばれ（`:61-63`）、仕様は見つかる。見つからなくなるのは、印の無い行が無い場合（初めて AI_INDEX に載る回に breaking である場合）だけ | 重複: A2 指摘#2（元の指摘） |

### 判定の補足
- **A4-38（一部確認）:** 「Step CROSS に書かれていない」は事実です。ただし Step CROSS が読む cross SPO の §4 に、提供リポジトリと消費リポジトリの列があります。そのため材料が無いのは、SPO に載っていない新しいインタフェースだけです。
- **A4-47（一部確認）:** 食い違いは確認しました。起きるのは、作業場所の latest-specs にそのモジュールが無く、DOCS には `source: spo` の版がある場合です。さらに上書きになるのは、写す先に同じ名前のファイルがある場合です。この状態がどのくらい起きるかは運用によります（確認していません）。
- **担当外の補足（一部確認）:** 印の付いた値がパスとして使われ、黙って飛ばされることは再現しました。ただし印の無い行が AI_INDEX に残り続けるので、既存のインタフェースは完全一致で見つかります。「仕様が見つからなくなる」のは、印の無い行が無い場合だけです。

## 2. 抜き取り確認の表

| 領域 | 約束（一覧の #） | 使った検索（パターンと範囲） | 漏れ | 漏れの書く側・読む側と食い違いの有無 |
|---|---|---|---|---|
| A4 | #14 cross CHD「インタフェース変更サマリ」の列 | `grep -rln 'breaking'`、`grep -rn 'CHD-{CR}-cross\|-cross\.md'` をファイルごとに数えた（CC 全体、tests を除く）。さらに promote の `detect_breaking_changes`（`promote.py:1025-1078`）を読んだ | あり（読む側） | `CC/agents/xddp-designer-agent.md:44,85,131`・`xddp-coder-agent.md:31`・`xddp-verifier-agent.md:87`・`xddp-test-writer-agent.md:103`・`xddp-07-code/SKILL.md:207`・`xddp-08-verify/SKILL.md:166`・`xddp-09-test/SKILL.md:159`。監査者は「工程7〜10 が cross CHD を読む約束（段階2b）」として確認していないことに明記しており、一覧の外にした理由は書かれている。値の形（breaking の true/false、変更種別の「新規追加」「変更」）の食い違いは見つからなかった。変更種別の値の語彙はどこにも決められていない（`06-design/SKILL.md:128-130` は例が1つだけ）。coder `:31` は「unchanged」を区別する |
| A4 | #16 latest-specs のフロントマターの必須キー | 監査者の `BASE_FRONTMATTER_KEYS` の grep は使わなかった。15個の `11_*-template.md` のフロントマターのキーを Python で取り出し、置かれるパスごとに `artifact_lint._required_keys_for_path` の結果と突き合わせた（`{V}` で実行） | 無し | 15個全部で必須キーがそろっていた |
| A4 | #24 `CURRENT_SPECS_REFS` | `grep '{DOCS}/{repo}/specs\|latest-specs/{repo}/{mod\|specs/{mod'`、`grep 'SPEC_FILE_PATHS\|CURRENT_SPECS\|SPECS_REFS'`（CC 全体） | 無し（書く側・読む側は一覧のとおり） | 隣の約束で食い違いを見つけた（下の新たな食い違い2） |

## 3. 新たに気付いた食い違い

1. **破壊的変更の印を付けた行が、AI_INDEX の「クロスインタフェース一覧」に重複して残る。**
   - 書く側: `promote.py:445-447`（印付きの名前をキー列に入れる）と `:580-582`（キー列は0列目）
   - 再現（`{V}`）: 印の無い行がある表に、印付きの行を upsert した。その後、次の CR の印の無い行を upsert した。結果、印付きの行（v2.0.0・CR-1）が古いまま残り、同じ spec を指す行が2つになった。
   - 今は元の担当外の指摘（A2 指摘#2）のために印が出ないので、印が出るようになってから起きる問題です。
   - ✅ 再現、🔵
2. **工程5・6 の Step 0 が「参照した資料を DSN・CHD の節に記録する」と書いているが、その節がテンプレートに無い。**
   - 書く側の指示: `xddp-05-arch/SKILL.md:124`（DSN "referenced past design documents" section）・`xddp-06-design/SKILL.md:64`（CHD "referenced past design documents and current specifications" section）
   - テンプレート: `05_design-approach-memo-template.md:16`・`06_change-design-document-template.md:24`・`06_change-design-document-index-template.md:17` には「参照資料」の行（CRS・SPO・DSN を並べるもの）しか無い。`grep 'referenced past'` の結果はこの2か所と `xddp-09-test/SKILL.md:42`（TSP）だけ。
   - 記録が「参照資料」の行に入るのか、どこにも入らないのかは LLM 次第です。
   - ✅（節が無いこと）／🔶（起きること）、🔵
   - A4 の領域外かもしれません（設計の成果物の約束）。

## 4. 実行したこと
- 読んだもの: 各指摘の両側の範囲を `awk`・`sed -n` で読みました。対象は 11-specs SKILL、mod・uc の両 agent、survey SKILL（60〜150・280〜400）、abort SKILL（全部）、close SKILL（15〜35・205〜250）、xddp-common の Resolve Affected Repos、`specout_bfs.py`（1300〜1415・1914〜1918・1975〜2000・2660〜2700）、`promote.py`（280〜330・434〜458・574〜590・1022〜1080）、`domain_refs.py`（46〜67・233〜236・300〜362）、`spec_version_delta.py`（200〜240）、各テンプレート、codemap SKILL（40〜160）。
- 再現（すべて `PYTHONDONTWRITEBYTECODE=1 python3 -B`。入力は `{V}` の中。`{W}` のスクリプトは `sys.path` から import しただけ）:
  - `_parse_module_catalog`・`_compute_module_priority`・`_module_dir_for_file`: A4-21 の補足
  - `domain_refs.resolve_matches`: 担当外の補足
  - `promote.upsert_table`: 新たな食い違い1
  - 15個のテンプレートのフロントマターと `_required_keys_for_path` の突き合わせ: 抜き取り #16
- `cd {W} && git status --short` は**空**でした。`{W}` 内の `__pycache__` も無いことを `find` で確かめました。
- 確認していないこと:
  - LLM の実際の解釈。A4-33・36・38・39・41・44、新たな食い違い2 が、これに依存します。
  - A4-46 の再現（V3 の結果をそのまま使いました）。
  - A4-35 の相対パスを実際にファイルを置いて解決すること（パスの構造を読んで確かめただけです）。
  - A4-47 の条件が、実際の運用でどのくらい起きるか。

## 5. やり直しの監査の質の所見
- **約束の一覧の網羅は、はっきり良くなっています。** 約束は #53〜#75 の23件が増え、時期の約束も abort・survey の承認前の書き込み・分割実行などを足しています。新しい指摘16件のうち、否定はありませんでした。とくに A4-39・A4-42・A4-43・A4-47 は、前回の範囲（パスの形）を越えて、状態と時期の約束まで洗い出せています。
- **書く側・読む側の洗い出しも良くなっています。** V3 が漏れとして挙げた #37 の読む側は全部取り込まれており、#6・#10・#24・#41 にも書く側・読む側が足されています。
- **残っている弱い点（気付いた点）:**
  - 書く側・読む側を数えたときに、「読む側が実際に読んでいる別の入力」を見落としたものがありました（A4-38 の cross SPO §4、担当外の補足の、印の無い行が残ること）。片方の文面だけで「材料が無い」「見つからない」と結論しています。
  - 範囲の外にした読む側が、一覧の行には書かれていません（#14 の工程6〜10。確認していないことにだけ書かれている）。一覧の行の中で「段階2b」と書けば、抜き取り確認と区別しやすくなります。
  - 隣の約束（SKILL がテンプレートの節の名前を指す約束。新たな食い違い2）は、まだ一覧にありません。SKILL の英語の地の文（"section" 等）で節を名指ししているところを検索すれば拾えます。
