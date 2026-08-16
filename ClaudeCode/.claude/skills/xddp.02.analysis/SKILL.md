---
description: XDDP フェーズ1: 要求分析メモを生成し、別コンテキストでAIレビュー→修正ループを実施する。「要求分析して」「ANA作って」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 02 — Requirements Analysis**.

> This step determines whether the CR solves the right problem. A missed ambiguity or misclassified requirement here cascades as a costly defect through every downstream artifact. Orchestrate with rigor.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date (YYYY-MM-DD).

(xddp.config.md lookup done in xddp.common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
DOCS_DIR, DOCS, REPOS_KEYS, IS_MULTI, CR_PROFILE.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step 0: Import Knowledge from DOCS_DIR

> **Role split with existing Step A0:**
> - Step 0 (this step): imports **approved knowledge from closed CRs** from `baseline_docs/`.
>   Targets: approved specs, finalized lessons, glossary.
> - Step A0 (existing): imports **in-progress knowledge from the current workspace** from `{XDDP_DIR}/lessons-learned.md`.
>   Filters on `#要求分析` `#仕様定義` `#見落とし` tags via the tag index (selective read, not full-file read) and passes results to analyst-agent as `LESSONS_CONTEXT`.
> Both steps read from different sources (finalized vs. in-progress) — their roles do not overlap.

1. （`DOCS_DIR`/`DOCS`/`REPOS_KEYS` は CR Resolution で取得済みのためここでの再読み取りは不要）
   If `REPOS:` is absent or empty, report error and stop.

2. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve Affected Repos" with:
     REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
   → let `AFFECTED_REPOS`.

3. **参照先パスの解決（既存知識の実体は読まない）:**
   本手順で Read するのは絞り込みの入力となる2種類のファイル
   （`{CR_PATH}/01_requirements/` 配下の変更要求書と `{DOCS}/AI_INDEX.md`）のみとする。
   絞り込んで確定した**既存知識の参照先ファイルは Read せず、パスと種別だけを収集する**
   （実体の読解は Step A で xddp-analyst-agent が行う）。

   3-0. `{CR_PATH}/01_requirements/` 配下の `.md` を Read し、以降の照合に使う
        **キーワード集合**（UR の対象語・モジュール名・機能名等）を抽出する。
        これは絞り込みの入力であり、既存知識の読解ではない（変更要求書は CR 固有の小さな文書であり、
        Step A で子エージェントも読むが、親側でも絞り込みのために必要なため重複を許容する）。

   3-1. `{DOCS}/AI_INDEX.md` が存在すれば Read する（知識ハブの目次。絞り込みの起点）。
        AI_INDEX.md 自身は分析対象の知識ではなく索引であるため、`DOMAIN_REF_PATHS` には含めない。
        存在しない場合は 3-2 のうち**索引を必要とする項目1・2・3 と項目5 のインタフェース仕様のみを
        スキップ**し、索引に依存しない項目（項目4 および項目5 の `lessons-learned.md`）は
        そのまま実施したうえで 3-1a（索引なし直接列挙）へ進む。

   3-1a. **索引なし直接列挙（`{DOCS}/AI_INDEX.md` 不在時のみ実施）:**
      索引が使えないため、3-2 の項目1・2 が対象とするディレクトリを**直接列挙**して代替する
      （`{DOCS}` 側の承認済み知識が、索引ファイル1件の欠落のみを理由に latest-specs/ への
      フォールバックへ落ちることを防ぐ）。
      a. `{DOCS}/system/specs/use-cases/*/description.md` のうち、ディレクトリ名（ユースケース名）が
         3-0 のキーワード集合と一致するもの（一致判定は 3-2 の正規化規則に従う）を収集する。
         `{DOCS}/system/specs/` 自体が存在しない場合はこの列挙を行わず、3-4 の条件表（`{DOCS}/system/specs/`
         が存在しない行）に従い latest-specs/ 側へフォールバックする。
      b. 各 `{repo}` in `AFFECTED_REPOS` の `{DOCS}/{repo}/specs/*/spec.md` のうち、
         ディレクトリ名（モジュール名）が 3-0 のキーワード集合と一致するものを収集する。
         `{DOCS}/{repo}/specs/` 自体が存在しない場合は当該 `{repo}` 分のみこの列挙を行わず、
         3-4 の条件表（`{DOCS}/{repo}/specs/` が存在しない行）に従い latest-specs/ へフォールバックする。
      c. `IS_MULTI` の場合、`{DOCS}/cross/specs/` についても b と同様に直接列挙する
         （`{DOCS}/cross/specs/` 自体が存在しない場合、本プランの対象外である cross インタフェース仕様の
         latest-specs フォールバックは変更前から未定義のため、この列挙は単に空になる＝非リグレッション）。
      d. code-knowledge インデックス（3-2 項目3）は AI_INDEX.md の当該セクションへの参照が前提のため、
         3-1a の対象外とする（索引なしでの代替収集手段は定義しない）。
      3-1a で収集したパスは取得元が `{DOCS}` であるため、手順3-3 のマッピング表で `仕様`／`ユースケース`
      として扱う（latest-specs/ 由来ではないため `DOMAIN_REF_MODE` の `degraded` 判定には寄与しない）。

   3-1b. **用語集の直接収集（`{DOCS}/AI_INDEX.md` の有無によらず常に実施）:**
      次のファイルが実在すれば、キーワード一致判定なしに無条件で収集する
      （用語集はプロジェクト・リポジトリ単位でファイル数が少なく、絞り込みの必要性が低いため）:
      a. `{DOCS}/glossary.md`
      b. 各 `{repo}` in `AFFECTED_REPOS` の `{DOCS}/{repo}/knowledge/glossary.md`
      c. `IS_MULTI` の場合: `{DOCS}/cross/knowledge/glossary.md`
      収集したパスは手順3-3 のマッピング表で種別 `用語` として扱う。

   3-2. **AI_INDEX.md を用いた絞り込み（対象の確定。いずれもパス収集のみで Read しない）:**
      1. **「ユースケース一覧」セクション**（あれば）の照合:
         3-0 のキーワード集合とユースケース名・目的列を照合し、一致したユースケースの
         `{DOCS}/system/specs/use-cases/{usecase}/description.md` を収集する
      2. **「モジュール別最新仕様」セクション**（あれば）の照合:
         上記1で一致したユースケースの「関連モジュール」列、または 3-0 のキーワード集合と
         「モジュール別最新仕様」のモジュール名を照合し、対象モジュールの
         `{DOCS}/{repo}/specs/{module}/spec.md` のみを収集する（ディレクトリ全スキャン不要）

      **照合の正規化規則（項目1・2 および 3-4 の a・b に共通）:** 比較の前に、両辺から
      区切り文字（`-` `_` 空白）と拡張子を除去し、大文字小文字を無視して突き合わせる
      （例: 要求書の `mod_a2.py` と仕様ディレクトリ名 `mod-a2` は一致とみなす）。
      完全一致が0件の場合は部分一致（いずれかが他方を含む）も一致として扱う。ただし部分一致は
      比較対象双方の正規化後の文字列が**3文字以上**の場合に限る（3文字未満の短い・汎用的な語
      （例：「値」「処理」等）による無関係な仕様の誤収集を防ぐ。完全一致には文字数制限を適用しない）。
      3. **「code-knowledge インデックス」セクション**（あれば）の照合:
         上記2で特定した対象モジュールに対応する `constraints.md` エントリを検索し、
         実在するファイルを収集する（実在しない場合はスキップ）。
         `_structures/`・`_constants/` はリポジトリ横断のモジュール間知識（構造体関連図・共有定数）
         のため、対象モジュールの種別に関わらず、インデックスにエントリが存在すれば実在するファイルを
         全件収集する（実在しない場合はスキップ）
      4. 各 `{repo}` in `AFFECTED_REPOS` の `{DOCS}/{repo}/knowledge/lessons-learned.md`
         を実在すれば収集する
      5. `IS_MULTI` の場合: AI_INDEX.md の「クロスインタフェース一覧」セクションで絞り込んだ
         `{DOCS}/cross/specs/` 配下のインタフェース仕様と、`{DOCS}/cross/knowledge/lessons-learned.md`
         を実在すれば収集する

   3-3. **取得元 → 種別のマッピング（本表を種別値の単一情報源とする）:**

      | 取得元 | 種別 |
      |---|---|
      | `{DOCS}/system/specs/use-cases/{usecase}/description.md` | `ユースケース` |
      | `{DOCS}/{repo}/specs/{module}/spec.md`／`{DOCS}/cross/specs/` 配下 | `仕様` |
      | `{DOCS}/{repo}/knowledge/lessons-learned.md`／`{DOCS}/cross/knowledge/lessons-learned.md` | `知見` |
      | code-knowledge の `constraints.md` | `制約` |
      | code-knowledge の `_structures/` 配下 | `共有構造体` |
      | code-knowledge の `_constants/` 配下 | `共有定数` |
      | フォールバック（3-4）の `latest-specs/{repo}/{module}/spec.md` | `仕様` |
      | フォールバック（3-4）の `latest-specs/system/use-cases/{usecase}/description.md` | `ユースケース` |
      | `{DOCS}/glossary.md`／`{DOCS}/{repo}/knowledge/glossary.md`／`{DOCS}/cross/knowledge/glossary.md`（3-1b） | `用語` |

   3-4. **フォールバック列挙（`{DOCS}` 側の該当ディレクトリ自体が存在しない場合）:**
      次の条件に該当する場合、**該当する列挙のみ**を `{WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/` から
      行う（`{DOCS}` から解決できた分はそのまま残す＝取得元の混在を許容する）。
      条件と列挙の対応は次のとおりで、`{DOCS}` 側で既に収集できたものは重複して収集しない:

      | 条件 | 実施する列挙 |
      |---|---|
      | `{DOCS}/{repo}/specs/` が存在しない（当該 `{repo}` のみ） | a（当該 `{repo}` 分のみ） |
      | `{DOCS}/system/specs/` が存在しない | b |

      > **`{DOCS}/AI_INDEX.md` の不在は本表の条件ではない。** 索引のみが欠落し `{DOCS}/{repo}/specs/`・
      > `{DOCS}/system/specs/` 自体は存在する場合は 3-1a（索引なし直接列挙）で `{DOCS}` 側から
      > 直接収集し、latest-specs/ へはフォールバックしない（`{DOCS}` 側が整備済みにもかかわらず
      > 未昇格の latest-specs/ を参照し ANA §0 に事実と異なる degraded 注記が出る事故を防ぐため）。
      > 本表が適用されるのは `{DOCS}` 側の当該ディレクトリ自体が存在しない場合のみである。

      索引が使えないため、列挙は次の要領で行う:
      a. `{WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/{repo}/*/spec.md` のうち、
         ディレクトリ名（モジュール名）が 3-0 のキーワード集合と一致するもの
         （一致判定は 3-2 の正規化規則に従う）
      b. `{WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/system/use-cases/*/description.md` のうち、
         ディレクトリ名が 3-0 のキーワード集合と一致するもの（同上）
      c. **実施した列挙**について一致0件で、かつ対象ディレクトリが実在する場合は、
         更新日時の新しい順に **その列挙につき最大3件まで** を収集する
         （全スキャンによるコンテキスト膨張を避けるための上限。実施していない列挙には適用しない）。
         本補完はキーワード一致に基づかない（更新日時のみを根拠とする）ため関連性が低い可能性がある。
         エージェント手順10 の「関係が見出せなかった場合は『今回の要求との直接の関係なし』」という
         既存の安全弁がこの観点でも機能するため、本件のための追加の変数・記録機構は導入しない

   3-5. **パス形式:** `DOMAIN_REF_PATHS` の各要素は**絶対パス**とする。
      `{DOCS}` は `{WORKSPACE_ROOT}/{DOCS_DIR}` として既に絶対だが、`{XDDP_DIR}` は
      ワークスペースルート相対のため、フォールバック分は `{WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/...`
      と絶対化してから格納する。子エージェントは Read で解決するため相対パスを渡してはならない。

   3-6. **区切り文字の混入防止:** 収集した要素の**絶対パスまたは種別**に区切り文字
      `|`（種別区切り）または `;`（要素区切り）が含まれる場合、その要素は `DOMAIN_REF_PATHS` へ
      含めず除外する（`{DOCS}` 配下のファイル・ディレクトリ名は母体コード側の既存資産に由来し
      うるため、区切り文字が含まれないことを無条件には仮定できない）。除外は個別の記録・報告を
      要しない軽量なガードとする（想定発生頻度が極めて低いため）。

4. 収集した結果を以下の2変数に格納する。ANA への記録は Step A で xddp-analyst-agent が行う
   （本スキルは記録しない。Step 0 実行時点で ANA ファイルは未生成のため）。

   Let `DOMAIN_REF_PATHS` = 収集した参照先の**絶対パス**のリスト。各要素は
   `{絶対パス} | {種別}` 形式とし、種別は手順3-3 のマッピング表で確定した値をそのまま用いる。
   下流へ渡す際は要素を ` ; `（セミコロン）で連結した**1行の文字列**とする。

   Let `DOMAIN_REF_MODE` = 次の順で判定する（先に該当したものを採る）:
   - `none`: `DOMAIN_REF_PATHS` が空（`{DOCS}` も `latest-specs/` も存在しない、
     または照合結果が0件）
   - `degraded`: 1件以上が `{XDDP_DIR}/latest-specs/` 由来である
     （`{DOCS}` 由来と混在する場合も `degraded` とする＝一部でも昇格未完了なら degraded）
   - `normal`: 上記以外（全件が `{DOCS}` 由来）

## Step 0.5: Mark In-Progress
Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 2, STATE: 🔄 進行中, DETAIL_STEP: `Step A: ANA生成中`

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Snapshot Phase Baseline" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 2

## Step A0: Reference Lessons Learned Log

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Lessons Context" with:
  LESSONS_FILE: {XDDP_DIR}/lessons-learned.md
  TARGET_TAGS: [#要求分析, #仕様定義, #見落とし]
→ let `LESSONS_CONTEXT`.

## Step A0.5: Load Domain Constraints

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Domain Constraints" with:
  XDDP_DIR: {XDDP_DIR}
→ let `DOMAIN_CONSTRAINTS`.

Let `CLASSIFICATION_TASK` =
  In section "2. 要求レベル分類", process each UR in the requirements as follows:
  1. Transcribe the original text.
  2. Classify as UR / SR / SP:
     - UR: what the user wants to do (abstract, user perspective) → "〜したい" form
     - SR: what the system must do (behavior/constraint) → "〜のとき、〜して、〜する" form
     - SP: concrete spec (expressible as Before/After) → "〜を〜する" form
  3. Describe the classification rationale.
  4. Generate a CRS-ready expression (in the format matching the classification).
  5. Generate a rationale sentence for the CRS "理由" field (〜なので / 〜のため).
（`CR_PROFILE` にも `{repo}` にも依存しないため、下記 Step A-profile（quick）と Step A（full）の
両方からこの1箇所の定義をそのまま参照する）

## Step A-profile: CR_PROFILE Branch

If `CR_PROFILE` = `quick`:
  1. Read `~/.claude/skills/xddp.02.analysis/templates/02_req-analysis-memo-template.md`
     （テンプレート存在確認のフェイルファストプリチェック。読み取り内容は変数に捕捉せず、ファイル不在時は
     Read 自体のエラーで停止する）。
  2. Use the **Agent tool** with `subagent_type=xddp-analyst-agent` and pass:
       ```
       CR_NUMBER: {CR}
       REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
       TEMPLATE_FILE: ~/.claude/skills/xddp.02.analysis/templates/02_req-analysis-memo-template.md
       OUTPUT_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
       TODAY: {TODAY}
       （LESSONS_CONTEXT が空でない場合のみ追加）LESSONS_CONTEXT: {LESSONS_CONTEXT}
       DOMAIN_REF_MODE: {DOMAIN_REF_MODE}
       （DOMAIN_REF_PATHS が空でない場合のみ追加）DOMAIN_REF_PATHS: {各要素を ` ; ` で連結した1行}
       （DOMAIN_CONSTRAINTS が空でない場合のみ追加）DOMAIN_CONSTRAINTS: |
         {DOMAIN_CONSTRAINTS}
       CLASSIFICATION_TASK: |
         {pass CLASSIFICATION_TASK content as-is}
       QUICK_PROFILE: `true`
       ```
     → generates `{CR_PATH}/02_analysis/ANA-{CR}.md`（軽量 ANA。出力範囲は `xddp-analyst-agent.md` の
     `QUICK_PROFILE` 定義に従う）。
  3. Wait for the agent to complete and confirm the file was created.
  4. Resolve Glossary Paths for the spec-writer:
       Let `GLOSSARY_PATHS` = 次の候補パスのうち実在するファイルの絶対パスを ` ; ` で連結した1行:
         - `{DOCS}/glossary.md`
         - For each `{repo}` in `AFFECTED_REPOS`: `{DOCS}/{repo}/knowledge/glossary.md`
         - If `IS_MULTI`: `{DOCS}/cross/knowledge/glossary.md`
       該当ファイルが1件もない場合、`GLOSSARY_PATHS` は空文字列とする。
       （`AFFECTED_REPOS` は Step 0 手順2 で解決済みの値をそのまま用いる）
  5. Use the **Agent tool** with `subagent_type=xddp-spec-writer-agent` and pass `MODE: create`:
       ```
       CR_NUMBER: {CR}
       MODE: create
       REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
       ANA_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
       CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
       TEMPLATE_FILE: ~/.claude/skills/xddp.03.req/templates/03_change-req-spec-template.md
       DEVELOPMENT_MODE: {DEVELOPMENT_MODE}
       （GLOSSARY_PATHS が空でない場合のみ追加）GLOSSARY_PATHS: {GLOSSARY_PATHS}
       TODAY: {TODAY}
       AUTHOR_NOTE: quick profile 統合生成
       QUICK_PROFILE: `true`
       ```
     → generates `{CR_PATH}/03_change-requirements/CRS-{CR}.md`（軽量 CRS）。
  6. Run `artifact_lint.py --doc-type CRS` on the generated CRS file
     （生成直後のフェイルファスト構造チェック。後段のレビューループでも同じ lint が毎ラウンド実行
     されるが、目的が異なるため二重実行ではない — 本手順は生成エージェント自体の構造バグを
     レビューラウンドに進む前に検出するゲート、後段はレビュアーへ検査結果を渡すためのもの）:
       `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/artifact_lint.py --file {CR_PATH}/03_change-requirements/CRS-{CR}.md --doc-type CRS`
     → let `LINT_RESULTS`（stdout の JSON 1オブジェクト）。
     If any element of `LINT_RESULTS.crs.issues` has `"level": "error"`: report the errors to the user and stop
     （fixer を介さず即座に停止する。`LINT_RESULTS.ok` は常に `true` を返すフィールドのため判定に
     使わない。実際の構造検査結果は `LINT_RESULTS.crs.issues` 配列の `"level": "error"` 要素の有無で
     判定する）。
  7. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
       CR_PATH: {CR_PATH}, STEP_NUM: 2, STATE: 🔄 進行中, DETAIL_STEP: `Step A-profile: AIレビュー中（quick、最大1ラウンド）`
  7b. Resolve the next document type:
       If `DEVELOPMENT_MODE` = `new`: Let `CRS_NEXT_DOCUMENT_TYPE` = `CHD`
         （`new` では工程4が `xddp.04.specout/SKILL.md` の「## Step -1: DEVELOPMENT_MODE Check」で
         即座にスキップされ、quick では同じ Step -1 が工程5のスキップも記録して `/xddp.06.design` を
         案内する。この経路では CRS を実際に受け取るのは CHD である）。
       Else: Let `CRS_NEXT_DOCUMENT_TYPE` = `SPO`（工程4が実行されるため）。
  8. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
       DOCUMENT_TYPE: CRS
       NEXT_DOCUMENT_TYPE: {CRS_NEXT_DOCUMENT_TYPE}
       CONFIG_KEY: REVIEW_MAX_ROUNDS.CRS
       MAX_ROUNDS_OVERRIDE: `1`
       TARGET_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
       REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md), {CR_PATH}/02_analysis/ANA-{CR}.md]
       REVIEW_OUTPUT_FILE: {CR_PATH}/03_change-requirements/review/03_change-requirements-review.md
       FIXER_AGENT: xddp-spec-writer-agent
       FIXER_PARAMS:
         CR_NUMBER: {CR}
         MODE: fix
         CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
         REVIEW_FILE: {CR_PATH}/03_change-requirements/review/03_change-requirements-review.md
         TODAY: {TODAY}
         AUTHOR_NOTE: レビュー指摘修正（quick, round {round}）
         QUICK_PROFILE: `true`
       PROGRESS_CR_PATH: {CR_PATH}
       PROGRESS_STEP_NUM: 2
       EXTRA_REVIEWER_PARAMS:
         QUICK_PROFILE: `true`
  9. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Regenerate CRS Excel" with:
       CR_PATH: {CR_PATH}
       CR: {CR}
  10. 実ファイルの「## Step B3: Extract project-rulebook Candidates」の手順をそのまま実行する
     （Step B3 は要求書から命名規約・ADR・禁止事項・ドメイン制約を抽出して project-rulebook.md へ
     蓄積する知識ベース更新処理であり、quick でも省略しない。CRS レビュー完了後・progress.md 更新前の
     本手順の位置で実行する）。
  11. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
       CR_PATH: {CR_PATH}, STEP_NUM: 2, STATE: ✅ 完了, DETAIL_STEP: `-`,
       ARTIFACT_LINK: `[ANA-{CR}.md](02_analysis/ANA-{CR}.md)`
  12. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
       CR_PATH: {CR_PATH}, STEP_NUM: 3, STATE: ⏭️ スキップ（工程2に統合）, DETAIL_STEP: `-`,
       ARTIFACT_LINK: `[CRS-{CR}.md](03_change-requirements/CRS-{CR}.md)`
  12b. Set next command → `/xddp.04.specout {CR}`
       （`DEVELOPMENT_MODE` によらず `/xddp.04.specout` を案内する。`new` の場合はそこで工程4a・4b・5の
       スキップが記録され `/xddp.06.design` へ案内が連鎖する）
  13. Tell the user:
     > `CR_PROFILE: quick` のため、工程2で軽量 ANA と CRS を統合生成し、CRS へ1ラウンドのAIレビューを実施しました。
     > **次のコマンド:** `/xddp.04.specout {CR}`
  14. Stop（実ファイルの Step A・Step B・Step B2・Step C・Step D には到達しない。Step B3 のみ上記
     手順10として quick パスからも実行する）。

