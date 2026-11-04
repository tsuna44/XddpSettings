# 監査者 A4 の報告（やり直し版・原文。PLAN-20261103-contract-audit 段階2a）

> 抜き取り確認の漏れを受けた人の判断で行ったやり直しの監査の最終報告をそのまま載せたもの（検証前）。前回の版は [A4-audit.md](A4-audit.md)。検証結果と統合後の重大度は [../xddp-contract-audit-2026-11.md](../xddp-contract-audit-2026-11.md) を参照。

# A4 仕様・用語・カタログ — 約束の監査の結果（やり直し・前回の報告を置き換える完全版）

`{W}` = `/private/tmp/claude-501/-Users-tsuna-Documents-src-git-work-XddpSettings/c3213ce8-a1bc-4469-9c03-6422385baffd/scratchpad/audit-ecb54c4`（ecb54c4）。`CC/` は `ClaudeCode/.claude/` の略。ファイルは書き換えておらず、スクリプト・テストも実行していません（再現の結果は V3 の報告によるものと明記します）。

**要点:** 重大な食い違いは、前回と同じく次の3つです。
- **A4-1・A4-2:** 工程11 は `04_specout/{repo}/modules/` の**ディレクトリ**をモジュール資料とみなします。スペックアウトは、統合パスでは SPO 本体の §2.A… に、分割パスでは `modules/{名前}-spo.md` という**ファイル**に資料を書きます。このため、工程11 はスペックアウトのモジュール資料をほぼ見つけられません。
- **A4-8:** 工程11 の GATE で人が削除した仕様を、close の C0-3 が DOCS から latest-specs に書き戻します。

今回新しく、🟡 の指摘を5つ見つけました。
- A4-39: 分割実行で、継続の対象が逆になっている
- A4-42: 過去の CR のユースケースが、毎回「廃止候補」になる
- A4-43: 中止した CR の最新仕様が latest-specs に残り、後の CR の close で DOCS へ昇格する
- A4-44: survey (c) が人の承認の前に latest-specs へ書く
- A4-47: survey の衝突判定が latest-specs だけを見て、DOCS の CR 検証済みの仕様を上書きし得る

見つけた方法の記号: (1) パス・ファイル名の一部、(2) 節・見出し・列の名前、(3) 変数名・入力キー・関数名、(4) プレースホルダー・書式の文字列、(5) 参照のたどり。grep の範囲は、どれも `CC/skills CC/agents`（tests も含めて検索し、tests は参考扱い）。

---

## 1. 確認した約束の一覧

