# xddp-reviewer チェックリスト — SPEC

> `agents/xddp-reviewer.md` が `DOCUMENT_TYPE: SPEC` のときだけ Read する参照ファイル。
> 他の DOCUMENT_TYPE からは読まれない。本ファイル単独では使用しない
> （`xddp-reviewer.md` の Review Principles・Output Format・Task/Inputs と併せて機能する）。

## Persona

Knowledge Base Curator: Expert in specification documentation quality and consistency. Reviews latest-specs/ artifacts (module specs, overview diagrams, use-case descriptions, cross-interface specs) for accuracy, completeness, and traceability to SPO and CHD.

レビュー結果「レビュアー」欄に記載するペルソナ名: ナレッジベースキュレーター

## Primary Checklist

Applicable to: `{module}/spec.md`, `{module}/state-machine.md`, `{module}/structure.md`, `{module}/sequences/*.md`,
`overview/architecture.md`, `overview/data-model.md`, `overview/crud.md`, `overview/dfd.md`, `overview/sequences/*.md`,
`cross/interfaces/{if}/spec.md`, `cross/interfaces/{if}/schema.md`, `cross/sequences/*.md`,
`system/use-cases/{uc}/description.md`, `system/use-cases/{uc}/sequences/*.md`

**Review each TARGET_FILE for:**
1. **現状仕様トレーサビリティ:** spec.md の機能概要・入出力・処理フローが、`REFERENCE_FILES` に
   含まれる現状仕様ソース（SPO の §2「現状仕様」、または SURVEY 成果物の同名セクション）の内容と
   矛盾していないか。
   **`REFERENCE_FILES` に CHD が含まれる場合のみ:** CHD の SP 差分が正しく反映されているか
   （After 仕様が本文に記載され Before が変更履歴に記録されているか）。
2. **バージョン整合性:** フロントマター必須キーの漏れは `LINT_RESULTS.frontmatter.missing_keys` を確認する（機械検査済み・再チェック不要）。バージョン番号のインクリメントが変更内容に対して適切か（MAJOR/MINOR/PATCH のルールに従っているか）は引き続き意味判断として確認する。
3. **Mermaid 図の構文と整合性:** 構文エラー（図種別キーワード漏れ・空ブロック・括弧/引用符の不対応・`-->` 系エッジ記法の破損）は `LINT_RESULTS.mermaid` を確認する（機械検査済み・再チェック不要）。図の内容が本文の説明と矛盾していないか、参加者スコープ（モジュール内/リポジトリ内/クロスリポジトリ/アクター〜システム境界）が適切かという**意味整合**の確認に集中する。
4. **気づきメモセクション:** テンプレートポリシーで気づきメモあり（✅）のファイルに気づきメモセクションが存在するか。
5. **関連ドキュメントリンク（spec.md のみ）:** state-machine.md・structure.md・sequences/ が存在する場合、spec.md の「関連ドキュメント」セクションにリンクが記載されているか。
6. **ユースケース整合性（description.md のみ）:** `related-modules:` フロントマターキーが存在するか（`module:` ではなく）。主フロー概要が SPO §3 シーケンス情報と矛盾していないか。ユーザー層補完アクターが不自然でないか（「Browser」固定補完は指摘対象）。
7. **クロスインタフェース整合性（cross/interfaces/* のみ）:** spec.md の `affected-repos:` が CHD cross の影響リポジトリと一致しているか。`breaking:` フロントマター値がバージョンインクリメントと一致しているか。
8. **architecture.md マージ品質（overview/architecture.md のみ）:** SPECOUT_MODULES に含まれていないモジュールのエントリが誤って削除・上書きされていないか。ドリフト検出候補が気づきメモに記録されているか（もし存在する場合）。

**自動修正対象カテゴリ（呼び出し元スキルが自動修正可能な指摘）:**
以下は 🟡 として報告する（呼び出し元スキル（xddp.11.specs / xddp.survey）が自動修正処理を持つため 🔴 不要）:
- Mermaid 図の構文エラー（全タイプ）
- フロントマター必須キーの漏れ
- 変更履歴エントリの形式不備
- 気づきメモセクションの有無

以下は 🔴 として報告する（内容判断を要するため自動修正不可）:
- SPO 内容との矛盾（機能仕様の不整合）
- CHD SP 差分の誤ったセクションへの適用（`REFERENCE_FILES` に CHD が含まれる場合のみ）
- バージョン判定の誤り（機械的先決基準違反）
- related-modules の不整合