Else（`CR_PROFILE` = `full`）:
  下記の Step A 以降にそのまま進む。

## Step A: Generate Analysis Memo

Use the **Agent tool** with `subagent_type=xddp-analyst-agent` and pass:
```
CR_NUMBER: {CR}
REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
TEMPLATE_FILE: ~/.claude/skills/xddp.02.analysis/templates/02_req-analysis-memo-template.md
OUTPUT_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
TODAY: {TODAY}
（LESSONS_CONTEXT が空でない場合のみ追加）LESSONS_CONTEXT: {LESSONS_CONTEXT}
DOMAIN_REF_MODE: {DOMAIN_REF_MODE}
（DOMAIN_REF_PATHS が空でない場合のみ追加）DOMAIN_REF_PATHS: {各要素を ` ; ` で連結した1行}
（DOMAIN_CONSTRAINTS が空でない場合のみ追加）DOMAIN_CONSTRAINTS: |
  {DOMAIN_CONSTRAINTS}
CLASSIFICATION_TASK: |
  {pass CLASSIFICATION_TASK content as-is}
```

Wait for the agent to complete and confirm the file was created.

## Step B: Review Loop

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 2, STATE: 🔄 進行中, DETAIL_STEP: `Step B: AIレビュー中`

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: ANA
  NEXT_DOCUMENT_TYPE: CRS
  CONFIG_KEY: REVIEW_MAX_ROUNDS.ANA
  TARGET_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md files)]
  REVIEW_OUTPUT_FILE: {CR_PATH}/02_analysis/review/02_analysis-review.md
  FIXER_AGENT: xddp-analyst-agent
  FIXER_PARAMS:
    CR_NUMBER: {CR}
    REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
    OUTPUT_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
    REVIEW_FILE: {CR_PATH}/02_analysis/review/02_analysis-review.md
    TODAY: {TODAY}
    DOMAIN_REF_MODE: {DOMAIN_REF_MODE}
    （DOMAIN_REF_PATHS が空でない場合のみ追加）DOMAIN_REF_PATHS: {各要素を ` ; ` で連結した1行}
  PROGRESS_CR_PATH: {CR_PATH}
  PROGRESS_STEP_NUM: 2

