# PLAN-20260504-req-to-project-steering-extraction

作成日: 2026-05-04  
ステータス: 草案 / 承認待ち / 承認済み / **実装完了**

---

## 1. 背景・目的

`xddp.02.analysis` の完了後、req ファイルを分析して project-steering.md に追記すべき内容（命名規約・アーキテクチャ決定・禁止事項・既存パターン）が含まれていれば、候補を提示してユーザ承認後に追記する機能を追加する。

これにより、プロジェクト横断の知見が req に記述されても自動的に project-steering に蓄積され、工程05・06 の成果物品質が向上する。

---

## 2. 変更対象ファイル

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `ClaudeCode/.claude/skills/xddp.02.analysis.md` | 修正 | Step B3（project-steering 追記候補抽出）を追加 |
| `ClaudeCode/.claude/commands/xddp.02.analysis.md` | 修正 | Step B3 の要約を追加 |
| `ClaudeCode/.claude/skills/xddp.07.code.md` | 修正 | Step A-Pre に project-steering.md 読み込みを追加し、coder-agent・verifier-agent に `STEERING_CONTEXT` を渡す。ルールファイル参照名も更新 |
| `ClaudeCode/.claude/commands/xddp.07.code.md` | 修正 | STEERING_CONTEXT 読み込みの要約を追加 |
| `ClaudeCode/.claude/skills/xddp.close.md` | 修正 | Step C6（project-steering.md の知識HUB昇格）を追加 |
| `ClaudeCode/.claude/commands/xddp.close.md` | 修正 | Step C6 の要約を追加 |
| `ClaudeCode/.claude/templates/xddp.05.rules.md` | リネーム | → `xddp.arch.rules.md`（DSN: 実装方式検討の品質ゲート） |
| `ClaudeCode/.claude/templates/xddp.06.rules.md` | リネーム | → `xddp.design.rules.md`（CHD: 変更設計書の品質ゲート） |
| `ClaudeCode/.claude/templates/xddp.07.rules.md` | リネーム | → `xddp.coding.rules.md`（コーディングの品質ゲート） |
| `ClaudeCode/.claude/skills/xddp.05.arch.md` | 修正 | ルールファイル参照を `xddp.arch.rules.md` に更新 |
| `ClaudeCode/.claude/skills/xddp.06.design.md` | 修正 | ルールファイル参照を `xddp.design.rules.md` に更新 |

---

## 3. 変更内容

### 3.1. `ClaudeCode/.claude/skills/xddp.02.analysis.md`

**挿入位置:** Step B2 と Step C の間（現 138 行目 `## Step C:` の直前）

**変更前:**
```
## Step C: Update progress.md
Read `{CR_PATH}/progress.md`, set step 2 → ✅ 完了, 詳細ステップ → `-`, today, link `ANA-{CR}.md`.
Set next command → `/xddp.03.req {CR}`.
```

**変更後:**
```
## Step B3: project-steering 追記候補の抽出

> **実行タイミング:** Step B2（人レビューゲート）確認後・Step C（progress.md 更新）の前に実行する。
> Step B2 で変更があった場合は最終 AI レビューパスが完了してから本ステップに進む。

1. `{XDDP_DIR}/project-steering.md` が存在するか確認する。
   - 存在しない場合: 「project-steering.md が見つかりませんでした（`{XDDP_DIR}/project-steering.md`）。
     `/xddp.01.init` を実行してファイルを生成してから再度お試しください。今回はスキップします。」
     とユーザに伝え、このステップをスキップする。

2. **冪等性チェック:** project-steering.md の「## 7. 変更履歴」セクションに {CR} の追記済みエントリが
   存在するか確認する（列に {CR} が含まれる行の有無）。
   存在する場合: 「{CR} の追記済みエントリが変更履歴に見つかりました。Step B3 をスキップします。」
   とユーザに伝え、このステップをスキップする。

3. `{CR_PATH}/01_requirements/` 配下の全 `.md` ファイルを読み込む。

4. 以下のカテゴリに該当する記述を req から抽出し、追記候補リストを作成する。
   **カテゴリ名で project-steering.md の対象見出しを特定する（セクション番号ではなく見出し名で照合する）。**

   | カテゴリ | 抽出対象の例（この CR 固有でなく横断的に適用すべきもののみ） | project-steering の対象見出し |
   |---|---|---|
   | 命名規約 | 「〇〇という名前で統一する」「命名規則は〇〇とする」 | `## 2. 命名規約` |
   | アーキテクチャ決定 | 「〇〇パターンを採用する」「〇〇方式に移行する」 | `## 3. アーキテクチャ決定記録（ADR）` |
   | 禁止事項 | 「〇〇は使用禁止」「〇〇してはならない」 | `## 5. 禁止事項・注意事項` |
   | 横断パターン | エラーハンドリング方針・非同期処理方針・ログ方針など<br>コードベース全体に適用する横断的パターン。<br>**特定機能の実装方式・この CR 固有の手順は対象外。** | `## 4. 既存パターン・慣習` |

