# PLAN-20261102-cochange-knowledge

作成日: 2026-11-02  
ステータス: 草案 / **承認待ち** / 承認済み / 実装完了
> 保留: PLAN-20261103-contract-audit で A1・A2 の指摘を割り当てたすべての修正プランの実装の後に、同プランの 3.3 のとおり再発防止を足し、AI レビューをやり直してから承認・実装に進む（同プランの 7. の 4.）。

---

## 1. 背景・目的

### 1.1 起きたこと

[PLAN-20261102-field-copy-trace](PLAN-20261102-field-copy-trace.md)（以下 ①）の 1.1 と同じ事例。機能A の構造体 S にフィールド f を足したとき、
S を通信用の構造体 M を経てフィールドごとにダンプする機能B の修正が漏れた。知見（code-knowledge）には機能A〜機能B の DFD があったが使われなかった。

この CR が終わった後に「S にフィールドを足したら、機能B のダンプにも足す」という関係を残す場所が無い。次に S を変える CR でも、同じ漏れが起きうる。

### 1.2 原因（コードで確認した事実）

1. **「X を変えたら Y も直す」という関係を貯める欄が無い。** code-knowledge の宛先は `xddp-rules/code-knowledge-boundary.md`「## 宛先ルーティング表」の6種
   （制約・落とし穴／構造体依存関係／共有定数・列挙値／機能間フロー（シーケンス）／データフロー図（DFD）／変数データフロー（callgraph））で、
   どれも図か自由文（`[CK-NNN]` のブロック等）である。工程4a の下調べが「変わる事実」と機械的に照合できる形が無い。
2. **CR クローズの知見の昇格が、一緒に直した箇所を読まない。** `agents/xddp-close-knowledge-agent.md`「### Step C3.6: code-knowledge 昇格」は
   SPO §3・§4.2・§4.5・§5.6、LL の `#リスク`・`#見落とし`・`#仕様定義`、TRS の NG を読むが、次を読まない。
   - 工程6 Step A2.5 の一緒に直す候補のうち CHD §4 に足したもの（①。`06_design/{repo}/work/cochange/cochange-candidates.json`）
   - CHD §4 にあって工程4a の文書化済みファイル台帳（`04_specout/{repo}/work/documented-files.md`）に無い変更（工程4a で読んでいなかった変更）
   - TRS の NG は「制約・落とし穴」として `constraints.md` に書く（同 Step C3.6「per-repo TRS 不具合エントリから昇格」）が、
     どの変更に合わせて何を直す必要があったかの関係としては残さない。
3. **知見の書き手と読み手でモジュールの決め方が違う。** 下調べは `{KNOW}/{第1階層}/constraints.md` を読む（`agents/xddp-specout-prelim-agent.md`「## Process」3. の既知制約）が、
   CR クローズは「ファイルパスの第1〜2階層ディレクトリ名」で書く（`agents/xddp-close-knowledge-agent.md` Step C3.6）。第2階層に書いた `constraints.md` を下調べは読まない。
   この不具合は [PLAN-20261102-constraints-module-key](PLAN-20261102-constraints-module-key.md) で直す（置き場所の規則を `code-knowledge-boundary.md`「## 知見の置き場所（MODULE）」に決める）。
   このプランの `_cochange/` も同じ規則で分ける（3.0.2）。

### 1.3 目的

「X を変えたら Y も直す」関係を、プラン②（以下 ②）の下調べが**スクリプトで照合できる表**として repo ごとに貯め、CR クローズで昇格する。

- 昇格の出どころは、①の結果・工程4a の後に CHD で増えた変更・テストで見つかった漏れの3つと、②で確かめた影響仮説（3.0.4。④とする）。
- 決定的な処理（出どころの抽出・形式の検査・ID の採番・upsert・再確認の回数）はスクリプト、意味の判定（関係として残すか・X は何か・理由）は LLM（新設のエージェント）が行う
  （CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」）。
- 人は CR クローズの Step D で確認し、知見のファイルを直接直せる。人が手で登録する経路（`/xddp-update-knowledge`）も設ける。

### 1.4 関連するプラン

| プラン | 内容 | 関係 |
|---|---|---|
| ① PLAN-20261102-field-copy-trace（実装済み） | 工程6 Step A2.5 の一緒に直す候補 | ③の出どころ (a)。`chd_cochange.py check` に出力を1つ足す（3.2） |
| ② PLAN-20261102-impact-hypotheses（並行して作成） | 工程4a の下調べで「変わる事実」と「使う側の仮説」を一覧にし、コードで確かめる | ②が③の 3.0.2 の形式を読み、3.0.3 の規則で照合する。③は②の影響仮説のファイルを出どころ (d) として読む |
| ③ このプラン | 一緒に直す箇所の知見を貯め、CR クローズで昇格する | — |

**共有する約束事（②と同じ内容。変える場合は両方のプランを直す）:**
- 知見のファイルの場所と表の列（3.0.2）、照合の規則（3.0.3）、キーの書式（3.0.1）、種類の語彙（3.0.1。②の「変わる事実」の種類と同じ）。
- これらは新設の共有規則 `xddp-rules/change-facts.md` に書く。③は「## 種類」「## キー」「## 一緒に直す箇所の知見」を、②は「## 種類ごとの使う側の観点」を書く
  （下調べのエージェント・SPO のレビュアー・③のエージェントが同じファイルを読むため、単一スキル専用の参照ファイルにしない）。先に実装するプランがファイルを作る。
- 形式の読み取りは `xddp-common/scripts/cochange_knowledge.py` の `load_relations`・`match_relations` だけが行う（②の `impact_hypotheses.py check` はこれを import する）。
- 影響仮説のファイルの読み取りは②の `xddp-common/scripts/impact_hypotheses.py` の `load_hypotheses` だけが行う（③の `collect` はこれを import する）。