## Step B2: Human Review Gate

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Human Review Gate" with:
  CR_PATH: {CR_PATH}
  STEP_NUM: 2
  STEP_LABEL: `Step B2`
  ARTIFACTS_TEXT: |
    - 成果物: `{CR_PATH}/02_analysis/ANA-{CR}.md`
    - AIレビュー結果: `{CR_PATH}/02_analysis/review/02_analysis-review.md`
  REVISE_COMMAND: `/xddp.revise {CR} analysis`
→ let `CHANGED`.

If `CHANGED`:
Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Final Review Pass" with:
  DOCUMENT_TYPE: ANA
  NEXT_DOCUMENT_TYPE: CRS
  TARGET_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md files)]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR_PATH}/02_analysis/review/02_analysis-review.md

## Step B3: Extract project-rulebook Candidates

> **Timing:** Run after Step B2 (human review gate) is confirmed, before Step C (progress.md update).
> If Step B2 had changes, wait for the final AI review pass to complete before this step.
>
> ⚠️ **並行 CR がある場合は xddp.02.analysis の Step B3 を逐次実行してください。**
> 複数の CR が同時に Step B3 を実行すると `project-rulebook.md` の同一ファイルに競合する可能性があります。
> 並行 CR が進行中の場合は、他 CR の Step B3 完了後に本 CR の Step B3 を実行してください。