5. 候補が0件の場合はこのステップをスキップする（何も報告しない）。

6. 候補が1件以上ある場合は、以下の形式でユーザに提示する。
   各候補には「カテゴリ名-連番」の一意ラベルを付与する。

   ```
   📋 project-steering.md への追記候補が見つかりました。

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

   上記を project-steering.md に追記しますか？
   ラベル名で指定してください（例: 「すべて追記」「禁止事項-1 のみ追記」「スキップ」）。
   ```

7. ユーザの回答に応じて処理する：
   - 「すべて追記」→ 全候補を該当見出しのコードブロック末尾（または ADR 見出し形式）に追記する
   - 「{ラベル名} のみ追記」→ 指定ラベルの候補のみ追記する
   - 「スキップ」→ 何もせず次のステップへ進む

   **追記フォーマットのルール:**
   - `## 2. 命名規約`・`## 4. 既存パターン・慣習`・`## 5. 禁止事項・注意事項`: 既存のコードブロック（``` ``` ）末尾に追記する
   - `## 3. アーキテクチャ決定記録（ADR）`: コードブロック外に `### ADR-NNN: {タイトル}` 見出し形式で追記する
     （ADR 番号は既存エントリの最大番号 +1 とする）

8. 追記した場合のみ、project-steering.md の **`## 7. 変更履歴`** にエントリを追加する：
   ```
   | {TODAY} | {CR} | {追記したカテゴリ名と件数を列挙。例: 禁止事項1件・命名規約1件}（req より抽出） |
   ```

## Step C: Update progress.md
Read `{CR_PATH}/progress.md`, set step 2 → ✅ 完了, 詳細ステップ → `-`, today, link `ANA-{CR}.md`.
Set next command → `/xddp.03.req {CR}`.
```

---

### 3.2. `ClaudeCode/.claude/commands/xddp.02.analysis.md`

**変更前:**
```
3. **Human review gate**: pause for human review of `ANA-{CR}.md`.
   - If changes made: run one final AI review pass.
4. Update `{CR}/progress.md`: step 2 ✅, next → `/xddp.03.req {CR}`.
```

**変更後:**
```
3. **Human review gate**: pause for human review of `ANA-{CR}.md`.
   - If changes made: run one final AI review pass.
3.5. **project-steering 追記候補の抽出**（Step B3）:
     - 冪等性チェック: 変更履歴に {CR} のエントリがあればスキップ。
     - req から命名規約・ADR・禁止事項・横断パターン（横断的なもののみ）を抽出。
     - 候補をカテゴリ名ラベル付きで提示し、ユーザ承認後に該当見出しへ追記。
     - `project-steering.md` 不在時はユーザに通知してスキップ。候補0件の場合もスキップ。
4. Update `{CR}/progress.md`: step 2 ✅, next → `/xddp.03.req {CR}`.
```

---

### 3.3. `ClaudeCode/.claude/skills/xddp.07.code.md`

**挿入位置:** Step A-Pre（現 18〜21 行目）に追記

**変更前:**
```
## Step A-Pre: コーディング品質ルールの読み込み

Read `~/.claude/templates/xddp.07.rules.md` to get `CODING_RULES`.
Pass `CODING_RULES` to the coder-agent and verifier-agent as the quality gate definition for this step.
```

**変更後:**
```
## Step A-Pre: コーディング品質ルールとプロジェクト記憶の読み込み

Read `~/.claude/templates/xddp.coding.rules.md` to get `CODING_RULES`.

If `{XDDP_DIR}/project-steering.md` exists, read it to get `STEERING_CONTEXT`.
If not found, set `STEERING_CONTEXT` = empty string.