| # | 約束 | 書く側（ファイル:行・節） | 読む側（ファイル:行・節） | 見つけた方法 | 結果 |
|---|---|---|---|---|---|
| 1 | モジュール資料の置き場所（ディレクトリかファイルか） | `CC/skills/xddp-04-specout/module-documentation.md:268-273,295-300`・`specout_bfs.py:7170`（`modules/{name}-spo.md`）・`:6956-7006` | `CC/agents/xddp-specs-mod-agent.md:49,125,160-161` | (1) `-spo\.md`・`modules/` ／ (2) `## 配置判定` ／ (5) mod-agent:49 → module-documentation | あり A4-1 |
| 2 | 統合パスの §2.A… を工程11 が読むか | `module-documentation.md:242-259,375` | `mod-agent.md:45-111`・`CC/skills/xddp-11-specs/SKILL.md:202-263`（統合パスの記述なし） | (2) `2\.A`・`統合` を 11-specs の SKILL・agent に対して grep（該当なし） ／ (5) module-documentation:375「工程11 の最新仕様書にも入る」 | あり A4-2 |
| 3 | `SPECOUT_MODULES`（ディレクトリ名リスト） | 同 #1 | `11-specs/SKILL.md:120,129-132,209-215,591-598`・`11_overview-architecture-template.md:35`・`reviewer-checklists/SPEC.md:32` | (3) `SPECOUT_MODULES` ／ (1) `modules/` | あり A4-3 |
| 4 | 廃止モジュールの判定の照合先 | 同 #1 | `mod-agent.md:170-171` | (5) mod-agent ／ (1) `modules/\*/` | あり A4-4 |
| 5 | precheck が SPO ファイルを引く名前 | `module-documentation.md:400,403` | `spec_version_delta.py:181-183,193-200`・`11-specs/SKILL.md:228` | (3) `_spo_file_for_module` ／ (5) SKILL:228 | あり A4-5 |
| 6 | spec.md の材料（`## 2. 現状仕様`・`## 3. 既存仕様の文書化…`） | `04_specout-module-template.md:23,75`・`specout_bfs.py:6983,6991` | `mod-agent.md:66-67`・`spec_version_delta.py:36` | (2) `現状仕様` ／ (5) svd:34-36 のコメント | なし |
| 7 | structure.md の材料「クラス図」 | `04_specout-module-template.md:106`（`### 4.2 データ型関連図`） | `mod-agent.md:90`・`spec_version_delta.py:37` | (2) `クラス図`・`データ型関連図` | あり A4-6 |
| 8 | structure.md の材料（データ構造・PAD） | `04_specout-module-template.md:123,131` | 同上 | (2) 同上 | なし |
| 9 | state-machine・モジュール内シーケンス図の材料 | `04_specout-module-template.md:93,145` | `mod-agent.md:98,106`・`spec_version_delta.py:38,40` | (2) `モジュール内シーケンス図` ／ (5) | なし |
| 10 | §2.7 追加調査・`## 波紋調査の結果` の位置 | `module-documentation.md:373-375`・`specout_bfs.py:4420,7347-7350`（`## 5.` の直前） | `mod-agent.md:66`（§2 を取る） | (2) `波紋調査の結果` ／ (3) `MODULE_RIPPLE_HEADING` | なし |
| 11 | SPO サマリーの節名（§2・§3・§4.2〜§4.4） | `04_specout-summary-template.md:32,47,79,93,118` | `11-specs/SKILL.md:123,154,171,176,189`・`CC/agents/xddp-specs-uc-agent.md:32` | (2) `全体アーキテクチャ図`・`モジュール間シーケンス図` ／ (5) | なし（名前の別名は A4-22） |
| 12 | §4.3 の `source` 注記 | 書く側なし | `11-specs/SKILL.md:186` | (4) `ai-inferred` ／ (2) `アノテーション` | あり A4-18 |
| 13 | cross SPO §3 を工程11 が読む（見出しの存在） | `04_specout-cross-repo-template.md:35` | `11-specs/SKILL.md:277,307`・`uc-agent.md:33` | (2) `## 3. シーケンス図` ／ (5) | なし（小見出しの意味は #58） |
| 14 | cross CHD「インタフェース変更サマリ」の列（インタフェース・変更種別・breaking） | `CC/skills/xddp-06-design/SKILL.md:126-130` | `11-specs/SKILL.md:285-303`・`promote.py:1022-1078` | (2) `インタフェース変更サマリ` ／ (3) `CROSS_SUMMARY_HEADING_RE` | なし |
| 15 | 同上の「影響リポジトリ」 | `06-design/SKILL.md:126-130`（その列が無い） | `xddp-common/SKILL.md:138-141`・`SPEC.md:31` | (2) `影響リポジトリ` ／ (5) | 段階2b（A4-20） |
| 16 | latest-specs のフロントマター必須キー（パスごと） | `11_*-template.md` の各フロントマター | `artifact_lint.py:58,101-121,124-129` | (3) `BASE_FRONTMATTER_KEYS` ／ (5) SKILL:372 | なし |
| 17 | 工程11 の自動修正の対象キー | 同上 | `11-specs/SKILL.md:372` | 同上 | あり A4-24 |
| 18 | 変更履歴の表の形（1列目が版・最後の行が最新） | `11_module-*`・`11_overview-*` の変更履歴の節 | `spec_version_delta.py:265,315-338` | (2) `変更履歴` ／ (3) `CHANGELOG_HEADING_RE` | なし（cross の spec は「バージョン履歴」だが compare の対象外） |
| 19 | 版の表示（フロントマターと §1 の「バージョン」行） | `11_module-spec-template.md:2,30` | `spec_version_delta.py:341-345` | (4) `| バージョン |` ／ (3) `rewrite_version` | あり A4-25 |
| 20 | compare の対象（SPO なし・CHD ありのモジュール） | `mod-agent.md:152` | `spec_version_delta.py:348-397` | (5) mod-agent → svd ／ (3) `compare` | あり A4-7 |
| 21 | `FORCE_UPDATE_FILES` の形（`{module}/{file}`） | `spec_version_delta.py:223,244` | `mod-agent.md:24-26,138`・`SKILL.md:229-231` | (3) `FORCE_UPDATE_FILES` ／ (5) | なし |
| 22 | シーケンス図ファイル名のケバブ変換（日本語） | `mod-agent.md:106-108`・`SKILL.md:154-155` | `spec_version_delta.py:97-101,131` | (3) `kebabify` ／ (4) `-seq.md` | あり A4-23 |
| 23 | latest-specs のモジュールディレクトリ名と、工程5・6 が使う `{mod}` | `mod-agent.md:159-163` | `xddp-05-arch/SKILL.md:117-122`・`06-design/SKILL.md:57-62` | (3) `CURRENT_SPECS_REFS` ／ (4) `{module-kebab}`・`{mod}` | あり A4-14 |
| 24 | `CURRENT_SPECS_REFS`（latest-specs を優先し、無ければ DOCS） | `05-arch/SKILL.md:118-123,237`・`06-design/SKILL.md:58-63,218` | `CC/agents/xddp-architect-agent.md:46,86`・`xddp-designer-agent.md:51,86` | (3) `CURRENT_SPECS_REFS` ／ (1) `latest-specs` | なし |
| 25 | `related-modules` の値の語彙 | `uc-agent.md:56-58,70` | `promote.py:387-394` → `domain_refs.py:257-264,288-290` | (3) `related-modules` ／ (5) | あり A4-15 |
| 26 | survey の `MODULE_KEBAB` と CR のモジュール名 | `xddp-survey/SKILL.md:130-142` | `survey/SKILL.md:295-304`・`mod-agent.md:154-163` | (3) `MODULE_KEBAB` ／ (5) | あり A4-16 |
| 27 | survey から mod-agent への入力（`SURVEY_MODE`・`SURVEY_FILE`・`CR_PATH` 空） | `survey/SKILL.md:318-332` | `mod-agent.md:19-39` | (3) `SURVEY_MODE` ／ (5) | なし |
| 28 | SURVEY 成果物のパス | `survey/SKILL.md:171-175,48-55` | `mod-agent.md:36,39` | (1) `survey/{REPO_NAME}/module` ／ (4) `SURVEY-{` | なし |
| 29 | SURVEY 成果物の形（モジュールテンプレートを使う） | `CC/agents/xddp-survey-agent.md:36-49` | `mod-agent.md:68,92,100,107` | (2) `## 2. 現状仕様` ／ (5) | なし（クラス図は A4-6 と同じ） |
| 30 | `source: survey` を廃止判定から外す | `mod-agent.md:83-87` | `mod-agent.md:124-128,173-175`・`survey/SKILL.md:296-304` | (4) `source: survey` ／ (5) | なし |
| 31 | 昇格の写し先（repo→`{repo}/specs`・cross→`cross/specs`・system→`system/specs`） | `promote.py:284-326` | `xddp-close/SKILL.md:245-248`（C0-4 の対応） | (1) `specs/` ／ (3) `promote_specs` | なし |
| 32 | close C0-3 の取り込みと「工程11 更新仕様書ファイル一覧」のパスの形 | `11-specs/SKILL.md:546-573`・`00_progress-management-template.md:46-49` | `close/SKILL.md:211-221,226-231` | (2) `更新仕様書ファイル一覧` ／ (3) `PROTECTED_FILES` | なし（時期の問題は A4-8〜A4-10） |
| 33 | 削除の伝わり方（モジュール・ユースケース） | `11-specs/SKILL.md:510-512` | `close/SKILL.md:211-218`・`promote.py:297-302,317-323` | (5) ／ (3) `deletion_candidates` | あり A4-8 |
| 34 | DOCS の cross 仕様のパス（`cross/specs/interfaces/{if}/spec.md`） | `promote.py:306`・`SKILL.md:298` | `domain_refs.py:331`（AI_INDEX あり）・`:354-359`（AI_INDEX なし） | (1) `cross/specs` ／ (5) | あり A4-12 |
| 35 | `{DOCS}/{repo}/specs/` の有無が「昇格済み」を意味するか | `CC/skills/xddp-01-init/SKILL.md:117-131` | `domain_refs.py:228,382-396`・`11-specs/SKILL.md:665-667` | (1) `{repo}/specs` ／ (3) `docs_repo_specs_exists` | あり A4-13 |
| 36 | system のユースケース（`system/specs/use-cases/{uc}/description.md`）とフォールバック | `promote.py:311-316` | `domain_refs.py:269,336-341,398-410` | (1) `use-cases` ／ (3) | なし |
| 37 | module-catalog のパス `{DOCS}/{repo}/module-catalog.md` | `CC/skills/xddp-codemap/SKILL.md:134-136` | `04-specout/SKILL.md:229,257,498,501`・`specout-finish.md:81`・`xddp-investigate/SKILL.md:172-173`（finish と同じ値）・`ripple-run.md:50-52`・`CC/agents/xddp-specout-prelim-agent.md:32,149`・`survey/SKILL.md:66-72,213`・`survey-agent.md:25,33,57-59`・`specout_bfs.py:1261,2668-2670` | (1) `module-catalog` ／ (3) `CATALOG_FILE`・`MODULE_CATALOG`・`module_catalog` ／ (5) investigate:172 → finish | なし |
| 38 | module-catalog の節名（`## 2. モジュール一覧`・`## 3. シンボル索引`） | `module-catalog-template.md:22,33` | `specout_bfs.py:1321,1351`・`survey/SKILL.md:78,147` | (2) 節名 ／ (3) `_parse_module_catalog` | なし |
| 39 | module-catalog の `**ディレクトリ：**`・`### {name}/`・シンボル索引の値の形と、specout が照合に使う形 | `codemap/SKILL.md:51-66,102-106`・`template:24-26,37-39` | `specout_bfs.py:1328-1334,1360-1365,1397-1411,1987-1995,2668-2679` | (3) `_module_dir_for_file` ／ (5) | あり A4-21 |
| 40 | module-catalog の依存先・被依存元（「なし」の書き方） | `template:28-29` | `specout_bfs.py:1335-1346` | (2) `依存先モジュール` ／ (5) | なし（「（なし）」は存在しないモジュール名として扱われるだけで影響なし） |
| 41 | glossary のパス（共通・repo・cross） | `CC/skills/xddp-update-knowledge/SKILL.md:35,220-223` | `domain_refs.py:375-379`・`02-analysis/SKILL.md:119-124`・`03-req/SKILL.md:54-61`・`promote.py:505-523` | (1) `glossary` ／ (3) `GLOSSARY_PATHS`・`KNOW_DIR` | なし |
| 42 | glossary の列（正式表記・別名・揺れ・使用禁止） | `glossary-template.md:16` | `CC/agents/xddp-spec-writer-agent.md:31-34`・`xddp-analyst-agent.md:86-92` | (2) `正式表記`・`別名・揺れ` ／ (5) | なし |
| 43 | glossary の `## 用語一覧` の表（用語数） | `glossary-template.md:9-18`・`update-knowledge/SKILL.md:224-228` | `promote.py:460-473` | (2) `用語一覧` ／ (3) `_glossary_term_count` | あり A4-31 |
| 44 | SPEC レビューに渡す参照ファイル（SPO・SURVEY） | `11-specs/SKILL.md:347-356`・`xddp-review/SKILL.md:83-89`・`survey/SKILL.md:345` | `SPEC.md:21-23,32,42` | (3) `REFERENCE_FILES` ／ (2) `現状仕様` | あり A4-17（survey は一致） |
| 45 | 「Section 3-0」「Section 3-4」の参照先 | 書く側なし | `uc-agent.md:29,76`・`SKILL.md:374` | (2) `Section 3-` ／ (5) | あり A4-19 |
| 46 | survey (c) の architecture.md 追記が DOCS に届くか | `survey/SKILL.md:366-381` | `close/SKILL.md:215`・`code-knowledge-boundary.md:32` | (1) `architecture.md` ／ (5) | あり A4-11・A4-30 |
| 47 | latest-specs/README.md と予約名 | `01-init/SKILL.md:81-91` | `xddp-common/SKILL.md:48,71` | (1) `latest-specs` ／ (5) | なし |
| 48 | 工程11 の `ARTIFACT_LINK`（`../latest-specs/`） | `11-specs/SKILL.md:543` | progress.md の位置（`{XDDP_DIR}/{CR}/`） | (1) ／ (5) | なし |
| 49 | 設定テンプレートの latest-specs のパス | `xddp.config.md:345-347` | 実際のパス（`11-specs/SKILL.md:176,188`） | (1) `latest-specs/overview` ／ (5) | あり A4-26 |
| 50 | abort・sync-design の latest-specs の説明 | `xddp-abort/SKILL.md:42-46`・`xddp-sync-design/SKILL.md:137` | close・工程11 の実際の動作 | (1) `latest-specs` ／ (5) | あり A4-28・A4-29 |
| 51 | architecture.md の材料にする SPO の節の名前 | `04_specout-summary-template.md:32` | `11-specs/SKILL.md:123`・`11_overview-architecture-template.md:33` | (2) `全体アーキテクチャ図`・`モジュール依存` | あり A4-22 |
| 52 | 工程4a の下調べエージェントへの仕様ディレクトリの入力 | `04-specout/SKILL.md:253-255`・`specout-finish.md:77-79` | `prelim-agent.md:28-30,149` | (3) `SPECS_DIR` ／ (1) `latest-specs` | なし（記述の揺れは A4-27） |
| 53 | document agent への仕様ディレクトリの入力（**今回追加**） | `specout-finish.md:150-152` | `CC/agents/xddp-specout-document-agent.md:27-28` | (3) `SPECS_DIR` ／ (5) finish:136 | なし |
| 54 | discovery-setup への BASELINE・CROSS（**今回追加**） | `04-specout/SKILL.md:303-304` | `CC/agents/xddp-specout-agent.md:28-32,162` | (3) `SPECS_DIR` ／ (5) | なし |
| 55 | module-catalog が無いときの意味（**今回追加**） | `04-specout/SKILL.md:519-520`（説明） | `specout_bfs.py:2680-2686,1987-1998`（実際の動作） | (3) `module_priority_mode` ／ (2) `module-catalog 不在` | あり A4-34 |
| 56 | survey が catalog から読む欄（**今回追加**） | `module-catalog-template.md:26-27`（ディレクトリ・主要シンボル） | `survey/SKILL.md:98`（「主要ファイル・ディレクトリ」） | (2) `主要ファイル`・`主要シンボル` ／ (5) | あり A4-33 |
| 57 | overview/deployment.md の材料の節（**今回追加**） | 書く側なし（SPO サマリーのテンプレートにその節が無い） | `11-specs/SKILL.md:194-196`・`11_overview-deployment-template.md:15` | (2) `デプロイ構成`・`ハードウェア構成` ／ (1) `deployment` | あり A4-32 |
| 58 | cross SPO §3 の小見出しの意味（フローかレベルか）（**今回追加**） | `04_specout-cross-repo-template.md:38,41,54`・`04-specout/SKILL.md:670` | `11-specs/SKILL.md:276-279,305-308` | (2) `シーケンス図` ／ (4) `{flow}` | あり A4-36 |
| 59 | ユースケースのシーケンスから overview のシーケンスへの相対リンク（**今回追加**） | `11_system-use-case-sequence-template.md:28` | 実際の配置（`11-specs/SKILL.md:562-570`・`promote.py:311-316`） | (4) `../../{repo}` ／ (1) `-seq.md` | あり A4-35 |
| 60 | CHD の「変更対象モジュール名」（**今回追加**） | `06_change-design-document-template.md`（見出し 17〜239行。その欄は無い。`:28` は「変更対象ファイル一覧」） | `mod-agent.md:50-55` | (2) `変更対象モジュール` ／ (5) | あり A4-37 |
| 61 | cross インタフェース仕様の `provider`・`affected-repos` の材料（**今回追加**） | `06-design/SKILL.md:120-124`（実装依存関係） | `11-specs/SKILL.md:284-303`・`11_cross-interface-spec-template.md:6-11`・`artifact_lint.py:106-107` | (4) `{provider-repo}` ／ (2) `実装依存関係` | あり A4-38 |
| 62 | 工程11 分割実行メモの「処理済みモジュール」（**今回追加**） | `11-specs/SKILL.md:519-528` | `11-specs/SKILL.md:42-49`・`CC/skills/xddp-status/SKILL.md:47-63` | (2) `分割実行メモ` ／ (3) `MODULE_SCOPE` | あり A4-39 |
| 63 | 分割実行メモの置き場所「progress.md §15」（**今回追加**） | `11-specs/SKILL.md:519` | `00_progress-management-template.md`（番号付きの節が無い） | (2) `§15` ／ (1) progress テンプレート | あり A4-40 |
| 64 | `RESUME_UR_LIST` の値の形（UR か、ケバブ名か）（**今回追加**） | `11-specs/SKILL.md:84-86,97,526-527` | `uc-agent.md:17,24-25,29` | (3) `RESUME_UR_LIST` ／ (2) `未処理UR` | あり A4-41 |
| 65 | ユースケースの廃止判定の照合対象（**今回追加**） | 過去の CR の uc-agent（`uc-agent.md:61-67`。複数の CR の UR が蓄積する） | `uc-agent.md:89-98`・`SKILL.md:454-457,510-512` | (2) `廃止候補` ／ (4) `status: orphaned` | あり A4-42 |
| 66 | 並行 CR 保護（`last-updated-cr` → 他の CR の progress.md「## CR クローズ」）（**今回追加**） | `close/SKILL.md:401-410`（「## CR クローズ」）・`xddp-abort/SKILL.md:138`（「## CR 中止」） | `mod-agent.md:129-133,176-178`・`uc-agent.md:92-97`・`SKILL.md:161-165` | (2) `## CR クローズ` ／ (3) `last-updated-cr` | あり A4-43（中止した CR だけ） |
| 67 | survey (c) が承認前に書く latest-specs と close の昇格（**今回追加**） | `survey/SKILL.md:318-332,360-362` | `close/SKILL.md:21-23,215`・`promote.py:287-292`・`xddp-common/SKILL.md:131-132` | (5) survey → close ／ (1) `latest-specs/{REPO_NAME}` | あり A4-44 |
| 68 | survey Step 7 のレビュー対象と Step 8② の architecture.md（**今回追加**） | `survey/SKILL.md:374-381` | `survey/SKILL.md:338-339` | (5) ／ (1) `architecture.md` | あり A4-45 |
| 69 | precheck の比較範囲（latest-specs の spec.md 全体 ↔ SPO §2）（**今回追加**） | `11_module-spec-template.md:23-118`（§1・§7〜§9 を持つ） | `spec_version_delta.py:203-237` | (3) `line_change_pct` ／ (5) | あり A4-46 |
| 70 | survey の衝突判定の照合先と写し先（**今回追加**） | 写し先: `survey/SKILL.md:366-371`（DOCS） | 判定: `survey/SKILL.md:295-316`（latest-specs だけを見る） | (4) `source: spo` ／ (1) `{DOCS}/{REPO_NAME}/specs/{module}` | あり A4-47 |
| 71 | GLOSSARY_PATHS の quick の経路（**今回追加**） | `02-analysis/SKILL.md:119-135` | `spec-writer-agent.md:31-34`（03-req Step A0 だけを書く） | (3) `GLOSSARY_PATHS` ／ (5) | なし（説明だけの揺れ。値は同じ） |
| 72 | code-knowledge-boundary の「仕様側」パスの表記（説明のみ）（**今回追加**） | `code-knowledge-boundary.md:32,46,89-90` | 読む側なし（昇格しない理由の説明） | (1) `specs/overview` ／ (5) | なし（説明のみ。DOCS 相対と latest-specs 相対の表記が混在） |
| 73 | C0-3 が持ち込む `latest-specs/{repo}/README.md` とディレクトリの列挙（**今回追加**） | `01-init/SKILL.md:120,180-183`（DOCS 側の README）→ `close/SKILL.md:215` | `spec_version_delta.py:193`・`mod-agent.md:170`・`promote.py:409,426`（どれもディレクトリだけを数える） | (1) `README.md` ／ (5) | なし |
| 74 | `pending-items/specs-baseline/` とレビューブリーフ（**今回追加**） | `11-specs/SKILL.md:218-225,261-263` | `xddp_review_brief.py:116-128`（CR 配下を全部走査） | (1) `specs-baseline` ／ (3) `_scan` | なし（compare に失敗したときだけ残り、ブリーフに混ざるだけ） |
| 75 | INSIGHTS の収集が除外するファイル名と `has_insights: false` のテンプレート（**参考・担当外 A3**） | `11_*-template.md` のフロントマター | `collect_insights.py:113-123` | (3) `LATEST_SPECS_EXCLUDE` ／ (4) `has_insights` | なし（A3 の担当。一致） |

