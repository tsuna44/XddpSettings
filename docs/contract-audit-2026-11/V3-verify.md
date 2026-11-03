# 検証者 V3 の報告（原文。PLAN-20261103-contract-audit 段階2a）

> 検証者の最終報告をそのまま載せたもの。統合後の結果は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。`{W}` は監査用の worktree（ecb54c4）、`{V}` は検証者ごとのスクラッチのディレクトリ（どちらもセッションのスクラッチに作り、後で削除）。

# V3 検証報告（A4-1〜A4-31・A4 の担当外、A5-15〜A5-28・A5 の担当外）

`{W}` = `.../scratchpad/audit-ecb54c4`（ecb54c4）、`CC/` = `ClaudeCode/.claude/`。再現は `{V}` = `.../scratchpad/verify-V3` の中だけで行いました。

## 1. 指摘の検証の表

| 指摘 | 判定 | 確度 | 重大度の案 | 根拠 | 重複 |
|---|---|---|---|---|---|
| A4-1 | 確認 | ✅ | 🔴 | 書く側: `CC/skills/xddp-04-specout/module-documentation.md:268-270`（統合パスは `modules/` を作らない。分割パスは `modules/{名前}-spo.md` というファイル）・`:295`（サブディレクトリ分割のときだけディレクトリ）・`specout_bfs.py:7170,7211-7238`。読む側: `CC/agents/xddp-specs-mod-agent.md:49`（`modules/*/`）・`:160-161`（ディレクトリ名から導く）。補強: 同じ工程11 の `spec_version_delta.py:181-183` は `modules/{module}-spo.md` という**ファイル**を引く。つまり工程11 の中でも、エージェントとスクリプトで前提が違う | — |
| A4-2 | 確認 | ✅ | 🔴 | `module-documentation.md:242-259`（§2.A… の構成）・`:375`（「工程11 の最新仕様書にも入る」）。`grep -n '統合\|2\.A\|-spo'` を 11-specs SKILL・mod-agent・uc-agent に対して実行し、統合パスの読み方が無いことを確かめた（:183 と :461 は無関係な行。:228 は precheck の行） | — |
| A4-3 | 確認 | ✅ | 🟡 | `CC/skills/xddp-11-specs/SKILL.md:120`・`:129-132`・`11_overview-architecture-template.md:35`・`SKILL.md:591-598` | A4 の担当外 #2・A2 指摘#8 と関係あり（原因は別） |
| A4-4 | 確認 | ✅ | 🟡 | `xddp-specs-mod-agent.md:170-171`。廃止候補は GATE で人に示される（`SKILL.md:459-462`） | — |
| A4-5 | 確認 | ✅（再現） | 🔵 | `spec_version_delta.py:181-183,194-200`。再現: `{V}/p1` に latest-specs `auth-service/` と SPO `auth_service-spo.md` を置いて precheck を実行 → `"auth-service": {"skipped": "no_spo_file"}`。行番号の訂正: 名前に使える文字は `module-documentation.md:400`（:398 ではない） | — |
| A4-6 | 確認 | ✅（再現） | 🟡 | `04_specout-module-template.md:106`（`### 4.2 データ型関連図`）、`spec_version_delta.py:37`（`クラス図`）、`xddp-specs-mod-agent.md:90`。再現: SPO に `### 4.2 データ型関連図`（辺の数を変えた classDiagram）を置いて precheck → `core/structure.md: skipped no_matching_spo_section` | — |
| A4-7 | 確認 | ✅ | 🔵 | `xddp-specs-mod-agent.md:152` に対して、`spec_version_delta.py:348-397`（ベースラインの全 `.md` を区別なく比べる）。ベースラインは repo の latest-specs 全体（`xddp-11-specs/SKILL.md:219-223`） | — |
| A4-8 | 確認 | ✅ | 🔴 | `xddp-11-specs/SKILL.md:512-514`（GATE でオーケストレーターが削除）・`:550-573`（一覧に載るのは生成・更新したファイルだけ）。読む側: `xddp-close/SKILL.md:211-216`（保護されていないファイルを DOCS から latest-specs へ写す）→ `promote.py:297-301,317-322`（latest-specs に無いディレクトリだけを削除候補にする）。前の CR で DOCS に昇格済みのモジュールに限って起きる | — |
| A4-9 | 判断できず | 🔶 | 🟡 | `xddp-11-specs/SKILL.md:550-551`（「全ファイルパスを列挙する」）と `:573`（Overwrite）。CR 全体で累積するとは書かれていない。下の補足を参照 | — |
| A4-10 | 確認 | ✅ | 🟡 | `xddp-11-specs/SKILL.md:447`・`:494-498`。C0-3 は一覧に無いファイルを写す（`xddp-close/SKILL.md:213-215`）。DOCS に前の版がある場合に限る | — |
| A4-11 | 確認 | ✅ | 🟡 | `xddp-survey/SKILL.md:366-372`（① はモジュールのディレクトリだけを写す）・`:374-381`（② は latest-specs だけに追記）→ 後の CR の C0-3（`xddp-close/SKILL.md:215`）。後の CR の AFFECTED_REPOS にその repo があり、その CR が architecture.md を更新しない場合に限る | A4-30 と同じ原因 |
| A4-12 | 確認 | ✅ | 🟡 | `domain_refs.py:354-359`（`cross/specs` 直下の名前、つまり `interfaces`・`sequences` に `/spec.md` を付けて探す）。AI_INDEX がある場合は `:331`（`interfaces/{name}/spec.md`）で正しい | — |
| A4-13 | 確認 | ✅ | 🟡 | `xddp-01-init/SKILL.md:117-130`（`{DOCS}/{repo}/specs/README.md` を作る）、`domain_refs.py:228,383-385`、`xddp-11-specs/SKILL.md:665-667`。system のフォールバック（b、`:398-399`）は init が `system/specs` を作らないので働く。働かないのは a だけ | 重複: A2 指摘#3 |
| A4-14 | 確認 | 🔶 | 🟡 | `xddp-05-arch/SKILL.md:117-121`・`xddp-06-design/SKILL.md:57-61`（SPO のモジュール名でパスを作る。ケバブ化の指示は無い）に対して、`xddp-specs-mod-agent.md:159-163` | — |
| A4-15 | 確認 | 🔶 | 🟡 | `xddp-specs-uc-agent.md:56-58` → `promote.py:387-394` → `domain_refs.py:257-264,288-290` | — |
| A4-16 | 一部確認 | 🔶 | 🟡 | 二つの規則が違うことは事実（`xddp-survey/SKILL.md:130-142` と `module-documentation.md:385-400`・`xddp-specs-mod-agent.md:159-161`）。ただし二重にできるのは、人が survey に渡す名前が CR のモジュール名と食い違うときだけ | — |
| A4-17 | 確認 | ✅ | 🟡 | `xddp-11-specs/SKILL.md:349-356`、`xddp-review/SKILL.md:81-88`（どちらも CRS＋CHD だけを渡す）。読む側: `reviewer-checklists/SPEC.md:21-23,32,42` | — |
| A4-18 | 確認 | ✅ | 🔵 | `xddp-11-specs/SKILL.md:186`。`grep -rn ai-inferred CC` の結果は 11-specs のテンプレートと uc-agent だけで、SPO 側には無い（`04_specout-summary-template.md:93-114`） | — |
| A4-19 | 確認 | ✅ | 🔵 | `xddp-specs-uc-agent.md:29,76`・`xddp-11-specs/SKILL.md:374`。`Section 3-` の定義はどこにも無い | — |
| A4-20 | 確認 | 🔶 | 🔵 | `xddp-06-design/SKILL.md:126-129`（列は インタフェース／変更種別／breaking だけ）に対して、`xddp-common/SKILL.md:138-141`・`SPEC.md:31` | — |
| A4-21 | 確認 | ✅ | 🔵 | 書く側: `specout_bfs.py:1331-1333`（ディレクトリは `src/auth` のような値）。読む側: `:1397-1410`（第1要素だけ）・`:2671`・`:2689-2696`（catalog モードでは `_module_dir_for_file`）・`:1990-1994`（引けなければ HIGH） | — |
| A4-22 | 一部確認 | ✅ | 🔵 | `xddp-11-specs/SKILL.md:123` は「全体アーキテクチャ図」セクション（`## 2.` または「モジュール依存・コンポーネント構成」）と書いており、正しい名前も含む。食い違いは `11_overview-architecture-template.md:33` の別名だけ。`## 2.` の接頭辞が `## 2.A.` にも当たる点は 🔶 | — |
| A4-23 | 確認 | ✅（再現） | 🔵 | `spec_version_delta.py:97-101,131`。再現: `sequences/ログイン処理-seq.md` と SPO の `#### ログイン処理` で precheck → `skipped no_matching_spo_section` | — |
| A4-24 | 確認 | ✅ | 🔵 | `xddp-11-specs/SKILL.md:372`（自動修正は4キーだけ）に対して、`artifact_lint.py:58,101-123` | — |
| A4-25 | 確認 | ✅ | 🔵 | `11_module-spec-template.md:30`。`rewrite_version` は frontmatter と変更履歴だけを書き換える（`spec_version_delta.py:264,341-345`）。`| バージョン |` の行は 11 系のテンプレート 15 個にある | — |
| A4-26 | 確認 | ✅ | 🔵 | `xddp-01-init/templates/xddp.config.md:346` | — |
| A4-27 | 確認 | ✅ | 🔵 | `CC/agents/xddp-specout-prelim-agent.md:30` に対して、`xddp-04-specout/SKILL.md:255`。実際に渡す値は正しい | — |
| A4-28 | 確認 | ✅ | 🔵 | `xddp-abort/SKILL.md:42-43` | — |
| A4-29 | 確認 | ✅ | 🔵 | `xddp-sync-design/SKILL.md:137`。mod-agent は REPO_PATH を受け取るが、コードを読む手順は無い | — |
| A4-30 | 確認 | ✅ | 🔵 | `xddp-rules/code-knowledge-boundary.md:32` に対して、`xddp-survey/SKILL.md:374-375` | 関係あり: A4-11 |
| A4-31 | 確認 | ✅（再現） | 🔵 | テンプレートそのままの glossary を `promote._glossary_term_count` に渡すと **1** を返した。見本の行を置き換える指示は無い（`xddp-update-knowledge/SKILL.md:224-227`） | — |
| A4 担当外 #1（breaking の印） | 確認 | ✅ | 🟡 | `promote.py:446`（ディレクトリ名）と `:1070-1076`（CHD の生の名前）を正規化せずに比べている。close の報告（`:1138`）には生の名前が出る | 重複: A2 指摘#2 |
| A4 担当外 #2（先行更新の行の集合） | 確認 | ✅ | 🔵 | `xddp-11-specs/SKILL.md:591-598` に対して、`promote.py:420-432`（latest-specs のディレクトリを全部列挙する） | 重複: A2 指摘#7（名前の件は A2 指摘#8） |
| A5-15 | 確認 | 🔶 | 🔵 | `CC/agents/xddp-close-knowledge-agent.md:50-51` に対して、`project-rulebook-repo-template.md:120,130,139` | — |
| A5-16 | 確認 | ✅ | 🔵 | `knowledge-agent.md:63-64`。置き換えるプレースホルダーは repo テンプレートの `:1,17,161,187`、cross テンプレートの `:155,177` | A3-20 と同じ型（別の対象） |
| A5-17 | 確認 | ✅ | 🔵 | `lessons-learned-template.md:17`（`#レビュー`）が `knowledge-agent.md:33-38` に無い | — |
| A5-18 | 確認 | 🔶 | 🟡 | `xddp-02-analysis/SKILL.md:287` に対して、`knowledge-agent.md:29,62-65`（読むのは `CR_LESSONS_FILE` だけ） | — |
| A5-19 | 確認 | ✅ | 🔵 | 行番号の訂正: `02-analysis:333,338`（:333-334 ではない）。共通テンプレートの §2 にはコードブロックが3つ（`:63-68,73-79,84-89`）、§4 にも3つ（`:119-128,133-137,140-146`） | — |
| A5-20 | 確認 | ✅ | 🔵 | 行番号の訂正: `02-analysis:314`（:312 ではない）。共通テンプレートは `:157-161`（`# ❌`） | — |
| A5-21 | 確認 | ✅（全部の出現を置き換えるかは 🔶） | 🔵 | `xddp-01-init/SKILL.md:238` と `project-rulebook-cross-template.md:155` | — |
| A5-22 | 確認 | ✅（同上） | 🔵 | `init:223,231`、共通テンプレート `:104`、repo テンプレート `:161` | — |
| A5-23 | 確認 | 🔶 | 🔵 | `load-domain-constraints.md:19-20`（「プレースホルダー `{...}` のみ」）に対して、テンプレート `:48-53`（種別の列に文言が入っている）。文言どおりに読むと空と判定しない | — |
| A5-24 | 確認 | ✅ | 🔵 | `promote.py:999-1006`。HAS_CROSS は「IS_MULTI かつ CR に cross の成果物がある」（`xddp-close/SKILL.md:24`）。補足: AI_INDEX の cross の行（`promote.py:534`）も同じ条件 | 同じ型: A3-8（Layer 2 の LL。別の対象） |
| A5-25 | 確認 | ✅ | 🔵 | `xddp-close/SKILL.md:348,352`（条件なしで「昇格」と書く）に対して、`promote.py:992-1006`（ファイルがあるときだけ写す） | — |
| A5-26 | 一部確認 | ✅ | 🔵 | パスの形 `cross/interfaces/{name}-spec.md` が間違っている点は確認（実際は `{interface-kebab}/spec.md`。`xddp-11-specs/SKILL.md:298`）。ただし「移行ガイド」の節は**存在する**: `11_cross-interface-spec-template.md:115` `## 6. 移行ガイド（MAJOR バージョンアップ時のみ記載）`。監査者の「grep で他に見つからない」は誤り | — |
| A5-27 | 確認 | ✅ | 🔵 | 行番号の訂正: `README.md:357`。共通テンプレート `:26-36` は表（名前・役割・主要技術）だけ | — |
| A5-28 | 確認 | 🔶 | 🟡 | `promote.py:988,996,1004`（copy2 で上書き）。C0-3・C0-4 が扱うのは latest-specs だけ（`xddp-close/SKILL.md:211-276`）。複数の作業場所が1つの DOCS を共有する運用のときに限る | 同じ型: A3-4（backlog） |
| A5 担当外（共通知識） | 確認 | ✅（再現） | 🔵（監査者 🔵〜🟡） | `upsert_table`（`promote.py:199-202`）に init の骨組み（`xddp-01-init/SKILL.md:173-177`）を渡すと、共通の rulebook の行が消え、repo の行だけになった。条件: 行が upsert されるのは repo 別・cross の rulebook があるとき（マルチ構成。またはシングル構成で A5-2 のファイルができた後）。`## 共通知識` を読むスクリプトは無い（grep で確認）ので、影響は索引のリンクだけ。🔵 とした | 重複: A2 指摘#6 |

