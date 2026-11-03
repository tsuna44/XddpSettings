# 監査者 A4 の報告（原文。PLAN-20261103-contract-audit 段階2a）

> 監査者の最終報告をそのまま載せたもの（検証前）。検証結果と統合後の重大度は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。パスの `{W}` は監査用の worktree（ecb54c4。セッションのスクラッチのディレクトリに作り、監査の後に削除）。

# A4 仕様・用語・カタログ — 約束の監査の結果

対象は `{W}` = `/private/tmp/claude-501/-Users-tsuna-Documents-src-git-work-XddpSettings/c3213ce8-a1bc-4469-9c03-6422385baffd/scratchpad/audit-ecb54c4`（ecb54c4）。`CC/` は `ClaudeCode/.claude/` の略です。ファイルは書き換えておらず、スクリプトも実行していません。

**要点:** 重い食い違いは2つあります。
- **工程11 がスペックアウトのモジュール資料を見つけられない（A4-1〜A4-5）。** 工程11 は `04_specout/{repo}/modules/` の**ディレクトリ**を前提にしています。一方スペックアウトは、統合パスでは SPO 本体の §2.A… に、分割パスでは `modules/{名前}-spo.md` という**ファイル**に資料を書きます。このため、統合パスの CR（波及10ファイル以下で普通に起きる）ではモジュール仕様が作られません。
- **工程11 で人が削除した最新仕様が元に戻る（A4-8）。** 工程11 の Step GATE で人が削除を選んだモジュール・ユースケースを、close の Step C0-3 が DOCS から latest-specs に書き戻します。廃止したはずの仕様が DOCS にも残ります。

---

## 1. 確認した約束の一覧

