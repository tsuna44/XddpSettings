# PLAN-20261102-impact-hypotheses

作成日: 2026-11-02  
ステータス: 草案 / **承認待ち** / 承認済み / 実装完了
> 保留: PLAN-20261103-contract-audit で A1・A2 の指摘を割り当てたすべての修正プランの実装の後に、同プランの 3.3 のとおり再発防止を足し、AI レビューをやり直してから承認・実装に進む（同プランの 7. の 4.）。

---

## 1. 背景・目的

### 1.1 起きたこと

[PLAN-20261102-field-copy-trace](PLAN-20261102-field-copy-trace.md)（以下 ①）の 1.1 と同じ事例。機能A の構造体 S にフィールド f を足したとき、
S を通信用の構造体 M を経てフィールドごとにダンプする機能B の修正が漏れた。知見（code-knowledge）には機能A〜機能B の DFD があったが使われなかった。

①は工程6 で CHD §4 の型のフィールドの行から一緒に直す候補を出すが、工程4a（スペックアウト）の段階では、機能B は SPO の影響範囲に現れない。
工程4b で CRS に「ダンプの形式が変わる」ことが入らず、工程5（方式検討）も機能B を前提にしない。

### 1.2 原因（コードで確認した事実）

1. **下調べの範囲は、CRS が述べる振る舞いで決まる。** `agents/xddp-specout-prelim-agent.md`「## Process」1.・2. は、CRS が変更対象として述べる振る舞いを列挙し、
   それを実装する母体コードを探して読む。CRS が述べない機能B は読まない。変更が「何に」依存されているか（変わる事実と、それを使う側）を考える手順が無い。
2. **下調べの入力に、使う側の手がかりになる知見・ユースケースが無い。** 同エージェントの Inputs は `BASELINE_SPECS_DIR`・`CROSS_SPECS_DIR`・`LATEST_SPECS_DIR`
   （`latest-specs/{repo}/`）・`DOCS`（手順3 の既知制約〔`constraints.md`〕だけに使う）・`MODULE_CATALOG_FILE`・`ENTRY_POINTS`。
   `{KNOW}/_flows/`（DFD・シーケンス・callgraph）・`{KNOW}/_structures/`・`latest-specs/system/use-cases/` は読まない（`{KNOW}` = `{DOCS}/{repo}/knowledge/code-knowledge`）。
3. **波紋調査は値の伝わり方を追い、LLM は届いた先を読まない。** フィールドを足しても機能B が読む既存のフィールドの値は変わらないので、機能B は影響先として現れない
   （ADR-0030 の Context）。届いた先も、資料を書く LLM は下調べ・追加下調べ・依頼調査の資料だけを読む（ADR-0023）。
4. **SPO レビューに、漏れを疑う手がかりの一覧が無い。** `xddp-common/reviewer-checklists/SPO.md` の L1 は「CRS の要求に照らして、変更で影響を受ける機能が SPO の影響範囲に漏れなく含まれているか」を見るが、
   何に依存している箇所を探すかを示す一覧が無い。
5. **既知制約の読み取りの階層が、書き手と合っていない。** 下調べは `{KNOW}/{第1階層}/constraints.md` を読む（同エージェント「## Process」3. の既知制約）が、
   CR クローズは「ファイルパスの第1〜2階層ディレクトリ名」で書く（`agents/xddp-close-knowledge-agent.md`「### Step C3.6」）。第2階層に書いた制約を下調べは読まない。
   この不具合は [PLAN-20261102-constraints-module-key](PLAN-20261102-constraints-module-key.md) で直す（このプランでは変えない）。

### 1.3 目的

工程4a の下調べで、CRS の変更によってコード上で**変わる事実**（データ・状態・単位・タイミング・列挙値）を一覧にし、それぞれについて**使う側の仮説**を、
知見・ユースケース・①のスクリプト・コードから立て、コードで確かめる（関係あり／関係なし〔根拠〕／確認できず）。

- 人は Step A-Seed で仮説の一覧を見て、判定を直し、仮説を足せる。
- 確かめた結果は SPO（§5.8 と別ファイルの全量）に残り、SPO レビュー L1 が仮説の一覧と照合する。関係ありで CRS に無い外から観測できる変更は SPO §7 で工程4b（CRS）へ申し送る。
- 変わる事実に型のフィールドの追加・変更・削除があれば、①のスクリプト（`specout_fieldtrace.py candidates`）を工程4a で動かし、候補を仮説として確かめる。
- 知見の「一緒に直す箇所」（プラン③）に当てはまる関係は、スクリプトがすべて仮説になっていることを確かめる（知見があったのに使われなかった、という今回の原因を機械的に防ぐ）。
- **工程2（要求分析）ではなく工程4a に置く:** 仮説はコードで確かめてから CRS に入れる（未確認の仮説を CRS に入れない）。
- 決定的な処理（仮説の一覧の書式・網羅の検査、知見との照合、①のスクリプトへの入力の変換、SPO への転記）はスクリプト、仮説を立てること・コードで確かめることは LLM が行う。

### 1.4 関連するプラン

| プラン | 内容 | 関係 |
|---|---|---|
| ① PLAN-20261102-field-copy-trace（実装済み） | 工程6 Step A2.5 の一緒に直す候補 | ②が `specout_fieldtrace.py candidates` を工程4a で使う（`--stage specout` を足す。3.2） |
| ② このプラン | 影響仮説 | — |
| ③ PLAN-20261102-cochange-knowledge（並行して作成） | 一緒に直す箇所の知見（`{KNOW}/_cochange/`）と CR クローズでの昇格 | ②が③の形式を読み、③の照合の規則で知見と事実を照合する。③は②の影響仮説のファイルを昇格の出どころ (d) として読む |

**共有する約束事（③と同じ内容。変える場合は両方のプランを直す）:**
- 種類の語彙（データ／状態／単位／タイミング／列挙値／その他）とキーの書式（①のキーと同じ `{ファイル}::{名前}`）は、③が作る共有規則 `xddp-rules/change-facts.md` の
  「## 種類」「## キー」に書く。②は同じファイルに「## 種類ごとの使う側の観点」を書く（3.4）。先に実装するプランがファイルを作る。
- 知見の読み取りと照合は③の `xddp-common/scripts/cochange_knowledge.py` の `load_relations`・`match_relations` だけが行う（②の `impact_hypotheses.py check` はこれを import する）。
- 影響仮説のファイルの読み取りは②の `xddp-common/scripts/impact_hypotheses.py` の `load_hypotheses` だけが行う（③の `collect` はこれを import する）。
- ③が読む影響仮説の列: 事実の「対象」「種類」、仮説の「使う側」「由来」（`知見 CC-NNN` の形）「判定」。

**実装の順序:** `change-facts.md`（③と②の節）と、③の `load_relations`・`match_relations`・②の `load_hypotheses` → ②の残り → ③の残り。