## 2. 時期の約束の表

| 書く側（スキル・Step） | 読む側（スキル・Step） | 順序の根拠（ファイル:行） | 結果 |
|---|---|---|---|
| 工程4a（SPO・modules・§2.A…） | 工程11 Step OV・MOD・UC | 工程11 は SPO がある repo だけを扱う（`xddp-common/SKILL.md:135-142`・`11-specs/SKILL.md:36-40`） | なし（中身の形は A4-1〜A4-3） |
| 工程11 Step OV | Step MOD のベースラインの退避・compare | Step の並び（`11-specs/SKILL.md:110,202,218`） | なし |
| Step MOD 退避 → mod-agent → compare → 後始末 | 同じ | `11-specs/SKILL.md:218-263` | なし |
| 工程11 Step DONE（更新仕様書ファイル一覧） | close Step C0-3・C0-4 | close は工程11 の ✅ を確かめる（`close/SKILL.md:28-31`）・案内（`11-specs/SKILL.md:544`） | なし |
| 工程11 Step GATE（廃止候補を削除） | close C0-3 → C2 | `11-specs/SKILL.md:510-512` → `close/SKILL.md:211-218` → `promote.py:297-323` | あり A4-8 |
| 工程11 分割実行（Step DONE が実行ごとに一覧を上書き） | close C0-3 | `11-specs/SKILL.md:546-551,573` | あり A4-9（🔶） |
| 工程11 分割実行 B（Step DONE が「処理済みモジュール」を書く） | 次の工程11 Step 0 | `11-specs/SKILL.md:525` → `:47` | あり A4-39 |
| 工程11 Step GATE（人が直接編集） | close C0-3 | `11-specs/SKILL.md:447,494-498` → `close/SKILL.md:215` | あり A4-10 |
| close C2（DOCS への昇格） | 次の CR の工程2（domain_refs）・工程4a・工程5・6 | 次の CR は close の後（`11-specs/SKILL.md:665-667`） | なし |
| 工程11 完了後・close 前 | 次の CR の工程2（latest-specs へのフォールバック） | `11-specs/SKILL.md:665-667`・`domain_refs.py:382-396` | あり A4-13 |
| 工程11 の完了後に `/xddp-abort` | 後の CR の close C0-3・C2、工程11 の並行 CR 保護 | abort は close の途中だけを止める（`xddp-abort/SKILL.md:36-46`）。「## CR 中止」を書く（`:138`） | あり A4-43 |
| survey (c) Step 6（latest-specs に書く）→ Step 8（承認） | 後の CR の close C0-3・C2 | `survey/SKILL.md:318-332,360-362` → `promote.py:287-292` | あり A4-44 |
| survey Step 8②（architecture.md に追記） | survey Step 7（レビュー） | Step 7 が先（`survey/SKILL.md:336-356` → `:360-381`） | あり A4-45 |
| survey (c) Step 8①（DOCS へ写す） | 工程2・工程11 | `survey/SKILL.md:366-371` | なし |
| survey (c) Step 8②（latest-specs だけに追記） | 後の CR の close C0-3・C2 | `survey/SKILL.md:374-381` → `close/SKILL.md:215` | あり A4-11 |
| codemap（module-catalog） | specout の init（`--module-catalog`）・下調べ・survey Step 1・4 | 随時。読む側がファイルの有無を確かめる（`04-specout/SKILL.md:229,501`・`ripple-run.md:52`・`specout-finish.md:81`・`survey/SKILL.md:66-72`） | なし |
| update-knowledge（glossary） | 工程2・工程3 | 随時。読む側がファイルの有無を確かめる（`domain_refs.py:233-236`・`02-analysis/SKILL.md:120-124`・`03-req/SKILL.md:54-61`） | なし |
| 前の CR の工程11（latest-specs） | 工程5・6 の `CURRENT_SPECS_REFS`・工程11 の mod-agent（前の版） | latest-specs を優先して読む（`05-arch/SKILL.md:120`） | なし（名前の問題は A4-14） |

