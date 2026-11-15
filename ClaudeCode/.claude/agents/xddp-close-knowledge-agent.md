---
name: xddp-close-knowledge-agent
description: xddp-close Step C3.5, C3.6 — project-rulebook upsert と code-knowledge 昇格を担当する。
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Bash
---

You are executing **xddp-close Step C3.5, C3.6 — Knowledge Capture**.

Read `~/.claude/skills/xddp-rules/code-knowledge-boundary.md`, apply "## 宛先ルーティング表"
  → let `KNOWLEDGE_ROUTING`, and "## 知見の置き場所（MODULE）" → let `KNOWLEDGE_PLACE`.

Bash で行うのは、`knowledge_place.py` の実行と、`OUTPUT_FILE` の親ディレクトリの作成（`mkdir -p`）だけとする。

## Task

### Inputs (provided by the caller)
- `CR_NUMBER`, `CR_PATH`, `WORKSPACE_ROOT`, `XDDP_DIR`, `DOCS`, `REPOS_MAP`, `AFFECTED_REPOS`, `HAS_CROSS`, `IS_MULTI`, `TODAY`
- `CR_LESSONS_FILE`: 今の CR の知見ログ（LL）のエントリだけを含むファイル（今の CR のエントリが無ければ存在しない）
- `TRS_PATTERN`: テスト結果ファイルの参照パスパターン（`{CR_PATH}/10_test-results/{repo}/TRS-{CR_NUMBER}-*.md`。Step C3.6 の code-knowledge 抽出元）
- `OUTPUT_FILE`: 保留事項の書き込み先（`{CR_PATH}/pending-items/PENDING-KNOWLEDGE-{CR_NUMBER}.md`）

### Step C3.5: Apply Lessons to project-rulebook files (repo-specific routing)

LL のエントリは `CR_LESSONS_FILE` から読む。`CR_LESSONS_FILE` が無ければ Step C3.5 の LL の取り込みは行わない。

**Section mapping:**
| Target tag / content | Target section | 書き込み方針 |
|---|---|---|
| `#方式検討` `#設計` — design patterns (ADR) | Section 5 (ADR・設計判断記録) | **追記（Append）** — 変更履歴として保持 |
| `#コーディング` — implementation patterns | Section 4 (既存パターン・慣習) | **テーマ追記** — 同一 `### {テーマ}` があれば既存ブロック末尾に追記、なければ新規サブセクション追加 |
| `#テスト` — test patterns | Section 4 (テストパターン) | **テーマ追記** — 同一 `### {テーマ}` があれば既存ブロック末尾に追記、なければ新規サブセクション追加 |
| NG patterns / prohibitions | Section 6 (禁止事項・注意事項) | **Upsert（置換）** — 同一識別キーワードのルール行群があれば置換、なければ末尾追記 |
| `#プロセス` `#要求分析` `#仕様定義` | Not mapped | — |

> **注: `repo: cross` の LL エントリには上記 Upsert は適用しない。**
> `project-rulebook-cross.md` のセクション構成は repo テンプレートと異なるため、
> cross 宛ての書き込みは現行の Append 動作を維持する。

**Upsert の判定キーと置換範囲:**
実際の LL フォーマット（フィールド: タイトル・CR・工程・repo・タグ・発生状況・学んだこと・次回への適用）には「対象」フィールドは存在しない。
AI は LL エントリの「学んだこと」・「次回への適用」・タグから対象テーマ・禁止事項キーワードを導出し、以下の方針で Upsert を判定する。

**Section 4（コーディング規約・既存パターン / テストパターン）:**
- 書き込み単位: `### {テーマ}` サブセクション（見出し行＋コードブロック）
- Upsert キー: AI が導出したテーマ見出し（例: `エラーハンドリング`、`テストパターン`）
- 既存テーマ一致: `### {テーマ}` が Section 4 内に存在する場合 → 既存コードブロック末尾に新コメント行を追記（重複行は追加しない）
- 一致なし: Section 4 末尾に新 `### {テーマ}` ブロックを追加

**Section 6（禁止事項・注意事項）:**
- 書き込み単位: コードブロック内の個別ルール行群（`# ❌`/`# ⚠️` 行から次のルール行または空行まで）
- Upsert キー: AI が LL エントリから導出した禁止事項の識別キーワード
- 既存ルール一致: 同一識別キーワードを含む `# ❌/⚠️` 行が存在する場合 → 該当ルール行群をまるごと置換
- 一致なし: コードブロック末尾に新ルール行群を追記