1. Check whether `{XDDP_DIR}/project-rulebook.md` exists.
   - If not found: tell the user "project-rulebook.md が見つかりませんでした（`{XDDP_DIR}/project-rulebook.md`）。
     `/xddp.01.init` を実行してファイルを生成してから再度お試しください。今回はスキップします。"
     and skip this step.

2. **Idempotency check:** check whether the "## 7. 変更履歴" section in project-rulebook.md already has an entry for {CR} (a row containing {CR}).
   If found: tell the user "{CR} のエントリが変更履歴に見つかりました。Step B3 をスキップします。" and skip this step.

   > **Per-repo steerings:** Candidates that are clearly specific to a single repository (e.g., naming rule for a specific module in one repo) should be noted as `→ project-rulebook-{repo}.md へ追記推奨` in the candidate list. The actual per-repo steering updates are done in xddp.close Step C3.5.

3. Read all `.md` files under `{CR_PATH}/01_requirements/`.

4. Extract items matching the following categories from the requirements and build a candidate list.
   **Identify the target heading in project-rulebook.md by heading name (not section number).**

   | Category | Example items to extract (cross-cutting only, not CR-specific) | Target heading in project-rulebook |
   |---|---|---|
   | Naming conventions | "Unify to 〇〇 naming", "Naming rule is 〇〇" | `## 2. 命名規約` |
   | Architecture decisions | "Adopt 〇〇 pattern", "Migrate to 〇〇 approach" | `## 3. アーキテクチャ決定記録（ADR）` |
   | Prohibitions | "〇〇 is prohibited", "Must not use 〇〇" | `## 5. 禁止事項・注意事項` |
   | Cross-cutting patterns | Error handling policy, async policy, logging policy, etc. — patterns applied codebase-wide.<br>**Exclude: implementation approach for a specific feature, or CR-specific procedures.** | `## 4. 既存パターン・慣習` |
   | ドメイン制約 | 「〇〇規格に準拠すること」「〇〇の上限は〇〇」など、**外部由来で CR 横断的に効く制約**。<br>**除外: 今回の CR だけで有効な数値・条件。** | `## 1.6 ドメイン制約` |