**実装の順序:** `change-facts.md`（③と②の節）と、③の 3.1 のうち形式の読み取り（`load_relations`・`match_relations`）・②の `load_hypotheses` → ②の残り → ③の残り（`collect`・`upsert`・クローズ）。
`_cochange/` の分け方は [PLAN-20261102-constraints-module-key](PLAN-20261102-constraints-module-key.md) の置き場所の規則を使うので、そのプランを先に（または同時に）実装する。
片方だけを先に承認・実装する場合は、相手の読み取り関数だけをそのプランの定めどおりに先に作る。

---

## 2. 変更対象ファイル

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `ClaudeCode/.claude/skills/xddp-common/scripts/cochange_knowledge.py` | 追加 | 形式の読み取り・照合（②と共有）、サブコマンド `collect`・`upsert`（3.1） |
| `ClaudeCode/.claude/skills/xddp-common/scripts/tests/test_cochange_knowledge.py` | 追加 | 3.1 のテスト |
| `ClaudeCode/.claude/skills/xddp-06-design/scripts/chd_cochange.py` | 修正 | `check` に `--status-out`（候補ごとの処理の結果を JSON に書く）（3.2） |
| `ClaudeCode/.claude/skills/xddp-06-design/scripts/tests/test_chd_cochange.py` | 修正 | `--status-out` のテスト |
| `ClaudeCode/.claude/skills/xddp-close/SKILL.md` | 修正 | 「## Step C3.7」の新設、Step D・E・F の報告（3.3） |
| `ClaudeCode/.claude/agents/xddp-close-cochange-agent.md` | 追加 | 出どころごとに、関係として残すか・X・理由を決めて提案を書く（3.4） |
| `ClaudeCode/.claude/skills/xddp-rules/change-facts.md` | 追加（②と共有） | 「## 種類」「## キー」「## 一緒に直す箇所の知見」（場所・列・同じ関係・照合の規則）。②は「## 種類ごとの使う側の観点」を書く（3.5） |
| `ClaudeCode/.claude/skills/xddp-rules/code-knowledge-boundary.md` | 修正 | 「## 宛先ルーティング表」に「一緒に直す箇所」の行を足す（3.5） |
| `ClaudeCode/.claude/skills/xddp-update-knowledge/SKILL.md` | 修正 | 種別 `cochange`（人が手で登録する）（3.6） |
| `ClaudeCode/.claude/skills/xddp-close/scripts/promote.py`・`tests/test_promote.py` | 修正 | AI_INDEX の「## code-knowledge インデックス」に `_cochange/` を足す（3.7） |
| `tools/harness/refcheck.py` | 修正 | 検査D の `DETERMINISTIC_SCRIPTS` に `cochange_knowledge.py`（3.8） |
| `docs/adr/ADR-0032-cochange-knowledge.md`・`docs/adr/README.md` | 追加・修正 | 設計根拠・却下した案・範囲外（3.9） |
| `README.md`・`CLAUDE.md` | 修正 | xddp-close・xddp-update-knowledge の説明、スクリプトの表、知見の構成（3.10） |

---

## 3. 変更内容

### 3.0 設計（共通）

#### 3.0.1 用語・キー・種類

| 用語 | 意味 |
|---|---|
| 関係 | 「**変えるもの** X を、**種類** K の点で変えたら、**一緒に直すもの** Y も直す必要がある」という1つの知見 |
| キー | X・Y の書き方。①のキー（ADR-0030・① 3.0.6）と同じ `{ファイル}::{名前}`。ファイルはリポジトリのルートからの相対パス（`/` 区切り）。名前は型 `{型名}`・型のフィールド `{型名}::{フィールド名}`・関数 `{関数}`（メソッドは `{クラス}::{名前}`）・列挙 `{列挙型}`／`{列挙型}::{列挙子}`・定数・変数 `{名前}`。名前空間の修飾・引数の並び `(…)`・テンプレート引数 `<…>` は付けない。ファイルだけのキー `{ファイル}` も書ける |
| 種類 | 変わる事実の種類。②の「変わる事実」と同じ語彙: `データ`（型のフィールド・データの形〔並び・大きさ〕・値の範囲）／`状態`（状態・モードの種類と遷移）／`単位`（単位・精度・表現の形式）／`タイミング`（呼ばれる時期・順序・周期・同期か非同期か）／`列挙値`（列挙・コード値・フラグ・種別の値の集合）／`その他` |

種類の語彙とキーの書式は `xddp-rules/change-facts.md` の「## 種類」「## キー」に書き（3.5）、②の下調べ・SPO のレビュアーと③のエージェントが同じ節を読む。

#### 3.0.2 貯める場所と形式（②が読む形式）

- **場所:** `{KNOW}/_cochange/{MODULE}.md`（`{KNOW}` = `{DOCS}/{repo}/knowledge/code-knowledge`）。
  `{MODULE}` は、変えるもの X のファイルに置き場所の規則（`code-knowledge-boundary.md`「## 知見の置き場所（MODULE）」。ファイルの所在ディレクトリ・リポジトリ直下は `_root`）を当てた値。
  `{MODULE}` が `src/auth/login` なら `{KNOW}/_cochange/src/auth/login.md`。スクリプトが決める（LLM・人に決めさせない）。
- **1行1関係の表**（Grep で1行に関係が収まるようにする）。ファイルは `cochange_knowledge.py` が作る（テンプレートは持たない。見出しと注記はスクリプトの定数）:

```
# 一緒に直す箇所 — {repo} / {MODULE}

> `cochange_knowledge.py` が書く（xddp-close・xddp-update-knowledge）。人が直してよいが、見出し名・列・ID を変えない。1行1関係。セル内の `|` は `\|`。
> 「変えるもの」を「種類」の点で変えたら、「一緒に直すもの」も直す必要がある（あった）関係。工程4a の下調べが「変わる事実」と照合し、影響仮説（由来 `知見 CC-NNN`）にする。

| ID | 変えるもの | 種類 | 一緒に直すもの | 理由 | 見つけた工程 | 確認した回数 | 出典 | 最終確認日 |
|---|---|---|---|---|---|---|---|---|
| CC-001 | `src/a/s.h::S` | データ | `src/b/dump.c::dump_m2` | M2 をフィールドごとに書き出す。S のフィールドは to_msg で M に写り、M2 に丸ごと写る | テストで発見 | 1 | CR-2026-010 | 2026-11-02 |
```