---

## 2. 変更対象ファイル

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `ClaudeCode/.claude/skills/xddp-common/scripts/impact_hypotheses.py` | 追加 | 影響仮説のファイルの読み取り（③と共有）、サブコマンド `check`・`elements`・`spo-section`（3.1） |
| `ClaudeCode/.claude/skills/xddp-common/scripts/tests/test_impact_hypotheses.py` | 追加 | 3.1 のテスト |
| `ClaudeCode/.claude/skills/xddp-04-specout/scripts/specout_fieldtrace.py`・`tests/test_specout_fieldtrace.py` | 修正 | `--stage specout`（3.2） |
| `ClaudeCode/.claude/agents/xddp-specout-prelim-agent.md` | 修正 | 入力（ユースケース・知見）、`PRELIM_MODE: initial` での影響仮説、`PRELIM_MODE: hypotheses` の新設（3.3） |
| `ClaudeCode/.claude/skills/xddp-rules/change-facts.md` | 追加（③と共有） | 「## 種類ごとの使う側の観点」（3.4）。③は「## 種類」「## キー」「## 一緒に直す箇所の知見」を書く |
| `ClaudeCode/.claude/skills/xddp-04-specout/impact-hypotheses.md` | 追加 | 下調べのエージェントが読む、影響仮説の立て方・確かめ方・書き方（単一スキル専用の参照ファイル。3.5） |
| `ClaudeCode/.claude/skills/xddp-04-specout/templates/04_specout-hypotheses-template.md` | 追加 | 影響仮説のファイルのひな形（3.0.2） |
| `ClaudeCode/.claude/skills/xddp-04-specout/SKILL.md` | 修正 | Step A-Prelim の入力と「仮説の確認」、Step A-Seed の提示と指示、前回の残骸の一覧、Step A2 の `REFERENCE_FILES`、Step A3 の成果物（3.6） |
| `ClaudeCode/.claude/skills/xddp-04-specout/templates/04_specout-summary-template.md` | 修正 | §5.8 影響仮説（3.7） |
| `ClaudeCode/.claude/skills/xddp-04-specout/scripts/specout_bfs.py`・テスト | 修正 | `assemble-spo --hypotheses-section-file`（§5.8 の差し込み・入力の指紋）（3.7） |
| `ClaudeCode/.claude/skills/xddp-common/procedures/specout-finish.md` | 修正 | `impact_hypotheses.py spo-section` の実行、document agent に `HYPOTHESES_FILE`（3.7） |
| `ClaudeCode/.claude/agents/xddp-specout-document-agent.md` | 修正 | §7・§9・§5.3 で影響仮説を扱う（3.8） |
| `ClaudeCode/.claude/skills/xddp-common/reviewer-checklists/SPO.md` | 修正 | L1・L2 に影響仮説の照合（3.9） |
| `ClaudeCode/.claude/skills/xddp-common/scripts/artifact_lint.py`・テスト | 修正 | SPO の S6（§5.8 の存在と記入）（3.10） |
| `tools/harness/refcheck.py` | 修正 | 検査D の `DETERMINISTIC_SCRIPTS` に `impact_hypotheses.py`（3.12） |
| `docs/adr/ADR-0031-specout-impact-hypotheses.md`・`docs/adr/README.md` | 追加・修正 | 設計根拠・却下した案・範囲外（3.13） |
| `README.md`・`CLAUDE.md` | 修正 | 工程4a の説明、スクリプトの表、参照ファイル（3.14） |

`xddp-investigate`・`xddp-05-arch` は共通プロシージャ `specout-finish.md` を通して §5.8 を書くので、SKILL は変えない（3.7）。設定キーは足さない。

---

## 3. 変更内容

### 3.0 設計（共通）

#### 3.0.1 用語

| 用語 | 意味 |
|---|---|
| 変わる事実 | CRS の変更によって、コード上で変わること。種類（`change-facts.md`「## 種類」）・対象（キー）・変わり方（`追加`／`変更`／`削除`）で書く。例: 「S にフィールド f が加わる」（データ・`src/a/s.h::S::f`・追加）、「速度の単位が km/h から m/s になる」（単位・`src/ctl/speed.c::g_speed`・変更） |
| 使う側 | 変わる事実に依存して処理している箇所。キーで書く（関数・型・ファイル。確かめる前はモジュールのディレクトリ `{ディレクトリ}/` も可） |
| 影響仮説（仮説） | 「使う側 U は、事実 F に依存しているので、F が変わると U も変える必要がある（または U の振る舞いが変わる）かもしれない」 |
| 由来 | 仮説を立てた手がかり（3.0.3） |
| 判定 | コードで確かめた結果。`関係あり`（U が F に依存して処理していることをコードで確かめた）／`関係なし`（依存していないことをコードで確かめた。具体的な根拠が要る）／`確認できず`（読んでも決められない）／`未確認`（人が足した直後だけ） |

対象・使う側のキーは①のキーと同じ書式（`change-facts.md`「## キー」）。まだコードに無い名前（足すフィールド等）は、それを持つ型の定義のファイルで書く（例: `src/a/s.h::S::f`）。

#### 3.0.2 影響仮説のファイル（形式）

- 場所: `{CR_PATH}/04_specout/{repo}/SPO-{CR}-hypotheses.md`（SPO と同じディレクトリ。人が見る成果物として `work/` に置かない）。cross には作らない。
- ひな形 `04_specout-hypotheses-template.md`:

```
# 影響仮説 — {CR} / {repo}

> 下調べ（xddp-specout-prelim-agent）が書き、`impact_hypotheses.py` が検査する。見出し名・列構成を変えない。セル内の `|` は `\|`。
> 種類・キーの書き方は `~/.claude/skills/xddp-rules/change-facts.md`。人が判定を直す場合は根拠を `人の判断: {理由}（{日付}）` とする。

## 変わる事実
| 事実ID | 種類 | 対象 | 変わり方 | 内容 | 根拠（CRS） |
|---|---|---|---|---|---|

## 使う側の仮説
| 仮説ID | 事実ID | 使う側 | 仮説 | 由来 | 判定 | 根拠 |
|---|---|---|---|---|---|---|

## 使う側の仮説を立てなかった事実
| 事実ID | 理由 |
|---|---|
```

| 列 | 値 |
|---|---|
| 事実ID・仮説ID | `F-{NNN}`・`H-{NNN}`。ファイルの中で一意 |
| 種類 | `change-facts.md`「## 種類」の語彙 |
| 対象・使う側 | キー（バッククォートで囲む） |
| 由来 | `CRS {SP-ID}`／`ユースケース {ユースケース名}`／`知見 _flows/{ファイル名}`／`知見 _structures/{ファイル名}`／`知見 constraints {置き場所} {CK-NNN}`（置き場所は `code-knowledge-boundary.md`「## 知見の置き場所（MODULE）」の `{MODULE}`）／`知見 {CC-NNN}`（③の一緒に直す箇所）／`写しの追跡`（①のスクリプト）／`コード`／`人が追加`。複数あれば `、` で並べる |
| 判定 | 3.0.1 |
| 根拠 | `関係あり`＝`{ファイル}:{行}` と依存の内容。`関係なし`＝コードで確かめた具体的な内容（「関係なし」「影響なし」だけは不可）。`確認できず`＝読んだ範囲と決められない理由 |