5. If 0 candidates: skip this step (report nothing).

6. If 1 or more candidates: present them to the user in the following format.
   Assign each candidate a unique label `{CategoryName}-{N}`.

   ```
   📋 project-rulebook.md への追記候補が見つかりました。

   [禁止事項-1]
   根拠（req より）: 「〇〇ライブラリは使用禁止とする」
   追記先: ## 5. 禁止事項・注意事項
   追記案（コードブロック内末尾に追加）:
     ❌ 〇〇ライブラリの使用禁止（{CR} より）

   [命名規約-1]
   根拠（req より）: 「APIエンドポイントは /kebab-case/{id} に統一する」
   追記先: ## 2. 命名規約
   追記案（コードブロック内末尾に追加）:
     # APIエンドポイント: /kebab-case/{id}（{CR} より）

   [ドメイン制約-1]
   根拠（req より）: 「〇〇規格 XYZ-123 に準拠すること」
   追記先: ## 1.6 ドメイン制約
   追記案（テーブル行として追加）:
     | 準拠すべき規格・法令 | 〇〇規格 XYZ-123 に準拠する | XYZ-123 | 〇〇に関する要求全般 |

   上記を project-rulebook.md に追記しますか？
   ラベル名で指定してください（例: 「すべて追記」「禁止事項-1 のみ追記」「スキップ」）。
   ```