Pass `CODING_RULES` and `STEERING_CONTEXT` to the coder-agent and verifier-agent as
the quality gate definition and project-specific constraints for this step.
```

**Step A（coder-agent 呼び出し）に `STEERING_CONTEXT` パラメータを追加:**
```
STEERING_CONTEXT: {project-steering.md の内容。なければ空}
```

**Step B（verifier-agent 呼び出し）に `STEERING_CONTEXT` パラメータを追加:**
```
STEERING_CONTEXT: {project-steering.md の内容。なければ空}
```

**理由:** xddp.05.arch・xddp.06.design ではすでに STEERING_CONTEXT を参照している。コーディング工程でも同様に参照することで、命名規約・禁止事項・横断パターンが実装に反映される。

---

### 3.4. `ClaudeCode/.claude/commands/xddp.07.code.md`

**変更前:**
```
1. Read `xddp.config.md` to extract `MULTI_REPO` and `REPOS_MAP` (マルチリポジトリ対応).
2. Invoke `xddp-coder-agent` (with `REPOS_MAP`) to implement source code changes per CHD.
```

**変更後:**
```
1. Read `xddp.coding.rules.md` → `CODING_RULES`。
   Read `{XDDP_DIR}/project-steering.md` → `STEERING_CONTEXT`（存在しない場合は空）。
   両方を coder-agent・verifier-agent に渡す。
2. Read `xddp.config.md` to extract `MULTI_REPO` and `REPOS_MAP` (マルチリポジトリ対応).
3. Invoke `xddp-coder-agent` (with `REPOS_MAP`, `STEERING_CONTEXT`) to implement source code changes per CHD.
   - CHD の `リポジトリ:` フィールドと `REPOS_MAP` を参照して対象ファイルを解決する。
4. Invoke `xddp-verifier-agent` to run static verification.
5. If NG: attempt one auto-fix round, then re-verify.
6. Update `{CR}/progress.md`: step 9 (コーディング) ✅, step 10 (静的検証) ✅ (or 🔁), next → `/xddp.08.test {CR}`.
   - 設計ミスによる NG の場合は `/xddp.06.design {CR}` へのロールバックを案内する.
```

---

### 3.5. `ClaudeCode/.claude/skills/xddp.close.md`

**挿入位置:** Step C5 と Step D の間に Step C6 を追加

**変更前:**
```
## Step D: Human Review Gate

Tell the user:
> ✅ クローズ処理が完了しました。内容を確認してください。
>
> **生成・更新した資料：**
> - 改善バックログ: `improvement-backlog.md`（追加 {n} 件）
> - 知見ログ: `lessons-learned.md`（追加 {n} 件）
> - 承認済み仕様書: `{DOCS}/{REPO_NAME}/specs/` に昇格（{n} ファイル）
> - 設計書: `{DOCS}/{REPO_NAME}/design/` に昇格（DSN・CHD）
> - テスト仕様書: `{DOCS}/{REPO_NAME}/test/` に昇格（TSP）
```

**変更後:**
```
## Step C6: project-steering.md の昇格（{XDDP_DIR}/ → DOCS_DIR/{REPO_NAME}/）

`{XDDP_DIR}/project-steering.md` が存在するか確認する。

存在する場合:
1. `{DOCS}/{REPO_NAME}/project-steering.md` へコピーする（既存ファイルは上書き）。
2. `{DOCS}/AI_INDEX.md` の「共通知識」テーブルに以下の行を追加・更新する
   （すでに同じ行が存在する場合は `最終更新CR` 列のみ更新する）:
   ```
   | [project-steering.md]({REPO_NAME}/project-steering.md) | 命名規約・ADR・コーディングパターン・禁止事項（最終更新CR: {CR}） |
   ```

存在しない場合: スキップし、スキップした旨を記録する。

## Step D: Human Review Gate