- 由来に `人が追加` を含む行は、LLM が `関係なし` にしない（確かめられなければ `確認できず` とし、依頼と食い違う点があれば根拠を書く。CLAUDE.md「人の依頼は LLM の関係判断で拒否しない」）。
- 「使う側の仮説を立てなかった事実」は、その事実を使う側が無いことをコードで確かめた場合だけに書く（理由に根拠を書く）。

#### 3.0.3 仮説の立て方（由来）

事実ごとに、次の手がかりから仮説を立てる（詳細は 3.5 の参照ファイル）。

| 由来 | 手がかり | 誰が |
|---|---|---|
| 知見 CC-NNN | `{KNOW}/_cochange/`（③）の関係のうち、③の照合の規則で事実に当てはまるもの。**当てはまる関係はすべて仮説にする**（`impact_hypotheses.py check` が確かめる） | 下調べ（LLM）＋スクリプトの検査 |
| 知見 _flows/・_structures/・constraints | 事実の対象の名前（型・フィールド・変数・関数・モジュール）で `{KNOW}/_flows/`・`{KNOW}/_structures/`・`constraints.md` を Grep し、当たったファイルを読む。図の下流の処理・モジュール、関連する型、制約の対象を使う側にする | 下調べ（LLM） |
| ユースケース | `{XDDP_DIR}/latest-specs/system/use-cases/`（無ければ `{DOCS}/system/specs/use-cases/`）のうち、関連モジュールに事実の対象のモジュールを含むもの。その他の関連モジュール・手順を使う側にする | 下調べ（LLM） |
| CRS | CRS が述べる他の機能・出力 | 下調べ（LLM） |
| コード | 種類ごとの観点（`change-facts.md`「## 種類ごとの使う側の観点」。3.4）でコードを探す。**1つの事実につき最大 20 件**（参照ファイルの定数）。超えた分は1行「ほか N 箇所（探し方）」として `確認できず` にする | 下調べ（LLM） |
| 写しの追跡 | 事実に型のフィールドの追加・変更・削除があるとき、①のスクリプトの確認対象の候補 | スクリプトが出し、下調べ（LLM）が確かめる |
| 人が追加 | Step A-Seed で人が足した仮説 | 人が足し、下調べ（LLM）が確かめる |

- 波紋調査は値の伝わり方（呼び出し・代入・参照）を追う。仮説はそれで届かない依存を主に探す（フィールドの追加・列挙値の追加・単位・タイミング・状態、
  ファイル・通信・バッファを経由する経路、関数ポインタ・イベント経由の呼び出し）。値が直接届く参照元を仮説にしてもよいが、上の上限に数える。
- 立てた仮説はすべて、使う側のコードを Read して判定する（判定の無い仮説を書かない）。

#### 3.0.4 機械検査（`impact_hypotheses.py check`）

| 検査 | 内容 | 結果 |
|---|---|---|
| 書式 | 見出し・列・ID の一意・種類と判定の語彙・キーの書式・事実ID の参照 | exit 1 |
| 知見の漏れ `knowledge_missing` | 事実ごとに `match_relations` で当てはまる関係（CC-NNN）について、その事実の仮説に由来 `知見 CC-NNN` が無い | 不足（exit 3） |
| 写しの追跡の漏れ `fieldtrace_missing` | `--cochange-candidates` の確認対象の候補のキーが、どの仮説の使う側にも無い | 不足 |
| 未確認 `unverified` | 判定が `未確認`・空 | 不足 |
| 仮説の無い事実 `facts_uncovered` | 仮説も「立てなかった」行も無い事実 | 不足 |
| 場所の無い関係あり `related_not_located` | 判定 `関係あり` で使う側がモジュールのディレクトリだけ | 不足 |
| 人の仮説の否定 `human_rejected` | 由来に `人が追加` を含み、判定 `関係なし` で根拠が `人の判断:` で始まらない | 不足 |
| 資料の無い関係あり `related_undocumented` | 判定 `関係あり` の使う側のファイルが台帳に無い | 報告だけ（不足にしない。3.0.5） |

#### 3.0.5 資料にする範囲

- 下調べ（`PRELIM_MODE: initial`）は、`関係あり` と判定した使う側のファイルを、文書化するファイルの一覧に入れて資料にする（台帳の工程 `下調べ`。
  台帳の「関係する振る舞い（CRS）」には `影響仮説 {仮説ID}` を書く）。下調べの調査範囲に上限を設けない既存の方針のまま。
- 下調べの後に確かめる仮説（写しの追跡・知見の漏れ・人が追加。`PRELIM_MODE: hypotheses`）は、判定だけを書き、資料は書かない。
  `関係あり` で資料の無い使う側は §5.8 の「資料」列で示し、Step A-Seed で `/xddp-investigate {CR} document` を案内する（人が頼めば資料になる）。

#### 3.0.6 工程4a の流れ

```
Step A-Prelim（repo ごと）
  1. 下調べ（PRELIM_MODE: initial）: SPO・資料・台帳・影響仮説のファイル・下調べ索引（最後）
  2. 仮説の確認（新設。work/hypotheses/check.json が無いか、下調べ索引・影響仮説のファイルより古い repo）:
     a. impact_hypotheses.py elements → 型のフィールドの事実があれば
     b. specout_fieldtrace.py candidates --stage specout → 確認対象の候補の要約
     c. impact_hypotheses.py check → 不足があれば下調べ（PRELIM_MODE: hypotheses）を1回 → もう一度 check（--metrics）
     d. 残った不足は Step A-Seed で ⚠️ として示す
discovery-setup → Step A-Seed（影響仮説を提示。人が判定を直す・仮説を足す → 2.c をやり直して再提示）→ 波紋調査 → SPO の仕上げ（§5.8）→ Step A2（レビュー L1）
```

#### 3.0.7 範囲外・限界（ADR に書く）

- 使う側のコードが母体の外・他の repo にある仮説（ダンプを読むツール等）。確かめられないので `確認できず` とし、根拠に「repo の外」と書く。cross には仮説を作らない。
- 工程6 以降（CHD）での仮説の照合はしない（型のフィールドは①が工程6 で扱う。SPO §5.8 は designer が読む SPO に入る）。
- 仮説を波紋調査のシードに自動で足さない（人が Step A-Seed で足せる）。
- 下調べの後に確かめた仮説の使う側は、自動では資料にしない（3.0.5）。
- コードから立てる仮説の上限（1つの事実につき 20 件）を超えた分は個別に確かめない。
- 知見の照合はキーの文字列で行う（③の 3.0.6）。ファイルの移動・名前の変更で当たらない関係は、LLM の Grep で補う。

