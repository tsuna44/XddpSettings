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
4. 確認項目 covers: normal paths, error paths, boundary values, and — REFERENCE_FILES に回帰の候補の要約（regression-digest-*.md）が含まれる場合は、
   要約の確認対象の候補がすべて §7 の確認種別「回帰」の行（「回帰の候補」列）か §7.1 にあり、§7.1 の理由がコードで確かめた具体的な内容であること
   （「関係なし」「影響なし」だけの理由は 🟡）。回帰の行の確認内容が、起点の変更シンボルの変更で壊れうる振る舞いを具体的に書いていること。
   SPO-{CR}.md が含まれない場合（新規開発モード）は新規コンポーネント間の依存整合性
   （CHD の確認項目に記載される「Inter-SP dependency integration」観点）。
   §7.1 が「なし」なのは、要約が REFERENCE_FILES に無い場合（確認対象の無いバッチ・Step A3 を行わない CHD）は正しい。
   （要約は最新の Step A3 の確認対象のあるバッチにだけ置かれる。古い要約は Step A3 が消す）
   （quick 時（`QUICK_PROFILE: true`）: 検査対象を normal paths（全 SP の After 条件）・SP が明示的に言及するエラー条件・
   要約の確認対象の候補（距離1）に対する regression・インタフェース契約遵守・（新規開発モード時）Inter-SP dependency integration に限定する。
   boundary values の網羅の欠落は仕様であり、指摘してはならない）
5. Changed interfaces are fully documented in Section 6（インタフェース設計）
6. Every design entry traces to an SP/SR/UR
7. Section 4 が1行1識別子で、種別・変更の内容が埋まり、第3章・第5章・第6章で変える要素がすべて載っていること。型のメンバー（メソッド・フィールド）が言語によらず `{型名}::{名前}` で書かれていること（`Foo.bar` と書くとグローバル変数のフィールドとして検索され、回帰の候補が漏れる。🟡）

## Downstream Readiness: CHD → TSP（QAエンジニア視点）

1. 確認項目（Section 7）がすべて TC（テストケース）として変換できる粒度か
2. エラーパス・境界値・NULL/空値のケースが確認項目として網羅されているか
3. 変更インタフェース（Section 6）の入出力仕様が明確で、等価クラス・境界値を特定できるか
4. REFERENCE_FILES に SPO-{CR}.md が含まれる場合: Section 7 の確認種別「回帰」の行から、
   デグレード確認の TC を設計できるか（確認内容が、変わってはならない既存の振る舞いを TC の期待結果にできる粒度で書かれているか）。
   含まれない場合（新規開発モード）: CHD 確認項目の
   「Inter-SP dependency integration」観点（本ファイル「CHD (Change Design Document)」チェックリスト
   項目4参照）から、新規コンポーネント間の依存整合性を確認する TC を設計できるか
5. テストデータ・前提環境の準備に必要な情報が十分で、テスト計画を立てられるか