| 列 | 値 |
|---|---|
| ID | `CC-{NNN}`。repo の `_cochange/` 全体で一意（スクリプトが既存の最大＋1 を振る） |
| 変えるもの・一緒に直すもの | キー（3.0.1）をバッククォートで囲む |
| 種類 | 3.0.1 の語彙 |
| 理由 | 1〜2文。Y が X の何に依存しているか（コード・CHD で確かめた内容） |
| 見つけた工程 | `一緒に直す候補`（①）／`設計で追加`（工程4a の資料に無く CHD §4 にあった）／`テストで発見`（TRS の NG）／`影響仮説`（②）／`人が登録` |
| 確認した回数 | その関係を確かめた CR・登録の数（同じ CR は1回） |
| 出典 | `CR-…` をカンマ区切り（人が登録したものは人が書いた出典） |
| 最終確認日 | YYYY-MM-DD |

- **同じ関係の判定（upsert のキー）:** （変えるもの, 種類, 一緒に直すもの）が同じ行。同じなら行を足さず、出典に CR を足し（既にあれば足さない）、
  確認した回数を足し、最終確認日を更新する。理由・見つけた工程は変えない（人が直した内容を残す）。

#### 3.0.3 照合の規則（②が使う）

`match_relations(relations, fact)` は、②の「変わる事実」1行（対象のキー・種類）に当てはまる関係を返す。
- 種類が同じで、かつ変えるもの X のキーの要素の並び（`::` で分けたもの。最初の要素はファイル）が、事実の対象のキーの要素の並びと同じか、その先頭に一致する。
  例: 事実 `src/a/s.h::S::f`（データ）には `src/a/s.h::S`（データ）と `src/a/s.h::S::f`（データ）が当てはまり、`src/a/s.h::S`（列挙値）・`src/a/t.h::S`（データ）は当てはまらない。
- X がファイルだけのキーなら、事実の対象のファイルが同じなら当てはまる。

照合はキーの文字列で行う（ファイルの移動・改名・名前の変更は追わない。②の LLM が名前で Grep して補う。3.0.6）。

#### 3.0.4 昇格の出どころ

CR クローズで、AFFECTED_REPOS の repo（cross を除く）ごとに次を集める（`cochange_knowledge.py collect`）。

| 出どころ | 集め方（スクリプト） | LLM が決めること |
|---|---|---|
| (a) 一緒に直す候補（①） | `cochange-candidates.json` の候補のうち、`chd_cochange.py check --status-out` の処理が `§4` のもの。X＝起点の要素の型（変更ファイル＋型名。CHD §4 の起点の行から）、種類＝`データ`、Y＝候補のキー | 関係として残すか・理由 |
| (b) 設計で追加 | CHD §4 の行（`chd_regression.py elements` のこの repo の行）のうち、変更ファイルが工程4a の台帳に無く、②の影響仮説で `関係あり` の使う側のファイルでもなく、(a) でもないもの。同じ仕様ID の他の §4 の行を X の候補として添える | X・種類・関係として残すか・理由 |
| (c) テストで発見 | `10_test-results/{repo}/TRS-{CR}-*.md` の「## 3. NG詳細」の NG のうち「変更設計書への影響」が `あり` のもの（NG の番号・対応確認項目・原因分析・影響箇所） | (b) のどの行に当たるか・X・Y・種類・残すか・理由。(b) と同じ変更なら見つけた工程を `テストで発見` にする |
| (d) 影響仮説（②） | 影響仮説のファイルの `関係あり` の行のうち、使う側のキーが CHD §4 のこの repo の行に当たるもの（ファイルが同じで、名前が同じか使う側がファイルだけのキー）。由来が `知見 CC-NNN` の行は**再確認**（下）に、それ以外は提案の出どころにする。X＝その行の事実の対象、種類＝事実の種類、Y＝使う側 | （再確認以外）残すか・理由。X を事実の対象より粗く（型のフィールド → 型）するかもここで決める |

- **再確認（LLM を使わない）:** (d) のうち由来が `知見 CC-NNN` の行は、`upsert` がその CC-NNN の確認した回数・出典・最終確認日を更新する（3.0.2 の同じ関係と同じ扱い）。
  CC-NNN が知見に無い（人が消した等）場合は更新せず、stdout の `reconfirm_missing` に返す。
- (a)〜(d) に同じ（X, 種類, Y）があれば、スクリプトが1行にまとめて元の番号を併記する。
- 出どころの各行には番号 `{repo}-S{NNN}` を振る。エージェントはすべての番号（再確認を除く）について、提案の表に「登録する」か「登録しない」を書く（`upsert` が照合する）。
- 出どころのファイルが無い場合（工程4a の台帳が無い・①を行っていない・②の影響仮説が無い・TRS が無い）は、その出どころを行わず stdout の `skipped_sources` に理由を返す。

#### 3.0.5 登録するか（エージェントの判断の観点。3.4 に書く）

- **登録する:** 「X を種類 K の点で変えると、Y の処理もそれに合わせて変える必要がある」ことを、CHD §3 の Before/After・Y のコード・TRS の原因分析から説明できる。
  この CR に固有の値（今回足したフィールドの名前等）ではなく、次に X を同じ種類の点で変える CR にも当てはまる形で、X・理由を書く（例: X を `S::f` ではなく `S` にする）。
- **登録しない:** Y の変更が X の変更とは別の要求による、Y がこの CR で新しく作ったもの、X を決められない、関係を説明できない。登録しない理由を書く（Step D で人が見直す）。
- 自動の経路なので、エージェントが絞り込んでよい（CLAUDE.md「人の依頼は LLM の関係判断で拒否しない」の自動の経路の扱い）。人が登録したいものは Step D で知見を直接直すか、`/xddp-update-knowledge` で登録する。

#### 3.0.6 範囲外・限界（ADR に書く）