### 3.1 `impact_hypotheses.py`（追加）

**変更前:** なし。

**変更後:** `xddp-common/scripts/` に置く（工程4a の SKILL・共通プロシージャ `specout-finish.md`・③の `cochange_knowledge.py` が使うため）。標準ライブラリのみ。

**ライブラリとして使う関数（③と共有。約束事）:** `load_hypotheses(path) -> dict`（事実・仮説・立てなかった事実の一覧。各行のファイル・行番号を含む。書式の誤りは例外）。

**サブコマンド:**

```
impact_hypotheses.py check --hypotheses HYP_MD --ledger LEDGER_MD --know-dir KNOW [--cochange-candidates JSON]
    --out CHECK_JSON [--metrics METRICS_JSONL --repo REPO --cr CR --today DATE]
impact_hypotheses.py elements --hypotheses HYP_MD --repo REPO --cr CR --out ELEMENTS_JSON
impact_hypotheses.py spo-section --hypotheses HYP_MD --ledger LEDGER_MD [--check-json CHECK_JSON] --out SECTION_MD
```

- `check`: 3.0.4 の検査。`--know-dir` の `_cochange/` が無ければ知見の漏れを調べない。stdout と `--out` に同じ JSON
  （`ok`・`counts`〔事実の種類別、仮説の由来別×判定別〕・不足の種類ごとの一覧・`related_undocumented`）。
  終了コード: 0＝不足なし／1＝書式の誤り（stderr `{ファイル}\t{行番号}\t{理由}`。`--out` は書かない）／2＝使い方の誤り／3＝不足あり（`--out` は書く）。
  `--metrics` を付けたときだけ `hypothesis_summary`（`counts`・不足の件数・`related_undocumented` の件数）を1行追記する（SKILL は最後の check にだけ付ける）。
- `elements`: 種類 `データ` で対象が `{ファイル}::{型}::{フィールド}`（変わり方 `追加`→`追加`、`変更`→`シグネチャ`、`削除`→`削除`）または `{ファイル}::{型}`（`変更`→`シグネチャ`）の事実を、
  `chd_regression.py elements` と同じ形の JSON（`repo`・`batch_name`〔`SPO-{CR}.md`〕・`sp`〔根拠の最初の SP〕・`file`・`symbol`〔ファイルを除いた名前〕・`kind`〔`データ構造`〕・`change`）にする。
  stdout `{ok, element_count}`。0件でも書く。
- `spo-section`: SPO §5.8 の本文（3.7）を書く。影響仮説のファイルが無ければ「影響仮説は作っていない（下調べの影響仮説のファイルが無い）」の1行。
  `関係あり`・`確認できず` の行を最大 30 行（スクリプトの定数）、`関係あり` で資料の無いもの → `確認できず` → `関係あり` の順。超えた分と `関係なし` は件数と全量の場所。
  `--check-json` があり不足が残っていれば ⚠️ の行（不足の種類と件数）を先頭に書く。
- テスト: 書式の誤り（列・語彙・ID の重複・存在しない事実ID）、3.0.4 の各検査（知見の漏れは③の照合の規則で、先頭の一致・種類の違いを含む）、`--metrics` で1行だけ追記、
  `elements` の変換（フィールド・型・データ以外を変換しない）、`spo-section` の上限・並び・⚠️・ファイルが無いとき。

**理由:** 仮説の一覧の網羅と知見との照合を決定的にし、「知見があったのに使われなかった」を機械的に見つけるため。①・③と同じく、検査の結果を件数で人とレビュアーに渡すため。

### 3.2 `specout_fieldtrace.py` の `--stage specout`（修正）

**変更前:** `candidates` は工程6 用。要約の文面は「§4 に足すか §4.1 に理由を書く」。`--design-dir` は必須で、書き先のバッチファイルは `{design-dir}/{repo}/{batch_name}`。

**変更後:** `--stage design|specout`（既定 `design`）を足す。`specout` のときは:
- `--design-dir` を要らない。候補の JSON の `batch_file` は空にし、要約のファイル名は `cochange-digest-{batch_name}`（`impact_hypotheses.py elements` が `batch_name` を `SPO-{CR}.md` にするので `cochange-digest-SPO-{CR}.md`）とする。
- 要約（`cochange-digest-SPO-{CR}.md`）と全量の文面を工程4a 用にする（「確認対象の候補ごとに、影響仮説（由来 `写しの追跡`）として使う側のコードで確かめる。キーを使う側の列にそのまま写す」）。
- 候補の求め方・確認の条件・上限・JSON の形は変えない（①の 3.0.3〜3.0.6 のまま）。
- テスト: `--stage specout` で `--design-dir` 無しで動く、文面が変わる、候補の JSON が `design` と同じ。

**理由:** ①の候補の求め方を工程4a でもそのまま使い、CHD の無い段階で動かすため。

### 3.3 `xddp-specout-prelim-agent.md`（修正）

**変更前:** Inputs は 1.2 の 2.。`PRELIM_MODE` は `initial`／`additional`／`requested`。出力に影響仮説は無い。

**変更後:**
- Inputs に足す:
  - `USE_CASES_DIR`（optional; empty = skip）: `{XDDP_DIR}/latest-specs/system/use-cases/`（無ければ `{DOCS}/system/specs/use-cases/`。どちらも無ければ空）
  - `KNOWLEDGE_DIR`（optional; empty = skip）: `{DOCS}/{REPO_NAME}/knowledge/code-knowledge`
  - `HYPOTHESES_TEMPLATE`: `~/.claude/skills/xddp-04-specout/templates/04_specout-hypotheses-template.md`
  - `HYPOTHESIS_TARGETS_FILE`（`hypotheses` のみ）: `check` の出力（`work/hypotheses/check.json`）
  - `COCHANGE_DIGEST`（`hypotheses` のみ・optional）: `--stage specout` の要約
  - `PRELIM_MODE` に `hypotheses` を足す。
- 出力ファイルに `{OUTPUT_DIR}/SPO-{CR_NUMBER}-hypotheses.md` を足す。
- 「## Process」（`initial`）:
  - 手順2 の後に手順を足す: Read `~/.claude/skills/xddp-04-specout/impact-hypotheses.md`, apply「## 変わる事実と使う側の仮説」。
    手順2 で見つけた変更対象のコードから変わる事実を決め、3.0.3 の由来から仮説を立て、使う側のコードを Read して判定し、影響仮説のファイルに書く（`HYPOTHESES_TEMPLATE` から作る）。
    `関係あり` の使う側のファイルを手順3 の文書化するファイルの一覧に入れる（3.0.5）。
  - 手順5 の前提「`prelim-index.md` を最後に書く」は変えない（影響仮説のファイルは手順4 までに書き終える）。