| # | 約束 | 書く側（ファイル:行・節） | 読む側（ファイル:行・節） | 見つけた方法 | 結果 |
|---|---|---|---|---|---|
| 1 | モジュール資料の置き場所（ディレクトリかファイルか） | `CC/skills/xddp-04-specout/module-documentation.md:261-273`（配置判定）・`:220`・`specout_bfs.py:7170` | `CC/agents/xddp-specs-mod-agent.md:49`（`modules/*/`）・`:161` | 書く側: `grep -rn -- '-spo\.md' CC/skills CC/agents`。読む側: 依頼文の一覧（`latest-specs`） | あり A4-1 |
| 2 | 統合パスの資料（SPO-{CR}.md の §2.A…）を工程11 が読むか | `module-documentation.md:242-255`（統合パスの §2.A… の構成） | `xddp-specs-mod-agent.md:49-59`・`CC/skills/xddp-11-specs/SKILL.md:216-246`（統合パスの記述なし） | `grep -n '統合\|2\.A' xddp-11-specs/SKILL.md xddp-specs-mod-agent.md`（該当なし） | あり A4-2 |
| 3 | `SPECOUT_MODULES` の取り方 | 同上（`modules/` の下はファイル） | `xddp-11-specs/SKILL.md:120`（ディレクトリ名）・`:129-132`・`11_overview-architecture-template.md:35` | `grep -rn SPECOUT_MODULES CC` | あり A4-3 |
| 4 | 廃止モジュールの判定の照合先 | 同上 | `xddp-specs-mod-agent.md:171` | #1 と同じ | あり A4-4 |
| 5 | precheck が SPO ファイルを引く名前 | `module-documentation.md:403`（`modules/{モジュール名}-spo.md`。名前には英数字・`-`・`_` が使える `:398`） | `spec_version_delta.py:181-183`（latest-specs のケバブ名＋`-spo.md`）・`:193-200` | `xddp-11-specs/SKILL.md:228` から参照をたどった | あり A4-5 |
| 6 | spec.md の材料（`## 2. 現状仕様`・`## 3. 既存仕様の文書化…`） | `04_specout-module-template.md:23,75` | `xddp-specs-mod-agent.md:66-67`・`spec_version_delta.py:36` | `grep -n '^#' 04_specout-module-template.md` | なし |
| 7 | structure.md の材料の見出し（クラス図） | `04_specout-module-template.md:106`（`### 4.2 データ型関連図`） | `xddp-specs-mod-agent.md:90`・`spec_version_delta.py:37`（`クラス図`） | 同上 | あり A4-6 |
| 8 | structure.md の材料（データ構造・PAD） | `04_specout-module-template.md:123,131` | `xddp-specs-mod-agent.md:90`・`spec_version_delta.py:37` | 同上 | なし |
| 9 | state-machine.md と sequences の材料の見出し | `04_specout-module-template.md:93,145` | `xddp-specs-mod-agent.md:98,106`・`spec_version_delta.py:38,40` | 同上 | なし |
| 10 | 並び順・依頼調査の節（§2.7・`## 波紋調査の結果`）の位置 | `module-documentation.md:375`・`specout_bfs.py:7348`（`## 5.` の直前） | `xddp-specs-mod-agent.md:66`（§2 を取る） | `grep -n '波紋調査の結果' specout_bfs.py` | なし |
| 11 | SPO サマリーの節名（§2・§3・§4.2〜§4.4） | `04_specout-summary-template.md:32,47,79,93,118` | `xddp-11-specs/SKILL.md:123,154,171,176,189`・`xddp-specs-uc-agent.md:32` | `grep -n '^#' 04_specout-summary-template.md` | なし（名前の表記は A4-22） |
| 12 | §4.3 の `source` 注記 | 書く側なし（`grep -rn ai-inferred` で SPO 側に該当なし） | `xddp-11-specs/SKILL.md:186` | `grep -rn 'ai-inferred' CC` | あり A4-18 |
| 13 | cross SPO §3（シーケンス図） | `04_specout-cross-repo-template.md:35` | `xddp-11-specs/SKILL.md:277,307`・`xddp-specs-uc-agent.md:33` | `grep -n '^#' 04_specout-cross-repo-template.md` | なし |
| 14 | cross CHD「インタフェース変更サマリ」の列 | `CC/skills/xddp-06-design/SKILL.md:126-129`（インタフェース・変更種別・breaking） | `xddp-11-specs/SKILL.md:284-303`・`promote.py:1022-1078`（`breaking` 列） | `grep -rn 'インタフェース変更サマリ' CC` | なし |
| 15 | 同上の「影響リポジトリ」 | `xddp-06-design/SKILL.md:126-129`（その列が無い） | `CC/skills/xddp-common/SKILL.md:138-141`・`reviewer-checklists/SPEC.md:31` | 同上 | あり A4-20 |
| 16 | latest-specs のフロントマターの必須キー | `11_*-template.md` の各1〜9行 | `artifact_lint.py:58,106-129` | `xddp-11-specs/SKILL.md:371` から参照をたどった | なし |
| 17 | 同上（工程11 の自動修正の対象キー） | 同上 | `xddp-11-specs/SKILL.md:372` | 同上 | あり A4-24 |
| 18 | 変更履歴の表の形（1列目がバージョン・最後の行が最新） | `11_module-*-template.md` の「変更履歴」節 | `spec_version_delta.py:315-338` | `awk` で各テンプレートの変更履歴を表示 | なし |
| 19 | 版数の表示（フロントマターと §1 の「バージョン」行） | `11_module-spec-template.md:2,30` | `spec_version_delta.py:341-345`（§1 を書き換えない） | 同上 | あり A4-25 |
| 20 | compare の対象（SPO が無く CHD だけがあるモジュールを除くか） | `xddp-specs-mod-agent.md:152` | `spec_version_delta.py:348-397` | エージェントから参照をたどった | あり A4-7 |
| 21 | `FORCE_UPDATE_FILES` の形（`{module}/{file}`） | `spec_version_delta.py:223,244` | `xddp-specs-mod-agent.md:24-26,138` | `xddp-11-specs/SKILL.md:229-231` | なし |
| 22 | シーケンス図のファイル名のケバブ変換（日本語の見出し） | `xddp-specs-mod-agent.md:106-108`・`xddp-11-specs/SKILL.md:154-155` | `spec_version_delta.py:97-101,131` | スクリプトを読んだ | あり A4-23 |
| 23 | latest-specs のモジュールディレクトリ名（`{module-kebab}`）と、読む側が使う `{mod}` | `xddp-specs-mod-agent.md:159-163` | `CC/skills/xddp-05-arch/SKILL.md:117-121`・`xddp-06-design/SKILL.md:57-61` | `grep -rn 'latest-specs' CC/skills/xddp-05-arch …` | あり A4-14 |
| 24 | `related-modules` の値の語彙 | `xddp-specs-uc-agent.md:56-58` | `promote.py:387-394` を経て `domain_refs.py:257-262,290` | `grep -n related` | あり A4-15 |
| 25 | survey の `MODULE_KEBAB` と CR のモジュール名 | `CC/skills/xddp-survey/SKILL.md:130-142` | `xddp-survey/SKILL.md:295-304`（衝突の判定）・`xddp-specs-mod-agent.md:159-161` | `grep -n MODULE_KEBAB xddp-survey/SKILL.md` | あり A4-16 |
| 26 | survey から mod-agent への入力（`SURVEY_MODE`・`SURVEY_FILE`・`OUTPUT_FILE`・`CR_PATH` は空） | `xddp-survey/SKILL.md:318-332` | `xddp-specs-mod-agent.md:19-39` | survey から参照をたどった | なし |
| 27 | SURVEY 成果物の形（モジュールテンプレートを使う） | `CC/agents/xddp-survey-agent.md:36-53` | `xddp-specs-mod-agent.md:68,92,100,107` | 同上 | なし（見出しの問題は A4-6 と同じ） |
| 28 | `source: survey` のモジュールを廃止判定から外す | `xddp-specs-mod-agent.md:83-87` | `xddp-specs-mod-agent.md:124-128,173-175`・`xddp-survey/SKILL.md:296-304` | エージェントを読んだ | なし |
| 29 | 昇格の写し先（latest-specs/{repo} → DOCS/{repo}/specs、cross → cross/specs、system → system/specs） | `promote.py:284-316` | `xddp-close/SKILL.md:246-248`（C0-4 の対応）・`promote.py:393,411-413,428-452`（AI_INDEX のリンク） | `grep -n 'specs/' promote.py` | なし |
| 30 | close C0-3 の取り込みと「工程11 更新仕様書ファイル一覧」 | `xddp-11-specs/SKILL.md:546-573`・`00_progress-management-template.md:46-49` | `xddp-close/SKILL.md:211-231` | `grep -rln 'C0-3' CC` | なし（パスの形は一致）。時期の問題は A4-8〜A4-11 |
| 31 | 削除の伝わり方（モジュール・ユースケース） | `xddp-11-specs/SKILL.md:510-512`（GATE で削除） | `xddp-close/SKILL.md:215-218`（C0-3）・`promote.py:297-323` | close を読んだ | あり A4-8 |
| 32 | DOCS の cross の仕様のパス（`cross/specs/interfaces/{if}/spec.md`） | `promote.py:306`・`xddp-11-specs/SKILL.md:298` | `domain_refs.py:331`（AI_INDEX あり）／`:354-359`（AI_INDEX なし） | `grep -n 'specs' domain_refs.py` | あり A4-12 |
| 33 | `{DOCS}/{repo}/specs/` の有無が「昇格済み」を意味するか | `CC/skills/xddp-01-init/SKILL.md:117-131`（init で必ず作る） | `domain_refs.py:228,383-385`・`xddp-11-specs/SKILL.md:665-667` | `grep -rn '{repo}/specs' CC` | あり A4-13 |
| 34 | system のユースケース（`system/specs/use-cases/{uc}/description.md`）とフォールバック | `promote.py:311-316` | `domain_refs.py:269,337-341,399-411` | 同上 | なし |
| 35 | 工程4a・5・6 に渡す仕様の入力（BASELINE・CROSS・LATEST_SPECS_DIR） | `xddp-04-specout/SKILL.md:253-255,303-304`・`specout-finish.md:77-81,150-152` | `CC/agents/xddp-specout-prelim-agent.md:28-30`・`CC/agents/xddp-specout-agent.md:28-32` | `grep -rn 'SPECS_DIR' CC` | なし（記述の揺れは A4-27） |
| 36 | `CURRENT_SPECS_REFS`（latest-specs を優先し、無ければ DOCS） | `xddp-05-arch/SKILL.md:120-123`・`xddp-06-design/SKILL.md:60-63` | `CC/agents/xddp-architect-agent.md:46`・`CC/agents/xddp-designer-agent.md:51` | `grep -rn 'latest-specs' CC/agents` | なし |
| 37 | module-catalog のパス | `CC/skills/xddp-codemap/SKILL.md:134` | `xddp-04-specout/SKILL.md:229`・`ripple-run.md:50-52`・`specout-finish.md:81`・`xddp-survey/SKILL.md:66` | `grep -rn module-catalog CC` | なし |
| 38 | module-catalog の節名（「## 2. モジュール一覧」「## 3. シンボル索引」） | `module-catalog-template.md:22,33` | `specout_bfs.py:1321,1351`・`xddp-survey/SKILL.md:78,147` | 同上 | なし |
| 39 | module-catalog の `**ディレクトリ：**` の値の形と、specout が照合に使う形 | `xddp-codemap/SKILL.md:51-66`・`module-catalog-template.md:26,39` | `specout_bfs.py:1331-1333,1393-1408,1982-1996,2668-2679` | specout_bfs を読んだ | あり A4-21 |
| 40 | module-catalog の見出し `### {name}/ — …`・依存先と被依存元 | `module-catalog-template.md:24,28-29` | `specout_bfs.py:1329,1335-1346` | 同上 | なし（「（なし）」の書き方は 🔶。指摘にはしない） |
| 41 | glossary のパス（共通・repo・cross） | `CC/skills/xddp-update-knowledge/SKILL.md:220-223` | `domain_refs.py:375-379`・`xddp-02-analysis/SKILL.md:121-123`・`xddp-03-req/SKILL.md:57-59`・`promote.py:507-523` | `grep -rn glossary CC` | なし |
| 42 | glossary の列（正式表記・別名・揺れ・使用禁止） | `glossary-template.md:16` | `CC/agents/xddp-spec-writer-agent.md:31-34`・`CC/agents/xddp-analyst-agent.md:86-92` | 同上 | なし |
| 43 | glossary の `## 用語一覧` の表（用語数を数える） | `glossary-template.md:9-18`・`xddp-update-knowledge/SKILL.md:224-228` | `promote.py:460-473` | 同上 | あり A4-31（🔶） |
| 44 | SPEC レビューに渡す参照ファイル（SPO・SURVEY） | `xddp-11-specs/SKILL.md:347-356`・`CC/skills/xddp-review/SKILL.md:84-88`・`xddp-survey/SKILL.md:345` | `reviewer-checklists/SPEC.md:21-25,32` | `grep -rn SPECOUT_MODULES CC` | あり A4-17（survey は一致） |
| 45 | uc-agent・SKILL が参照する「Section 3-0」「Section 3-4」 | 書く側なし | `xddp-specs-uc-agent.md:29,76`・`xddp-11-specs/SKILL.md:374` | `grep -rn 'Section 3-'` | あり A4-19 |
| 46 | survey の (c) で architecture.md に追記した内容が DOCS に届くか | `xddp-survey/SKILL.md:366-381` | `xddp-close/SKILL.md:215`・`code-knowledge-boundary.md:32` | survey を読んだ | あり A4-11・A4-30 |
| 47 | latest-specs/README.md と予約名 | `xddp-01-init/SKILL.md:81-91` | `xddp-common/SKILL.md:48,71` | `grep -rn latest-specs` | なし |
| 48 | 工程11 の `ARTIFACT_LINK`（`../latest-specs/`） | `xddp-11-specs/SKILL.md:543` | progress.md の位置（`{XDDP_DIR}/{CR}/`） | SKILL を読んだ | なし |
| 49 | 設定テンプレートの latest-specs のパス | `xddp-01-init/templates/xddp.config.md:345-347` | 実際のパス（`xddp-11-specs/SKILL.md:176,188`） | `grep -rn latest-specs` | あり A4-26 |
| 50 | abort・sync-design の latest-specs の説明 | `xddp-abort/SKILL.md:43`・`xddp-sync-design/SKILL.md:137` | 実際の動作（close・工程11） | 同上 | あり A4-28・A4-29 |
| 51 | architecture.md の材料にする SPO の節の名前 | `04_specout-summary-template.md:32` | `xddp-11-specs/SKILL.md:123`・`11_overview-architecture-template.md:33` | テンプレートを読んだ | あり A4-22 |

