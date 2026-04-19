# XDDP プロセス図 — タスク・成果物フロー

> スキル番号（xddp.0X）と工程番号（progress.md の 1〜15）は別体系です。

---

## レビューパターン（各工程共通）

各工程は以下のレビューサイクルを内包します。

```mermaid
flowchart LR
    ART[/"成果物"/]
    AIR["🤖 xddp-reviewer<br/>(単一エージェント・最大5回ループ)"]
    RVF[/"review/0X_*-review.md<br/>───────────<br/>🔴 重大（要修正・手戻りリスク）<br/>🟡 軽微（修正望ましい）<br/>🔵 提案（任意改善）"/]
    HG["👀 人レビュー待ち<br/>(Human Review Gate)"]
    NXT["次の工程へ"]

    ART --> AIR
    AIR -->|"生成"| RVF
    RVF -->|"🔴🟡 問題あり→自動修正"| ART
    RVF -->|"問題なし"| HG
    HG -->|"xddp.revise で修正"| ART
    HG -->|"確認完了"| NXT
```

> **実装上の注意:** 専門家ペルソナとクリティカルシンキング原則は**1エージェントが同時に担う**（並行実行ではない）。

### xddp-reviewer の内部構造（1回の呼び出し）

```mermaid
flowchart TD
    subgraph REVIEWER["xddp-reviewer（1エージェント・独立コンテキスト）"]
        direction TB
        PERSONA["① 専門家ペルソナ<br/>（文書種別で切り替え）"]
        subgraph CT["② クリティカルシンキング原則（全ペルソナ共通）"]
            direction TB
            CT1["🧠 独立コンテキスト実行<br/>作成者バイアスを排除"]
            CT2["📌 証拠ベース指摘<br/>セクション名・SP番号・行を明示"]
            CT3["🔁 後工程インパクト評価<br/>手戻りリスクを最優先"]
            CT4["🔍 エッジケース追跡<br/>異常系・境界値を確認"]
            CT5["🔗 トレーサビリティ検証<br/>UR→SR→SP→設計→テスト"]
            CT1 --> CT2 --> CT3 --> CT4 --> CT5
        end
    end
    PERSONA -->|"組み合わせて適用"| CT
```

### 専門家ペルソナ一覧（文書種別で切り替え）

| 文書 | ペルソナ | 主なレビュー視点 |
|------|----------|----------------|
| **ANA**（要求分析メモ） | 要件アナリスト | ビジネス要件・ユーザーニーズの網羅性、曖昧さ・抜け漏れ・矛盾の検出、後工程への影響評価 |
| **CRS**（変更要求仕様書） | シニア要件エンジニア | UR→SR→SP の階層的整合性、USDM構造・トレーサビリティ、エッジケース網羅、矛盾検出 |
| **SPO**（スペックアウト） | 経験豊富なソフトウェア開発者 | コードベースへの深い理解、影響範囲分析の妥当性、波紋検索の見落としリスク |
| **DSN**（実装方式検討メモ） | ソフトウェアアーキテクト | 複数案の客観的比較・評価、技術的トレードオフ・リスク・拡張性 |
| **CHD**（変更設計書） | シニアソフトウェア開発者 | Before/After コードの論理的正確性、ヌルポインタ・境界値・エラーパスの網羅、設計と仕様の一致 |
| **TSP**（テスト仕様書） | QAエンジニア（テスト設計専門） | テストカバレッジ・再現性・境界値、C0/C1 達成可能性、CHD確認項目とのトレーサビリティ |

---

## プロセス全体フロー