- **repo をまたぐ関係・cross:** Y が他の repo にある関係は貯めない（エージェントは「登録しない（repo をまたぐ）」とする）。cross の CHD は対象にしない。
- **直さなくてよい知識:** CHD §4.1 の `不要`（一緒に直す候補だが直さなかった）は貯めない（次の CR で同じ判断が当てはまるとは限らない）。
- **古くなった関係:** 自動では消さない。②の下調べが Y を見つけられなければ、その仮説を `関係なし`（根拠に「一緒に直すもの が見つからない」）とする。消すかは人が決める（知見のファイルを直接直す）。
- **キーのずれ:** ファイルの移動・改名・名前の変更で X のキーが変わると、3.0.3 の照合では当たらない（②の LLM が名前で Grep して補う）。
- **(b) はファイル単位:** 台帳にあるファイルの別の関数を CHD で足した場合は、工程4a で読んでいなかった変更として拾わない。
- `DEVELOPMENT_MODE: new` の CR は行わない（既存のコードが無く、工程4a も無い）。

### 3.1 `cochange_knowledge.py`（追加）

**変更前:** なし。

**変更後:** `xddp-common/scripts/` に置く（xddp-close・xddp-update-knowledge・②の `impact_hypotheses.py` が使うため）。標準ライブラリのみ。

**ライブラリとして使う関数（②と共有。約束事）:**
- `load_relations(know_dir) -> list`: `{know_dir}/_cochange/` の下の `.md`（入れ子を含めて再帰。`_cochange/src/auth/login.md` 等）の表を読み、関係（ID・変えるもの・種類・一緒に直すもの・理由・見つけた工程・確認した回数・出典・最終確認日・ファイル・行）の一覧を返す。
  ディレクトリが無ければ空。書式の誤りは例外（呼び出し元が `{ファイル}\t{行番号}\t{理由}` で stderr に出す）。
- `match_relations(relations, fact_target, fact_kind) -> list`: 3.0.3 の規則。

**サブコマンド:**

```
cochange_knowledge.py collect --cr CR --repo REPO
  --elements-file ELEMENTS_JSON                 chd_regression.py elements の出力（この repo の行だけを使う）
  [--ledger LEDGER_MD]                          工程4a の台帳（無ければ (b) を行わない）
  [--hypotheses HYP_MD]                         ②の影響仮説（無ければ (d) を行わず、(b) の除外にも使わない）
  [--cochange-candidates JSON --cochange-status JSON]   ①（無ければ (a) を行わない）
  [--trs-dir DIR]                               {CR_PATH}/10_test-results/{repo}（無ければ (c) を行わない）
  --know-dir KNOW                               (d) の再確認で既存の関係を引く
  --out-json OUT_JSON --digest-out DIGEST_MD

cochange_knowledge.py upsert --proposals PROPOSALS_MD --know-dir KNOW --repo REPO --cr CR --today DATE
  [--sources-json OUT_JSON]                     collect の出力（提案の網羅の照合と再確認。手で登録するときは付けない）
  [--manual]                                    見つけた工程を `人が登録` にする
```

- `collect`: 3.0.4 の出どころを集め、`OUT_JSON`（全量。各行に番号・出どころ・X の候補・種類・Y・根拠の抜き出し〔CHD の行・バッチファイル・TRS の NG〕）と
  `DIGEST_MD`（LLM 向けの要約。出どころごとに最大 30 行〔スクリプトの定数〕、超えた分は件数と全量の場所。再確認の件数）を書く。
  stdout（JSON）: `ok`・`counts`（出どころ別）・`reconfirm_count`・`skipped_sources`（出どころと理由）。終了コード: 0＝成功（0件を含む）／1＝入力の誤り（JSON・台帳・影響仮説・TRS を読めない。stderr に原因のファイル）／2＝使い方の誤り。
- `upsert`: 提案の表（3.4 の形式）のうち `--repo` の行を読み、次を検査してから書く。
  - 書式（列・種類の語彙・キーの書式・判断が `登録する`／`登録しない`・登録しない行の理由）。誤りは exit 1（stderr `{ファイル}\t{行番号}\t{理由}`）。
  - `--sources-json` を付けたとき、再確認を除くすべての出どころの番号が提案のどれかの行の「元」にあること。無ければ exit 3（stdout `missing_sources`）。
  - exit 1・3 では知見のファイルを1つも変えない（すべての検査の後に書く）。
  - 登録する行を 3.0.2 の場所に upsert し、`--sources-json` の再確認を反映する。X のファイルが今のリポジトリに無い場合も書く（stdout の `warnings` に返す）。
  stdout（JSON）: `ok`・`added`・`updated`・`reconfirmed`・`reconfirm_missing`・`not_registered`・`files`（書いたファイル）・`warnings`。
- テスト（`test_cochange_knowledge.py`）: 形式の読み取り（列・ID・書式の誤り）、3.0.3 の照合（先頭の一致・種類の違い・ファイルだけのキー・別のファイル）、
  `collect` の (a)〜(d) の抽出と (b) の除外（台帳・関係ありの使う側・(a)）、同じ（X, 種類, Y）をまとめる、出どころが無いときの `skipped_sources`、要約の上限、
  `upsert` の新規・同じ関係（出典・回数・日付だけが変わり、理由・見つけた工程が変わらない）・同じ CR の2回目で回数が増えない・ID の採番（repo 全体で一意）・
  MODULE の決め方（置き場所の規則。所在ディレクトリ・`_root`）・入れ子のファイルの読み込みと入れ子をまたいだ ID の採番・exit 1・exit 3 で何も書かない・再確認・`reconfirm_missing`・`--manual`。

**理由:** 形式を1つのモジュールに閉じ、②の照合と③の書き込みが同じ読み取りを使うようにするため。出どころの抽出と upsert を決定的にし、LLM には判断だけをさせるため。

### 3.2 `chd_cochange.py check` の `--status-out`（修正）

**変更前:** `check` の stdout は件数（`mapped_count` 等）と `unmapped`・`unknown`・`conflicts`・上限超過の先頭を返し、候補ごとの処理の結果は `--human-out` の全量の「処理」列（人向けの Markdown）にだけ書く。