## 2. 時期の約束の表

| 書く側（スキル・Step） | 読む側（スキル・Step） | 順序の根拠（ファイル:行） | 結果 |
|---|---|---|---|
| 工程4a specout（SPO・modules） | 工程11 Step OV・MOD・UC | 工程11 は SPO がある repo だけを扱う（`xddp-common/SKILL.md:136-138`・`xddp-11-specs/SKILL.md:37-40`） | なし（中身の形は A4-1〜A4-3） |
| 工程11 Step OV（overview を書く） | 工程11 Step MOD のベースラインの退避・compare | Step の並び（`xddp-11-specs/SKILL.md:110,202,218`） | なし |
| Step MOD のベースラインの退避 → mod-agent → compare → 後始末 | 同じ | `xddp-11-specs/SKILL.md:218-263` | なし |
| 工程11 Step DONE（更新仕様書ファイル一覧） | close Step C0-3・C0-4 | close は工程11 の完了を確かめてから始まる（`xddp-close/SKILL.md:28-31`）・工程11 の次のコマンドは close（`xddp-11-specs/SKILL.md:544`） | なし |
| 工程11 Step GATE（廃止候補を削除） | close Step C0-3（DOCS から取り込み）→ C2（削除の伝播） | `xddp-11-specs/SKILL.md:510-512` → `xddp-close/SKILL.md:211-218` → `promote.py:297-323` | あり A4-8 |
| 工程11 を分割して実行（Step DONE を実行ごとに上書き） | close Step C0-3 | `xddp-11-specs/SKILL.md:546-573`（「Overwrite the section」） | あり A4-9（🔶） |
| 工程11 Step GATE（人が直接編集） | close Step C0-3 | `xddp-11-specs/SKILL.md:447,494-498` → `xddp-close/SKILL.md:215` | あり A4-10 |
| close Step C2（DOCS への昇格） | 次の CR の工程2（domain_refs）・工程4a 下調べ・工程5・6 | 次の CR は close の後（`xddp-11-specs/SKILL.md:665-667` の案内） | なし |
| 工程11 の完了後で close の前 | 次の CR の工程2（latest-specs へのフォールバック） | `xddp-11-specs/SKILL.md:665-667`・`domain_refs.py:383-385` | あり A4-13 |
| survey (c) Step 6 → 7 → 8①（DOCS へ写す） | 工程2・工程11 | `xddp-survey/SKILL.md:293-372` | なし |
| survey (c) Step 8②（latest-specs の architecture.md に追記） | 後の CR の close Step C0-3・C2 | `xddp-survey/SKILL.md:374-381` → `xddp-close/SKILL.md:215` | あり A4-11 |
| codemap（module-catalog） | specout の init `--module-catalog`・survey Step 1 | 随時。読む側がファイルの有無を確かめる（`xddp-04-specout/SKILL.md:229,501`・`xddp-survey/SKILL.md:66-72`） | なし |
| update-knowledge（glossary） | 工程2・工程3 | 随時。読む側がファイルの有無を確かめる（`domain_refs.py:232-235`・`xddp-02-analysis/SKILL.md:120-124`） | なし |
| 前の CR の工程11（latest-specs） | 工程5・6 の `CURRENT_SPECS_REFS`・工程11 の mod-agent（前の版） | latest-specs を優先して読む（`xddp-05-arch/SKILL.md:120`） | なし（名前の問題は A4-14） |