```mermaid
flowchart TD
    %% ─── 外部入力 ───
    REQ(["📄 要求書<br/>REQ-{CR}.md"])
    SRC(["🗂️ 母体ソースコード<br/>(対象プロジェクト)"])
    KNW(["💡 前CR以前の知見<br/>lessons-learned.md<br/>patterns.md"])
    SPECS(["📖 承認済み仕様書<br/>docs/specs/*.md"])

    %% ─── フェーズ1: 初期化 ───
    subgraph PH1["フェーズ 1｜初期化（工程1）"]
        S01["🔧 xddp.01.init<br/>CRワークスペース初期化"]
        A01[/"📁 フォルダ構成<br/>progress.md / xddp.config.md"/]
    end

    %% ─── フェーズ2: 要求分析 ───
    subgraph PH2["フェーズ 2｜要求分析（工程2）"]
        S02["🔍 xddp.02.analysis<br/>要求分析"]
        A02[/"📝 ANA-{CR}.md<br/>要求分析メモ"/]
    end

    %% ─── フェーズ3: 変更要求仕様書 ───
    subgraph PH3["フェーズ 3｜変更要求仕様書（工程3）"]
        S03["📋 xddp.03.req<br/>変更要求仕様書作成"]
        A03[/"📑 CRS-{CR}.md<br/>変更要求仕様書"/]
    end

    %% ─── フェーズ4: 母体調査 ───
    subgraph PH4["フェーズ 4｜スペックアウト（工程4〜5）"]
        S04["🔎 xddp.04.specout<br/>スペックアウト＋CRS更新"]
        A04[/"🗃️ SPO-{CR}.md<br/>スペックアウトサマリ<br/>modules/*.md"/]
    end

    %% ─── フェーズ5: 方式検討 ───
    subgraph PH5["フェーズ 5｜実装方式検討（工程6）"]
        S05["🏗️ xddp.05.arch<br/>実装方式検討"]
        A05[/"🗺️ DSN-{CR}.md<br/>実装方式検討メモ"/]
    end

    %% ─── フェーズ6: 変更設計 ───
    subgraph PH6["フェーズ 6｜変更設計書（工程7〜8）"]
        S06["✏️ xddp.06.design<br/>変更設計書作成＋CRSフィードバック"]
        A06[/"📐 CHD-{CR}.md<br/>変更設計書"/]
    end

    %% ─── フェーズ7: コーディング ───
    subgraph PH7["フェーズ 7｜コーディング＋静的検証（工程9〜10）"]
        S07["💻 xddp.07.code<br/>コーディング＋静的検証"]
        A07[/"🔨 ソースコード変更<br/>CODING-{CR}.md"/]
        VF07[/"08_code-review/VERIFY-{CR}.md<br/>静的検証レポート"/]
    end

    %% ─── フェーズ8: テスト ───
    subgraph PH8["フェーズ 8｜テスト（工程11〜14）"]
        S08["🧪 xddp.08.test<br/>テスト設計＋実行＋不具合修正"]
        A08[/"✅ TSP-{CR}.md<br/>テスト仕様書<br/>10_test-results/*.md"/]
    end

    %% ─── フェーズ9: 最新仕様書 ───
    subgraph PH9["フェーズ 9｜最新仕様書（工程15）"]
        S09["📚 xddp.09.specs<br/>最新仕様書作成"]
        A09[/"📖 latest-specs/*.md<br/>最新仕様書"/]
    end

    %% ─── フェーズ10: クローズ ───
    subgraph PH10["フェーズ 10｜CRクローズ"]
        S10["🔒 xddp.close<br/>CRクローズ＋知見集約"]
        A10[/"💡 lessons-learned.md（追記）<br/>improvement-backlog.md（追記）<br/>docs/specs/（昇格済み仕様書）<br/>docs/specs/AI_INDEX.md<br/>─────────────────<br/>→ 次回CR開始時に「前CR以前の知見」として参照"/]
    end

    %% ─── 主フロー ───
    REQ --> S01
    S01 --> A01
    A01 --> S02
    REQ --> S02
    KNW --> S02
    S02 --> A02
    A02 --> S03
    REQ --> S03
    S03 --> A03

    A03 --> S04
    SRC --> S04
    SPECS --> S04
    S04 --> A04
    A04 -.->|"CRS補足フィードバック"| A03

    A03 --> S05
    A04 --> S05
    KNW --> S05
    SPECS --> S05
    S05 --> A05

    A05 --> S06
    A03 --> S06
    A04 --> S06
    S06 --> A06
    A06 -.->|"CRSフィードバック"| A03

    A06 --> S07
    S07 --> A07
    S07 --> VF07
    A07 --> S08
    VF07 --> S08
    A06 --> S08
    A03 --> S08
    A04 --> S08
    S08 --> A08

    A04 --> S09
    A06 --> S09
    A03 --> S09
    SPECS --> S09
    S09 --> A09
    A09 --> S10

    KNW --> S10
    A02 --> S10
    A03 --> S10
    A04 --> S10
    A05 --> S10
    A06 --> S10
    A08 --> S10
    S10 --> A10
    RF09 -.->|"🔴🟡 xddp.revise"| A09
```