## 3. 指摘

### A4-1 工程11 が、ディレクトリしかモジュール資料とみなさない
- **約束:** スペックアウトのモジュール資料の置き場所
- **書く側:** `module-documentation.md:268-273`（統合パスは `modules/` を作らない。分割パスは `modules/{名前}-spo.md` というファイル）・`:295-300`（サブディレクトリ分割のときだけ、ディレクトリと索引）・`specout_bfs.py:7170`
- **読む側:** `mod-agent.md:49`（`modules/*/` の下に SPO ファイルがあるモジュール）・`:125`・`:160-161`（ディレクトリ名から導く）
- **食い違い:** 分割パスのモジュール資料はファイルです。ディレクトリがあるのは、サブディレクトリ分割したモジュールだけです。同じ工程11 の中でも、`spec_version_delta.py:181-183` はファイル（`{module}-spo.md`）を引いており、エージェントと前提が違います（V3 の補強）。
- **起きること:** 分割パスでもほとんどのモジュールが「SPO ありモジュール」にならず、spec.md 等が作られません。既存のモジュールは「SPO なし・CHD あり」の扱い（PATCH 固定）になります。
- **確度:** ✅
- **重大度の案:** 🔴
- **修正案（任意）:** 読む側を `modules/*-spo.md`（索引の場合はサブモジュール資料）に合わせる。