- 「## PRELIM_MODE: hypotheses」を新設する（`additional`・`requested` と同じ形）:
  1. Read `impact-hypotheses.md`・`CRS_FILE`・影響仮説のファイル・`HYPOTHESIS_TARGETS_FILE`・（あれば）`COCHANGE_DIGEST`。
  2. 不足の種類ごとに: 知見の漏れ＝その関係の行を由来 `知見 CC-NNN` で足して確かめる／写しの追跡の漏れ＝要約の候補を由来 `写しの追跡` で足して確かめる（要約の印・経路を仮説の文に使う）／
     未確認＝確かめる（由来 `人が追加` は `関係なし` にしない）／仮説の無い事実＝仮説を立てるか「立てなかった」行を書く／場所の無い関係あり＝使う側をファイル以下に絞る／
     人の仮説の否定＝`確認できず` に直し、根拠に食い違いの内容を書く。
  3. 影響仮説のファイルだけを書く。既存の行は、不足として渡された行（未確認・場所の無い関係あり・人の仮説の否定）だけを直し、他の行と根拠が `人の判断:` で始まる行は変えない。資料・観察メモ・台帳・SPO・下調べ索引は書かない。
  4. 返答は1行: `OK: 仮説 追加 {n}・判定 {m}`。続行できない場合は `NG: {原因}`。
- 返す値（「## Output」）に、変わる事実の数・仮説の数を足す。

**理由:** 下調べの範囲を、CRS が述べる振る舞いから、変わる事実を使う側まで広げるため。下調べの後に確かめる仮説を、資料の配置（スクリプトが決める）に影響させずに扱うため。

### 3.4 `change-facts.md` の「## 種類ごとの使う側の観点」（追加・③と共有）

**変更前:** なし（ファイルは③と②のどちらか先に実装する方が作る）。

**変更後:** 種類ごとに、使う側を探す観点を書く（複数のドメインの例を並べる。CLAUDE.md「適用ドメインの中立性」）。

| 種類 | 使う側を探す観点 |
|---|---|
| データ | 型のフィールドを並べて扱う箇所（写し・書き出し〔ファイル・通信・バッファ・表示・ログ〕・比較・初期化・検証・読み出し）、データの形（並び・大きさ）を前提にする箇所（大きさの定数・丸ごとの写し・形式のバージョン）、同じデータを別の型として読む箇所 |
| 状態 | 状態・モードで分岐する箇所、遷移の表、状態を保存・復元・通知する箇所 |
| 単位 | 値を変換・比較・閾値で判定・表示・保存・送信する箇所、単位を前提にした定数 |
| タイミング | 前後関係に依存する箇所（初期化の順・周期・割り込み・スレッド・イベントの購読側・呼び出しの順） |
| 列挙値 | 値の集合で分岐する箇所（すべての値を扱う分岐・表・名前の一覧・範囲の検査・最大値の定数）、値を保存・送信して別の場所で解釈する箇所 |
| その他 | 変更の内容に依存する箇所 |

SPO のレビュアー（3.9）と下調べ（3.5）がこの節を読む。

**理由:** 仮説を立てる観点と、レビューで漏れを疑う観点を同じにするため。単一スキル専用の参照ファイルは他スキル（`xddp-common/reviewer-checklists/`）から読めないため、共有規則に置く。

### 3.5 `xddp-04-specout/impact-hypotheses.md`（追加）

**変更前:** なし。

**変更後:** `# 影響仮説` ＋ blockquote でスコープを示す（`xddp-specout-prelim-agent` だけが読む。フロントマターなし）。節:
- 「## 変わる事実と使う側の仮説」: 3.0.1〜3.0.3・3.0.5 の手順（事実の決め方、由来ごとの読み方〔知見は Grep で絞ってから読む・`_cochange/` は事実の対象のファイルに当てはまる置き場所の
  `{MODULE}.md`〔置き場所の規則の読み方〕を読み、名前でも Grep する〕、コードから立てる上限 20 件、判定と根拠の書き方、`人が追加` の扱い、書き込みの順〔仮説の行は判定と同時に書く〕）。
- 「## PRELIM_MODE: hypotheses の手順」の細部（3.3 の 2. の各不足の扱い）。
- 種類の語彙・キー・種類ごとの観点は `change-facts.md` を読むよう書く（繰り返さない）。

**理由:** エージェントの定義を長くしないため（`module-documentation.md` と同じ遅延ロードの形）。

### 3.6 `xddp-04-specout/SKILL.md`（修正）

**変更前:** Step A-Prelim は下調べのエージェントを起動し、`prelim-index.md` の有無で成否を決める。Step A-Seed はシード候補・同じ呼び出し口の関数を示す。

**変更後:**

(a) **Step A-Prelim**
- 下調べのエージェントの引数に `USE_CASES_DIR`・`KNOWLEDGE_DIR`・`HYPOTHESES_TEMPLATE` を足す（3.3）。
- 前回の残骸の一覧に `SPO-{CR}-hypotheses.md`・`work/hypotheses/` を足す。
- 手順4 の後に「5. 仮説の確認」を足す（`PRELIM_FAILED_REPOS` を除く setup 対象 repo。`{OUT}` = `{CR_PATH}/04_specout/{repo}`、`{HW}` = `{OUT}/work/hypotheses`、`PY` = `$(command -v python3 || command -v python)`）:
  ```
  5. 次のいずれかの repo で行う: `{HW}/check.json` が無い、または `work/prelim-index.md`・`SPO-{CR}-hypotheses.md` より古い。
     `{OUT}/SPO-{CR}-hypotheses.md` が無ければ（下調べのエージェントが書けなかった）、`HYP_NOTES[repo]` に「影響仮説のファイルが無い。下調べからやり直すには `{OUT}/work/prelim-index.md` を消して `/xddp-04-specout {CR}` を再実行する」を足し、a〜d を行わない。
     a. Run via Bash: `"$PY" ~/.claude/skills/xddp-common/scripts/impact_hypotheses.py elements --hypotheses {OUT}/SPO-{CR}-hypotheses.md --repo {repo} --cr {CR} --out {HW}/elements.json`
        exit 1（書式の誤り）なら `HYP_NOTES[repo]` に stderr を足し、b・c を行わない。
     b. `element_count` > 0 なら Run via Bash: `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_fieldtrace.py candidates --stage specout --elements-file {HW}/elements.json
        --repo {repo} --repo-path {REPOS_MAP[repo]} --cr {CR} --engine {EFFECTIVE_SLICE_ENGINE} --slice-h-as {SPECOUT_SLICE_H_AS} --exclude '{EXCLUDE_PATTERNS}'
        --include-ext '{INCLUDE_EXTENSIONS}' --min-fields {DESIGN_COCHANGE_MIN_FIELDS} --max-depth {DESIGN_COCHANGE_MAX_DEPTH} --out-dir {HW} --human-out {HW}/cochange-candidates.md`
        exit 1・5 は `HYP_NOTES[repo]` に stderr を足し、c で `--cochange-candidates` を渡さない。
     c. Let `CHECK_CMD` = `"$PY" ~/.claude/skills/xddp-common/scripts/impact_hypotheses.py check --hypotheses {OUT}/SPO-{CR}-hypotheses.md --ledger {OUT}/work/documented-files.md
        --know-dir {DOCS}/{repo}/knowledge/code-knowledge [--cochange-candidates {HW}/cochange-candidates.json] --out {HW}/check.json`。実行する。
        exit 3 なら下調べのエージェントを `PRELIM_MODE: hypotheses`（`HYPOTHESIS_TARGETS_FILE: {HW}/check.json`、b の要約があれば `COCHANGE_DIGEST`）で1回起動し、
        `CHECK_CMD --metrics {CR_PATH}/metrics.jsonl --repo {repo} --cr {CR} --today {TODAY}` を実行する。exit 0 なら `--metrics` を付けてもう一度実行する（metrics を repo ごとに1行にするため）。
        exit 1 は `HYP_NOTES[repo]` に stderr を足す（人が Step A-Seed で直す）。
     d. 最後の check が exit 3 なら、残った不足の種類と件数を `HYP_NOTES[repo]` に足す。
  ```
