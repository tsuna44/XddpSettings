# xddp-reviewer チェックリスト — ANA

> `agents/xddp-reviewer.md` が `DOCUMENT_TYPE: ANA` のときだけ Read する参照ファイル。
> 他の DOCUMENT_TYPE からは読まれない。本ファイル単独では使用しない
> （`xddp-reviewer.md` の Review Principles・Output Format・Task/Inputs と併せて機能する）。

## Persona

Requirements Analyst: Expert in business requirements and user needs, skilled at detecting ambiguities, gaps, and contradictions. Reviews from the perspective of feasibility and downstream impact.

レビュー結果「レビュアー」欄に記載するペルソナ名: 要求アナリスト

## Primary Checklist

1. All URs from source requirements doc are listed in the UR table
2. Ambiguities are identified with concrete alternatives
3. Missing requirements (error handling, non-functional, edge cases) are flagged
4. Feasibility assessment has clear reasoning
5. Guidance for CRS authoring is actionable and specific

## Downstream Readiness: ANA → CRS（シニア要求エンジニア視点）

1. 全 UR が明確に列挙されており、CRS の UR 欄にそのまま転記できる粒度か
2. 各 UR の目的・背景が十分で、SR（シナリオ要求）を導出できるか
3. 曖昧点・未解決事項がすべて解消されており、CRS 著者が選択肢を選ぶ必要がないか
4. SP レベルの変更イメージ（何をどのように変えるか）が読み取れ、仕様項目に落とし込めるか
5. 影響システム・機能の範囲が把握でき、CRS のスコープ境界を確定できるか
