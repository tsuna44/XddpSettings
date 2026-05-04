# PLAN-20260503-config-upward-search

作成日: 2026-05-03  
ステータス: 草案 / 承認待ち / **承認済み** / 実装完了

---

## 1. 背景・目的

レビュー指摘 N-007 への対応として、`xddp.close` の `xddp.config.md` 探索を「cwdのみ」から「cwdから上位ディレクトリへの探索」に変更する。
あわせて、全XDDPスキルで同じ問題が潜在するため、共通アルゴリズムを `CLAUDE.md` に定義し、全14スキル（`xddp.01.init` を除く）へ適用する。

これにより、ユーザーが CR ディレクトリ内や任意のサブディレクトリからコマンドを実行してもワークスペースルートの `xddp.config.md` が正しく発見される。

---

## 2. 変更対象ファイル

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `ClaudeCode/.claude/CLAUDE.md` | 修正 | `xddp.config.md` 上位探索アルゴリズムのセクションを追加 |
| `ClaudeCode/.claude/skills/xddp.close.md` | 修正 | `Read xddp.config.md (project root)` → 上位探索に変更（複数箇所: ヘッダー + Step C2〜C5 のDOCS_DIR読み込み） |
| `ClaudeCode/.claude/skills/xddp.02.analysis.md` | 修正 | 同上（複数箇所: ヘッダー + Step B レビューループ内） |
| `ClaudeCode/.claude/skills/xddp.03.req.md` | 修正 | 同上（複数箇所: ヘッダー + Step B レビューループ内） |
| `ClaudeCode/.claude/skills/xddp.04.specout.md` | 修正 | 同上（複数箇所） |
| `ClaudeCode/.claude/skills/xddp.05.arch.md` | 修正 | 同上（複数箇所: ヘッダー + Step B レビューループ内） |
| `ClaudeCode/.claude/skills/xddp.06.design.md` | 修正 | 同上（複数箇所: ヘッダー + Step B レビューループ内） |
| `ClaudeCode/.claude/skills/xddp.07.code.md` | 修正 | 同上（要実装時確認） |
| `ClaudeCode/.claude/skills/xddp.08.test.md` | 修正 | 同上（複数箇所: ヘッダー + Step B レビューループ内） |
| `ClaudeCode/.claude/skills/xddp.09.specs.md` | 修正 | 同上（複数箇所: ヘッダー + Step A2 レビューループ内） |
| `ClaudeCode/.claude/skills/xddp.status.md` | 修正 | 同上（要実装時確認） |
| `ClaudeCode/.claude/skills/xddp.review.md` | 修正 | 同上（要実装時確認） |
| `ClaudeCode/.claude/skills/xddp.revise.md` | 修正 | 同上（要実装時確認） |
| `ClaudeCode/.claude/skills/xddp.excel2md.md` | 修正 | 同上（要実装時確認） |
| `ClaudeCode/.claude/skills/xddp.md2excel.md` | 修正 | 同上（要実装時確認） |

※ `xddp.01.init` は対象外。init はワークスペースルートに `xddp.config.md` を**生成**するコマンドであり、cwdが生成先になる。

---

## 3. 変更内容

### 3.1. `ClaudeCode/.claude/CLAUDE.md` — 上位探索アルゴリズムの追加

**変更前（末尾）:**
```
（既存の内容）
```

**変更後（末尾に追記）:**
```markdown
## xddp.config.md 探索アルゴリズム

XDDP スキル（`xddp.01.init` を除く）は、`xddp.config.md` を以下の手順で発見する。

1. cwd に `xddp.config.md` が存在するか確認する
2. 存在しない場合、親ディレクトリを順に確認する（cwd → parent → grandparent → …）
3. ファイルが見つかった最初のディレクトリを **ワークスペースルート** とし、そのファイルを読み込む
4. ファイルシステムのルートまで探索しても見つからない場合は、
   "xddp.config.md が見つかりません。ワークスペースルートまたはそのサブディレクトリで実行してください。"
   を報告して停止する

> **Note:** `xddp.01.init` のみ例外。init は cwd に `xddp.config.md` を生成するコマンドであり、上位探索は行わない。
```

**理由:** DRY原則。共通アルゴリズムを1箇所に定義し、各スキルから参照する。

---

### 3.2. 各スキルファイル — 参照文の変更

**変更前パターン（1回目: ヘッダーの XDDP_DIR 解決）:**
```
Read `xddp.config.md` (project root) and extract `XDDP_DIR` (default: `.` if the key is absent). Let `CR_PATH` = `{XDDP_DIR}/{CR}`.
```

**変更後パターン（1回目: ヘッダーの XDDP_DIR 解決）:**
```
Find `xddp.config.md` by upward search (CLAUDE.md — xddp.config.md 探索アルゴリズム).
Let `WORKSPACE_ROOT` = the directory where `xddp.config.md` was found.
Extract `XDDP_DIR` (default: `xddp` if the key is absent). Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.
```

エラー停止処理は CLAUDE.md のアルゴリズム step 4 に一元化済みのため、スキル個別のエラー記述は不要。

---

**変更前パターン（2回目以降: レビューループ内の REVIEW_MAX_ROUNDS 等）:**
```
Read `xddp.config.md` (project root). Extract `REVIEW_MAX_ROUNDS.XXX` ...
```

**変更後パターン（2回目以降）:**
```
Read the `xddp.config.md` found earlier (`{WORKSPACE_ROOT}/xddp.config.md`). Extract `REVIEW_MAX_ROUNDS.XXX` ...
```

---

**xddp.close.md 固有の追加変更（R-001 対応）:**

PLAN-20260430 で追加した Step C2〜C5 の `xddp.config.md` 読み込みも変換対象とする。
Step C2 の現在パターン：
```
`xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`）。
```

変更後：
```
ヘッダーで発見した `{WORKSPACE_ROOT}/xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`）。
```

同様に Step C4・Step C5 冒頭の `xddp.config.md` 参照もすべて `{WORKSPACE_ROOT}/xddp.config.md` に置き換える。

---

## 4. 影響範囲

- **影響するスキル・コマンド:** 全14スキル（xddp.01.init を除く）
- **影響する工程:** 工程2〜15・close・review・revise・status・excel変換
- **後方互換性:** 完全互換。ワークスペースルートで実行する既存の使い方はそのまま動作する。サブディレクトリからの実行が新たに許容されるのみ。

---

## 5. 確認項目

- [ ] スキル・コマンドの同期（commands への影響なし — 内部処理のみの変更）
- [ ] 実装前に全14スキルの `Read \`xddp.config.md\`` 出現箇所数を grep で確認し、2回目以降は「found earlier」パターンに変換する
- [ ] ワークスペースルートから実行 → 従来通り動作することを確認
- [ ] CR ディレクトリ（`xddp/{CR}/`）から実行 → 上位探索で `xddp.config.md` が発見されることを確認
- [ ] `xddp.config.md` が存在しないディレクトリから実行 → エラーメッセージで停止することを確認
- [ ] xddp.close.md の Step C2〜C5 の `xddp.config.md` 参照がすべて `{WORKSPACE_ROOT}/xddp.config.md` に置き換わっていることを確認
- [ ] XDDP_DIR のデフォルト値が全スキルで `xddp` に統一されていることを確認（`default: '.' if the key is absent` が残っていないこと）
- [ ] CLAUDE.md のアルゴリズム step 4 のエラーメッセージが各スキルで機能することを確認（xddp.close 個別のエラー記述が削除されていること）

---

## 6. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | |
| 承認日 | |
| 備考 | |