- `DESIGN_COCHANGE_MIN_FIELDS`・`DESIGN_COCHANGE_MAX_DEPTH` は `## Load Config` の値を使う（①の設定。工程4a でも同じ値）。

(b) **Step A-Seed**
- 提示（repo ごと。候補表の前）に足す（件数は `{HW}/check.json` の値を使い、自分で数えない）:
  ```
  > 🧭 **{repo} の影響仮説**（`{CR_PATH}/04_specout/{repo}/SPO-{CR}-hypotheses.md`）: 変わる事実 {n} 件・使う側の仮説 {m} 件（関係あり {a}・関係なし {b}・確認できず {c}）
  > {確認できず の行: `H-n` `{使う側}` — {仮説}（{根拠}）}
  > {由来が 知見・写しの追跡・人が追加 で 関係なし の行（最大 10 行。超えた分は件数）: `H-n` `{使う側}` — {根拠}}
  > {related_undocumented があれば: 関係ありで資料の無い使う側: {一覧}（資料にする場合は工程4a の後に `/xddp-investigate {CR} document --repo {repo} {パス}`）}
  > {HYP_NOTES[repo] があれば ⚠️ {内容}}
  ```
- `GATE` = true の質問に足す: 「影響仮説の判定を直す場合は「`{repo}`: 仮説 `H-n` は関係あり（理由）」／「…は関係なし（理由）」、仮説を足す場合は
  「`{repo}`: 仮説を追加: `{使う側}` — {内容}（`F-n`）」と指示してください」。
- 指示の扱いに足す: 判定の指示は SKILL が影響仮説のファイルのその行の判定と根拠（`人の判断: {理由}（{TODAY}）`）を Edit する。
  仮説の追加は SKILL が行を足す（仮説ID は既存の最大＋1、由来 `人が追加`、判定 `未確認`）。どちらの後も Step A-Prelim の 5.c をその repo で `--metrics` を付けずに行ってから手順1 へ戻る（再提示）。
- `GATE` = false の場合は提示だけ（既存どおり）。

(c) **Step A2** の `REFERENCE_FILES` に「（repo が cross 以外で、存在する場合のみ）`{CR_PATH}/04_specout/{repo}/SPO-{CR}-hypotheses.md`」を足す。

(d) **Step A3**（人のレビュー）の成果物の一覧に `SPO-{CR}-hypotheses.md` を足す。

(e) **Step E**（報告）に repo ごとの影響仮説の件数（`check.json`）を足す。

**理由:** 下調べの直後に機械検査と①のスクリプトを挟み、人がシード確認と同じ場所で仮説を確かめられるようにするため。

### 3.7 SPO §5.8・`assemble-spo`・`specout-finish.md`（修正）

**変更前:** SPO テンプレートの §5 は §5.0〜§5.7。`assemble-spo` に影響仮説の入力は無い。

**変更後:**
- テンプレートの §5.7 の後（`## 6.` の前）に足す:
  ```
  ### 5.8 影響仮説
  <!-- 書き手: スクリプト（impact_hypotheses.py spo-section → specout_bfs.py assemble-spo）。手で直さない（再実行で上書きされる） -->

  > 下調べが立てた「変わる事実」と「使う側の仮説」のうち、関係あり・確認できずのもの（最大30行）。全量と関係なしの根拠は `SPO-{CR番号}-hypotheses.md`。
  > 「資料」は使う側のファイルが下調べ・追加下調べ・依頼調査の資料にあるか。

  | 仮説ID | 変わる事実 | 使う側 | 由来 | 判定 | 資料 | 根拠 |
  |---|---|---|---|---|---|---|
  ```
- `specout_bfs.py assemble-spo` に `--hypotheses-section-file FILE` を足す。指定時は §5.8 の見出しの下（注記の後）をファイルの内容で置き換える。
  ファイルの内容を `inputs_fingerprint` に含める（影響仮説が変われば document agent をやり直す）。未指定なら §5.8 を変えない。テストを足す。
- `specout-finish.md`「## Specout Finish」の手順5（組み立て）の前に、Run via Bash:
  `"$PY" ~/.claude/skills/xddp-common/scripts/impact_hypotheses.py spo-section --hypotheses {OUT}/SPO-{CR}-hypotheses.md --ledger {OUT}/work/documented-files.md --check-json {OUT}/work/hypotheses/check.json --out {OUT}/work/hypotheses/spo-section.md`
  （`check.json` が無ければ `--check-json` を渡さない）。exit 1（影響仮説のファイルの書式の誤り。人が直した場合等）は stderr を示して `stopped` にする。
  手順5 の `assemble-spo` に `--hypotheses-section-file {OUT}/work/hypotheses/spo-section.md` を足す。手順6 の document agent に `HYPOTHESES_FILE: {OUT}/SPO-{CR}-hypotheses.md`（存在する場合のみ）を足す。

**理由:** 影響仮説を、工程5・6 が読む SPO に入れるため。全量は別ファイルにし、SPO には上限つきの要約だけを置く（ADR-0023・ADR-0024 の2層）。

### 3.8 `xddp-specout-document-agent.md`（修正）

**変更前:** §5.3・§7・§9 は資料と CRS から書く。

**変更後:** Inputs に `HYPOTHESES_FILE`（optional）を足し、次を書く。
- §7: `関係あり` の仮説のうち、使う側の振る舞いが外から観測できる形（出力・保存の形式・通信のメッセージ・表示）で変わり、CRS の SP に無いものを、
  「CRS に {内容} を足す必要がある（影響仮説 {仮説ID}）」として書く。