### 判定の補足
- **A4-9（判断できず）:** 「全ファイルパスを列挙する」（`xddp-11-specs/SKILL.md:550-551`）と「既存の節を上書きする」（`:573`）を合わせても、分割実行の後の回で前の回のファイルを含めるかが決まっていません。決めるには、エージェントが分割実行の最後の回に前の回のファイルも一覧へ書くかを、実際の実行で確かめる必要があります。または一覧を累積する指示があるかで決まりますが、今はその指示がありません。前の回のファイルを書かなければ、A4-10 と同じ仕組みで上書きされます。
- **A4-16（一部確認）:** 規則の違いは事実です。ただし二重にできるのは、survey に渡す名前（例 `src/auth`）と CR のモジュール名（例 `auth`）が食い違うときだけです。モジュール一覧があるときに survey がどちらの規則を使うかは確認していません。
- **A4-22（一部確認）:** SKILL の本文は正しい名前（全体アーキテクチャ図）を先に挙げています。食い違うのはテンプレートの別名だけです。
- **A5-26（一部確認）:** 監査者の根拠の一部（節が無い）は誤りです。パスの書式の誤りだけが残ります。

## 2. 抜き取り確認の表

| 領域 | 約束（一覧の #） | 使った検索（パターンと範囲） | 漏れ | 漏れの書く側・読む側と食い違いの有無 |
|---|---|---|---|---|
| A4 | #37 module-catalog のパス | `grep -rn 'CATALOG_FILE\s*[=:]\|catalog\.md\|--module-catalog'` と `grep -rln 'MODULE_CATALOG\|module_catalog'`（CC/skills・CC/agents、tests を除く） | あり（読む側の一覧に無い箇所） | `xddp-04-specout/SKILL.md:257`（prelim へ渡す）・`CC/agents/xddp-specout-prelim-agent.md:32`・`xddp-survey/SKILL.md:213`・`CC/agents/xddp-survey-agent.md:59`。どれもパスは `{DOCS}/{repo}/module-catalog.md` で一致。食い違いは無し |
| A4 | #41 glossary のパス | `grep -rn 'glossary\.md\|GLOSSARY\|用語集'`（同じ範囲）＋ `KNOW_DIR` の定義（`xddp-update-knowledge/SKILL.md:35`） | 無し（一覧の書く側・読む側でそろっている。`KNOW_DIR` が `{DOCS}/{repo}/knowledge` であることも確認） | — |
| A5 | #31 RULEBOOK_CONTEXT の読み込み方 | `grep -rn 'Steering Context'`、`grep -rln 'RULEBOOK'`、`INCLUDE_CROSS`（同じ範囲） | あり（軽い） | `xddp-07-code/SKILL.md:111`（repo ごとに読むという説明の文）・`xddp-templates/xddp.skill-template.md:35,44`（開発用のひな形）。10-test-run の値は verifier へ（`:236`）、feedback の値は chd-sync へ（`:238`）渡り、どちらも Inputs に持つ。食い違いは無し |
| A5 | #3 cross ファイルのパス | `grep -rn 'rulebook-cross\|cross/project-rulebook\|rulebook_cross\|cross_rb'`、`CROSS_RULEBOOK_CONTEXT`（同じ範囲） | あり | `xddp-fill-rulebook/SKILL.md:12,52,62`・`xddp-01-init/SKILL.md:268`（案内）・`promote.py:534`（AI_INDEX の cross の行。`has_cross` が条件で、A5-24 と同じ型）。パスはそろっている。新しい食い違いは無し（`:534` の条件は A5-24 に含めてよい） |
| A5 | #34 verifier が使う禁止事項の節番号 | `grep -rn '禁止事項\|Section 5\|Section 6\|§5\|§6'`（verifier・test-writer・coder・designer・architect・chd-sync・design-sync の各 agent） | 無し | — |