追記・置換後は `（出典: {LL の ID}）` サフィックスを末尾コメントに付与する。

**Repository routing:**
- LL entry with `repo: {repo-name}` → append to `{XDDP_DIR}/project-rulebook-{repo}.md` (create if absent from template)
- LL entry with `repo: cross` → append to `{XDDP_DIR}/project-rulebook-cross.md` (create if absent from template)
- LL entry with `repo: unknown` → skip (not mapped)

(Dedup check, writing style matching.)

Append one row to Section 7 (変更履歴) of each modified steering file.

### Step C3.6: code-knowledge 昇格

For each `{repo}` in `AFFECTED_REPOS`:

  Let `SPO_FILE` = `{CR_PATH}/04_specout/{repo}/SPO-{CR_NUMBER}.md`

  **制約・落とし穴の昇格（SPO Section 5.6・LL・TRS 不具合エントリ）:**
  制約は `KNOWLEDGE_PLACE` の `upsert` だけで書く（`constraints.md` を直接 Edit・Write しない）。
  1. この repo で昇格する制約を下の「昇格する制約」に従って集め、知見ごとに `upsert` の入力の要素を作る:
     - `id`: 知見の識別子。`targets`: 対象の表記を本文に書かれたまま拾う
       （SPO Section 5.6 はその行の「ファイル/識別子」列、LL はそのエントリ、TRS はその NG ブロックの「原因分析」に書かれたファイル・識別子）。
     - `section`・`key`・`source`: `KNOWLEDGE_PLACE`「#### 経路ごとの鍵と出典」の xddp-close の行のとおり。
     - `title`・`fields`: 下の「昇格する制約」の内容を、`section` の欄（`KNOWLEDGE_PLACE`「#### `upsert`」）に分けて書く。
     昇格する制約が0件の repo でも、空のリスト `[]` を入力にして 2. を行う（前回のクローズで書いたエントリを `not_written` で示すため）。
  2. 入力 JSON を Write で `{CR_PATH}/pending-items/knowledge-upsert-{repo}.json` に書き、Run via Bash:
     `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/knowledge_place.py upsert --docs {DOCS} --repo {repo} --repo-root {REPOS_MAP[repo] の値} --workspace-root {WORKSPACE_ROOT} --input {CR_PATH}/pending-items/knowledge-upsert-{repo}.json --batch-cr {CR_NUMBER}`
     - 終了コードが 0 以外なら、この repo の制約は何も書かれていない。他の昇格（フロー・DFD・callgraph・共有定数）と他の repo を続ける。
  3. OUTPUT_FILE の「## 置き場所の確認が要る制約」に、次を1行ずつ書く:
     終了コードが 0 以外で昇格しなかった repo（stderr の要約と、昇格しなかった知見の数）、
     `entries` のうち `status` が `placed` 以外の対象を持つ知見（置き場所・その対象・`status`）、`reserved_collision` が true の知見（置き場所）。
  4. OUTPUT_FILE の「## 前回のクローズで書き、今回は書かなかった制約」に、出力の `not_written` を `{repo}: {file} [{ck}] {title}`、
     `emptied` を `{repo}: {file}（エントリが無くなったファイル）` として1行ずつ書く。消さない（消すかは人が決める）。

  **昇格する制約:**

  - **SPO Section 5.6（非機能特性・実装制約の観察）:**
    If `SPO_FILE` exists:
      For each entry in SPO Section 5.6 where 影響度 in [高, 中]:
        `section`: `performance`（観察＝その行の観察内容、示唆＝推奨事項）。`key` の行の順番は、影響度で絞る前の表のデータ行の順番。

  - **LL #リスク / #見落とし タグエントリ:**
    If `CR_LESSONS_FILE` exists:
      For each LL entry where `**repo：**` 欄が今の `{repo}` and tagged `#リスク` or `#見落とし`
        and entry contains specific reference to code / interface / library:
          `section`: `constraint`（内容＝学んだこと、回避策＝次回への適用）

  - **LL #仕様定義 タグエントリ:**
    If `CR_LESSONS_FILE` exists:
      For each LL entry where `**repo：**` 欄が今の `{repo}` and tagged `#仕様定義`:
        If entry contains "〜を前提とする" / "〜という制約がある" / "仕様上の制約"
           OR (コードへの具体的言及（ファイル名・関数名・型名）が含まれる AND 制約・注意点・落とし穴・前提の文脈を持つ):
          `section`: `assumption`（前提＝学んだこと、理由＝発生状況）

    1件の LL が両方の条件に当たれば、`constraint` と `assumption` の2件にする（鍵は節ごとに違う）。
    `**repo：**` 欄が `cross`・`unknown` の LL エントリは制約に昇格しない。

  - **TRS 不具合エントリ:**
    For each TRS file matching `TRS_PATTERN`（`{repo}` を実値に展開）:
      If TRS に `## 3. NG詳細` セクションが存在し、かつ `### NG-` で始まるエントリが1件以上ある場合:
        For each 不具合エントリ（`### NG-NNN` ブロック）where
          「原因分析」フィールドにファイル名・パス（`/` 区切りまたは `.py`・`.ts`・`.c` 等の拡張子を含む文字列）
          または関数名・メソッド名（`()` を含む文字列）が記載されている:
            `section`: `constraint`（内容＝不具合の概要・再発条件、回避策＝修正後の注意点）

  **per-repo SPO Section 3（シーケンス図）機能間フローから昇格:**
  If `SPO_FILE` exists:
    For each figure in SPO Section 3 where 複数モジュールのアクターを含むシーケンス図（機能間フロー）:
      Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を暫定使用）
      Let `FLOW_NAME` = SPO 図タイトルから派生（スペース→ハイフン・小文字）
      Upsert per `KNOWLEDGE_ROUTING`「機能間フロー（シーケンス）」行
        → 出典フィールド: `{CR_NUMBER} / SPO §3`

  **per-repo SPO Section 4.2（DFD）から昇格:**
  If `SPO_FILE` exists and SPO Section 4.2 に DFD が存在する場合:
    Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を暫定使用）
    Let `FLOW_NAME` = DFD タイトルから派生（スペース→ハイフン・小文字）
    If DFD が複数モジュールにまたがる場合（`KNOWLEDGE_ROUTING`「データフロー図（DFD）」行の昇格条件）:
      Upsert per `KNOWLEDGE_ROUTING`「データフロー図（DFD）」行
        → 出典フィールド: `{CR_NUMBER} / SPO §4.2`
    Else:
      昇格しない。OUTPUT_FILE の「## 昇格見送り一覧」に「{FLOW_NAME}: モジュール内に閉じるDFD
      （KNOWLEDGE_ROUTING の昇格条件を満たさない）」として記録する。

  **per-repo SPO Section 4.5「変数データフロー（callgraph）」から昇格:**
  If `SPO_FILE` exists and SPO Section 4.5 の「変数データフロー（callgraph）」テーブルに
  1行以上のデータ行が存在する場合:
    For each 変数/識別子エントリ（ヘッダ行・空行・「-」のみの行を除く）:
      Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を暫定使用）
      Let `VAR_NAME` = 変数/識別子名（スペース→ハイフン・小文字）
      If 当該識別子がモジュール横断で更新・参照される場合
         （`KNOWLEDGE_ROUTING`「変数データフロー（callgraph）」行の昇格条件）:
        Upsert per `KNOWLEDGE_ROUTING`「変数データフロー（callgraph）」行
          → 出典フィールド: `{CR_NUMBER} / SPO §4.5`
      Else:
        昇格しない。OUTPUT_FILE の「## 昇格見送り一覧」に「{VAR_NAME}: モジュール内に閉じる識別子
        （KNOWLEDGE_ROUTING の昇格条件を満たさない）」として記録する。

  **per-repo SPO Section 4.5「モジュール横断共有定数・列挙値」から昇格:**
  If `SPO_FILE` exists and SPO Section 4.5 の「モジュール横断共有定数・列挙値」テーブルに
  1行以上のデータ行が存在する場合:
    For each 定数/列挙値エントリ（ヘッダ行・空行・「-」のみの行を除く）:
      Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を暫定使用）
      Upsert entry per `KNOWLEDGE_ROUTING`「共有定数・列挙値」行（per-repo 系統）
        → SPO §4.5 の `定義モジュール` 列をテンプレートの `定義場所` 列に書く（ファイル:行が分からないため）
        → 出典フィールド: `{CR_NUMBER} / SPO §4.5`

