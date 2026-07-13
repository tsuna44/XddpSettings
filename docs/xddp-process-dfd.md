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
>
> **適用範囲:** 本サイクル（`xddp-reviewer` 使用）はフェーズ2〜6・フェーズ8のテスト設計（xddp.09.test）・フェーズ9が対象。
> フェーズ1（初期化。レビュー対象成果物なし）、フェーズ7（コーディング＋静的検証。専用の `xddp-verifier-agent` による
> 別方式の検証フローを使用）、フェーズ8のテスト実行（xddp.10.test-run。`xddp-test-runner-agent` を使用）は
> 本サイクルの対象外。随時実行の `xddp.review`／`xddp.feedback`（design/code）／`xddp.sync-design`／`xddp.plan-review` も
> 同じ `xddp-reviewer` を再利用する。

### xddp-reviewer の内部構造（1回の呼び出し）

```mermaid
flowchart TD
    subgraph REVIEWER["xddp-reviewer（1エージェント・独立コンテキスト）"]
        PERSONA["① 専門家ペルソナ<br/>（文書種別で切り替え）"]
        CT1["🧠 独立コンテキスト実行<br/>作成者バイアスを排除"]
        CT2["📌 証拠ベース指摘<br/>セクション名・SP番号・行を明示"]
        CT3["🔁 後工程インパクト評価<br/>手戻りリスクを最優先"]
        CT4["🔍 エッジケース追跡<br/>異常系・境界値を確認"]
        CT5["🔗 トレーサビリティ検証<br/>UR→SR→SP→設計→テスト"]
        PERSONA -->|"② クリティカルシンキング原則を組み合わせて適用"| CT1
        CT1 --> CT2 --> CT3 --> CT4 --> CT5
    end
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
| **SPEC**（最新仕様書、latest-specs/） | ナレッジベースキュレーター | モジュール仕様・概要図・ユースケース・cross仕様の正確性・網羅性、SPO/CHDとのトレーサビリティ |
| **PLAN**（スキル変更プラン、CR外） | シニアアーキテクト | プロセス設計・エージェント構成・テンプレート設計の妥当性、Before/After・影響範囲の具体性、スキル呼び出し契約の整合性 |

---

## プロセス全体フロー

```mermaid
flowchart TD
    %% ─── 外部入力 ───
    REQ(["📄 要求書<br/>REQ-{CR}.md"])
    SRC(["🗂️ 母体ソースコード<br/>(対象プロジェクト)"])
    KNW(["💡 前CR以前の知見<br/>{DOCS_DIR}/{repo}/knowledge/lessons-learned.md<br/>{DOCS_DIR}/{repo}/knowledge/code-knowledge/**"])
    SPECS(["📖 承認済み仕様書<br/>{XDDP_DIR}/latest-specs/{repo}/**（優先）<br/>{DOCS_DIR}/{repo}/specs/**（フォールバック）"])
    CATALOG(["🗺️ モジュールカタログ<br/>{DOCS_DIR}/{repo}/module-catalog.md<br/>(xddp.codemap 生成)"])

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
    subgraph PH4["フェーズ 4｜スペックアウト（工程4a〜4b）"]
        S04["🔎 xddp.04.specout<br/>スペックアウト＋CRS更新"]
        A04[/"🗃️ SPO-{CR}.md<br/>スペックアウトサマリ<br/>modules/*.md"/]
    end

    %% ─── フェーズ5: 方式検討 ───
    subgraph PH5["フェーズ 5｜実装方式検討（工程5）"]
        S05["🏗️ xddp.05.arch<br/>実装方式検討"]
        A05[/"🗺️ DSN-{CR}.md<br/>実装方式検討メモ"/]
    end

    %% ─── フェーズ6: 変更設計 ───
    subgraph PH6["フェーズ 6｜変更設計書（工程6a〜6b）"]
        S06["✏️ xddp.06.design<br/>変更設計書作成＋CRSフィードバック"]
        A06[/"📐 CHD-{CR}.md<br/>変更設計書"/]
    end

    %% ─── フェーズ7: コーディング ───
    subgraph PH7["フェーズ 7｜コーディング＋静的検証（工程7〜8）"]
        S07["💻 xddp.07.code<br/>コーディング＋静的検証"]
        A07[/"🔨 ソースコード変更<br/>CODING-{CR}.md"/]
        VF07[/"08_code-review/VERIFY-{CR}-{repo}.md<br/>VERIFY-{CR}-cross.md（マルチリポジトリ時）<br/>静的検証レポート"/]
    end

    %% ─── フェーズ8: テスト ───
    subgraph PH8["フェーズ 8｜テスト（工程9〜10）"]
        S08["🧪 xddp.09.test / xddp.10.test-run<br/>テスト設計→実行→不具合修正"]
        A08[/"✅ TSP-{CR}.md<br/>テスト仕様書<br/>10_test-results/*.md"/]
    end

    %% ─── フェーズ9: 最新仕様書 ───
    subgraph PH9["フェーズ 9｜最新仕様書（工程11）"]
        S09["📚 xddp.11.specs<br/>最新仕様書作成"]
        A09[/"📖 latest-specs/*.md<br/>最新仕様書"/]
    end

    %% ─── フェーズ10: クローズ ───
    subgraph PH10["フェーズ 10｜CRクローズ"]
        S10["🔒 xddp.close<br/>CRクローズ＋知見集約"]
        A10[/"💡 lessons-learned.md（追記）<br/>improvement-backlog.md（追記）<br/>─────────────────<br/>DOCS_DIR/{REPO}/specs/（昇格済み仕様書）<br/>DOCS_DIR/{REPO}/design/（DSN・CHD昇格）<br/>DOCS_DIR/{REPO}/test/（TSP昇格）<br/>DOCS_DIR/{REPO}/project-rulebook.md（昇格）<br/>DOCS_DIR/AI_INDEX.md（更新）<br/>─────────────────<br/>→ 次回CR開始時に「前CR以前の知見」として参照"/]
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
    CATALOG --> S04
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
```

> **設定による分岐（xddp.config.md）:**
> - `DEVELOPMENT_MODE: new`（新規開発）の場合、フェーズ4（スペックアウト）は母体コードが存在しないためスキップされる。
> - フェーズ8（テスト実行・xddp.10.test-run）はカバレッジが `MIN_COVERAGE`（デフォルト80%）以上で自動合格。未満の場合は
>   人が承認するかテストを追加するかを選択するゲートが入る（100に設定すると旧動作＝100%強制に戻る）。

---

## 随時実行スキル（工程外）

```mermaid
flowchart LR
    DOC(["任意の成果物"])
    SRC2(["🗂️ 母体ソースコード"])

    subgraph UTILS["随時実行スキル（CR成果物を操作）"]
        REV["🔍 xddp.review<br/>単体AIレビュー（随時）"]
        RVS["📝 xddp.revise<br/>人レビュー指摘反映"]
        FDB["📤 xddp.feedback<br/>arch/design/test/code → CRS反映"]
        SYNC["🔄 xddp.sync-design<br/>コード→DSN再生成"]
        STS["📊 xddp.status<br/>進捗確認"]
        M2E["📊 xddp.md2excel<br/>CRS → Excel (USDM)"]
        E2M["📄 xddp.excel2md<br/>Excel → Markdown"]
    end

    REVIEW_OUT[/"review/<br/>(任意のレビュー結果)"/]
    EXCEL_OUT[/"CRS-{CR}.xlsx<br/>USDM形式Excel"/]
    CRS_OUT[/"CRS-{CR}.md<br/>（design/codeの場合はTM-{CR}.mdも）"/]
    DSN_REV_OUT[/"DSN-{CR}-rev{N}.md<br/>（AIレビュー→人承認）"/]

    DOC --> REV --> REVIEW_OUT
    REVIEW_OUT --> RVS --> DOC
    DOC --> FDB --> CRS_OUT
    SRC2 --> SYNC --> DSN_REV_OUT
    DOC --> STS
    DOC --> M2E --> EXCEL_OUT
    EXCEL_OUT --> E2M --> DOC