**変更後:** `--status-out STATUS_JSON` を足す。指定したときは、全候補（確認対象・上限超過・遠い名前の一致のみ）について `{キー: 処理}`（`§4`／`§4.1 不要`／`§4.1 確認できず`／`未処理`。
`--human-out` の「処理」列と同じ値・同じ優先順位）を JSON に書く。既存の出力・終了コードは変えない。テストを足す。

**理由:** CR クローズで、①の候補のうち §4 に足したものを、Markdown を解析せずに読むため。

### 3.3 `xddp-close/SKILL.md`（修正）

**変更前:** Step C2〜C7（`promote.py`）→ Step C3.5・C3.6（`xddp-close-knowledge-agent`）→ Step D → Step E → Step F。

**変更後:** Step C3.5・C3.6 の節の後に「## Step C3.7: Co-change Knowledge」を新設し、Step C3.5・C3.6 のエージェントと C3.7 のエージェントを同じメッセージで並列に起動する
（書くファイルが重ならないため。C3.7-collect は両方の起動の前に行う）。

```
## Step C3.7: Co-change Knowledge

If `DEVELOPMENT_MODE` = `new`: Let `COCHANGE_RESULT` = 「対象外（新規開発）」とし、このステップを行わない。
Let `PY` = `$(command -v python3 || command -v python)`. Let `CW` = `{CR_PATH}/pending-items/cochange`. Let `COCHANGE_REPOS` = AFFECTED_REPOS から cross を除いたもの。Let `COCHANGE_NOTES` = []。

### C3.7-collect（Step C3.5, C3.6 のエージェントの起動の前に行う）
For each `{repo}` in `COCHANGE_REPOS`:
1. Run via Bash: `"$PY" ~/.claude/skills/xddp-06-design/scripts/chd_regression.py elements --design-dir {CR_PATH}/06_design --specout-dir {CR_PATH}/04_specout --repos {REPOS_KEYS をカンマ区切り} --repo {repo} --cr {CR} --out {CW}/{repo}-elements.json`
   exit 1（CHD §4 の書式の誤り）または CHD が無い: `COCHANGE_NOTES` に「{repo}: CHD §4 を読めないため一緒に直す箇所を昇格しない: {stderr}」を足し、この repo の残りを行わない。
2. `{CR_PATH}/06_design/{repo}/work/cochange/cochange-candidates.json` があれば Run via Bash:
   `"$PY" ~/.claude/skills/xddp-06-design/scripts/chd_cochange.py check --candidates {その JSON} --design-dir {CR_PATH}/06_design --repo {repo} --cr {CR} --status-out {CW}/{repo}-cochange-status.json`
   exit が 0 でなければ `COCHANGE_NOTES` に「{repo}: 一緒に直す候補を照合できないため、出どころ (a) を使わない: {stderr}」を足し、2. の出力を使わない。
3. Run via Bash: `"$PY" ~/.claude/skills/xddp-common/scripts/cochange_knowledge.py collect --cr {CR} --repo {repo} --elements-file {CW}/{repo}-elements.json
   （存在するものだけ）--ledger {CR_PATH}/04_specout/{repo}/work/documented-files.md --hypotheses {CR_PATH}/04_specout/{repo}/SPO-{CR}-hypotheses.md
   --cochange-candidates {…}/cochange-candidates.json --cochange-status {CW}/{repo}-cochange-status.json --trs-dir {CR_PATH}/10_test-results/{repo}
   --know-dir {DOCS}/{repo}/knowledge/code-knowledge --out-json {CW}/{repo}-sources.json --digest-out {CW}/{repo}-sources.md`
   → `COLLECT[repo]`。exit 1 は `COCHANGE_NOTES` に stderr を足し、この repo の残りを行わない。
   `skipped_sources` があれば `COCHANGE_NOTES` に出どころと理由を足す。
Let `COCHANGE_TARGET_REPOS` = `COLLECT` が成功し、`counts` の合計が1以上の repo。`reconfirm_count` だけが1以上の repo は `COCHANGE_RECONFIRM_REPOS` とする。

### C3.7-agent（Step C3.5, C3.6 のエージェントと同じメッセージで起動する。`COCHANGE_TARGET_REPOS` が空なら起動しない）
**Agent tool** `subagent_type=xddp-close-cochange-agent`:
  CR_NUMBER: {CR}, CR_PATH: {CR_PATH}, REPOS_MAP: {REPOS_MAP},
  SOURCES: {COCHANGE_TARGET_REPOS の各 repo の `{repo}: {CW}/{repo}-sources.md`（全量 {CW}/{repo}-sources.json）`}，
  OUTPUT_FILE: {CR_PATH}/pending-items/COCHANGE-{CR}.md, TODAY: {TODAY}

### C3.7-upsert（両方のエージェントの完了の後）
For each `{repo}` in `COCHANGE_TARGET_REPOS` ∪ `COCHANGE_RECONFIRM_REPOS`:
  Run via Bash: `"$PY" ~/.claude/skills/xddp-common/scripts/cochange_knowledge.py upsert --proposals {CR_PATH}/pending-items/COCHANGE-{CR}.md --know-dir {DOCS}/{repo}/knowledge/code-knowledge --repo {repo} --cr {CR} --today {TODAY} --sources-json {CW}/{repo}-sources.json`
  （`COCHANGE_RECONFIRM_REPOS` だけの repo で提案のファイルが無ければ、表の頭だけの提案のファイルを Write で作ってから実行する）
  - exit 3（提案に無い出どころ）: エージェントを `MISSING_SOURCES: {missing_sources}` を足して1回だけ再度呼び、もう一度 upsert する。まだ exit 3 なら `COCHANGE_NOTES` に残りの番号を足す（知見は書かない）。
  - exit 1（提案の書式の誤り）: エージェントを `FORMAT_ERRORS: {stderr}` を足して1回だけ再度呼び、もう一度 upsert する。まだ exit 1 なら `COCHANGE_NOTES` に stderr を足す。
  - exit 0: stdout を `COCHANGE_UPSERT[repo]` に保持する。