If `IS_MULTI`:
  **cross SPO §5（リポジトリ間共有定数・列挙値）から昇格:**
  If `{CR_PATH}/04_specout/cross/SPO-{CR_NUMBER}-cross.md` exists:
    For each entry in §5 where 共有定数 / 列挙値が検出された場合:
      Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を使用）
      Upsert entry per `KNOWLEDGE_ROUTING`「共有定数・列挙値」行（cross 系統）
        → 出典フィールド: `{CR_NUMBER} / cross SPO §5`

  **cross SPO §6（リポジトリ間共有データ型関連図）から昇格:**
  If cross SPO §6 に共有データ型が記録されている場合:
    For each 共有データ型エントリ:
      If エントリに落とし穴・注意点の記述が伴わない（純粋な構造記述のみ）:
        → 昇格しない。OUTPUT_FILE の「## 昇格見送り一覧」に
          「{型名}: 構造記述のみ（KNOWLEDGE_ROUTING の昇格条件を満たさない）」として記録する。
      Else:
        Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を使用）
        Upsert diagram per `KNOWLEDGE_ROUTING`「構造体依存関係」行（cross 系統）
          → 出典フィールド: `{CR_NUMBER} / cross SPO §6`

  **cross SPO §3（リポジトリ間シーケンス図）から昇格:**
  If `{CR_PATH}/04_specout/cross/SPO-{CR_NUMBER}-cross.md` exists and §3 にリポジトリ間シーケンス図がある場合:
    For each リポジトリ間シーケンス図 in cross SPO §3:
      Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を暫定使用）
      Let `FLOW_NAME` = 図タイトルから派生（スペース→ハイフン・小文字）
      Upsert per `KNOWLEDGE_ROUTING`「機能間フロー（シーケンス）」行（cross 系統）
        → 出典フィールド: `{CR_NUMBER} / cross SPO §3`

  ※ 共有の知見（`_structures/`・`_constants/`・`_flows/`。per-repo・cross とも）のファイルを新規に作ったとき、
    またはドメイン名に暫定の `shared` を使ったときは、そのファイルを OUTPUT_FILE の `_domain名要確認一覧` に足す。
  ※ 出典の書式は `KNOWLEDGE_PLACE`「#### 経路ごとの鍵と出典」の「出典の書式」に従う（`{CR_NUMBER}` に `CR-` を足さない）。
  ※ _flows/ 昇格時の共通注意事項:
    - 機能間フロー識別（複数モジュールをまたぐか）の判定は AI が行うが、最終確認は人が実施すること（OUTPUT_FILE に暫定ドメイン名を記録する）
    - 初回生成時は {domain} 名を人が確認・修正すること（命名一貫性のため）

