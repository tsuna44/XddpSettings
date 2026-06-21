---
name: xddp-close-knowledge-agent
description: xddp.close Step C3.5, C3.6 — project-rulebook upsert と code-knowledge 昇格を担当する。
tools:
  - Read
  - Write
  - Edit
  - Glob
---

You are executing **xddp.close Step C3.5, C3.6 — Knowledge Capture**.

## Task

### Inputs (provided by the caller)
- `CR_NUMBER`, `CR_PATH`, `XDDP_DIR`, `DOCS`, `REPOS_MAP`, `AFFECTED_REPOS`, `HAS_CROSS`, `IS_MULTI`, `TODAY`, `LESSONS_FILE`
- `TRS_PATTERN`: テスト結果ファイルの参照パスパターン（`{CR_PATH}/10_test-results/{repo}/TRS-{CR_NUMBER}-*.md`。Step C3.6 の code-knowledge 抽出元）
- `OUTPUT_FILE`: 保留事項の書き込み先（`{CR_PATH}/pending-items/PENDING-KNOWLEDGE-{CR_NUMBER}.md`）

### Step C3.5: Apply Lessons to project-rulebook files (repo-specific routing)

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

追記・置換後は `（出典: LL-{NNN}, {CR_NUMBER}）` サフィックスを末尾コメントに付与する。

**Repository routing:**
- LL entry with `repo: {repo-name}` → append to `{XDDP_DIR}/project-rulebook-{repo}.md` (create if absent from template)
- LL entry with `repo: cross` → append to `{XDDP_DIR}/project-rulebook-cross.md` (create if absent from template)
- LL entry with `repo: unknown` → skip (not mapped)

(Dedup check, writing style matching.)

Append one row to Section 7 (変更履歴) of each modified steering file.

### Step C3.6: code-knowledge 昇格

For each `{repo}` in `AFFECTED_REPOS`:

  **per-repo SPO Section 5.6（非機能特性・実装制約の観察）から昇格:**
  Let `SPO_FILE` = `{CR_PATH}/04_specout/{repo}/SPO-{CR_NUMBER}.md`
  If `SPO_FILE` exists:
    For each entry in SPO Section 5.6 where 影響度 in [高, 中]:
      Let `MODULE` = 対象ファイル/識別子から推定されるモジュール名（ファイルパスの第1〜2階層ディレクトリ名。推定不可な場合は `"_general"` を使用）
      Upsert entry to `{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`
        → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-constraints-template.md`
        → セクション: "パフォーマンス・非機能特性"
        → 出典フィールド: `{CR_NUMBER}`

  **LL #リスク / #見落とし タグエントリから昇格:**
  If `LESSONS_FILE` exists:
    For each LL entry tagged `#リスク` or `#見落とし`
      where entry contains specific reference to code / interface / library:
        Let `MODULE` = 対象モジュール名（推定不可な場合は `"_general"` を使用）
        Upsert entry to `{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`
          → セクション: "既知の制約・落とし穴"

  **LL #仕様定義 タグエントリから昇格:**
  For each LL entry tagged `#仕様定義`:
    If entry contains "〜を前提とする" / "〜という制約がある" / "仕様上の制約"
       OR (コードへの具体的言及（ファイル名・関数名・型名）が含まれる AND 制約・注意点・落とし穴・前提の文脈を持つ):
      Upsert to `{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`
        → セクション: "仕様上の暗黙の前提"

  **per-repo SPO Section 3（シーケンス図）機能間フローから昇格:**
  If `SPO_FILE` exists:
    For each figure in SPO Section 3 where 複数モジュールのアクターを含むシーケンス図（機能間フロー）:
      Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を暫定使用）
      Let `FLOW_NAME` = SPO 図タイトルから派生（スペース→ハイフン・小文字）
      Upsert to `{DOCS}/{repo}/knowledge/code-knowledge/_flows/{DOMAIN}-{FLOW_NAME}-sequence.md`
        → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-flows-sequence-template.md`

  **per-repo SPO Section 4.2（DFD）から昇格:**
  If `SPO_FILE` exists and SPO Section 4.2 に DFD が存在する場合:
    Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を暫定使用）
    Let `FLOW_NAME` = DFD タイトルから派生（スペース→ハイフン・小文字）
    Upsert to `{DOCS}/{repo}/knowledge/code-knowledge/_flows/{DOMAIN}-{FLOW_NAME}-dfd.md`
      → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-flows-dfd-template.md`

  **per-repo TRS 不具合エントリから昇格:**
  For each TRS file matching `TRS_PATTERN`（`{repo}` を実値に展開）:
    If TRS に `## 3. NG詳細` セクションが存在し、かつ `### NG-` で始まるエントリが1件以上ある場合:
      For each 不具合エントリ（`### NG-NNN` ブロック）where
        「原因分析」フィールドにファイルパス（`/` 区切りまたは `.py`・`.ts`・`.c` 等の拡張子を含む文字列）
        または関数名・メソッド名（`()` を含む文字列）が記載されている:
          Let `MODULE` = 対象ファイル/識別子から推定されるモジュール名（ファイルパスの第1〜2階層ディレクトリ名。推定不可な場合は `"_general"` を使用）
          Let `UPSERT_KEY` = `CR-{CR_NUMBER} / NG-{NNN}`（例: `CR-2026-002 / NG-001`）
          Upsert entry to `{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`
            → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-constraints-template.md`
            → セクション: "既知の制約・落とし穴"
            → 内容: 不具合の概要・修正後の注意点・再発条件
            → **Upsertキー:** constraints.md の各 `[CK-NNN]` エントリの `出典` フィールドに
              `{UPSERT_KEY}` が含まれるか検索する。
              - 一致エントリが存在する場合: `[CK-NNN]` 番号を維持したままエントリ全体を置換
              - 一致なしの場合: 新規 `[CK-NNN]` エントリを追加（`NNN` = 既存最大番号 + 1、
                ファイルが存在しない場合は `001`）
            → 出典フィールド: `CR-{CR_NUMBER} / NG-{NNN} / 発見日: {TODAY}`

If `IS_MULTI`:
  **cross SPO §5（リポジトリ間共有定数・列挙値）から昇格:**
  If `{CR_PATH}/04_specout/cross/SPO-{CR_NUMBER}-cross.md` exists:
    For each entry in §5 where 共有定数 / 列挙値が検出された場合:
      Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を使用）
      Upsert entry to `{DOCS}/cross/knowledge/code-knowledge/_constants/{DOMAIN}-constants.md`
        → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-constants-template.md`

  **cross SPO §6（リポジトリ間共有データ型関連図）から昇格:**
  If cross SPO §6 に共有データ型が記録されている場合:
    Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を使用）
    Upsert diagram to `{DOCS}/cross/knowledge/code-knowledge/_structures/{DOMAIN}-relations.md`
      → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-structures-template.md`

  **cross SPO §3（リポジトリ間シーケンス図）から昇格:**
  If `{CR_PATH}/04_specout/cross/SPO-{CR_NUMBER}-cross.md` exists and §3 にリポジトリ間シーケンス図がある場合:
    For each リポジトリ間シーケンス図 in cross SPO §3:
      Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を暫定使用）
      Let `FLOW_NAME` = 図タイトルから派生（スペース→ハイフン・小文字）
      Upsert to `{DOCS}/cross/knowledge/code-knowledge/_flows/{DOMAIN}-{FLOW_NAME}-sequence.md`
        → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-flows-sequence-template.md`

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
```
本エージェントは内部でユーザーへのドメイン名確認を行わない（OUTPUT_FILE に保留事項として書き込むのみ。Step D で人に提示）。