## 3. 指摘

### A4-1 工程11 が、ディレクトリしかモジュール資料とみなさない
- **約束:** スペックアウトのモジュール資料の置き場所
- **書く側:** `CC/skills/xddp-04-specout/module-documentation.md:261-273`（統合パスでは `modules/` を作らない。分割パスでは `modules/{モジュール名}-spo.md` というファイル）・`:295-300`（サブディレクトリ分割のときだけ `modules/{名前}/` というディレクトリと索引ファイル）。`specout_bfs.py:7170,7211-7238` も同じ形で書く。
- **読む側:** `CC/agents/xddp-specs-mod-agent.md:49`（「`modules/*/` 以下に SPO ファイルが存在するモジュール」）・`:161`（「`modules/auth/` → `auth`」のようにディレクトリ名から導く）
- **食い違い:** 分割パスのモジュール資料はディレクトリではなくファイルです。ディレクトリがあるのはサブディレクトリ分割したモジュールだけで、その中身は索引とサブモジュール資料です。
- **起きること:** 分割パスでも、サブディレクトリ分割していないモジュールは「SPO ありモジュール」にならず、spec.md・structure.md 等が作られません。既存のモジュールは「SPO なし・CHD あり」として扱われ、PATCH 固定・`last-verified-cr` 据え置きになります（`:50-58`）。
- **確度:** ✅（両側を読んだ。LLM が `*-spo.md` から読み替える可能性はありますが、手順の文はディレクトリと明記しています）
- **重大度の案:** 🔴
- **修正案:** 読む側を `modules/*-spo.md`（索引の場合はサブモジュール資料）に合わせる。

### A4-2 統合パスの §2.A… を工程11 が読まない
- **約束:** 統合パスのモジュール資料（`SPO-{CR}.md` の `## 2.A. {モジュール名}`、`### 2.A.1`〜`### 2.A.10`）
- **書く側:** `module-documentation.md:242-255`
- **読む側:** `xddp-specs-mod-agent.md:45-59,63-111`・`xddp-11-specs/SKILL.md:202-263`。統合パスについての記述がどこにもありません（`grep -n '統合\|2\.A'` で該当なし）。
- **食い違い:** 統合パスでは `modules/` が無く、モジュール仕様の材料は SPO 本体の §2.A… にしかありません。
- **起きること:** 文書化したファイルが `SPECOUT_MAX_FILES_PER_MODULE`（既定10）以下の CR では、新しいモジュールの latest-specs が作られません。既存のモジュールも CRS の SP 差分だけで更新されます。ADR-0018:103 は統合パスが「波及10ファイル以下の CR で普通に起き」ると書いています。さらに `### 2.A.10`（依頼調査の追記）は、`module-documentation.md:375` が「工程11 の最新仕様書にも入る」と約束していますが、届きません。
- **確度:** ✅
- **重大度の案:** 🔴
- **修正案:** mod-agent に統合パスの読み方（§2.A.n → §2.n、§2.A.8.n → §4.n の対応）を足す。