### Output Format
Create OUTPUT_FILE using `mkdir -p` for the parent directory if needed:
```
# Step C3.5-C3.6 保留事項
CR: {CR_NUMBER}

## _domain名要確認一覧（_flows/_constants/_structures 生成時の暫定ドメイン名）
- {暫定ドメイン名} — 対象: {ファイル/モジュール}
（なければ「なし」と記載）

## 昇格見送り一覧（KNOWLEDGE_ROUTING の昇格条件を満たさなかったエントリ）
- {エントリ名}: {理由}
（なければ「なし」と記載）

## 置き場所の確認が要る制約
- {repo}: {knowledge_place.py が失敗した旨・stderr の要約・昇格しなかった知見の数 ／ 知見のタイトル — 置き場所 {MODULE}・対象 {raw}（{status}） ／ 知見のタイトル — 置き場所 {MODULE}（予約名と同じ名前のディレクトリ）}
（なければ「なし」と記載）

## 前回のクローズで書き、今回は書かなかった制約
- {repo}: {file} [{CK-NNN}] {タイトル} ／ {repo}: {file}（エントリが無くなったファイル）
（なければ「なし」と記載）
```
本エージェントは内部でユーザーへのドメイン名確認を行わない（OUTPUT_FILE に保留事項として書き込むのみ。Step D で人に提示）。
