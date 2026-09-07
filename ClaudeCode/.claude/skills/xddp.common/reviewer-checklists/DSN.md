# xddp-reviewer チェックリスト — DSN

> `agents/xddp-reviewer.md` が `DOCUMENT_TYPE: DSN` のときだけ Read する参照ファイル。
> 他の DOCUMENT_TYPE からは読まれない。本ファイル単独では使用しない
> （`xddp-reviewer.md` の Review Principles・Output Format・Task/Inputs と併せて機能する）。

## Persona

Software Architect: Able to objectively compare and evaluate multiple design approaches. Reviews with focus on technical tradeoffs, risks, and extensibility.

レビュー結果「レビュアー」欄に記載するペルソナ名: SWアーキテクト

## Primary Checklist

1. At least 2 distinct approaches are compared, or 1 approach with explicit justification that no meaningful alternative exists
2. Comparison matrix criteria are objective and complete
3. Recommended approach is fully justified
4. All SP items in CRS are addressable by the recommended approach
5. Risks and mitigations are concrete
6. Section 5 guidance is specific enough to author a CHD

## Downstream Readiness: DSN → CHD（シニア開発者視点）

1. 採用アプローチの実装手順が理解でき、Before/After コードのスケルトンをイメージできるか
2. 各 SP に対する具体的な実装方針があり、コード変更の対象箇所と変更内容が明確か
3. 新規データ構造・インタフェース変更の仕様が十分で、CHD Section 5（データ設計）・Section 6（インタフェース設計）を埋められるか
4. リスク・注意点が具体的で、どのような確認項目を設けるべきか判断できるか
5. 未解決の技術的判断事項が残っておらず、設計者が自己判断せずに詳細設計を開始できるか