### A4-3 `SPECOUT_MODULES` をディレクトリ名から取っている
- **書く側:** #1 と同じ
- **読む側:** `xddp-11-specs/SKILL.md:120`（「`modules/` 配下のディレクトリ名リスト（機械的取得）」）・`:129-132`（architecture.md のマージ規則）・`11_overview-architecture-template.md:35`
- **食い違い:** 統合パスでは空になり、分割パスではサブディレクトリ分割したモジュールだけになります。
- **起きること:** architecture.md の「最新の SPO で更新するモジュール」が空かごく一部になり、調べたモジュールの記述が更新されません。AI_INDEX の先行更新の行の範囲（`:591-598`）も同じ値を使っています（担当外の A2 にも記載）。
- **確度:** ✅
- **重大度の案:** 🟡
- **修正案:** A4-1 と同じ方針で、`modules/*-spo.md`（統合パスは SPO §8 または台帳）から取る。

### A4-4 廃止モジュールの判定の照合先がディレクトリ
- **書く側:** #1 と同じ
- **読む側:** `xddp-specs-mod-agent.md:170-171`（「`modules/*/` に対応するディレクトリがないもの」を廃止候補にする）
- **起きること:** latest-specs の既存モジュールのほとんどが毎回「廃止候補」として GATE に出ます。人が提示どおり削除を選ぶと、有効な仕様が消えます（その後 A4-8 で元に戻るので、結果は不定になります）。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-5 precheck が SPO ファイルを引く名前が、ファイル名とずれる
- **書く側:** `module-documentation.md:403`（ファイル名はモジュール名そのもの。名前には `_`・大文字が使える `:398`）
- **読む側:** `spec_version_delta.py:181-183,194-200`（latest-specs のディレクトリ名＝ケバブ名に `-spo.md` を付けて探す）
- **食い違い:** `auth_service`・`AuthService` のようなモジュールは見つからず、`no_spo_file` で飛ばされます。サブディレクトリ分割したモジュールは、索引のファイルと比べて、誤って「更新あり」になり得ます。統合パスは常に飛ばされます。
- **起きること:** 機械的な先決判定が効かず、LLM の判断だけになります（安全側に倒れるので、失われるものはありません）。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-6 structure.md の材料の見出し「クラス図」が SPO に無い
- **書く側:** `04_specout-module-template.md:106`（`### 4.2 データ型関連図`）。survey も同じテンプレートを使う（`xddp-survey-agent.md:36-37`）。
- **読む側:** `xddp-specs-mod-agent.md:90`（`### クラス図`・`### データ構造`・`### PAD（問題分析図）` を見出し名で照合）・`spec_version_delta.py:37`（names に `クラス図`）
- **起きること:** 型どうしの関係の図（classDiagram）が structure.md に写らず、precheck の比較にも入りません。structure.md の「## 2. クラス図」（`11_module-structure-template.md:33`）がテンプレートのまま残るか、空になり得ます。
- **確度:** ✅（スクリプト）／🔶（LLM が意味で照合する可能性あり）
- **重大度の案:** 🟡

### A4-7 compare が、SPO の無いモジュールにも版の下限を当てはめる
- **約束:** `xddp-specs-mod-agent.md:152`「SPO なし CHD あり モジュールは compare の対象外とし、PATCH 固定」
- **読む側（実装）:** `spec_version_delta.py:348-397`（ベースラインの全 `.md` を、モジュールの区別なく比べる）
- **起きること:** SPO の無いモジュールでも、見出しが増減すれば MINOR・MAJOR へ自動で書き換えられ、「確認が不完全なことを PATCH で示す」という約束（`:57-58`）が崩れます。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-8 工程11 の GATE で削除した仕様を、close C0-3 が元に戻す
- **約束:** 削除の伝わり方
- **書く側:** `xddp-11-specs/SKILL.md:510-512`（人が選んだ廃止候補を、オーケストレーターがディレクトリごと削除する）・`:546-573`（更新仕様書ファイル一覧に載るのは生成・更新したファイルだけ）
- **読む側:** `xddp-close/SKILL.md:211-218`（C0-3: `{DOCS}/{repo}/specs/`・`system/specs/`・`cross/specs/` から「保護されていないファイル」を latest-specs へ写す）→ `promote.py:297-302,317-323`（latest-specs に無く DOCS にあるディレクトリを削除候補にする）
- **食い違い:** 削除したモジュール・ユースケースのファイルは保護一覧に無いので、C0-3 が DOCS から latest-specs に書き戻します。そのため C2 の削除候補の検出にもかかりません。
- **起きること:** 人が廃止と判断した仕様が latest-specs・DOCS・AI_INDEX に残り、次の CR の工程2・5・6 が現在の仕様として読みます。削除候補にも出ないので、人は気付けません。廃止シーケンスファイル（`:159-168,305-308`）も同じです。
- **確度:** ✅（両側を読んだ。ADR に、制限として受け入れた記述はありません）
- **重大度の案:** 🔴
- **修正案:** 工程11 が削除したパスを progress.md に記録し、C0-3 が取り込みから外す（C2 で削除候補にする）。