### A4-2 統合パスの §2.A… を工程11 が読まない
- **書く側:** `module-documentation.md:242-259`・`:375`（「工程11 の最新仕様書にも入る」と約束している）
- **読む側:** `mod-agent.md:45-111`・`11-specs/SKILL.md:202-263`（統合パスの記述が無い）
- **起きること:** 文書化したファイルが `SPECOUT_MAX_FILES_PER_MODULE` 以下の CR では、モジュール仕様が作られません。§2.A.10（依頼調査の追記）も届きません。
- **確度:** ✅
- **重大度の案:** 🔴
- **修正案（任意）:** mod-agent に §2.A.n → §2.n、§2.A.8.n → §4.n の読み方を足す。

### A4-3 `SPECOUT_MODULES` をディレクトリ名から取っている
- **読む側:** `11-specs/SKILL.md:120,129-132`・`:209-215`（モジュール数の合計）・`:591-598`・`11_overview-architecture-template.md:35`・`SPEC.md:32`
- **起きること:** 統合パスでは空になり、分割パスでは一部だけになります。architecture.md の「最新の SPO で更新するモジュール」が欠け、Step MOD の分割の判断（モジュール数）も誤ります。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-4 廃止モジュールの判定の照合先がディレクトリ
- **読む側:** `mod-agent.md:170-171`
- **起きること:** 既存のモジュールのほとんどが、毎回 GATE に廃止候補として出ます（`SKILL.md:459-462`）。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-5 precheck が SPO ファイルを引く名前が、ファイル名とずれる
- **書く側:** `module-documentation.md:400,403`（モジュール名には英数字・`-`・`_` が使える。ファイル名はモジュール名そのもの）
- **読む側:** `spec_version_delta.py:181-183,193-200`（latest-specs のケバブ名に `-spo.md` を付けて探す）
- **起きること:** `auth_service` のような名前は `no_spo_file` になります（V3 で再現）。サブディレクトリ分割した索引とは誤って比べます。統合パスは常に飛ばされます。LLM の判断が残るので、失われるものはありません。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-6 structure.md の材料の見出し「クラス図」が SPO に無い
- **書く側:** `04_specout-module-template.md:106`（`### 4.2 データ型関連図`）。survey も同じテンプレートを使います（`survey-agent.md:36-37`）。
- **読む側:** `mod-agent.md:90`・`spec_version_delta.py:37`
- **起きること:** classDiagram が structure.md の「## 2. クラス図」に写りません。precheck の比較にも入りません（V3 で再現）。
- **確度:** ✅（スクリプト）／🔶（LLM は意味で照合するかもしれない）
- **重大度の案:** 🟡

### A4-7 compare が、SPO の無いモジュールにも版の下限を当てはめる
- `mod-agent.md:152`（対象外・PATCH 固定）に対して、`spec_version_delta.py:348-397` はベースラインのすべての `.md` を比べます。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-8 工程11 の GATE で削除した仕様を、close C0-3 が元に戻す
- **書く側:** `11-specs/SKILL.md:510-512`（オーケストレーターが削除する）・`:546-573`（一覧に載るのは、生成・更新したファイルだけ）
- **読む側:** `close/SKILL.md:211-218`（保護されていないファイルを DOCS から写す）→ `promote.py:297-302,317-323`
- **起きること:** 削除したモジュール・ユースケースが latest-specs・DOCS に戻ります。削除候補にも出ないので、人は気付けません。前の CR で DOCS に昇格済みのものに限ります。
- **確度:** ✅
- **重大度の案:** 🔴
- **修正案（任意）:** 削除したパスを progress.md に記録し、C0-3 の取り込みから外す。

### A4-9 分割して実行すると、前の回の更新が保護から外れる
- `11-specs/SKILL.md:546-551,573`（「Overwrite the section」）・`close/SKILL.md:213-215`
- **確度:** 🔶（一覧を累積するかが書かれていない。V3 も「判断できず」）
- **重大度の案:** 🟡

### A4-10 GATE で人が直接編集した「一覧に無いファイル」が C0-3 で元に戻る
- `11-specs/SKILL.md:447,494-498` → `close/SKILL.md:215`。DOCS に前の版がある場合に限ります。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-11 survey (c) の architecture.md への追記が DOCS に届かず、後の close で上書きされる
- `survey/SKILL.md:366-372`（DOCS へ写すのはモジュールのディレクトリだけ）・`:374-381` → `close/SKILL.md:215`
- **確度:** ✅
- **重大度の案:** 🟡

### A4-12 AI_INDEX が無いとき、domain_refs が cross のインタフェース仕様を誤ったパスで探す
- `domain_refs.py:354-359`（`cross/specs` の直下の `interfaces`・`sequences` に `/spec.md` を付けて探す）に対して、正しいパスは `promote.py:306`・`SKILL.md:298` の形です。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-13 latest-specs へのフォールバックが、init が作るディレクトリのために働かない
- `01-init/SKILL.md:117-131`（`{DOCS}/{repo}/specs/README.md` を必ず作る）に対して、`domain_refs.py:228,382-385` はそのディレクトリがあればフォールバックしません。`11-specs/SKILL.md:665-667` の案内とも違います。system のフォールバック（`:398`）は働きます。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-14 工程5・6 が latest-specs を探すときのモジュール名が、ディレクトリ名とずれる
- `05-arch/SKILL.md:117-122`・`06-design/SKILL.md:57-62`（SPO のモジュール名でパスを作る）に対して、書く側は `mod-agent.md:159-163`（ケバブ化し、予約名なら `mod-` を付ける）です。
- **確度:** 🔶
- **重大度の案:** 🟡

