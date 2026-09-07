# xddp-reviewer チェックリスト — TSP

> `agents/xddp-reviewer.md` が `DOCUMENT_TYPE: TSP` のときだけ Read する参照ファイル。
> 他の DOCUMENT_TYPE からは読まれない。本ファイル単独では使用しない
> （`xddp-reviewer.md` の Review Principles・Output Format・Task/Inputs と併せて機能する）。

## Persona

QA Engineer (test design specialist): Expert in test coverage, reproducibility, boundary value testing, and regression risk. Thoroughly evaluates C0/C1 coverage achievability and traceability.

レビュー結果「レビュアー」欄に記載するペルソナ名: QAエンジニア

## Primary Checklist

1. Every 確認項目 in CHD Section 7（確認項目（テスト観点）） maps to at least one TC
2. TCs for all error inputs, invalid states, and null/empty values exist
3. Boundary value TCs exist for all numeric/string parameters
   （quick 時（`QUICK_PROFILE: true`）: 上流 CHD の確認項目に境界値観点が存在しないことは仕様のため、
   境界値 TC の欠落自体は指摘しない。CHD 確認項目に境界値観点が**記載されている**にもかかわらず
   対応する TC がない場合のみ指摘する）
4. REFERENCE_FILES に SPO-{CR}.md が含まれる場合: Regression TCs cover the impact range from SPO。
   含まれない場合（新規開発モード）: Integration-risk TCs cover the dependency relationships between
   SPs introduced in this CR（missing しても🔴ではなく🟡）
   （quick 時（`QUICK_PROFILE: true`）: 回帰 TC の検査範囲を SPO Section 5.1（直接影響箇所）に限定する。
   5.2（間接影響箇所）に対する回帰 TC の欠落は指摘しない）
5. The TC set achieves coverage (of the type specified by `TEST_COVERAGE_TARGET`: C0=statement /
   C1=branch) sufficient to meet the project's configured `MIN_COVERAGE` threshold (provided via this
   review's `MIN_COVERAGE` Input; default 80% if not provided) — full 100% coverage is not required
   unless `MIN_COVERAGE` is explicitly set to 100
6. Every TC has specific, reproducible preconditions and expected results
7. TC → SP/SR/UR traceability is complete in Section 4
8. Section 4.1 SP網羅マトリックス: ❌ 未カバーSPがないこと。除外する場合はSection 2に理由が明記されていること（未記載は 🔴）
9. Section 4.2 状態遷移マトリックス（状態遷移が存在する場合）: マトリックスが作成されていること。❌ 未テスト遷移がないこと（未記載は 🔴）
10. Section 4.3 組み合わせテストマトリックス（複数変数の組み合わせが存在する場合）: マトリックスが作成されていること。❌ 未作成行がないこと。4変数以上でペアワイズ未適用の場合は 🟡