### A4-9 分割して実行すると、前の回の更新が保護から外れる
- **書く側:** `xddp-11-specs/SKILL.md:546-573`（「Overwrite the section if it already exists」。分割実行でも実行ごとに書く）
- **読む側:** `xddp-close/SKILL.md:213-215`
- **起きること:** 前の回に更新したモジュールのファイルが保護から外れ、C0-3 が DOCS の古い版で上書きします。その CR で更新した仕様が黙って失われます。
- **確度:** 🔶（「全ファイルパスを列挙する」を、CR 全体で累積する意味に読む余地があるため）
- **重大度の案:** 🟡

### A4-10 GATE で人が直接編集した「一覧に無いファイル」が C0-3 で元に戻る
- **書く側:** `xddp-11-specs/SKILL.md:447`（直接編集を案内）・`:494-498`（一覧に無いファイルの編集はスナップショットに捕捉されないと認めている）
- **読む側:** `xddp-close/SKILL.md:215`
- **起きること:** 今回の更新対象外のファイル（例: 更新しなかった architecture.md、他のモジュール）を人が直した内容が、DOCS に前の版があると close で上書きされ、黙って失われます。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-11 survey の (c) で architecture.md に追記した内容が DOCS に届かず、後の close で上書きされる
- **書く側:** `xddp-survey/SKILL.md:366-372`（DOCS へ写すのはモジュールのディレクトリだけ）・`:374-381`（architecture.md は latest-specs にだけ追記する）
- **読む側:** `xddp-close/SKILL.md:215`（後の CR の C0-3）
- **起きること:** 後の CR の工程11 が architecture.md を更新しなかった場合（保護一覧に無い場合）、DOCS の前の版で上書きされ、survey が足したモジュールの記述が消えます。AI_INDEX の overview のリンク（`xddp-survey/SKILL.md:396-397`）も、DOCS 側ではその間ずっと古い版を指します。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-12 domain_refs が、AI_INDEX の無いときに cross のインタフェース仕様を誤ったパスで探す
- **書く側:** `promote.py:306`（`latest-specs/cross` → `{DOCS}/cross/specs`。中身は `interfaces/{if}/spec.md`、`xddp-11-specs/SKILL.md:298`）
- **読む側:** `domain_refs.py:354-359`（`cross/specs` 直下のディレクトリ名〔`interfaces`・`sequences`〕に `/spec.md` を付けて探す）。AI_INDEX のある経路（`:331`）は `interfaces/{name}/spec.md` で正しい。
- **起きること:** AI_INDEX が無いマルチリポジトリの CR では、cross のインタフェース仕様が工程2 の参照先に一度も入りません（黙って失われる）。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-13 latest-specs へのフォールバックが、init が作るディレクトリのせいで働かない
- **書く側:** `xddp-01-init/SKILL.md:117-131`（DOCS を作るとき、全 repo に `{DOCS}/{repo}/specs/README.md` を作る）
- **読む側:** `domain_refs.py:228,383-385`（`{DOCS}/{repo}/specs/` が存在すれば latest-specs へフォールバックしない）。`xddp-11-specs/SKILL.md:665-667` は「次の CR の xddp-02-analysis は `latest-specs/` から直接参照します」と案内している。
- **食い違い:** init 後は repo の specs ディレクトリが常にあるので、フォールバック a（repo のモジュール仕様）は実際には起きません。close 前の前の CR の latest-specs は参照されません。AI_INDEX の先行更新の行は DOCS 側のパスを指すので、そこでも見つかりません（`domain_refs.py:290`）。
- **起きること:** 並行して進む CR、または close の前に始めた CR の工程2 が、直前の CR の最新仕様を読まずに分析します。工程11 の案内とも違います。
- **確度:** ✅（CLAUDE.md の説明「`{DOCS}` 側ディレクトリ自体が不在の場合のみ」とは一致しますが、init との組み合わせで効かなくなっています）
- **重大度の案:** 🟡

### A4-14 工程5・6 が latest-specs を探すときのモジュール名が、ディレクトリ名とずれる
- **書く側:** `xddp-specs-mod-agent.md:159-163`（ケバブ化し、`overview`・`cross`・`system` と同じなら `mod-` を付ける）
- **読む側:** `xddp-05-arch/SKILL.md:117-121`・`xddp-06-design/SKILL.md:57-61`（「SPO から影響モジュール名を読み」、その名前でパスを作る）
- **起きること:** `AuthService`・`auth_service` 等のモジュールでは現在の仕様が見つからず、「現状仕様なし（初回 CR）」として扱われ、インタフェースとの整合の確認が抜けます。
- **確度:** 🔶（LLM がケバブ化してから引く可能性あり）
- **重大度の案:** 🟡

### A4-15 `related-modules` の値と latest-specs のディレクトリ名がずれる
- **書く側:** `xddp-specs-uc-agent.md:56-58`（SPO のモジュール名で照合する）
- **読む側:** `promote.py:387-394` → AI_INDEX の「関連モジュール」→ `domain_refs.py:257-262,290`（その値でパス `{repo}/specs/{m}/spec.md` を作る）
- **起きること:** 名前がケバブ名と違うと、ユースケースに関係するモジュール仕様が工程2 の参照先に入りません。
- **確度:** 🔶
- **重大度の案:** 🟡

### A4-16 survey の `MODULE_KEBAB` と CR のモジュール名の決め方が違う
- **書く側:** `xddp-survey/SKILL.md:130-142`（ディレクトリが一致したときはパスの `/` を `-` に置き換える。例 `src/auth` → `src-auth`）
- **読む側:** `xddp-specs-mod-agent.md:159-161`（CR では SPO のモジュール名をケバブ化）・`xddp-survey/SKILL.md:295-304`（衝突の判定は同じ名前のディレクトリだけを見る）
- **起きること:** 同じコードの仕様が `src-auth/` と `auth/` に二重にでき、`source: spo` を上書きから守る判定も素通りします。
- **確度:** 🔶（名前は LLM・カタログ次第）
- **重大度の案:** 🟡