### A4-15 `related-modules` の値と latest-specs のディレクトリ名がずれる
- `uc-agent.md:56-58` → `promote.py:387-394` → `domain_refs.py:257-264,288-290`
- **確度:** 🔶
- **重大度の案:** 🟡

### A4-16 survey の `MODULE_KEBAB` と、CR のモジュール名の決め方が違う（**内容を補足**）
- `survey/SKILL.md:130-142`（`src/auth` → `src-auth`）に対して、`mod-agent.md:159-161`・`module-documentation.md:385-400` は別の決め方をします。
- 衝突の判定（`survey/SKILL.md:295-304`）は、同じ名前のディレクトリだけを見ます。
- 補足: `CATALOG_AVAILABLE = true` で解決したモジュールの `MODULE_KEBAB` の決め方は、項番1・2 のどちらにも当たらず、書かれていません（`:130-142`）。
- **確度:** 🔶（二重にできるのは、名前が食い違うときだけ）
- **重大度の案:** 🟡

### A4-17 SPEC レビューに SPO が渡らない
- `11-specs/SKILL.md:349-356`・`xddp-review/SKILL.md:83-89`（CRS＋CHD だけを渡す）に対して、`SPEC.md:21-23,32,42` は SPO を前提にしています。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-18 SPO §4.3 の `source` 注記を書く側がいない
- `11-specs/SKILL.md:186`。`ai-inferred` を書くのは 11 のテンプレートと uc-agent だけで、SPO 側には無い。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-19 「Section 3-0」「Section 3-4」の参照先が無い
- `uc-agent.md:29,76`・`SKILL.md:374`
- **確度:** ✅
- **重大度の案:** 🔵

### A4-21 module-catalog のディレクトリの形と、specout が照合に使う形が合わない（**内容を補足**）
- **書く側:** `codemap/SKILL.md:51-66`（入れ子のディレクトリがモジュールになる）。`template:24,26,39`。ディレクトリを相対・絶対のどちらで書くかは決まっていません。
- **読む側:** `specout_bfs.py:1397-1411`（確定ファイルのモジュールはパスの第1要素）・`:1987-1995`（引けなければ HIGH）
- **補足:** 見出しの正規表現 `^###\s+([^\s/]+)/`（`:1328`）は、モジュール名に `/` を含むと第1要素だけを取ります。そのため `src/auth`・`src/db` は同じ名前 `src` になり、ディレクトリが上書きされます。
- **起きること:** 入れ子の配置では、優先度の制御が働きません（全部 HIGH。失われるものはない）。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-22 architecture.md の材料の節の名前（**内容を修正**）
- SKILL の本文（`11-specs/SKILL.md:123`）は正しい名前（全体アーキテクチャ図）を先に挙げています。
- 食い違うのは、テンプレート `11_overview-architecture-template.md:33` の別名「モジュール依存・コンポーネント構成」だけです。
- `## 2.` という接頭辞が統合パスの `## 2.A.` にも当たる点は 🔶 です。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-23 日本語の見出しのケバブ変換が決まっていない
- `spec_version_delta.py:97-101,131`・`mod-agent.md:106`（V3 で再現）
- **確度:** ✅
- **重大度の案:** 🔵

### A4-24 自動修正の対象キー（4つ）と lint の必須キーが違う
- `SKILL.md:372` と `artifact_lint.py:58,101-121`
- **確度:** ✅
- **重大度の案:** 🔵

### A4-25 compare が §1 の「バージョン」行を書き換えない
- `11_module-spec-template.md:30` と `spec_version_delta.py:341-345`
- **確度:** ✅
- **重大度の案:** 🔵

### A4-26 設定テンプレートの latest-specs のパスに `{repo}/` が無い
- `xddp.config.md:346`
- **確度:** ✅
- **重大度の案:** 🔵

### A4-27 下調べエージェントの `LATEST_SPECS_DIR` の説明に `{XDDP_DIR}/` が無い
- `prelim-agent.md:30`（呼び出し元の `04-specout/SKILL.md:255`・`specout-finish.md:79` は `{XDDP_DIR}/` 付き）
- **確度:** ✅
- **重大度の案:** 🔵

### A4-28 abort の説明が close の動作と違う
- `xddp-abort/SKILL.md:42-46`
- **確度:** ✅
- **重大度の案:** 🔵

### A4-29 sync-design の説明が工程11 の動作と違う
- `xddp-sync-design/SKILL.md:137`（工程11 はコードを読まない）
- **確度:** ✅
- **重大度の案:** 🔵

### A4-30 code-knowledge-boundary の書き手の欄が、survey の実際の書き先と違う
- `code-knowledge-boundary.md:32` と `survey/SKILL.md:374-375`
- **確度:** ✅
- **重大度の案:** 🔵

### A4-31 glossary をテンプレートから作ると、見本の行が用語数に数えられる
- `glossary-template.md:18`・`update-knowledge/SKILL.md:224-228` → `promote.py:460-473`（V3 で 1 を返すことを再現）
- **確度:** ✅
- **重大度の案:** 🔵

### A4-32 overview/deployment.md の材料の節を、SPO のどこも書かない（新規）
- **約束:** 「ハードウェア構成・デプロイ構成」の節があれば deployment.md を作る
- **書く側:** 無し。`04_specout-summary-template.md` の見出し（11〜332行）にその節が無く、grep でも 11-specs の外に該当がありません。
- **読む側:** `11-specs/SKILL.md:194-196`・`11_overview-deployment-template.md:15-18`（組み込みでは必須のビューになることが多い、と書いている）
- **起きること:** deployment.md は作られません。黙って欠けます。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-33 survey が module-catalog の「主要ファイル」欄を読むことになっているが、その欄が無い（新規）
- **書く側:** `module-catalog-template.md:26-27`（ディレクトリ・主要シンボルだけ）
- **読む側:** `survey/SKILL.md:98`（「主要ファイル・ディレクトリ」から TARGET_FILES を確定する）
- **確度:** 🔶（LLM はディレクトリで代用できる）
- **重大度の案:** 🔵

### A4-34 module-catalog が無いときの動作の説明が、スクリプトと違う（新規）
- **説明:** `04-specout/SKILL.md:519-520`（「空の場合は優先度差別化なしの通常 BFS になる」）
- **実際:** `specout_bfs.py:2680-2686`（簡易の近傍優先 `simple`）・`:1987-1998`（近くないディレクトリは LOW。後回しにする）
- **起きること:** 人は、遠いモジュールが後回しになることを知らずに結果を読みます。失われるものはありません。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-35 ユースケースのシーケンス図から overview のシーケンス図へのリンクの相対パスが誤っている（新規）
- **書く側:** `11_system-use-case-sequence-template.md:28`（`../../{repo}/overview/sequences/{feature}-seq.md`）
- **実際の配置:** ファイルは `latest-specs/system/use-cases/{uc}/sequences/` にあります（`SKILL.md:570`）。`../../` は `use-cases/` を指すので、リンク先は存在しません。DOCS では `system/specs/…` と `{repo}/specs/…` で深さが違い（`promote.py:311-316`）、どちらでも成り立つ1つの相対パスはありません。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-36 cross SPO §3 の小見出しはレベルごとなのに、工程11 はフローの名前として使う（新規）
- **書く側:** `04_specout-cross-repo-template.md:38,41,54`（`### 3.1 {レベル名}レベルのシーケンス図`）
- **読む側:** `11-specs/SKILL.md:276-279`（小見出しをケバブ変換して `cross/sequences/{flow}-seq.md`）・`:305-308`（廃止候補の照合）
- **起きること:** フローではなくレベルの名前のファイルになります。日本語なので、変換も決まっていません（A4-23 と同じ）。
- **確度:** 🔶
- **重大度の案:** 🔵

