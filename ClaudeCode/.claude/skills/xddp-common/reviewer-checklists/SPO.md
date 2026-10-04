# xddp-reviewer チェックリスト — SPO

> `agents/xddp-reviewer.md` が `DOCUMENT_TYPE: SPO` のときだけ Read する参照ファイル。
> 他の DOCUMENT_TYPE からは読まれない。本ファイル単独では使用しない
> （`xddp-reviewer.md` の Review Principles・Output Format・Task/Inputs と併せて機能する）。

## Persona

Experienced Software Developer (with design skills): Deep understanding of codebases and ripple analysis. Focuses on accuracy of existing specs, validity of ripple search, and risk of overlooked impacts.

レビュー結果「レビュアー」欄に記載するペルソナ名: 経験豊富な開発者

## Primary Checklist

**Structure:** TARGET_FILE は SPO-{CR}.md。直接影響のモジュール資料と `work/digest/index.md` が REFERENCE_FILES に入る。
funcmap・funcmap-counts・discovery-log は渡されない。機械検査の結果は `LINT_RESULTS` の `spo` カテゴリで渡されるので転記する。

**L1 影響範囲の十分性（🔴）:** CRS の要求（各 UR/SR/SP）に照らして、変更で影響を受ける機能が SPO の
影響範囲（§5.0 機能一覧・§5.1 直接影響・§5.2 間接影響・直接影響のモジュール資料 §2.2 の変更対象の関数）と
除外の判断（§5.3。「無関係」だけの理由は不十分）に漏れなく含まれているか。漏れが疑われるときは母体コードを
確認し、根拠のファイルと行を示して指摘する（確認していない場合は「確認していません」と書く）。
（`QUICK_PROFILE: true` のとき §5.2 は代表例のみが仕様であり、網羅性の不足を指摘してはならない。）

## Downstream Readiness: SPO → DSN（SWアーキテクト視点）

**L2 設計への申し送り（🟡）:** 設計に必要な情報（直接影響ファイルの責務・インタフェース、既存の設計パターン・制約、
§5.7 で「矛盾あり」とした既知制約との矛盾）が §7（変更要求仕様書への反映事項）と直接影響のモジュール資料にあり、
SW アーキテクトが設計選択肢を絞り込めるか。矛盾を発見したのに §7 に申し送りがない場合は 🔴 とする。
