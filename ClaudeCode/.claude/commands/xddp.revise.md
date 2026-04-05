You are executing XDDP Revise: Apply Human Review Comments to a Document (人レビュー指摘の反映).

**Arguments:** $ARGUMENTS = CR_NUMBER DOCUMENT_TYPE
- CR_NUMBER: e.g., `REQ-2026-001`
- DOCUMENT_TYPE: one of `analysis`, `req`, `arch`, `design`, `test`, or a file path

If DOCUMENT_TYPE is omitted, ask the user which document to revise.

---

## Instructions

### 1. Identify the target document
Map DOCUMENT_TYPE to the file path:
- `analysis`  → `{CR_NUMBER}/02_analysis/ANA-{CR_NUMBER}.md`
- `req`       → `{CR_NUMBER}/03_change-requirements/CRS-{CR_NUMBER}.md`
- `arch`      → `{CR_NUMBER}/05_architecture/DSN-{CR_NUMBER}.md`
- `design`    → `{CR_NUMBER}/06_design/CHD-{CR_NUMBER}.md`
- `test`      → `{CR_NUMBER}/09_test-spec/TSP-{CR_NUMBER}.md`
- Otherwise: treat DOCUMENT_TYPE as a file path.

### 2. Ask for review comments
Tell the user:
> 修正したい箇所と内容を教えてください。以下の形式で入力してください：
> - セクション名または行番号（任意）
> - 指摘内容または修正内容
> 
> 複数の指摘がある場合はリスト形式で入力してください。

Wait for the user's input.

### 3. Apply the revisions
Read the target document. Apply each revision the user specified:
- Make minimal, targeted changes — do not rewrite unaffected sections.
- Preserve document structure and format.
- Ensure consistency between changed sections and the rest of the document.

### 4. Record the revisions
In a corresponding review file (e.g., `{CR_NUMBER}/review/XX_doctype-review.md`):
- If the file exists: append the human review items and mark them ✅ 対応済.
- If it does not exist: create one using the review template format, with reviewer "人間（{今日の日付}）".

### 5. Update version history in the target document
Increment version by 0.1, today's date, Author: "人" or user-provided name, brief description of revisions.

### 6. Display summary in Japanese
Report what was changed, the new version number, and ask if further revisions are needed.