- §9: `確認できず` の仮説を、人が確かめる事項として書く（仮説ID・使う側・決められない理由）。
- §5.3: `関係あり` の使う側を「影響なしと判断した範囲」に書かない。`関係なし` の仮説は §5.3 に繰り返さない（§5.8 と全量にある）。

**理由:** 確かめた仮説を工程4b（CRS）へ申し送り、決められなかった仮説を人に渡すため。

### 3.9 `reviewer-checklists/SPO.md`（修正）

**変更前:** L1・L2（1.2 の 4.）。

**変更後:**
- Structure に「`SPO-{CR}-hypotheses.md`（影響仮説の全量）が REFERENCE_FILES に入る（ある場合）。§5.8 はその要約」を足す。
- L1 に足す: 「影響仮説（§5.8・`SPO-{CR}-hypotheses.md`）について、(i) CRS の変更から変わる事実が漏れていないか（種類は `~/.claude/skills/xddp-rules/change-facts.md`「## 種類」。
  漏れは CRS の SP とコードの根拠を示して指摘する）、(ii) 各事実に、`change-facts.md`「## 種類ごとの使う側の観点」で使う側の仮説が立っているか
  （漏れが疑われるときは母体コードを確認し、根拠のファイルと行を示す）、(iii) `関係なし` の根拠がコードで確かめた具体的な内容か（「関係なし」「影響なし」だけは 🟡）、
  (iv) §5.8 に ⚠️（機械検査で残った不足）があれば、その内容が §9 で人に伝わっているか（🟡）。影響仮説のファイルが無い repo（「影響仮説は作っていない」）は (i)〜(iv) を行わない。」
- L2 に足す: 「`関係あり` の仮説のうち、外から観測できる形の変更で CRS の SP に無いものが §7 にあるか（無ければ 🔴）。」

**理由:** レビューで漏れを疑う手がかりを、仮説の一覧と種類ごとの観点にするため。

### 3.10 `artifact_lint.py`（修正）

**変更前:** SPO の S1〜S5（§4.1・§4.2・§5.5・§5.6・§5.7）。

**変更後:** S6 を足す: §5.8 の見出しがあり、プレースホルダー（`{…}`）の行が残っていない（「影響仮説は作っていない」の1行も可）。cross/ では行わない。テストを足す。

**理由:** スクリプトが §5.8 を書けていないことを機械的に見つけるため。

### 3.11 既知制約の読み取りの階層

このプランでは変えない。[PLAN-20261102-constraints-module-key](PLAN-20261102-constraints-module-key.md) が、置き場所の規則（書く側）と読み方（読む側）を
`code-knowledge-boundary.md`「## 知見の置き場所（MODULE）」に決め、下調べの既知制約の読み方を直す。影響仮説の由来 `知見 constraints …` はその読み方で読んだ制約を指す。

### 3.12 `tools/harness/refcheck.py`（修正）

`DETERMINISTIC_SCRIPTS` に `"impact_hypotheses.py"` を足す（検査D）。

### 3.13 ADR-0031（追加）

`docs/adr/ADR-0031-specout-impact-hypotheses.md` を作る。Context に 1.1・1.2、Decision に 3.0（工程4a に置く理由・由来・資料にする範囲・機械検査・①の再利用・SPO への2層の出力）、
却下した案（6.）、範囲外・限界（3.0.7）、再検討条件。前提 ADR に ADR-0018（下調べ・シード確認）・ADR-0023（2層）・ADR-0026（依頼調査）・ADR-0030（①）を挙げ、③の ADR-0032 と相互に参照する。
`docs/adr/README.md` の表に1行足す。

**再検討条件:** 工程6 の①・工程10 のテストで、工程4a の仮説に無かった漏れが継続して見つかる（③の出どころ (b)・(c) の件数）／`関係なし` の仮説が多く下調べのトークンが問題になる
（`hypothesis_summary`）／コードから立てる仮説の上限 20 件を超える事実が多い。

### 3.14 README.md・CLAUDE.md（修正）

- README のフェーズ一覧の `/xddp-04-specout` の行に「下調べで変わる事実と使う側の仮説を一覧にしてコードで確かめ（`SPO-{CR}-hypotheses.md`）、シード確認で人が直せる。
  型のフィールドの変更は工程6 の一緒に直す候補と同じスクリプトで確かめる」を足す。成果物に `SPO-{CR}-hypotheses.md` を足す。「### 決定的処理スクリプト」に `impact_hypotheses.py` を足す。
- CLAUDE.md のファイル構成の表: `xddp-common/scripts/` の行に `impact_hypotheses.py`（影響仮説の検査・知見との照合・①への入力の変換・SPO §5.8）、
  `xddp-04-specout/scripts/` の `specout_fieldtrace.py` に `--stage specout`、`xddp-rules/` の行に `change-facts.md`、単一スキル専用の参照ファイルの例に `xddp-04-specout/impact-hypotheses.md`、
  `artifact_lint.py` の SPO 機械検査に S6 を足す。「xddp.config.md の位置付け」の `DESIGN_COCHANGE_*` の説明に「工程4a の影響仮説でも使う」を足す。

---

## 4. 影響範囲

- 影響するスキル・コマンド: `/xddp-04-specout`（Step A-Prelim・A-Seed・A2・A3・E）。共通プロシージャ `specout-finish.md` を通して `/xddp-investigate`・`/xddp-05-arch` の SPO の仕上げも §5.8 を書く（影響仮説のファイルは工程4a の下調べだけが作る）。
- 影響する工程: 工程4a（下調べのトークンと時間が増える。下調べの後に、①のスクリプトと検査・不足があれば下調べのエージェントを1回）。工程4b は SPO §7 の申し送りが増えうる。工程5・6 は SPO §5.8 を読む（エージェントの変更は無い）。
- `quick`: full と同じに行う（下調べの調査範囲は `CR_PROFILE` によらない既存の方針）。`DEVELOPMENT_MODE: new`: 工程4 を行わないので無い。
- 波紋調査なし（`no-ripple.json`）の repo: 影響仮説は下調べで作るので同じに行う。
- マルチリポジトリ: repo ごと。cross には作らない。他の repo の使う側は `確認できず`（3.0.7）。
- 共有のスクリプト: `impact_hypotheses.py` が③の `cochange_knowledge.py` を import する。③の `collect` が `impact_hypotheses.py` を import する。
- トークン: 下調べのエージェントの読む量が増える（知見・ユースケースは Grep で絞ってから読む。コードから立てる仮説は1つの事実につき最大 20 件）。`PRELIM_MODE: hypotheses` は不足がある repo で1回。
- 後方互換性: 考慮しない（CLAUDE.md「後方互換性ポリシー」）。既存の CR の SPO に §5.8 は無く、工程4a をやり直すと作られる。
- ドメインの中立性: 種類と観点の例を複数のドメインで書く（3.4）。