Tell the user:
> ✅ クローズ処理が完了しました。内容を確認してください。
>
> **生成・更新した資料：**
> - 改善バックログ: `improvement-backlog.md`（追加 {n} 件）
> - 知見ログ: `lessons-learned.md`（追加 {n} 件）
> - 承認済み仕様書: `{DOCS}/{REPO_NAME}/specs/` に昇格（{n} ファイル）
> - 設計書: `{DOCS}/{REPO_NAME}/design/` に昇格（DSN・CHD）
> - テスト仕様書: `{DOCS}/{REPO_NAME}/test/` に昇格（TSP）
> - project-steering: `{DOCS}/{REPO_NAME}/project-steering.md` に昇格（Step C6 がスキップされた場合はこの行を省略）
```

---

### 3.6. `ClaudeCode/.claude/commands/xddp.close.md`

**変更前:**
```
6.5. テスト仕様書の昇格（Step C5）: TSP を `{DOCS_DIR}/{REPO_NAME}/test/` にコピーし、`AI_INDEX.md` のテスト仕様列を更新する。
7. **Human review gate**: ユーザによる確認を待つ（バックログ・知見・昇格仕様書の3点を確認）。
```

**変更後:**
```
6.5. テスト仕様書の昇格（Step C5）: TSP を `{DOCS_DIR}/{REPO_NAME}/test/` にコピーし、`AI_INDEX.md` のテスト仕様列を更新する。
7. project-steering の昇格（Step C6）: `{XDDP_DIR}/project-steering.md` を
   `{DOCS_DIR}/{REPO_NAME}/project-steering.md` にコピーし、`AI_INDEX.md` の「共通知識」テーブルを更新する。
   ファイルが存在しない場合はスキップ。
8. **Human review gate**: ユーザによる確認を待つ（バックログ・知見・昇格仕様書の3点を確認）。
```

---

### 3.7. ルールファイルのリネームと参照更新

**背景:** `xddp.05.rules.md` 等のファイル名ではステップ番号しかわからず、内容が直感的に把握できないため、役割を示す名前に変更する。

> **実装順序の注意:** Section 3.3（`xddp.07.code.md` への `xddp.coding.rules.md` 参照追加）は
> 本セクションのリネームが完了してから実施すること。
> リネーム前に 3.3 を実装すると、`~/.claude/templates/xddp.coding.rules.md` が存在せず参照エラーになる。

#### テンプレートファイルのリネーム

| 旧ファイル名 | 新ファイル名 | 内容 |
|---|---|---|
| `xddp.05.rules.md` | `xddp.arch.rules.md` | DSN（実装方式検討）の設計品質ゲート |
| `xddp.06.rules.md` | `xddp.design.rules.md` | CHD（変更設計書）の設計品質ゲート |
| `xddp.07.rules.md` | `xddp.coding.rules.md` | コーディングの品質ゲート |

`ClaudeCode/.claude/templates/` 配下で `git mv`（またはリネーム＋削除）を実施する。

#### スキルファイルの参照更新

**`xddp.05.arch.md`（50 行目）**

変更前:
```
Read `~/.claude/templates/xddp.05.rules.md` to get `ARCH_RULES`.
```
変更後:
```
Read `~/.claude/templates/xddp.arch.rules.md` to get `ARCH_RULES`.
```

**`xddp.06.design.md`（42 行目）**

変更前:
```
Read `~/.claude/templates/xddp.06.rules.md` to get `DESIGN_RULES`.
```
変更後:
```
Read `~/.claude/templates/xddp.design.rules.md` to get `DESIGN_RULES`.
```

**`xddp.07.code.md`（20 行目）** → 3.3 の変更後に含まれるため、本セクションでは記載のみ。

---

## 4. 影響範囲

- 影響するスキル・コマンド: `xddp.02.analysis`・`xddp.05.arch`・`xddp.06.design`・`xddp.07.code`・`xddp.close`
- 影響する工程: 工程2（要求分析）・工程6〜7（設計）・工程9〜10（コーディング・静的検証）・CRクローズ
- 後方互換性:
  - project-steering.md 関連: あり（ファイルが存在しない場合はすべてスキップ）
  - ルールファイルリネーム: `~/.claude/` への `setup.sh` 再実行が必要（旧ファイル名のままでは参照エラーになる）

---

## 5. 確認項目

- [ ] **実装順序**: 3.7（テンプレートリネーム）→ 3.3（`xddp.07.code.md` 修正）の順に実施すること
- [ ] スキル・コマンドの同期（対応する commands も更新済み）
- [ ] `~/.claude/templates/` から旧ルールファイル（`xddp.05.rules.md`・`xddp.06.rules.md`・`xddp.07.rules.md`）を手動削除する
- [ ] sample-project / sample-multiproject で動作確認
- [ ] CLAUDE.md の記述と整合

---

## 6. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | tsuna44 |
| 承認日 | 2026-05-04 |
| 備考 | |