### A4-17 SPEC レビューに SPO が渡らない
- **書く側:** `xddp-11-specs/SKILL.md:347-356`（バッチ1・2 は CRS＋CHD だけ）・`xddp-review/SKILL.md:84-88`（同じ）
- **読む側:** `reviewer-checklists/SPEC.md:21-23`（`REFERENCE_FILES` の SPO §2 と矛盾が無いか）・`:32`（`SPECOUT_MODULES` を使う）・`:42`（「SPO 内容との矛盾」は 🔴）
- **起きること:** 最新仕様と SPO の矛盾を AI レビューで見つけられません（A4-1・A4-2 の取りこぼしも見つからない）。survey 側（`xddp-survey/SKILL.md:345`）は SURVEY を渡しているので一致しています。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-18 SPO §4.3 の `source` 注記を書く側がいない
- **読む側:** `xddp-11-specs/SKILL.md:186`
- **書く側:** `04_specout-summary-template.md:93-114` に注記の欄が無く、`grep -rn ai-inferred` でも specout 側に該当がありません。
- **起きること:** data-model.md の `source` はテンプレートの既定値 `ai-inferred` のままになります。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-19 「Section 3-0」「Section 3-4」を参照しているが、その節が無い
- `xddp-specs-uc-agent.md:29,76`・`xddp-11-specs/SKILL.md:374`
- 命名規則・版の判定基準・気づきメモの方針の参照先が存在しません。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-20 「影響リポジトリ」を cross CHD の表から読むことになっているが、その列が無い
- **書く側:** `xddp-06-design/SKILL.md:126-129`（列はインタフェース・変更種別・breaking。提供元・消費先は `:120-124` の「実装依存関係」）
- **読む側:** `xddp-common/SKILL.md:138-141`（工程11 の AFFECTED_REPOS の追加条件）・`reviewer-checklists/SPEC.md:31`（`affected-repos:` との照合）
- **起きること:** SPO の無い消費側 repo を工程11 の対象に足す条件が働かない可能性があります。
- **確度:** 🔶（LLM が「実装依存関係」の表で代用する可能性あり）
- **重大度の案:** 🔵

### A4-21 module-catalog のディレクトリと、specout が照合に使う値の形が合わない
- **書く側:** `xddp-codemap/SKILL.md:51-66`（深さ3まで。中にディレクトリしかないディレクトリはモジュールにしない＝`src/auth` のような入れ子が普通）・`module-catalog-template.md:26,39`
- **読む側:** `specout_bfs.py:1393-1408`（確定ファイルのモジュールをパスの第1要素とする）・`:1990-1994`（frontier をその値で引き、見つからなければ HIGH）。テスト（`tests/test_specout_bfs.py:851-892`）も最上位のディレクトリだけで確かめている。
- **起きること:** 入れ子の配置の repo では、カタログによる優先度の制御が働きません（全部 HIGH。失われるものはありません）。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-22 architecture.md の材料にする SPO の節の名前が違う
- `xddp-11-specs/SKILL.md:123`・`11_overview-architecture-template.md:33` は「モジュール依存・コンポーネント構成」と書いていますが、SPO の節名は「## 2. 全体アーキテクチャ図」（`04_specout-summary-template.md:32`）です。
- また、`## 2.` という接頭辞は統合パスの `## 2.A.`… にも一致します。
- **確度:** ✅（接頭辞の重なりの影響は 🔶）
- **重大度の案:** 🔵

### A4-23 日本語の見出しのケバブ変換が決まっていない
- `spec_version_delta.py:97-101` は ASCII 以外の文字を消すので、日本語の見出しは空の文字列になり、シーケンス図のファイルと一致しません（`:131`）。エージェント側（`xddp-specs-mod-agent.md:106`）の変換規則も決まっていません。
- 判定を飛ばすだけなので、失われるものはありません。
- **確度:** ✅／🔶
- **重大度の案:** 🔵

### A4-24 自動修正の対象キーと、lint の必須キーが違う
- 工程11 の自動修正の対象は 4 キーだけです（`xddp-11-specs/SKILL.md:372`）。lint の必須キーは `last-verified-cr`・`source`・`has_insights`・パスごとの追加キーも含みます（`artifact_lint.py:58,106-123`）。
- **重大度の案:** 🔵

### A4-25 compare が書き換えない版数の表示が残る
- compare は spec.md 等の §1 文書概要の「バージョン」行（`11_module-spec-template.md:30`）を書き換えません（`spec_version_delta.py:341-345`）。フロントマターと表示が食い違います。
- **重大度の案:** 🔵

### A4-26 設定テンプレートの latest-specs のパスに `{repo}/` が無い
- `xddp.config.md:346` は `latest-specs/overview/data-model.md` と書いていますが、実際は `latest-specs/{repo}/overview/data-model.md` です。
- **重大度の案:** 🔵

### A4-27 下調べエージェントの `LATEST_SPECS_DIR` の説明に `{XDDP_DIR}/` が無い
- `xddp-specout-prelim-agent.md:30` は `latest-specs/{REPO_NAME}/` と書いています。呼び出し元（`xddp-04-specout/SKILL.md:255`）は `{XDDP_DIR}/` 付きです。
- **重大度の案:** 🔵

### A4-28 abort の説明が close の動作と違う
- `xddp-abort/SKILL.md:43` は「C3.5/C3.6 等により一部成果物が `latest-specs/` へ昇格済み」と書いています。実際の close は latest-specs から DOCS へ写し、C3.5・C3.6 は DOCS に書きます。
- **重大度の案:** 🔵