Let `COCHANGE_RESULT` = repo ごとの「登録 {added} 件（新規）・{updated} 件（既存の関係に出典を追加）・再確認 {reconfirmed} 件・登録しない {not_registered} 件」と `COCHANGE_NOTES`。
```

- 「## Step D: Human Review Gate」の提示に次を足す（「**ドメイン名要確認**」の後）:
  ```
  > **一緒に直す箇所（{DOCS}/{repo}/knowledge/code-knowledge/_cochange/）：**
  > {COCHANGE_RESULT。登録しない行がある場合は「登録しない理由は {CR_PATH}/pending-items/COCHANGE-{CR}.md を参照。登録する場合は知見のファイルに行を足すか /xddp-update-knowledge {repo} cochange」}
  ```
- 「## Step E」の progress.md の追記に「- **一緒に直す箇所：** {repo ごとの登録・再確認の件数}」を足す。「## Step F」の報告に `COCHANGE_RESULT` を含める。
- AI_INDEX の更新は Step C2〜C7 の `promote.py` が行うため、この CR で初めて作った `_cochange/` は次の CR のクローズで索引に載る（他の code-knowledge と同じ。3.7）。

**理由:** 出どころの抽出と upsert をスクリプトで挟み、LLM は判断だけを書く。既存の知見のエージェントと書くファイルが重ならないので並列にして待ち時間を増やさない。

### 3.4 `xddp-close-cochange-agent.md`（追加）

**変更前:** なし。

**変更後:** 次の内容のエージェントを作る（CLAUDE.md「新規エージェント作成のルール」）。

- `tools:` Read・Grep・Glob・Write・Edit（Bash は使わない。スクリプトの実行は SKILL が行う）。
- Inputs: `CR_NUMBER`・`CR_PATH`・`REPOS_MAP`・`SOURCES`（repo ごとの要約と全量）・`OUTPUT_FILE`・`TODAY`、再度呼ぶときだけ `MISSING_SOURCES`・`FORMAT_ERRORS`。
- Process:
  1. Read `~/.claude/skills/xddp-rules/change-facts.md`（「## 種類」「## キー」「## 一緒に直す箇所の知見」）。各 repo の要約を Read する（全量は要約の上限を超えた出どころがあるときだけ Read する）。
  2. 出どころの行ごとに、要約に示された CHD のバッチファイル（§3 の Before/After・§4 の同じ仕様ID の行）・TRS の NG・`REPOS_MAP[repo]` の下の Y のコードを必要なだけ Read し、3.0.5 の観点で判断する。
     (b)・(c) は X を決める（同じ仕様ID の §4 の行・CHD §3・原因分析から）。(c) が (b) のどの行に当たるかを決め、当たれば1行にまとめて見つけた工程を `テストで発見` にする。
  3. `OUTPUT_FILE` に次の表を書く（既にあれば `MISSING_SOURCES`・`FORMAT_ERRORS` の分だけを足す・直す。他の行は変えない）:
     ```
     # 一緒に直す箇所の昇格の提案 — {CR}

     > xddp-close-cochange-agent が書き、`cochange_knowledge.py upsert` が読む。列を変えない。
     > 判断: 登録する／登録しない。「元」は出どころの番号（複数ならカンマ区切り）。

     | 元 | repo | 変えるもの | 種類 | 一緒に直すもの | 理由 | 見つけた工程 | 判断 | 登録しない理由 |
     |---|---|---|---|---|---|---|---|---|
     ```
  4. 返答は1行: `OK: 登録する {n} 行・登録しない {m} 行`。続行できない場合は `NG: {原因}`。

**理由:** 既存の `xddp-close-knowledge-agent` は SPO・LL・TRS から6種の知見を書く大きな手順を持つ。足すと文脈が大きくなり、再度呼ぶとき（`MISSING_SOURCES`）に他の手順をやり直すことになる。
別のエージェントにして、並列に起動し、再度呼ぶときはこの判断だけをやり直す。

### 3.5 `change-facts.md`（追加・②と共有）・`code-knowledge-boundary.md`（修正）

**変更前:** 種類の語彙・キーの書式を書いた規則は無い。`code-knowledge-boundary.md`「## 宛先ルーティング表」に6行。一緒に直す箇所の行は無い。

**変更後:**
- `xddp-rules/change-facts.md` を作る（`xddp-rules/*.md` と同じく `# 見出し` ＋ blockquote でスコープを示し、フロントマターは持たない）。③が書く節:
  - 「## 種類」: 3.0.1 の語彙。各語の説明と例を複数のドメインで並べる（例: データ＝構造体・レコード・メッセージ・レジスタの割り当て、
    単位＝物理量・時間・通貨・座標・文字の符号化、タイミング＝周期・割り込み・スレッド・イベントの順序・初期化の順）。
  - 「## キー」: 3.0.1 のキーの書式（①のキーと同じ）。
  - 「## 一緒に直す箇所の知見」: 3.0.2 の場所・列・同じ関係の判定、3.0.3 の照合の規則、「書くのは `cochange_knowledge.py` だけ（LLM は提案の表を書く）」。
  - ②が「## 種類ごとの使う側の観点」を書く（②のプランの 3.4）。
- `code-knowledge-boundary.md`「## 宛先ルーティング表」に1行足す:
  `| 一緒に直す箇所 | 関係として説明できるもの（自動抽出経路は xddp-close-cochange-agent が「登録する」としたもの） | 1・2 | {KNOW}/_cochange/{MODULE}.md | （テンプレートなし。cochange_knowledge.py が作る。形式は change-facts.md「## 一緒に直す箇所の知見」） | — |`
  「経路ごとの拘束範囲」の自動抽出経路に xddp-close Step C3.7 を、手動登録経路の説明に「`cochange` 種別も `cochange_knowledge.py upsert --manual` で書く」を足す。

**理由:** code-knowledge の宛先の単一情報源（`code-knowledge-boundary.md` の注記「宛先パス・テンプレート・セクションをこの表以外の場所に定義してはならない」）に従うため。
種類の語彙・キーを、②の下調べ・SPO のレビュアー（`xddp-common/reviewer-checklists/SPO.md`）・③のエージェントが同じファイルから読むため
（単一スキル専用の参照ファイル〔`skills/<skill-name>/*.md`〕は他スキルから参照できない。CLAUDE.md のファイル構成の表）。

### 3.6 `xddp-update-knowledge/SKILL.md`（修正）

**変更前:** 種別は `constraint|flow|callgraph|lesson|note|glossary|structure`。

**変更後:**
- 種別に `cochange` を足す（引数・`Resolve type`・番号つきの一覧）。
- Step 1 の入力:
  ```
  変えるもの（`{ファイル}::{名前}`。名前空間・引数の並びは書かない）:
  種類（データ／状態／単位／タイミング／列挙値／その他）:
  一緒に直すもの（`{ファイル}::{名前}`）:
  理由（一緒に直す必要がある理由。1〜2文）:
  出典（例: manual/2026-11-02、CR-2026-010）:
  ```
- Step 3: 入力を提案の表（3.4 の形式。元＝`manual`、判断＝`登録する`、見つけた工程＝`人が登録`）として Write で `{KNOW_DIR}/code-knowledge/_cochange/.manual-{TODAY}.md` に書き、
  Run via Bash: `"$PY" ~/.claude/skills/xddp-common/scripts/cochange_knowledge.py upsert --proposals {その一時ファイル} --know-dir {KNOW_DIR}/code-knowledge --repo {TARGET_REPO} --cr manual --today {TODAY} --manual`。
  exit 1 は stderr を示して入力をやり直す。成功・失敗にかかわらず一時ファイルを消す。出典は手で入力した値を使う（`--manual` のとき `--cr` の値は出典に使わない）。
- 引数の説明・Step 4 の報告の種別の表に `cochange` を足す。

**理由:** 人が知っている関係（今回の事例の発端の関係を含む）を CR を待たずに登録できるようにするため。形式の検査と ID の採番を、クローズと同じスクリプトに任せるため。

### 3.7 `promote.py`（修正）

**変更前:** AI_INDEX「## code-knowledge インデックス」は `_structures`・`_constants`・`_flows` を載せる（`update_ai_index` の「6. code-knowledge インデックス」）。

**変更後:** `("_cochange", "一緒に直す箇所")` を同じ並びに足す。テストを足す。

**理由:** 知見の入口（AI_INDEX）から一緒に直す箇所を辿れるようにするため。

### 3.8 `tools/harness/refcheck.py`（修正）

**変更前:** `DETERMINISTIC_SCRIPTS` に `cochange_knowledge.py` は無い。

**変更後:** `"cochange_knowledge.py"` を足す（検査D で SKILL の呼び出しのサブコマンド・フラグを照合する）。

### 3.9 ADR-0032（追加）

`docs/adr/ADR-0032-cochange-knowledge.md` を作る。Context に 1.1・1.2、Decision に 3.0（場所と形式・照合の規則・出どころ・再確認・登録の観点）、
却下した案（6.）、範囲外・限界（3.0.6）、再検討条件（下）。前提 ADR に ADR-0005（知識参照ガイドを初回のみ生成する理由。AI_INDEX の構成）・ADR-0027・ADR-0030 を挙げる。`docs/adr/README.md` の表に1行足す。②の ADR-0031 と相互に参照する。

**再検討条件:** 登録しない行が継続して多い（出どころが雑音）／②で `知見 CC-NNN` の仮説が `関係なし` になる行が多い（古い・粗すぎる関係）／
repo をまたぐ関係の漏れが起きた／`_cochange/` の1ファイルが大きくなり、②の下調べが読む量が問題になった。

### 3.10 README.md・CLAUDE.md（修正）

- README のフェーズ一覧の `/xddp-close` の行に「一緒に直す箇所（`_cochange/`）の昇格（①の候補・工程4a の後に CHD で増えた変更・テストで見つかった漏れ・影響仮説）」を足す。
  `/xddp-update-knowledge` の種別に `cochange` を足す。「### 決定的処理スクリプト」に `cochange_knowledge.py` を足す。知見の構成の説明に `_cochange/` を足す。
- CLAUDE.md のファイル構成の表の `xddp-common/scripts/` の行に `cochange_knowledge.py`（形式の読み取り・照合・出どころの抽出・upsert）を、`xddp-06-design/scripts/` の行の
  `chd_cochange.py` に `--status-out` を足す。エージェントの説明は表に無いので足さない（確認した範囲。実装時に表を見直す）。

---

## 4. 影響範囲

- 影響するスキル・コマンド: `/xddp-close`（Step C3.7 の新設・Step D・E・F の報告）、`/xddp-update-knowledge`（種別 `cochange`）。
- 影響しないもの: `xddp-close-knowledge-agent` の Step C3.5・C3.6（TRS の NG を constraints.md に書く手順を含む）は変えない。①の SKILL（xddp-06-design）の動作は変えない（`--status-out` は省略時に何もしない）。
- 読み手: ②の下調べ（`_cochange/` を読む）。②を実装しない間は、貯めた関係を読む工程は無い（人と AI_INDEX から辿れる）。
- 共有のスクリプト: `cochange_knowledge.py` を②の `impact_hypotheses.py` が import する。`impact_hypotheses.py` の `load_hypotheses` を③の `collect` が import する。
- マルチリポジトリ: repo ごとに集め、repo ごとの `_cochange/` に書く。cross には行わない。
- `quick`: full と同じに行う。`DEVELOPMENT_MODE: new`: 行わない。
- トークン: 出どころが1件以上の CR でエージェントを1回（提案の漏れ・書式の誤りで1回追加）。出どころの要約は出どころごとに最大 30 行。出どころの無い CR では起動しない。
- 後方互換性: 考慮しない（CLAUDE.md「後方互換性ポリシー」）。既存の知見に `_cochange/` は無く、最初のクローズで作られる。
- ドメインの中立性: 種類の語彙と例を複数のドメインで書く（3.5）。

**デグレードのリスク:**
- Step D の提示の項目が1つ増える。Step C3.5・C3.6 の起動の位置が変わる（並列にする）。既存の提示の順・`KNOWLEDGE_RESULT` の扱いは変えない。
- `upsert` が知見のファイルを壊すと②の下調べが読めない。exit 1・3 で何も書かないこと、同じ関係で理由・見つけた工程を変えないことをテストで確かめる。

---

## 5. 確認項目

- [ ] `make test`（refcheck・全 unittest）が緑
- [ ] `cochange_knowledge.py` の単体テスト（3.1 のテストの項目）が通る
- [ ] `chd_cochange.py check --status-out` の値が `--human-out` の「処理」列と一致する。省略時の出力・終了コードが変わらない
- [ ] ①の標準の題材（`tests/fixtures/fieldtrace/`）で CHD §4 に `dump` を足した CR を作り、クローズで (a) から `S → dump`（データ）の関係が `_cochange/` に登録される
- [ ] 工程4a の台帳に無いファイルを CHD §4 に足した CR で、(b) に出て、エージェントが X を決めて登録する。台帳にあるファイル・②で `関係あり` の使う側のファイルは (b) に出ない
- [ ] TRS に「変更設計書への影響: あり」の NG がある CR で、(c) に出て、(b) の同じ変更と1行にまとまり、見つけた工程が `テストで発見` になる
- [ ] ②の影響仮説で由来 `知見 CC-NNN`・`関係あり`・CHD §4 にある行が、LLM を通さずに CC-NNN の確認した回数・出典・最終確認日を更新する。同じ CR の再実行で回数が増えない
- [ ] 提案に無い出どころの番号があると exit 3 で何も書かず、エージェントを1回だけ再度呼ぶ
- [ ] `/xddp-update-knowledge {repo} cochange` で1行登録でき、ID が repo の `_cochange/` 全体で一意になる。一時ファイルが残らない
- [ ] AI_INDEX の「## code-knowledge インデックス」に `_cochange/` が載る（`_cochange/` があるクローズで）
- [ ] マルチリポジトリで repo ごとに別の `_cochange/` に書き、cross に書かない
- [ ] `DEVELOPMENT_MODE: new` で Step C3.7 を行わない
- [ ] `make smoke-full-all`（close を含む全通し。既知の制限あり〔tools/README.md 3.5節〕）で Step C3.7 が動くか。close 単体の `smoke-full PHASE` は無い（README の「開発時テストハーネス」では `NN∈02〜11`）。動かせない場合は fixture の CR で手で確かめ、その旨をプランに記録する
- [ ] スキルの同期（xddp-close・xddp-update-knowledge・code-knowledge-boundary.md・change-facts.md〔②の節と矛盾しない〕）
- [ ] CLAUDE.md・README.md の記述と整合
- [ ] 特定ドメインへの偏りがないか（種類の語彙の例）
- [ ] 実行時ファイルに設計根拠・プランへの参照を書いていない（refcheck 検査F）

---

## 6. 却下した案

- **`constraints.md` に節を足して貯める:** `constraints.md` は LLM が `[CK-NNN]` のブロックで書く自由文のファイルで、スクリプトが表を upsert すると LLM の書き込みと衝突しうる。
  モジュールの決め方も書き手と読み手で食い違っている（1.2 の 3.）。スクリプトだけが書く別のファイルにし、モジュールをスクリプトが決める。
- **repo に1つのファイルにまとめる:** CR を重ねると大きくなり、人が読みにくい。②の下調べは Grep と変えるもののモジュールで読むので、モジュールで分けても読む量は増えない。
- **ドメイン名（`{DOMAIN}`）で分ける（`_flows/` と同じ）:** ドメイン名は人の確認待ちになる（`xddp-close/SKILL.md` Step D「ドメイン名要確認」）。スクリプトが決められる置き場所の規則（既知制約と同じ）で分ける。
- **既存の `xddp-close-knowledge-agent` に Step を足す:** 3.4 の理由。
- **LLM に知見のファイルを直接 upsert させる:** ID の採番・同じ関係の判定・回数の更新は決定的な処理。書式の誤りで②の照合が壊れる。
- **CHD §4.1 の `不要` も貯める:** 次の CR で同じ判断が当てはまるとは限らず、②の仮説を誤って打ち消しうる（3.0.6）。
- **古くなった関係を自動で消す:** Y が見つからない理由（改名・移動・削除）をスクリプトは区別できない。②で `関係なし` とし、人が消す（3.0.6）。
- **出どころ (b) を関数単位にする:** 工程4a の台帳はファイル単位。関数単位にするには工程4a の資料から関数を抜き出す必要があり、資料の書き方に依存する。

---

## 7. 未決事項（レビューで確認したい点）

1. 出どころに②の影響仮説（(d)）を足した。合意した範囲（①の結果・CHD で増えた変更・テストで見つかった漏れ）を広げている。
   (d) の再確認（LLM を使わない）は②の照合の精度を測るのにも使える（`確認した回数`）が、範囲を合意どおりにするなら (d) を外す。
2. 要約の上限（出どころごとに 30 行）。①・回帰の要約と同じ値にした仮の値。
3. 種類の語彙（データ／状態／単位／タイミング／列挙値／その他）。②と同じ語彙。語を足すと②の照合と既存の知見の両方に効く。
4. X を粗くするか（フィールド → 型）の判断を LLM に任せた（3.0.5）。粗すぎると②で `関係なし` が増え、細かすぎると当たらない。
5. **スクリプトの中の細部は実装時にテストで確定する**（①と同じ方針）: 要約の列と並び、同じ（X, 種類, Y）のまとめ方、`warnings` の内容、提案の表の検査の細部。
   ファイル間の約束事（3.0.2 の場所と列、3.0.3 の照合、3.1 の関数・サブコマンド・終了コード、3.4 の提案の表の列、②と共有する関数）を変える必要が出た場合は、
   実装を止めて人に相談する（②のプランも直す）。

---

## 8. レビュー

AIレビュー結果: [plans/review/PLAN-20261102-cochange-knowledge-review.md](review/PLAN-20261102-cochange-knowledge-review.md)（未実施）

---

## 9. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | |
| 承認日 | |
| 備考 | |
