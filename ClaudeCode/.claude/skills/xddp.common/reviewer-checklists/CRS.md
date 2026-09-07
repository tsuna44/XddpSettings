# xddp-reviewer チェックリスト — CRS

> `agents/xddp-reviewer.md` が `DOCUMENT_TYPE: CRS` のときだけ Read する参照ファイル。
> 他の DOCUMENT_TYPE からは読まれない。本ファイル単独では使用しない
> （`xddp-reviewer.md` の Review Principles・Output Format・Task/Inputs と併せて機能する）。

## Persona

Senior Requirements Engineer: Expert in UR/SR/SP hierarchical consistency and spec completeness. Strictly evaluates USDM structure, traceability, and edge case coverage.

レビュー結果「レビュアー」欄に記載するペルソナ名: シニア要求エンジニア

## Primary Checklist

1. Every UR is covered by at least one SR
2. Every SR is covered by at least one SP
3. Every SP has Before (or "なし") and After content（`DEVELOPMENT_MODE: change` の場合。TARGET_FILE の
   SP 記述が `**仕様：**` 形式であれば新規開発モードと判断し、代わりに「目標動作が具体的に記述され、
   実装者が質問なしに実装できる粒度か」を確認する）
4. TM correctly maps UR → SR → SP with no gaps
5. No contradictions between requirements
6. USDM structure: requirement + reason + specification
7. New edge cases and error specifications are present
8. **USDM semantic review points（言語判断が必要な観点。機械検査 `LINT_RESULTS.crs` とは別に確認する）:**
   - 各 SR が振る舞い（動詞連鎖）で書かれ、動詞が 5〜7 個程度に収まっているか（8 個以上なら分割を提案）（出典: AFFORDD USDM小冊子 基礎編 4.2.2）
   - SR の各動詞＋目的語に仕様グループが 1 対 1 対応しているか（対応する仕様グループの欠落を検出）（出典: 補足編 2.3）
   - 各 SP が「コードがイメージできる」粒度か（抽象すぎる SP は要求として再考を提案）（出典: 補足編 2.4）
   - 各 SP が親 SR の範囲内に収まっているか（範囲外仕様の混入を検出）（出典: 基礎編 メリット④）
   - 述語が「〜しない」で終わる SP に、else 側（それ以外の条件）の仕様が併記されているか（出典: 基礎編 4.5.4）
   - 要求が名詞形（「〜の表示」等）で書かれていないか（動詞形「〜する／〜したい」に直すよう提案）（出典: 基礎編 2.2.3）
   （参考チェックリスト: `docs/refs/usdm-notation-rules.md` §12・`docs/refs/usdm-canonical-schema-rules.md` §11 を観点の根拠として参照する）

## Downstream Readiness: CRS → SPO（経験豊富な開発者視点）

1. 各 SP の「変更前」記述に影響ファイル・モジュールの手がかりがあり、初期調査クエリを立てられるか
2. SP の「変更後」記述が具体的で、どのソースコード箇所を探すべきかわかるか
3. スコープが明確で、調査境界（どこまで波及調査するか）を判断できるか
4. 依存モジュール・外部システムへの言及があり、波及調査の起点を設定できるか
5. 変更量の規模（小・中・大）が推定でき、調査計画を立てられるか

## Downstream Readiness: CRS → DSN（新規開発モード。SWアーキテクト視点）

1. 各SPの「仕様」記述から、新規実装すべきインタフェース（関数シグネチャ・プロトコル・データ構造等）の
   概要が把握できるか
2. 非機能要求（性能・セキュリティ・信頼性等）がCRSに明記されており、設計選択肢を実態に基づいて
   絞り込めるか
3. 依存する外部システム・ライブラリへの言及があり、設計時の技術選定に活用できるか
4. 想定規模（UR/SR/SP数）が把握でき、設計範囲・工数を見積もれるか
5. 付記B（前提条件・実装参考情報）に、設計判断に必要な制約が記録されているか

## Downstream Readiness: CRS → CHD（工程5をスキップする経路。シニア開発者視点）

`CR_PROFILE: quick` かつ `DEVELOPMENT_MODE: new` の場合、工程4（スペックアウト）と工程5（実装方式
検討）がともにスキップされ、CRS が CHD の直接の入力になる。この経路でのみ使用する。

1. 各SPの「仕様」記述から、実装すべきインタフェース（関数シグネチャ・プロトコル・データ構造等）を
   CHD Section 6（インタフェース設計）に落とせる粒度で把握できるか
2. 新規データ構造の仕様が、CHD Section 5（データ設計）を埋められる程度に記述されているか
3. SP 間の依存関係（実装順序に影響するもの）が読み取れるか
4. 非機能要求（性能・セキュリティ・信頼性等）が明記されており、設計判断の制約として使えるか
5. DSN が存在しないため、設計方式の選択判断を CHD 作成時に行う必要がある。その判断に必要な制約が
   CRS 本文または付記B（前提条件・実装参考情報）に記録されているか
