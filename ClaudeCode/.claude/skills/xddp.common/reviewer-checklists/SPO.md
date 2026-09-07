# xddp-reviewer チェックリスト — SPO

> `agents/xddp-reviewer.md` が `DOCUMENT_TYPE: SPO` のときだけ Read する参照ファイル。
> 他の DOCUMENT_TYPE からは読まれない。本ファイル単独では使用しない
> （`xddp-reviewer.md` の Review Principles・Output Format・Task/Inputs と併せて機能する）。

## Persona

Experienced Software Developer (with design skills): Deep understanding of codebases and ripple analysis. Focuses on accuracy of existing specs, validity of ripple search, and risk of overlooked impacts.

レビュー結果「レビュアー」欄に記載するペルソナ名: 経験豊富な開発者

## Primary Checklist

**Structure:** The SPO consists of four file types. TARGET_FILE is the summary (SPO-{CR}.md).
Module files (modules/*-spo.md), the funcmap file (SPO-{CR}-funcmap.md), and cross-module files (cross-module/*-cross.md) are included in REFERENCE_FILES — reference them as needed.

**Summary file (SPO-{CR}.md) checks:**
1. Section 5.1 (直接影響箇所) includes all files that the subsequent CHD will modify
2. Section 5.2 (間接影響箇所・波紋) records indirect impact files (Wave 1 onward) with sufficient breadth
   （quick 時（`QUICK_PROFILE: true`）: 5.2 は代表例のみの記載が仕様である（`SPO_DETAIL_LEVEL: brief`）。
   網羅性の不足を指摘してはならない。代わりに (a) 代表例のみである旨の注記が 5.2 に存在するか、
   (b) 記載された代表例が discovery-log.md の内容と矛盾していないか、の2点のみを検査する）
3. Section 5.3 (影響なしと判断した範囲) has explicit exclusion reasons (simply saying "not related" is insufficient)
4. funcmap file (SPO-{CR}-funcmap.md) §1 の機能ソースコード対応表が以下の基準を満たすか
   - `SPO-{CR}-funcmap.md` が REFERENCE_FILES に列挙されているが Read 時にファイルが物理的に存在しない場合はチェック項目4をスキップし、
     レビューレポートに「funcmap 未生成のためチェック項目4を検査不可（/xddp.04.specout を document モードで実行してください）」と記録すること。
   - `SPO-{CR}-funcmap.md` が REFERENCE_FILES に列挙されていない場合（cross/ リポジトリなど仕様として funcmap が生成されないケース）はチェック項目4をスキップし、
     レビューレポートに「cross/ リポジトリのため funcmap は生成対象外。チェック項目4はスキップ（仕様）」と記録すること。
   - CRS の全 SP 項目をカバーしているか（行抜けなし）
   - 全行で「直接呼び出し元数」が記入されているか（空欄なし）
     discovery-log.md が REFERENCE_FILES に列挙されている場合: 対象識別子について、discovery-log.md の
     Wave 0 テーブルから「派生元」列に「CRS（初期シンボル: {対象識別子}）」を含む行を抽出し、
     そのユニークファイル数を算出して funcmap の「直接呼び出し元数」と機械的に突き合わせる（不一致は
     🔴として報告）。対象識別子そのものの派生元行のみを抽出すること。サブクラス・実装クラス名・
     re-exportファイル由来の initial_symbols も同じ「CRS（初期シンボル: {symbol}）」形式で記載される
     が、{symbol} に入る文字列が対象識別子と異なるため、固定文言一致条件（「{対象識別子}」を含む行）
     では自動的に除外される。Wave 1 以降は対象識別子そのものではなく派生シンボルを検索する波である
     ため、本検証では参照しない。
     discovery-log.md が REFERENCE_FILES に列挙されていない場合（cross/ リポジトリ、discovery-log.md が
     行ID/派生元列を持たない旧フォーマットのCR等）は、フォールバックとして記入有無のみを確認する
     （旧フォーマットへの対応は本プロジェクトの後方互換性ポリシーにより保証しない。再生成を促してよい）。
   - 「影響種別」列の値が SPO-{CR}.md §5.1 の同一識別子と一致しているか
5. Section 7 (変更要求仕様書への反映事項) is described at a granularity that xddp-spec-writer-agent can act on immediately
6. Section 8 (調査済みモジュール一覧) links match the actually created module files

**Per-module files (modules/*-spo.md) checks (verify all files):**
7. Section 2 describes the CURRENT behavior, not the expected behavior after the change
8. Section 2.2 process/logic table enumerates all functions and classes that are change targets
9. Diagrams (Section 4) are consistent with the behavior description in Section 2

**Cross-module file (cross-module/*-cross.md) checks (if it exists):**
10. Structure diagram (Section 2) accurately shows inter-module dependency directions
11. Sequence diagrams (Section 3) are created for each level specified in SPECOUT_SEQUENCE_LEVELS
12. If async processing exists, it is explicitly noted

**SPO レビュー追加基準（Section 4.1 / 4.2 / 5.5テスト可能性 / 5.6 / 5.7）:**
- Section 4.1（外部副作用一覧）が存在するか:
    - 副作用がない場合は「副作用なし」と明記されているか（空欄・省略は NG）
    - MODULE-LEVEL エントリがある場合は「（MODULE-LEVEL） | {モジュールパス}/* | 調査未実施 | — | ...」
      形式の行が存在するか
- Section 4.2（データフロー図）が存在するか:
    - 副作用あり時: Mermaid DFD（graph LR）が記載されているか（「副作用なし（省略）」は NG）
    - 副作用なし時: 入出力データフロー図（Mermaid graph LR）が記載されているか（「副作用なし（省略）」は NG）
    - どちらの場合も `{SIDE_EFFECTS_DFD_PLACEHOLDER}` のプレースホルダーが残っていないか（残存は 🔴）
- Section 5.5 に「テスト可能性」列が存在し、すべての行に値（DI可能/密結合/シングルトン/未確認/
  未確認（MODULE-LEVEL）またはそれらの多値列挙）が記入されているか
- Section 5.6（非機能特性・実装制約の観察）が存在するか:
    - 観察がなかった場合は「観察なし」と明記されているか（空欄・省略は NG）
    - MODULE-LEVEL エントリがある場合は「MODULE-LEVEL のため詳細調査未実施。影響度: 高」が記録されているか
- Section 5.7（既知制約との照合）が存在するか:
    - code-knowledge 参照なし、または該当制約なしの場合は「対象外（...）」と明記されているか（空欄は NG）
    - MODULE-LEVEL エントリがある場合は「MODULE-LEVEL のため制約照合未実施｜未確認（MODULE-LEVEL）」が記録されているか
    - 「矛盾あり」の行がある場合、Section 7（変更要求仕様書への反映事項）に対応する記載があるか
      （矛盾を発見したのに後続工程への申し送りがない場合は 🔴）

## Downstream Readiness: SPO → DSN（SWアーキテクト視点）

1. 直接影響ファイルの責務・インタフェース（関数シグネチャ・プロトコル・バスI/F・レジスタ等）が把握できるか
2. 既存設計パターン・制約が記録されており、設計選択肢を実態に基づいて絞り込めるか
3. 波及リスクが定量的（ファイル数・モジュール数等）に把握でき、変更スコープを確定できるか
4. テスト容易性の観察（密結合・シングルトン等）が記録されており、設計時に対処を検討できるか
5. 非機能特性（機能安全（Functional Safety）・セキュリティ・タイミング制約・リソース制約等）の観察が記録されているか
