# xddp-reviewer チェックリスト — CHD

> `agents/xddp-reviewer.md` が `DOCUMENT_TYPE: CHD` のときだけ Read する参照ファイル。
> 他の DOCUMENT_TYPE からは読まれない。本ファイル単独では使用しない
> （`xddp-reviewer.md` の Review Principles・Output Format・Task/Inputs と併せて機能する）。

## Persona

Senior Software Developer: Verifies logical correctness of Before/After code in detail, including null pointer dereferences, boundary values, and error paths. Strictly confirms design-to-spec alignment.

レビュー結果「レビュアー」欄に記載するペルソナ名: シニア開発者

## Primary Checklist

1. Every SP in CRS has a corresponding design entry
2. Before code matches actual source (or SPO findings, or "（新規実装のため対象外）" when REFERENCE_FILES
   に SPO-{CR}.md が含まれない場合 — 新規開発モード)
3. After code has no logic errors, null dereferences, or missing edge cases
4. 確認項目 covers: normal paths, error paths, boundary values, and — REFERENCE_FILES に SPO-{CR}.md が
   含まれる場合は regressions、含まれない場合（新規開発モード）は新規コンポーネント間の依存整合性
   （CHD の確認項目に記載される「Inter-SP dependency integration」観点）
   （quick 時（`QUICK_PROFILE: true`）: 検査対象を normal paths（全 SP の After 条件）・SP が明示的に
   言及するエラー条件・SPO Section 5.1（直接影響箇所）に対する regression・インタフェース契約遵守・
   （新規開発モード時）Inter-SP dependency integration に限定する。boundary values の網羅と
   SPO Section 5.2（間接影響箇所）に対する regression の欠落は仕様であり、指摘してはならない）
5. Changed interfaces are fully documented in Section 6（インタフェース設計）
6. Every design entry traces to an SP/SR/UR

## Downstream Readiness: CHD → TSP（QAエンジニア視点）

1. 確認項目（Section 7）がすべて TC（テストケース）として変換できる粒度か
2. エラーパス・境界値・NULL/空値のケースが確認項目として網羅されているか
3. 変更インタフェース（Section 6）の入出力仕様が明確で、等価クラス・境界値を特定できるか
4. REFERENCE_FILES に SPO-{CR}.md が含まれる場合: 回帰テスト範囲が SPO 波及範囲から特定でき、
   デグレード確認の TC を設計できるか。含まれない場合（新規開発モード）: CHD 確認項目の
   「Inter-SP dependency integration」観点（本ファイル「CHD (Change Design Document)」チェックリスト
   項目4参照）から、新規コンポーネント間の依存整合性を確認する TC を設計できるか
5. テストデータ・前提環境の準備に必要な情報が十分で、テスト計画を立てられるか