---

## 随時実行スキル（工程外）

```mermaid
flowchart LR
    DOC(["任意の成果物"])

    subgraph UTILS["随時実行スキル"]
        direction TB
        REV["🔍 xddp.review<br/>単体AIレビュー（随時）"]
        RVS["📝 xddp.revise<br/>人レビュー指摘反映"]
        STS["📊 xddp.status<br/>進捗確認"]
        M2E["📊 xddp.md2excel<br/>CRS → Excel (USDM)"]
        E2M["📄 xddp.excel2md<br/>Excel → Markdown"]
    end

    REVIEW_OUT[/"review/<br/>(任意のレビュー結果)"/]
    EXCEL_OUT[/"CRS-{CR}.xlsx<br/>USDM形式Excel"/]

    DOC --> REV --> REVIEW_OUT
    REVIEW_OUT --> RVS --> DOC
    DOC --> STS
    DOC --> M2E --> EXCEL_OUT
    EXCEL_OUT --> E2M --> DOC
```

---

## 成果物一覧（フォルダ対応表）

> **外部入力（前CRの成果が次CRへ引き継がれるもの）**
>
> | 入力 | パス | 参照スキル |
> |---|---|---|
> | 過去の知見 | `lessons-learned.md`, `docs/projects/.../knowledge/patterns.md` | xddp.02, xddp.05, xddp.close |
> | 承認済み仕様書 | `docs/specs/*.md` | xddp.04, xddp.05, xddp.09 |

| 工程 | フォルダ | ファイル | 生成スキル | レビューファイル |
|---|---|---|---|---|
| 初期化 | `{CR}/01_requirements/` | `REQ-{CR}.md` | xddp.01.init（コピー） | — |
| 要求分析 | `{CR}/02_analysis/` | `ANA-{CR}.md` | xddp.02.analysis | `review/02_analysis-review.md` |
| 変更要求仕様書作成 | `{CR}/03_change-requirements/` | `CRS-{CR}.md` | xddp.03.req | `review/03_change-requirements-review.md` |
| スペックアウト | `{CR}/04_specout/` | `SPO-{CR}.md`, `modules/*.md` | xddp.04.specout | `review/04_specout-review.md` |
| 実装方式検討 | `{CR}/05_architecture/` | `DSN-{CR}.md` | xddp.05.arch | `review/05_architecture-review.md` |
| 変更設計書作成 | `{CR}/06_design/` | `CHD-{CR}.md` | xddp.06.design | `review/06_design-review.md` |
| コーディング | `{CR}/07_coding/` | `CODING-{CR}.md` + ソース変更 | xddp.07.code | — |
| 静的検証 | `{CR}/08_code-review/` | `VERIFY-{CR}.md` | xddp.07.code（静的検証） | — |
| テスト設計・実行 | `{CR}/09_test-spec/` | `TSP-{CR}.md` | xddp.08.test | `review/09_test-spec-review.md` |
| テスト設計・実行 | `{CR}/10_test-results/` | テスト結果 `.md` | xddp.08.test | — |
| 最新仕様書作成 | `latest-specs/` | `{module}-spec.md` | xddp.09.specs | `review/09_specs-review.md` |
| 随時 | `{CR}/review/` | 各レビュー結果 `*.md` | 各スキル内レビューループ / xddp.review | — |
| CRクローズ | `./` | `lessons-learned.md`, `improvement-backlog.md` | xddp.close | — |
| CRクローズ（仕様書昇格） | `docs/specs/` | `{module}-spec.md`, `AI_INDEX.md` | xddp.close（Step C2） | — |
| 初期化 | `./` | `xddp.config.md`, `progress.md` | xddp.01.init | — |