### A4-37 mod-agent が CHD の「変更対象モジュール名」を探すが、CHD にその欄が無い（新規）
- **書く側:** `06_change-design-document-template.md`（`## 2. 変更対象ファイル一覧`（:28）だけ）
- **読む側:** `mod-agent.md:50-55`（導出方法1）。CHD のパスも、mod-agent には渡されていません（`SKILL.md:234-246`）。
- **起きること:** 導出方法1 は適用されず、常に AI の照合になります。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-38 cross インタフェース仕様の `provider`・`affected-repos` の材料が、Step CROSS に書かれていない（新規）
- **書く側（材料）:** `06-design/SKILL.md:120-124`（実装依存関係の表）
- **読む側:** `11-specs/SKILL.md:284-303`（「インタフェース変更サマリ」だけを読む）
- **必須とする側:** `11_cross-interface-spec-template.md:6-11`・`artifact_lint.py:106-107`
- **確度:** 🔶
- **重大度の案:** 🔵
- **関連:** A4-20（段階2b）

### A4-39 分割実行 B の継続で、処理済みのモジュールだけをもう一度処理する（新規）
- **書く側:** `11-specs/SKILL.md:525`（`処理済みモジュール: {…} in {repo}`）
- **読む側:** `11-specs/SKILL.md:47`（「`処理済みモジュール:` が存在する場合は当該 repo の MODULE_SCOPE をその値に限定する」）
- **食い違い:** UR では、未処理の一覧で継続します（`:48`）。モジュールでは、処理済みの一覧に限定しており、継続の対象が逆です。未処理のモジュールの欄もありません。
- **起きること:** 残りのモジュールの仕様が作られないまま、工程11 が完了し得ます。
- **確度:** ✅（文面）／🔶（LLM が逆に読む可能性）
- **重大度の案:** 🟡

### A4-40 分割実行メモの置き場所「progress.md §15」が存在しない（新規）
- `11-specs/SKILL.md:519` に対して、`00_progress-management-template.md` には番号付きの節がありません。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-41 `RESUME_UR_LIST` の値が、UR かケバブ名かで揺れる（新規）
- **書く側:** `SKILL.md:84-86,97`（初回は「指定 UR」）・`:526-527`（継続は「URケバブ名一覧」）
- **読む側:** `uc-agent.md:17,24-25`（「処理対象 UR のリスト」）
- **確度:** 🔶
- **重大度の案:** 🔵

### A4-42 過去の CR のユースケースが、毎回「廃止候補」になる（新規）
- **書く側:** `uc-agent.md:61-67`（description.md には複数の CR の UR が蓄積する、と認めている）
- **読む側:** `uc-agent.md:89-98`（今回の CRS に同じケバブ名の UR が無ければ廃止候補）・`SKILL.md:454-457`
- **起きること:** 人が「保持」を選ぶと、有効なユースケースに `status: orphaned` が付きます（`:512`。この値を読む側はいない）。「削除」を選ぶと有効な仕様が消えます（その後 A4-8 で戻る）。
- **確度:** ✅
- **重大度の案:** 🟡

### A4-43 中止した CR の最新仕様が latest-specs に残り、後の CR の close で DOCS へ昇格する（新規）
- **書く側:** 工程11（latest-specs に書く）の後に `/xddp-abort`。abort は close の途中だけを止め（`xddp-abort/SKILL.md:36-46`）、latest-specs を戻しません（VCS の revert は母体コードだけが対象。`:90`）。
- **読む側:** 後の CR の close。C0-3（`close/SKILL.md:215`）は、DOCS にある既存のファイルだけを元に戻します。C2 は latest-specs/{repo} を全部写すので（`promote.py:287-292`、対象は REPOS_KEYS 全部。`close/SKILL.md:21-23`）、中止した CR が新しく作ったモジュール・ユースケースは DOCS に昇格します。
- さらに並行 CR 保護（`mod-agent.md:129-133,176-178`・`uc-agent.md:92-97`）は「## CR クローズ」の有無で判定します。中止した CR の progress.md には「## CR 中止」（`abort:138`）しかないので、進行中とみなされ続け、廃止候補になりません。
- **確度:** ✅（両側の文面）。条件は、工程11 の後・close の前に中止した場合に限ります。
- **重大度の案:** 🟡

### A4-44 survey (c) が人の承認の前に latest-specs へ書き、承認されなかったときの扱いが無い（新規）
- **書く側:** `survey/SKILL.md:318-332`（Step 6 で mod-agent が latest-specs に書く）・`:360-362`（Step 8 で承認を待つ。却下の分岐が無い）
- **読む側:** 後の CR の close。C0-3 は DOCS にあるものだけを戻し、C2 は latest-specs/{repo} を全部写します（`promote.py:287-292`）。
- **起きること:** 人が承認しなかった survey の仕様のうち、DOCS に前の版の無いモジュールが、後の CR の close で DOCS へ昇格します。
- **確度:** 🔶（却下時の扱いが書かれていない）
- **重大度の案:** 🟡

### A4-45 survey Step 7 が、まだ書かれていない architecture.md をレビュー対象に入れる（新規。V3 の新たな食い違い1）
- **読む側:** `survey/SKILL.md:338-339`（Step 7）
- **書く側:** `:374-381`（Step 8②。Step 7 と人の承認の後）
- **起きること:** architecture.md への追記はレビューされません。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-46 precheck が latest-specs の spec.md 全体と SPO の §2 だけを比べる（新規。V3 の新たな食い違い3）
- **比べる側:** `spec_version_delta.py:203-237`
- **比べられる側:** `11_module-spec-template.md`（§1 文書概要・§7 関連ドキュメント・§8・§9 変更履歴を持つ）
- **起きること:** 行数の変化率が大きく出て、毎回「更新あり」になり得ます（V3 で 46.15% を再現）。失われるものはありません。
- **確度:** ✅
- **重大度の案:** 🔵

### A4-47 survey の衝突判定は latest-specs だけを見るが、写し先は DOCS（新規）
- **判定:** `survey/SKILL.md:295-316`（`latest-specs/{REPO_NAME}/{MODULE_KEBAB}/spec.md` の `source` を見る）
- **写し先:** `:366-371`（`{DOCS}/{REPO_NAME}/specs/{module}/` へコピー）
- **起きること:** 作業場所の latest-specs にそのモジュールが無く、DOCS には `source: spo` の版がある場合（例: close の C0-3 をまだ行っていない作業場所）、「全上書き」の確認なしに、CR 検証済みの仕様を survey の内容で上書きします。
- **確度:** ✅（両側を読んだ。起きるのは上の条件のときだけ）
- **重大度の案:** 🟡