7. Process the user's response:
   - "すべて追記" → append all candidates to the relevant heading's code block (or ADR heading format)
   - "{ラベル名} のみ追記" → append only the specified candidate(s)
   - "スキップ" → do nothing, proceed to next step

   **Append format rules:**
   - `## 2. 命名規約`, `## 4. 既存パターン・慣習`, `## 5. 禁止事項・注意事項`: append inside the existing code block (``` ``` ```) at the end
   - `## 3. アーキテクチャ決定記録（ADR）`: append outside code blocks as a `### ADR-NNN: {title}` heading
     (ADR number = existing max + 1)
   - `## 1.6 ドメイン制約`: append as a new row to the existing table
     （列: 種別 / 制約内容 / 根拠 / 影響する要求の観点）。種別列には project-rulebook-template.md §1.6
     で事前定義された6種別（準拠すべき規格・法令／安全性・信頼性の要件／性能・リソースの下限／上限／
     データの取り扱い制約／互換性の維持義務／運用・保守上の制約）のうち、制約内容に最も適合するものを
     選択する。根拠が req 原文から明確に読み取れない場合は根拠列に「未確認」と記載する
     （project-rulebook-template.md §1.6 の記入時の注意に合わせる）

8. If any items were appended, add an entry to **`## 7. 変更履歴`** in project-rulebook.md:
   ```
   | {TODAY} | {CR} | {categories appended and counts, e.g., 禁止事項1件・命名規約1件}（req より抽出） |
   ```

## Step C: Update progress.md
Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 2, STATE: ✅ 完了, DETAIL_STEP: `-`,
  ARTIFACT_LINK: `[ANA-{CR}.md](02_analysis/ANA-{CR}.md)`
Set next command → `/xddp.03.req {CR}`.

## Step D: Report in Japanese
Summary: review rounds completed, final issue count, next command.