**デグレードのリスク:**
- 下調べのエージェントの手順が増え、既存の資料・台帳・下調べ索引の書き方に影響しうる。影響仮説のファイルは手順4 までに書き、`prelim-index.md` を最後に書く順を変えない。
- `assemble-spo` の入力の指紋に §5.8 を足すので、影響仮説が変わると document agent をやり直す（入力が同じなら起動しない既存の動作は保つ）。
- §5.8 を足すと SPO の章立てが変わる。§5.x を番号で読むスクリプト（`artifact_lint.py` の `_spo_section`・`specout_bfs.py`）が §5.8 で止まることを確かめる。

---

## 5. 確認項目

- [ ] `make test`（refcheck・全 unittest）が緑
- [ ] `impact_hypotheses.py` の単体テスト（3.1 のテストの項目）が通る
- [ ] ①の標準の題材（`tests/fixtures/fieldtrace/`）に「S にフィールドを足す」CRS を当てた工程4a で、変わる事実に `S::{新しいフィールド}`（データ・追加）が入り、
      `--stage specout` の確認対象（`to_msg`・`dump`・型 M 等）がすべて仮説（由来 `写しの追跡`）になり、判定がある
- [ ] `{KNOW}/_cochange/` に `S → dump` の関係（③の形式）を置いた題材で、下調べがその仮説（由来 `知見 CC-NNN`）を立てる。下調べのエージェントが立てなかった場合に `check` が `knowledge_missing` を返し、`PRELIM_MODE: hypotheses` で足される
- [ ] `{KNOW}/_flows/` の DFD に機能B が描かれた題材で、下調べが機能B の仮説（由来 `知見 _flows/…`）を立てる（LLM の挙動。smoke で確かめる）
- [ ] Step A-Seed で影響仮説が提示され、「仮説 `H-n` は関係あり（理由）」「仮説を追加: …」の指示で影響仮説のファイルが変わり、`check` をやり直して再提示される。`人が追加` の仮説が `関係なし` にならない
- [ ] SPO §5.8 に関係あり・確認できずの行が最大30行で入り、資料の有無・⚠️ が出る。影響仮説のファイルが無い SPO は「影響仮説は作っていない」の1行
- [ ] document agent が、関係ありで CRS に無い外から観測できる変更を §7 に、確認できずを §9 に書く
- [ ] SPO レビューで、REFERENCE_FILES に影響仮説のファイルが入り、L1 の (i)〜(iv)・L2 の追加が使われる
- [ ] `artifact_lint.py --doc-type SPO` の S6 が §5.8 の欠落・プレースホルダーで落ちる
- [ ] tree-sitter が無い環境（`SPECOUT_SLICE: off`）で、`--stage specout` が規則判定で動く
- [ ] 下調べを再利用する再実行で、`check.json` が新しければ 5. を行わない。影響仮説のファイルを人が直した後の再実行では 5.c を行う
- [ ] `make smoke-full PHASE=04` で、影響仮説のファイル・§5.8・`hypothesis_summary` ができる
- [ ] スキルの同期（xddp-04-specout・specout-finish.md・下調べと document のエージェント・SPO.md・change-facts.md〔③の節と矛盾しない〕）
- [ ] CLAUDE.md・README.md の記述と整合
- [ ] 特定ドメインへの偏りがないか（種類と観点の例）
- [ ] 実行時ファイルに設計根拠・プランへの参照を書いていない（refcheck 検査F）

---

## 6. 却下した案

- **工程2（要求分析）で仮説を立てる:** コードで確かめる前の仮説が工程3 の CRS に入る。工程4a でコードを読んで確かめてから、§7 で工程4b に申し送る。
- **波紋調査で届いたファイルを LLM に読ませる:** 量が多い（ADR-0023・ADR-0024 で LLM に全量を渡さないと決めた）うえ、フィールドの追加のように値が変わらない依存には届かない。
- **知見のディレクトリをすべて読ませる:** CR を重ねると大きくなる。事実の対象の名前で Grep して絞る。`_cochange/` は表なので、照合の漏れをスクリプトで確かめる。
- **知見との照合を LLM だけに任せる:** 今回の事例の原因（知見があったのに使われなかった）を防げない。表の形の知見（③）は `check` で網羅を確かめる。図・自由文の知見（`_flows/` 等）は LLM の Grep に任せる。
- **仮説を自動で波紋調査のシードにする:** 使う側は変更の下流で、値の変化は波紋調査がシードから追う。シードを増やすとヒット過多・予算超過になりうる。人が Step A-Seed で足せる。
- **下調べの後に確かめた仮説の使う側も自動で資料にする:** 資料の書き先はスクリプトが配置判定で決める（ADR-0018・ADR-0023）。下調べの後に足すには台帳の工程の新設と書き先の決定が要る。
  §5.8 の「資料」列で示し、人が `/xddp-investigate document` で頼めるようにする。
- **工程6（CHD）でも仮説と §4 を照合する:** 型のフィールドは①が工程6 で扱う。それ以外の仮説の照合は、③で漏れの件数を測ってから決める（再検討条件）。
- **コードから立てる仮説に上限を設けない:** 広く使われる型・変数では使う側が数百になり、下調べが終わらない。上限を超えた分は `確認できず` として人に示す。

---

## 7. 未決事項（レビューで確認したい点）

1. コードから立てる仮説の上限（1つの事実につき 20 件）。参照ファイルの定数にした（設定キーにしない）。
2. 下調べの後に確かめた仮説の使う側を資料にしない（3.0.5）。資料にする場合は、台帳の工程の新設（例: `仮説の確認`）と書き先の決定（依頼調査と同じ `assemble-spo --layout-only --only requested`）が要る。
3. §5.8 の上限（30 行）と並び。①・回帰の要約と同じ値にした仮の値。
4. 種類の語彙（③と共有）。
5. Step A-Seed で人が判定を直す指示の形（「仮説 `H-n` は関係あり（理由）」）。
6. **スクリプトの中の細部は実装時にテストで確定する**（①と同じ方針）: 検査の細部、§5.8 の列と並び、⚠️ の文言、`hypothesis_summary` の項目。
   ファイル間の約束事（影響仮説のファイルの場所と列・語彙、3.1 の関数・サブコマンド・終了コード、`PRELIM_MODE: hypotheses` の入出力、`--stage specout`、`assemble-spo` の引数、③と共有する関数と `change-facts.md` の節）を
   変える必要が出た場合は、実装を止めて人に相談する（③のプランも直す）。

---

## 8. レビュー

AIレビュー結果: [plans/review/PLAN-20261102-impact-hypotheses-review.md](review/PLAN-20261102-impact-hypotheses-review.md)（未実施）

---

## 9. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | |
| 承認日 | |
| 備考 | |