## 3. 新たに気付いた食い違い

1. **survey の Step 7 が、まだ書かれていない architecture.md をレビュー対象に入れる（時期の食い違い）。** `CC/skills/xddp-survey/SKILL.md:339`（Step 7。「Step 8② で architecture.md を新規作成・追記した場合はそれも TARGET_FILES に含める」）。ところが Step 8② は、Step 7 と人の承認の後に実行されます（`:357-375`）。そのため architecture.md への追記はレビューされません。✅ 読んで確認、🔵。
2. **設定テンプレートの `SPECOUT_DIAGRAM_LEVEL` の説明が、モジュール資料の節番号・範囲と合わない。** `xddp-01-init/templates/xddp.config.md:341-343` は「minimal: 6.1 のみ／standard: 6.1〜6.4, 6.7, 6.8／full: 6.1〜6.9」と書いています。一方 `module-documentation.md` の「Section 4（モジュール内ダイアグラム）の生成範囲」は「minimal: 必須図以外は対象外／standard: 4.1〜4.3／full: ＋4.4・4.6・4.7」です。✅、🔵。
3. **precheck は、latest-specs の spec.md の全体と SPO の §2 だけを比べる。** `spec_version_delta.py:203-214,236-237`。本文の行数の変化率が、テンプレートの他の節（概要・関連ドキュメント・変更履歴）の分だけ大きく出ます。再現: `{V}/p2` に、11 の spec テンプレートと 04 のモジュールテンプレートを置いて実行すると 46.15% になり、`force_update_files` に入りました（最初の再現でも、同じ内容で 71%）。実際の CR で毎回「更新あり」になり、版が上がるかは 🔶 です。失われるものはありません。🔵。

