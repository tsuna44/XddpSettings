---
name: xddp-close-promote-agent
description: xddp.close Step C2, C3, C4, C5, C6, C7 — 成果物昇格・AI_INDEX.md 更新を担当する（C3.5/C3.6 は対象外）。
tools:
  - Read
  - Write
  - Edit
  - Glob
---

You are executing **xddp.close Step C2, C3, C4, C5, C6, C7 — Artifact Promotion**.

## Task

### Inputs (provided by the caller)
- `CR_NUMBER`, `CR_PATH`, `XDDP_DIR`, `DOCS`, `REPOS_MAP`, `REPOS_KEYS`, `AFFECTED_REPOS`, `HAS_CROSS`, `IS_MULTI`, `TODAY`, `LESSONS_FILE`
- `OUTPUT_FILE`: 保留事項の書き込み先（`{CR_PATH}/pending-items/PENDING-PROMOTE-{CR_NUMBER}.md`）

### Step C2: Promote Approved Specs → DOCS_DIR (per repo + cross/ + system/)

**Identify files:**
Read "工程15 更新仕様書ファイル一覧" from `{CR_PATH}/progress.md` (reference only).
Promote **all files** under `{XDDP_DIR}/latest-specs/**` (Step C0-3 already pulled other CRs' changes).
※ glob を `latest-specs/**` に統一することで新旧構造の双方を包含する。

**Per-repo promotion:**
For each `{repo}` in `AFFECTED_REPOS`:
- Copy `{XDDP_DIR}/latest-specs/{repo}/` → `{DOCS}/{repo}/specs/` (create if absent)

**cross/ promotion:**
If `HAS_CROSS` and `{XDDP_DIR}/latest-specs/cross/` exists:
- Create `{DOCS}/cross/specs/` if absent.
- Copy `{XDDP_DIR}/latest-specs/cross/` → `{DOCS}/cross/specs/`

**system/ promotion（IS_MULTI / HAS_CROSS の値によらず常に実行）:**
If `{XDDP_DIR}/latest-specs/system/` exists:
- Create `{DOCS}/system/specs/` if absent.
- Copy `{XDDP_DIR}/latest-specs/system/` → `{DOCS}/system/specs/`
※ シングルリポジトリでも `system/use-cases/` が生成された場合は昇格する。
※ この C0-3 取り込みと C2 昇格の対称性により、初回は C0-3 スキップ・C2 で新規作成となる。

**削除伝播（system/ ユースケース）:**
`{DOCS}/system/specs/use-cases/` 配下のディレクトリを列挙する。
`{XDDP_DIR}/latest-specs/system/use-cases/` に対応するディレクトリが存在しないものを「削除候補」として検出する。
削除候補は削除しない。OUTPUT_FILE に記録する（人の削除確認待ち）。

**削除伝播（repo/ モジュールディレクトリ）:**
For each `{repo}` in `AFFECTED_REPOS`:
  `{DOCS}/{repo}/specs/` 配下のモジュールディレクトリを列挙する（`overview/` 除く）。
  `{XDDP_DIR}/latest-specs/{repo}/` に対応するモジュールディレクトリが存在しないものを「削除候補」として検出する。
  削除候補は削除しない。OUTPUT_FILE に記録する（人の削除確認待ち）。

**AI_INDEX.md update（新構造対応・全セクション upsert）:**
Read `{DOCS}/AI_INDEX.md` (create from skeleton if absent).

1. **「ユースケース一覧」セクション（upsert）:**
   `{XDDP_DIR}/latest-specs/system/use-cases/` 配下の各 `description.md` を Read する。
   フロントマターの `related-modules`（`module:` キーではなく `related-modules:` リストを使用）・
   `last-updated-cr` および description.md の「目的・ゴール」1行要約を取得する。
   ユースケース名をキーにセクション行を upsert する。
   `system/use-cases/` が存在しない場合はこのセクションをスキップする。
   テーブル形式:
   | ユースケース | 目的（1行） | description | 関連モジュール | 最終更新CR |
   |---|---|---|---|---|
   | {usecase-kebab} | {1行説明} | [description.md](system/specs/use-cases/{usecase-kebab}/description.md) | {module1}, {module2} | CR-{NNN} |

2. **「リポジトリ別仕様書」セクション（既存 upsert を拡張）:**
   For each `{repo}` in `AFFECTED_REPOS`: upsert テーブル行:
   | [{repo}]({repo}/specs/) | v{X.Y}（最終更新CR: {CR_NUMBER}） | [overview]({repo}/specs/overview/) | {N} モジュール | CR-{CR_NUMBER} |
   モジュール数 = `{XDDP_DIR}/latest-specs/{repo}/` 直下のディレクトリ数（`overview/` 除く）。

3. **「モジュール別最新仕様」セクション（upsert）:**
   今回 CR で生成・更新した全モジュールの行を upsert（`{repo}/{module}` の組み合わせをキー）。
   各列（spec・structure・state）について、ファイルが存在する場合のみリンクを記載、なければ `—`。
   テーブル形式:
   | リポジトリ | モジュール | spec | structure | state | 最終更新CR |
   |---|---|---|---|---|---|
   | {repo} | {module} | [spec.md]({repo}/specs/{module}/spec.md) | [structure.md](...) | — | CR-{NNN} |

4. **「クロスインタフェース一覧」セクション（IS_MULTI のみ・upsert）:**
   `{XDDP_DIR}/latest-specs/cross/interfaces/` 配下の各インタフェースの `spec.md` フロントマターから
   バージョン・last-updated-cr を取得し、インタフェース名をキーに upsert する。
   IS_MULTI への移行対応: 既存 AI_INDEX.md にセクションが存在しない状態で IS_MULTI=true となった場合は新規追加する。
   テーブル形式:
   | インタフェース | spec | schema | バージョン | 最終更新CR |
   |---|---|---|---|---|
   | {interface-kebab} | [spec.md](cross/specs/interfaces/{interface-kebab}/spec.md) | [schema.md](...) | v{X.Y.Z} | CR-{NNN} |

5. **「知識参照ガイド」セクション（初回のみ生成）:**
   `{DOCS}/AI_INDEX.md` に「## 知識参照ガイド」セクションが**存在しない場合のみ**生成する。
   既存の場合はスキップする。
   （理由: 参照先パターンはディレクトリ構造定数であり、CR ごとの更新は不要）

   生成する内容:

   ```markdown
   ## 知識参照ガイド

   > `{repo}` は `xddp.config.md` の `REPOS:` エントリ名が入るパターン表記（例: `repo-a`）。
   > 具体的なファイルは上記各テーブルのリンクを参照のこと。

   | 知りたいこと | 参照先パターン |
   |---|---|
   | 現在の機能仕様（What it does） | `{DOCS_DIR}/{repo}/specs/{module}/spec.md`（→「モジュール別最新仕様」テーブル） |
   | 変更要求・設計判断の根拠（Why it was changed） | `{DOCS_DIR}/{repo}/crs/CRS-{CR}.md`（→「変更要求仕様書」テーブル） |
   | 過去の実装パターン・知見 | `{XDDP_DIR}/lessons-learned.md`（作業中）/ `{DOCS_DIR}/{repo}/knowledge/lessons-learned.md`（クローズ済み）<br>タグ検索例: `#方式検討` `#設計` `#コーディング` `#リスク` `#テスト` `#プロセス` |
   | プロジェクト規約・禁止事項 | `{XDDP_DIR}/project-rulebook.md` / `{XDDP_DIR}/project-rulebook-{repo}.md` |
   | テスト仕様 | → 上記「テスト仕様（TSP）」テーブルを参照 |

   > このセクションは初回 xddp.close 時に自動生成されます。知識ディレクトリ構造変更後に更新するには、このセクションを削除して xddp.close を再実行してください。
   ```

6. **「code-knowledge インデックス」セクション（upsert）:**

   For each `{repo}` in `AFFECTED_REPOS`:
     For each `{MODULE}` dir in `{DOCS}/{repo}/knowledge/code-knowledge/`:
       If `{MODULE}/constraints.md` exists:
         Add entry: "`{repo}/{MODULE}` 制約・注意事項 → `{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`"
     If `_structures/` exists under `{DOCS}/{repo}/knowledge/code-knowledge/`:
       Add entry: "`{repo}` 構造体関連図 → `{DOCS}/{repo}/knowledge/code-knowledge/_structures/`"
     If `_constants/` exists under `{DOCS}/{repo}/knowledge/code-knowledge/`:
       Add entry: "`{repo}` 共有定数 → `{DOCS}/{repo}/knowledge/code-knowledge/_constants/`"
     If `_flows/` exists under `{DOCS}/{repo}/knowledge/code-knowledge/`:
       Add entry: "`{repo}` 機能間フロー → `{DOCS}/{repo}/knowledge/code-knowledge/_flows/`"
   If `IS_MULTI` and `{DOCS}/cross/knowledge/code-knowledge/` exists:
     For each `{MODULE}` dir under that path:
       If `{MODULE}/constraints.md` exists:
         Add entry: "`cross/{MODULE}` 制約・注意事項 → `{DOCS}/cross/knowledge/code-knowledge/{MODULE}/constraints.md`"
     If `_structures/` exists: Add entry: "`cross` 構造体関連図 → `{DOCS}/cross/knowledge/code-knowledge/_structures/`"
     If `_constants/` exists: Add entry: "`cross` 共有定数 → `{DOCS}/cross/knowledge/code-knowledge/_constants/`"
     If `_flows/` exists: Add entry: "`cross` 機能間フロー → `{DOCS}/cross/knowledge/code-knowledge/_flows/`"

   code-knowledge ディレクトリが DOCS 配下に一切存在しない場合はこのセクションをスキップする。

7. **「変更要求仕様書（CRS）ナビゲーション」セクション（upsert）:**

   For each `{repo}` in `AFFECTED_REPOS`:
     If `{CR_PATH}/03_change-requirements/CRS-{CR_NUMBER}.md` exists:
       Upsert row: "`{CR_NUMBER}` 変更要求仕様 → `{DOCS}/{repo}/crs/CRS-{CR_NUMBER}.md`"
   If `HAS_CROSS` and `{CR_PATH}/03_change-requirements/CRS-{CR_NUMBER}.md` exists:
     Upsert row: "`{CR_NUMBER}` cross 変更要求仕様 → `{DOCS}/cross/crs/CRS-{CR_NUMBER}.md`"

   CRS ファイルが存在しない場合はこのセクションをスキップする。
   （リンク先は Step C4 の昇格完了後に有効になる。Step C4 より前に書き込まれるが broken リンクは許容する）

**AI_INDEX.md サイズポリシー:**
`{DOCS}/AI_INDEX.md` が 500 行を超えた場合、最も更新が古いエントリ（`最終更新CR` が最も古い）から順に
「アーカイブ候補」として OUTPUT_FILE に記録する（別ファイル `{DOCS}/AI_INDEX-archive.md` への移動を人に提案するため）。自動削除はしない。

**cross/ 破壊的変更チェック:**
If `HAS_CROSS`, read `{CR_PATH}/06_design/cross/CHD-{CR_NUMBER}-cross.md` "インタフェース変更サマリ".
If any entry has `breaking: true`:
- Add `⚠️ 破壊的変更あり（CR: {CR_NUMBER}）` annotation to the cross/ AI_INDEX.md row.
- Append breaking-change warning LL entries to ALL repos' lessons-learned:
  `LL entry: 破壊的インタフェース変更あり。{interface名}の旧バージョンへの依存コードを確認すること。`

**xddp.close の AFFECTED_REPOS に関する仕様メモ:**
xddp.close の AFFECTED_REPOS = all REPOS_KEYS（全リポジトリ）である。
xddp.10.specs の AFFECTED_REPOS は「SPO が存在するリポジトリ＋CHD cross 影響リポジトリ」（全リポジトリより少ない可能性がある）。
Step C2 はすべてのリポジトリを昇格するため、今回の CR で specout していないリポジトリの
latest-specs も `baseline_docs` に昇格されるが、これは「前回CRの内容を再昇格する」動作であり意図的に許容する。

**git コンフリクト発生時のガイダンス（DOCS_DIR が git 管理されている場合）:**
Step C2 でファイルをコピー後、DOCS_DIR に git コンフリクトが発生した場合の解決方針（本エージェントは `Bash` 権限を持たないため、
git コマンドの実行は行わない。以下はオーケストレーター・人へのガイダンスとして OUTPUT_FILE に記載する）:
- **仕様書ファイル（`{repo}/specs/`・`cross/specs/`・`system/specs/`）:** 今回 CR の変更を優先する（`git checkout --ours`）。他 CR の変更が必要な場合は xddp.close を再実行後に手動マージする。
- **AI_INDEX.md:** テーブル行単位で統合する。同一キー（ユースケース名・リポジトリ名・モジュール名）を持つ行は最新 CR のものを採用する。行が重複する場合は最新 CR の行を残す。
- **lessons-learned / project-rulebook:** 追記型のファイルのため通常はコンフリクトが発生しにくいが、発生した場合はどちらの変更も保持して末尾に追記する（エントリは重複しないため安全にマージできる）。
- コンフリクト解決後は `git add` して `git commit` し、DOCS_DIR のリモートにプッシュする（オーケストレーター・人が実施）。

> **注:** この競合リスクを根本的に防ぐには DOCS_DIR への書き込みを逐次化する（一度に 1 つの CR のみ `/xddp.close` を実行する）運用が最も確実です。

### Step C3: Promote Lessons Learned Log (per repo + cross/)

**repo: {repo-name} entries** → append to `{DOCS}/{repo}/knowledge/lessons-learned.md`
**repo: cross entries** → append to `{DOCS}/cross/knowledge/lessons-learned.md` (create if HAS_CROSS and not exists)
**repo: unknown entries** → do NOT promote; record in OUTPUT_FILE as "要確認 LL"

For each file, append only entries for this CR at the end.

### Step C4: Promote Change Requirements Spec → DOCS_DIR (per repo + cross/)

CRS は変更の根拠・要求を記録した唯一の永続成果物として昇格する。
DSN・CHD・CODING・VERIFY は作業中の過程成果物であり、git 履歴・lessons-learned・latest-specs で代替できるため昇格しない。

For each `{repo}` in `AFFECTED_REPOS`:
  Let `CRS_TARGET` = `{DOCS}/{repo}/crs/`.
  Create `{CRS_TARGET}` if absent.
  If `{CR_PATH}/03_change-requirements/CRS-{CR_NUMBER}.md` exists:
    copy to `{CRS_TARGET}/CRS-{CR_NUMBER}.md`

If `HAS_CROSS`:
  Create `{DOCS}/cross/crs/` if absent.
  If `{CR_PATH}/03_change-requirements/CRS-{CR_NUMBER}.md` exists:
    copy to `{DOCS}/cross/crs/CRS-{CR_NUMBER}.md`

Update AI_INDEX.md "変更要求仕様書（CRS）ナビゲーション" table (upsert per repo + cross).

### Step C5: Promote Test Specs and Results → DOCS_DIR (per repo + cross/)

For each `{repo}` in `AFFECTED_REPOS`:
  Let `TEST_TARGET` = `{DOCS}/{repo}/test/`.
  If `{CR_PATH}/09_test-spec/{repo}/TSP-{CR_NUMBER}.md` exists: copy to `{TEST_TARGET}/TSP-{CR_NUMBER}.md`
  For each TRS file in `{CR_PATH}/10_test-results/{repo}/TRS-{CR_NUMBER}-*.md`: copy to `{TEST_TARGET}/`

If `HAS_CROSS`:
  Create `{DOCS}/cross/test/` if absent.
  If `{CR_PATH}/09_test-spec/cross/TSP-{CR_NUMBER}-cross.md` exists: copy to `{DOCS}/cross/test/`
  For each TRS in `{CR_PATH}/10_test-results/cross/TRS-{CR_NUMBER}-*.md`: copy to `{DOCS}/cross/test/`

Update AI_INDEX.md "テスト仕様（TSP）" columns (upsert).

### Step C6: Promote project-rulebook files → DOCS_DIR

`{XDDP_DIR}/project-rulebook.md` → `{DOCS}/project-rulebook.md` (overwrite)

For each `{repo}` in `REPOS_KEYS`:
  If `{XDDP_DIR}/project-rulebook-{repo}.md` exists:
    `{XDDP_DIR}/project-rulebook-{repo}.md` → `{DOCS}/{repo}/project-rulebook.md`

If `HAS_CROSS` and `{XDDP_DIR}/project-rulebook-cross.md` exists:
  Create `{DOCS}/cross/` if absent.
  `{XDDP_DIR}/project-rulebook-cross.md` → `{DOCS}/cross/project-rulebook.md`

Update AI_INDEX.md "共通知識" table (upsert per-repo and cross entries).

### Step C7: improvement-backlog を DOCS_DIR に昇格

If `{XDDP_DIR}/improvement-backlog.md` exists:
  Copy `{XDDP_DIR}/improvement-backlog.md` → `{DOCS}/improvement-backlog.md`
  （追記ではなく上書きコピー。`{XDDP_DIR}` 側が master）
  Record in OUTPUT_FILE: "improvement-backlog.md を `{DOCS}/improvement-backlog.md` に昇格済み"

※ ファイルが存在しない場合はスキップ。
※ `{XDDP_DIR}` 側の improvement-backlog.md は削除しない（master として維持）。

### リポジトリ別処理結果の記録

For each `{repo}` in `AFFECTED_REPOS`: C2/C4/C5/C6 の処理が正常に完了したかを判定し、OUTPUT_FILE の
「リポジトリ別処理結果一覧」に成功/失敗を記録する。失敗した場合は失敗したステップ名（C2/C4/C5/C6 のいずれか）と
理由を理由欄に含める。`AFFECTED_REPOS` を単純にループするのではなく、各 repo の実際の処理結果を記録すること。

### Output Format
Create OUTPUT_FILE using `mkdir -p` for the parent directory if needed:
```
# Step C2-C7 保留事項
CR: {CR_NUMBER}

## リポジトリ別処理結果一覧
- {repo}: {成功/失敗}（失敗の場合は失敗ステップ名（C2/C4/C5/C6）と理由を記載）
（AFFECTED_REPOS の全 repo を列挙する。Step D はこの一覧を「repo ごとに成功したか」の唯一の根拠として参照する）

## 要確認LL一覧（repo:unknown スキップ分）
- {LLエントリ} — repo: unknown
（なければ「なし」と記載）

## 破壊的変更フラグ・対象インタフェース一覧
- 破壊的変更: {あり/なし}
- 対象インタフェース: {一覧、またはなし}

## 削除候補一覧（system/use-cases・repo モジュールディレクトリ）
- {ディレクトリパス} — 理由: {...}
（なければ「なし」と記載）

## AI_INDEX.md アーカイブ候補
- {エントリ} — 最終更新CR: {CR}
（500行超でなければ「なし」と記載）
```
本エージェントは内部でユーザーへの削除確認を行わない（OUTPUT_FILE に保留事項として書き込むのみ。Step D で人に提示）。
git コンフリクト発生時のガイダンス（上記参照）はエージェント内のドキュメント記述として保持する
（git コマンド自体は Step C-Pre/C0 でオーケストレーターが実行済みのため、本エージェントに `Bash` 権限は付与しない）。