```

```mermaid
flowchart LR
    SRC3(["🗂️ 母体ソースコード"])
    PLAN_DOC(["📋 plans/PLAN-*.md<br/>(ClaudeCode/.claude/ 変更プラン)"])

    subgraph UTILS2["随時実行スキル（CR非依存・リポジトリ横断）"]
        CMAP["🗺️ xddp.codemap<br/>モジュールカタログ生成"]
        UPDK["💡 xddp.update-knowledge<br/>知識登録（対話/引数形式）"]
        FILLR["📋 xddp.fill-rulebook<br/>project-rulebook 自動ドラフト"]
        PREV["🧐 xddp.plan-review<br/>スキル変更プランのAIレビュー"]
    end

    CATALOG_OUT[/"{DOCS_DIR}/{repo}/module-catalog.md<br/>→ xddp.04.specout の BFS 優先度制御に使用"/]
    KNOW_OUT[/"{DOCS_DIR}/{repo}/knowledge/**<br/>（lessons-learned.md 以外の知見）"/]
    RULEBOOK_OUT[/"project-rulebook*.md<br/>（ドラフト→人承認）"/]
    PLAN_REVIEW_OUT[/"plans/review/PLAN-*-review.md"/]

    SRC3 --> CMAP --> CATALOG_OUT
    UPDK --> KNOW_OUT
    SRC3 --> FILLR --> RULEBOOK_OUT
    PLAN_DOC --> PREV --> PLAN_REVIEW_OUT