### A4-29 sync-design の説明が工程11 の動作と違う
- `xddp-sync-design/SKILL.md:137` は「xddp-11-specs は現状コードと CHD を参照」と書いていますが、工程11 は SPO・CHD・CRS を読み、コードは読みません。
- **重大度の案:** 🔵

### A4-30 code-knowledge-boundary の書き手の欄が、survey の実際の書き先と違う
- `code-knowledge-boundary.md:32` は、survey が `{DOCS}/{repo}/specs/overview/architecture.md` に追記すると書いています。実際は latest-specs にだけ追記します（A4-11 と関連）。
- **重大度の案:** 🔵

### A4-31 glossary をテンプレートから作ると、見本の行が用語数に数えられる可能性
- update-knowledge がテンプレートから作るとき、見本の行 `| {用語} | … |`（`glossary-template.md:18`）が残ると、`promote.py:460-473` が用語として数えます。
- **確度:** 🔶（作成時に見本の行を置き換えるかが、手順に書かれていない。`xddp-update-knowledge/SKILL.md:224-228`）
- **重大度の案:** 🔵

## 4. 担当外の指摘

- **担当外（A2）:** 破壊的変更の印が AI_INDEX に出ない。`promote.py:446` はインタフェースのディレクトリ名（`{interface-kebab}`。`xddp-11-specs/SKILL.md:289-296` で変換したもの）を、`promote.py:1077` が集めた CHD の表の生の名前（例 `POST /jobs`）と比べています。名前が一致しないので「⚠️ 破壊的変更あり」が出ません。✅、🟡。
- **担当外（A2）:** AI_INDEX の先行更新の行の範囲が実質空になる。`xddp-11-specs/SKILL.md:591-598` は `SPECOUT_MODULES` の範囲に限っていますが、その値が実質空です（A4-3）。また `:595-597` は「`promote.py` と同じ行の集合」と書いていますが、`promote.py:420-432` は latest-specs の全モジュールのディレクトリを列挙しており、同じ集合ではありません。✅、🔵。

## 5. 段階2b の候補

なし。

## 6. 読んだファイルの一覧と、確認していないこと

**全文を読んだもの:**
- `CC/skills/xddp-11-specs/SKILL.md`
- `CC/agents/xddp-specs-mod-agent.md`
- `CC/agents/xddp-specs-uc-agent.md`
- `CC/skills/xddp-11-specs/scripts/spec_version_delta.py`
- `CC/skills/xddp-04-specout/templates/04_specout-module-template.md`
- `CC/skills/xddp-common/reviewer-checklists/SPEC.md`
- `CC/skills/xddp-codemap/SKILL.md`
- `CC/skills/xddp-codemap/templates/module-catalog-template.md`
- `CC/skills/xddp-update-knowledge/templates/glossary-template.md`
- `CC/agents/xddp-survey-agent.md`（1〜80行。全体）

**範囲を読んだもの:**
- `CC/skills/xddp-11-specs/templates/*.md`（各ファイルの1〜20行と見出しの一覧。module 系は変更履歴の節、spec は 20〜118行、architecture は 28〜60行、description は 30〜40行）
- `04_specout-summary-template.md`（1〜140行と見出しの一覧）
- `04_specout-cross-repo-template.md`（見出しの一覧）
- `module-documentation.md`（191〜420行と見出しの一覧）
- `promote.py`（1〜135、255〜640、1018〜1244行）
- `xddp-close/SKILL.md`（1〜60、185〜400行）
- `xddp-survey/SKILL.md`（60〜409行）
- `xddp-01-init/SKILL.md`（78〜207行）
- `domain_refs.py`（200〜425行）
- `tests/test_domain_refs.py`（245〜295行）
- `xddp-02-analysis/SKILL.md`（30〜70、112〜130行）
- `xddp-05-arch/SKILL.md`（108〜130行）
- `xddp-06-design/SKILL.md`（48〜72、98〜150行）
- `xddp-common/SKILL.md`（120〜160行）
- `artifact_lint.py`（55〜160行）
- `specout_bfs.py`（1300〜1415、1975〜2005、2660〜2700行と grep の結果）
- `tests/test_specout_bfs.py`（851〜895行）
- `xddp-update-knowledge/SKILL.md`（20〜60、90〜130、200〜240行）
- `xddp-review/SKILL.md`（68〜115行）
- `xddp-rules/code-knowledge-boundary.md`（14〜40行）
- `xddp-analyst-agent.md`（150〜165行）
- `xddp-abort/SKILL.md`（35〜50行）
- `xddp-sync-design/SKILL.md`（120〜140行）
- `xddp-01-init/templates/xddp.config.md`（280〜295、338〜350行）
- `00_progress-management-template.md`（C0-3 の前後）
- `docs/adr/ADR-0023`（135〜150行）
- grep の結果だけ見たもの: prelim agent、specout agent、`xddp-04-specout/SKILL.md`、`specout-finish.md`、`ripple-run.md`、`xddp-03-req`、`xddp-spec-writer-agent.md`、`collect_insights.py`、`xddp_review_brief.py`、`xddp-reviewer.md`、ADR-0018 と ADR-0026 の該当行

**確認していないこと:**
- 下調べエージェント・依頼調査が統合パス／分割パスを実際どう書くか（実行時の挙動）
- `collect_insights.py` の latest-specs の走査（A3 の担当）
- `xddp_review_brief.py`・gate snapshot が `pending-items/specs-baseline/` を拾うか
- 工程7〜10 の cross CHD の読み方（段階2b）
- `upsert_table` の詳細
- survey の module-catalog があるときの `MODULE_KEBAB` の導き方（項番1・2 のどちらに当たるか）
- codemap が実際に書く `{module-name}`・`{path}` の値
- スクリプトとテストの実行（行っていません）