## 4. 実行したこと
- 読んだもの: A4・A5 の指摘ごとに書く側・読む側の該当範囲（`sed -n`）。他の報告 A1〜A3 は、重複の確認のために grep だけしました。
- 再現（すべて `PYTHONDONTWRITEBYTECODE=1 python3 -B`。入力は `{V}` の中）:
  - `spec_version_delta.py precheck`（`{V}/p1`）: A4-5（`no_spo_file`）・A4-6（structure の `no_matching_spo_section`）・A4-23（日本語のシーケンス図）を再現しました。
  - `{V}/p2`: 新たな食い違い3を再現しました。
  - `promote._glossary_term_count`（テンプレートのコピー `{V}/g.md`）が 1 を返しました（A4-31）。
  - `promote.upsert_table` に init の「共通知識」の骨組みを渡し、共通の rulebook の行が消えることを再現しました（A5 の担当外）。
- `cd {W} && git status --short` → **空**。`{W}` に新しい `__pycache__` も無いことを `find` で確かめました。
- 確認していないこと:
  - LLM（mod-agent・knowledge-agent・fill-rulebook・init）が実際にどう解釈するか（A4-9・A4-14〜16・A4-20・A5-15・A5-18・A5-21〜23）。
  - survey でモジュール一覧があるときの `MODULE_KEBAB` の実際の値。
  - `domain_refs.py` を CLI から通しで動かす再現（A4-12・A4-13 は読んで確認しただけ）。
  - A1〜A3 の指摘そのものの正しさ（重複の照合だけ行いました）。