## 4. 担当外の指摘

- **担当外（A2）:** 破壊的変更の印が AI_INDEX に出ない。`promote.py:446` はディレクトリ名（`{interface-kebab}`）を、`:1070-1076` が集めた CHD の生の名前と比べています。✅、🟡（V3 で A2 指摘#2 と重複と判定）。補足: 印が出るようになると、セルの値が `{name} ⚠️ 破壊的変更あり…` になり、`domain_refs.py:328-331` がその値をそのままパスに使うので、仕様が見つからなくなります（🔶）。
- **担当外（A2）:** 先行更新の行の範囲。`11-specs/SKILL.md:591-598` が「`promote.py` と同じ行の集合」と書いていますが、`promote.py:420-432` は全モジュールを列挙します。✅、🔵（A2 指摘#7・#8 と重複）。
- **担当外（どの領域にも属さない。specout の設定の説明）:** `xddp.config.md:341-343` の `SPECOUT_DIAGRAM_LEVEL` の節番号（6.1〜6.9）が、`module-documentation.md:233-240` の範囲（4.1〜4.7）と合いません（V3 の新たな食い違い2）。✅、🔵。
- **担当外（A5）:** `project-rulebook-cross-template.md:165` の `cross/interfaces/{name}-spec.md`（A5-26 に含まれる）。

## 5. 段階2b の候補

- **段階2b（A4-20）:** 「影響リポジトリ」を cross CHD の表から読むことになっているが、その列が無い。
  - 書く側: `06-design/SKILL.md:126-130`（列はインタフェース・変更種別・breaking）
  - 読む側: `xddp-common/SKILL.md:138-141`・`SPEC.md:31`
  - 確度: 🔶。latest-specs 側の材料の問題は A4-38 に分けた。

## 6. 前回からの変更

- **新しく足した約束:** #53〜#75（#75 は参考）
- **新しく見つけた書く側・読む側:**
  - #37 に `04-specout/SKILL.md:257,498,501`・`prelim-agent.md:32,149`・`survey/SKILL.md:213`・`survey-agent.md:25,33,57-59`・`specout-finish.md:81`・`investigate/SKILL.md:172-173`・`specout_bfs.py:1261,2668-2670`
  - #6 に `specout_bfs.py:6983,6991`
  - #10 に `specout_bfs.py:4420,7347-7350`
  - #24 に `05-arch:237`・`06-design:218`
  - #41 に `update-knowledge:35`（KNOW_DIR）
  - #62 に `xddp-status/SKILL.md:47-63`
  - #53 に document-agent
  - #54 に specout-agent
  - #66 に `xddp-abort/SKILL.md:138`
  - 前回の #35 は、#52〜#54 に分けた
- **新しい指摘:** A4-32〜A4-47
- **取り下げた指摘:** なし
- **番号を変えずに内容を直した指摘:**
  - A4-16（catalog で解決した場合の規則の欠落を補足）
  - A4-21（見出しの正規表現と、相対・絶対の未定義を補足）
  - A4-22（SKILL の本文は正しく、食い違いはテンプレートの別名だけ、と修正）
  - A4-5（行番号を `:400` に訂正）
  - A4-20 は段階2b に移した

## 7. 読んだファイルの一覧と、確認していないこと

**全文を読んだもの:**
- `CC/skills/xddp-11-specs/SKILL.md`
- `CC/agents/xddp-specs-mod-agent.md`
- `CC/agents/xddp-specs-uc-agent.md`
- `CC/skills/xddp-11-specs/scripts/spec_version_delta.py`
- `CC/skills/xddp-codemap/SKILL.md`
- `CC/skills/xddp-codemap/templates/module-catalog-template.md`
- `CC/skills/xddp-update-knowledge/templates/glossary-template.md`
- `CC/skills/xddp-common/reviewer-checklists/SPEC.md`

**範囲を読んだもの:**
- `xddp-survey/SKILL.md` 40〜434
- `xddp-survey-agent.md` 14〜68
- `xddp-close/SKILL.md` 15〜40・187〜310・398〜412
- `promote.py` 255〜540・1022〜1030（他は grep）
- `domain_refs.py` 200〜430
- `specout_bfs.py` 1255〜1265・1300〜1415・1975〜2000・2660〜2700・6940〜7010・7342〜7350（他は grep）
- `module-documentation.md` 216〜406（と見出しの一覧）
- `04_specout-summary-template.md` 30〜120（と見出し）
- `04_specout-cross-repo-template.md` 20〜70（と見出し）
- `04_specout-module-template.md` 104〜122（と見出し）
- `11_*-template.md` の全15ファイル: フロントマター・見出し・変更履歴の節。spec は 10〜40、architecture は 12〜66、deployment は 12〜20、uc-description は 12〜40、uc-sequence は 20〜32
- `xddp-common/SKILL.md` 120〜144（と grep）
- `xddp-04-specout/SKILL.md` 225〜262・295〜310・494〜521
- `specout-finish.md` 66〜90（と grep）
- `xddp-investigate/SKILL.md` 170〜185
- `ripple-run.md` 44〜54
- `xddp-specout-prelim-agent.md` 18〜40
- `xddp-specout-document-agent.md` 20〜36
- `xddp-05-arch/SKILL.md` 108〜126
- `xddp-06-design/SKILL.md` 48〜66・110〜135
- `xddp-02-analysis/SKILL.md` 95〜140
- `xddp-spec-writer-agent.md` 25〜40
- `xddp-update-knowledge/SKILL.md` 28〜40・94〜125・205〜260
- `xddp-01-init/SKILL.md` 76〜135
- `xddp.config.md` 330〜350
- `00_progress-management-template.md` 1〜80
- `xddp-status/SKILL.md` 40〜70
- `xddp-abort/SKILL.md` 36〜60
- `xddp-sync-design/SKILL.md` 132〜140
- `xddp-review/SKILL.md` 70〜100
- `artifact_lint.py` 50〜140・935〜960
- `xddp_review_brief.py` 60〜135
- `code-knowledge-boundary.md` 14〜95
- CHD テンプレート・CRS テンプレートの見出し

**grep の結果だけ見たもの:**
- `xddp-specout-agent.md`・`xddp-architect-agent.md`・`xddp-designer-agent.md`・`xddp-analyst-agent.md`
- `xddp-03-req/SKILL.md`・`collect_insights.py`・`xddp-reviewer.md`
- tests（`test_spec_version_delta.py`・`test_promote.py`・`test_domain_refs.py`）

**確認していないこと:**
- LLM（mod-agent・uc-agent・下調べ）の実際の解釈。A4-9・14〜16・33・36・38・39・41・44 は、これに依存します。
- codemap が実際に書くモジュール名・ディレクトリの値（相対か絶対か）
- スクリプト・テストの実行（行っていません。再現の記述は V3 の報告によります）
- ADR に、これらを受け入れた制限として書いた記述があるか（今回は ADR を読んでいません）
- 工程7〜10 が cross CHD を読む約束（段階2b）
- AI_INDEX の行・節の正しさ（A2 の担当）