```

---

## 成果物一覧（フォルダ対応表）

> **外部入力（前CRの成果が次CRへ引き継がれるもの）**
>
> | 入力 | パス | 参照スキル |
> |---|---|---|
> | 過去の知見 | `{DOCS_DIR}/{repo}/knowledge/lessons-learned.md`（cross は `{DOCS_DIR}/cross/knowledge/lessons-learned.md`）、`{DOCS_DIR}/{repo}/knowledge/code-knowledge/**`（xddp.update-knowledge が随時追加） | xddp.02, xddp.05, xddp.06, xddp.09, xddp.close |
> | 承認済み仕様書 | `{XDDP_DIR}/latest-specs/{repo}/**`（優先）, `{DOCS_DIR}/{repo}/specs/**`（フォールバック） | xddp.04, xddp.05, xddp.11 |
> | モジュールカタログ | `{DOCS_DIR}/{repo}/module-catalog.md`（xddp.codemap が生成、specout の BFS 優先度制御に使用） | xddp.04 |

| 工程 | フォルダ | ファイル | 生成スキル | レビューファイル |
|---|---|---|---|---|
| 初期化 | `{CR}/01_requirements/` | `REQ-{CR}.md` | xddp.01.init（テンプレートから生成。要求書ファイル指定時は参照コピーも追加配置） | — |
| 要求分析 | `{CR}/02_analysis/` | `ANA-{CR}.md` | xddp.02.analysis | `review/02_analysis-review.md` |
| 変更要求仕様書作成 | `{CR}/03_change-requirements/` | `CRS-{CR}.md` | xddp.03.req | `review/03_change-requirements-review.md` |
| スペックアウト | `{CR}/04_specout/` | `SPO-{CR}.md`, `modules/*.md` | xddp.04.specout | `review/04_specout-review.md` |
| 実装方式検討 | `{CR}/05_architecture/` | `DSN-{CR}.md` | xddp.05.arch | `review/05_architecture-review.md` |
| 変更設計書作成 | `{CR}/06_design/` | `CHD-{CR}.md` | xddp.06.design | `review/06_design-review.md` |
| コーディング | `{CR}/07_coding/` | `CODING-{CR}.md` + ソース変更 | xddp.07.code | — |
| 静的検証 | `{CR}/08_code-review/` | `VERIFY-{CR}-{repo}.md`, `VERIFY-{CR}-cross.md`（マルチリポジトリ時） | xddp.07.code（静的検証）/ xddp.08.verify | — |
| テスト設計 | `{CR}/09_test-spec/` | `TSP-{CR}.md` | xddp.09.test | `review/09_test-spec-review.md` |
| テスト実行・不具合修正 | `{CR}/10_test-results/{repo}/`（＋マルチリポジトリ時は `cross/`） | `TRS-{CR}-0{N}.md`（実行回ごと） | xddp.10.test-run | — |
| 最新仕様書作成 | `latest-specs/` | `{repo}/{module}/spec.md` 等（モジュール仕様・`overview/*`・`cross/interfaces/*`・`system/use-cases/*`） | xddp.11.specs | `{CR}/review/09_specs-batch{N}-review.md` |
| 随時 | `{CR}/review/` | 各レビュー結果 `*.md` | 各スキル内レビューループ / xddp.review | — |
| CRクローズ | `{XDDP_DIR}/` | `lessons-learned.md`, `improvement-backlog.md` | xddp.close | — |
| CRクローズ（仕様書昇格） | `{DOCS_DIR}/{REPO}/specs/` | `latest-specs/{repo}/**` と同一構造でコピー（`{module}/spec.md` 等） | xddp.close（Step C2） | — |
| CRクローズ（設計書昇格） | `{DOCS_DIR}/{REPO}/design/` | `DSN-{CR}.md`, `CHD-{CR}.md` | xddp.close（Step C4） | — |
| CRクローズ（テスト仕様昇格） | `{DOCS_DIR}/{REPO}/test/` | `TSP-{CR}.md` | xddp.close（Step C5） | — |
| CRクローズ（steering昇格） | `{DOCS_DIR}/{REPO}/` | `project-rulebook.md` | xddp.close（Step C6） | — |
| CRクローズ（インデックス） | `{DOCS_DIR}/` | `AI_INDEX.md` | xddp.close（Step C2〜C6） | — |
| 初期化 | `./` | `xddp.config.md`, `progress.md` | xddp.01.init | — |
