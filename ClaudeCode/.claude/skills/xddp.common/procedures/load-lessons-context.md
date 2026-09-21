# Load Lessons Context

> xddp.common の共通プロシージャ。呼び出し元スキルから apply される。

## Load Lessons Context

lessons-learned.md のタグ別インデックスを使い、対象タグに該当するエントリのみを選択的に読み取る共通手順
（全文読み取りによるコンテキスト消費を避ける。E-01 対応）。各スキルの「知見ログ参照」ステップから apply して使用する。

**Input:**
- `LESSONS_FILE`: lessons-learned.md のパス
- `TARGET_TAGS`: 対象タグのリスト（例: `[#要求分析, #仕様定義, #見落とし]`）

**Output:** `LESSONS_CONTEXT`（該当エントリの本文を連結した文字列。該当エントリがない場合は空文字列）

**Process:**
1. If `{LESSONS_FILE}` が存在しない: `LESSONS_CONTEXT` = 空文字列を返して終了する。
2. Read `{LESSONS_FILE}`。
3. `## タグ別インデックス` セクションを確認する。
   - セクションが存在しない、またはテーブル内の対象タグ行がすべて `—`（未 populate）の場合:
     **フォールバック** — `## 知見詳細` 全体を対象に `TARGET_TAGS` のいずれかをタグに含むエントリを
     抽出する（既存の互換動作。インデックス未整備の既存ファイルでも動作することを保証する）。
   - セクションが存在し、対象タグ行の少なくとも1行にエントリ番号が記載されている場合（`TARGET_TAGS` の一部のみ
     populate 済みの場合を含む）:
     `TARGET_TAGS` に対応する行のエントリ番号（カンマ区切り、例 `LL-003, LL-005`）を集約し重複を除いた
     `TARGET_IDS` を求める。未 populate（`—`）の行は0件として扱う（フォールバックには遷移しない。
     populate 済みの行から得られる結果のみで集約すれば安全に動作するため）。`## 知見詳細` セクションから
     `### {id}：` に一致するエントリのみを抽出する（他のエントリは `LESSONS_CONTEXT` に含めない）。
4. 抽出したエントリ本文（タイトル〜次のエントリ直前まで）を連結し `LESSONS_CONTEXT` とする。
5. Return `LESSONS_CONTEXT`.
