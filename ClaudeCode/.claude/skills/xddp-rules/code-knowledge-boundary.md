# code-knowledge 書き分け規約

## spec.md に書くもの（機能の「今何ができるか」）

- 機能の入力・出力・振る舞いの定義
- 正常系・異常系のシーケンス
- インタフェースの型定義・シグネチャ
- データ構造のフィールド定義

## constraints.md に書くもの（コードの「気をつけること」）

- 制限事項（呼び出しスレッド・タイミング制約・再入不可等）
- 落とし穴・過去の不具合パターン
- 暗黙の前提（コードを読んでも分からないビジネス・ハードウェア制約）
- パフォーマンス感度・非機能特性の観察

## 判断フローチャート

```
SPO Section 5.6 / LL エントリを見て:
  「この情報はモジュールの仕様（どう動くか）か？」
    YES → spec.md（または latest-specs に書かれているはず）
    NO  → 「コードを正しく使う / 修正するための注意事項か？」
      YES → constraints.md（code-knowledge）
      NO  → lessons-learned.md（プロセス知見）
```

## overview/ vs _structures/ の役割分担

| 場所 | 目的 | 管理工程 |
|---|---|---|
| `{DOCS}/{repo}/specs/overview/architecture.md` | 現在の正確なシステム構造（仕様の一部として管理） | xddp-11-specs（工程11）／ xddp-survey（追記のみ。承認の後に `{DOCS}` と latest-specs の両方へ） |
| `{DOCS}/{repo}/knowledge/code-knowledge/_structures/` | モジュール間の構造体依存関係 ＋ 落とし穴注記 | xddp-close（cross の `{XKNOW}` のみ）／ xddp-survey ／ xddp-update-knowledge |

**書き分け基準:**
- `architecture.md`: 「今この時点のシステム構造はこうなっている」（仕様的記述・常に最新に保つ）
- `_structures/{domain}-relations.md`: 「このモジュールがあのモジュールを参照するときの注意点」（経験的知識・CR を重ねるごとに精緻化）

**更新のトリガー:**
- `architecture.md` はモジュール構造が変わるたびに更新する（xddp-11-specs が担当）
- `_structures/` は構造体間の依存関係から生じる落とし穴・制約が判明したときに更新する
  （xddp-close Step C3.6〔cross の `{XKNOW}` のみ〕／ xddp-survey の knowledge 昇格 ／ xddp-update-knowledge が担当）

**昇格条件（重要）:** `_structures/` へエントリを作るのは、構造体依存関係に**落とし穴・注意点の記述が
伴う場合のみ**とする。純粋な構造記述（依存図・型定義のみで注意点を伴わないもの）は仕様側
（`specs/overview/architecture.md`・`specs/overview/data-model.md`・`cross/interfaces/{if}/schema.md`）に
置き、`_structures/` へは昇格しない。

両ファイルが同一 CR で更新される場合がある（構造体変更 CR）が、記述の視点が異なるため重複ではない。

## 宛先ルーティング表

> code-knowledge へ書き込む全経路（xddp-close Step C3.6・xddp-survey の knowledge 昇格・
> xddp-update-knowledge Step 3）はこの表を単一情報源とする。
> 宛先パス・テンプレート・セクションをこの表以外の場所に定義してはならない。
>
> **経路ごとの拘束範囲:**
> - **自動抽出経路**（xddp-close Step C3.6・xddp-survey の knowledge 昇格）:
>   全列に拘束される（**昇格条件列を含む**）。
> - **手動登録経路**（xddp-update-knowledge）: **出力パス・テンプレート・セクション列のみ**に拘束される（出力パスの `{MODULE}` を決める「## 知見の置き場所（MODULE）」を含む）。
>   昇格条件列は適用しない（人が登録対象を判断済みであるため、機械的な条件で拒否しない）。

**判断軸:** 宛先は次の2軸のいずれかに該当するかで決まる。

| 軸 | 問い | 該当する場合 |
|---|---|---|
| 軸1（性質） | 仕様（どう動くか）ではなく、コードを正しく使う・直すための注意事項か | code-knowledge へ |
| 軸2（スコープ） | 単一モジュールに閉じず、モジュール／リポジトリを横断する情報か | code-knowledge へ |

軸2が必要な理由: `specs/{module}/spec.md` はモジュール単位のファイルであり、
モジュールを横断する情報には仕様側に置き場が無い。

**パス略記:** `{KNOW}` = `{DOCS}/{repo}/knowledge/code-knowledge`、
`{XKNOW}` = `{DOCS}/cross/knowledge/code-knowledge`（`IS_MULTI` の場合のみ）。

| 知識種別 | 昇格条件 | 軸 | 出力パス | テンプレート | セクション |
|---|---|---|---|---|---|
| 制約・落とし穴 | 常に | 1 | `{KNOW}/{MODULE}/constraints.md`（`{MODULE}` は「## 知見の置き場所（MODULE）」） | `xddp-close/templates/code-knowledge-constraints-template.md` | 既知の制約・落とし穴 ／ 仕様上の暗黙の前提 ／ パフォーマンス・非機能特性 |
| 構造体依存関係 | 落とし穴・注意点の記述が伴う場合のみ | 1 | `{KNOW}/_structures/{DOMAIN}-relations.md` ／ `{XKNOW}/_structures/{DOMAIN}-relations.md` | `xddp-close/templates/code-knowledge-structures-template.md` | 注意事項・制約 |
| 共有定数・列挙値 | モジュール横断／リポジトリ間で共有されるもののみ | 2 | `{KNOW}/_constants/{DOMAIN}-constants.md` ／ `{XKNOW}/_constants/{DOMAIN}-constants.md` | `xddp-close/templates/code-knowledge-constants-template.md` | — |
| 機能間フロー（シーケンス） | 複数モジュール／複数リポジトリにまたがるフローのみ | 2 | `{KNOW}/_flows/{DOMAIN}-{FLOW_NAME}-sequence.md` ／ `{XKNOW}/_flows/{DOMAIN}-{FLOW_NAME}-sequence.md` | `xddp-close/templates/code-knowledge-flows-sequence-template.md` | — |
| データフロー図（DFD） | 複数モジュールにまたがる場合のみ | 2 | `{KNOW}/_flows/{DOMAIN}-{FLOW_NAME}-dfd.md` | `xddp-close/templates/code-knowledge-flows-dfd-template.md` | — |
| 変数データフロー（callgraph） | モジュール横断で更新・参照される識別子のみ | 2 | `{KNOW}/_flows/{DOMAIN}-{VAR_NAME}-callgraph.md` | `xddp-update-knowledge/templates/callgraph-template.md` | — |

**per-repo / cross の使い分け:**
単一リポジトリ内のモジュール間で共有される情報 → per-repo（`{KNOW}`）。
リポジトリ間で共有される情報 → cross（`{XKNOW}`。`IS_MULTI` の場合のみ）。

**昇格条件を満たさない情報の行き先:** 仕様側（`specs/{module}/spec.md`・
`specs/overview/architecture.md`・`specs/overview/data-model.md`・`cross/interfaces/{if}/schema.md`）。
code-knowledge へは昇格しない。

## 知見の置き場所（MODULE）

> 宛先ルーティング表の `{MODULE}` の決め方と読み方。書く側（xddp-close Step C3.6・xddp-survey の knowledge 昇格・
> xddp-update-knowledge）と読む側（工程4a の下調べ・AI_INDEX の作り直し〔`ai_index.py`〕・工程2 の参照先）はこの節に従う。

### 書く側: 置き場所は `knowledge_place.py place`、制約は `knowledge_place.py upsert` で書く

置き場所は `knowledge_place.py` で決める。手で当てない（正規化・実体の確認・知見1件の置き場所の決定はスクリプトが行う）。
制約（`constraints.md` のエントリ）は `upsert` だけで書く。エージェント・スキルは `constraints.md` を直接 Edit・Write しない
（採番・同じエントリかの照合・節と欄の書式はスクリプトが行う）。共有の知見（`_structures/`・`_constants/`・`_flows/`）は各経路が宛先ルーティング表に従って書く。

#### `place`（置き場所だけを決める）

```
PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/knowledge_place.py place --repo-root {REPOS_MAP[repo] の値} --workspace-root {WORKSPACE_ROOT} --input {入力 JSON のファイル}
```

- **入力**（`--input` のファイル、省略時は stdin）: `[{"id": "…", "targets": ["…", …], "fallback": "_general"}, …]`
  - `id`: 呼び出し側が付ける知見の識別子（出力をどの知見に当てるかの対応だけに使う）。
  - `targets`: その知見の対象の表記を、本文に書かれたまま並べる（`src/db.go:45`・`parse_header()`・`lib/net/` 等。正規化しない）。
  - `fallback`（省略時 `_general`）: 対象にパスが1つも無いとき・予約名と衝突したときの置き場所。
  - 対象の表記はバッククォート・`$`・引用符を含みうるので、シェルのコマンド行に JSON を書かない。
    エージェントは Write で入力 JSON をファイルに書いて `--input` で渡す。スキルは引用符付きのヒアドキュメント（`<<'EOF'`）で stdin に渡してよい。
  - JSON の文字列の `\` は `\\`、`"` は `\"` と書く（パスは `/` で区切ってよい）。対象・識別子の欄に制御文字（`\` の書き漏らしでできる `\n`・`\f` 等）があれば終了コード 2。
  - 1回の呼び出しで複数の知見をまとめて渡す（repo ごとに1回）。
- **出力**（stdout の JSON 1行）: `[{"id": "…", "module": "…", "reserved_collision": false, "targets": [{"raw": "…", "status": "…", "rel": "…", "place": "…"}, …]}, …]`
  - `module`: その知見の置き場所（`{MODULE}`）。
  - `status`: `placed`（置き場所を決めた）／`no-path`（パスとして扱わない表記）／`url`／`outside-repo`（リポジトリの外）／`not-found`（所在ディレクトリがリポジトリに無い）。
    `/` で始まり、ワークスペースの下でもリポジトリの下でもないパスは、リポジトリのルートからの意味でも所在ディレクトリが無ければ `outside-repo`
    （`not-found` は、相対パスと、リポジトリの下の絶対パスで所在ディレクトリが無いときだけ）。
    限界: リポジトリのルートからの意味で `/` を付けて、まだ無いディレクトリを書いたもの（`/src/newdir/x.c`）も `outside-repo` になる。
  - `reserved_collision`: 対象の共通の先頭の第1要素が予約名と同じ名前のリポジトリのディレクトリのとき true。
    `_structures`・`_constants`・`_flows`・`_cochange` と同じ名前なら、その置き場所は読まれないので、置き場所を `fallback` にする。
    `_root`・`_general` と同じ名前なら、その置き場所のまま（その置き場所に混ざるが読まれる）。
- **終了コード:** 0＝成功、1＝`--repo-root` のディレクトリが無い、2＝引数・入力 JSON の誤り。
- **人に示すもの:** `status` が `placed` 以外の対象を持つ知見（置き場所が `fallback` になったもの・対象の一部を置き場所に使わなかったもの）、
  `reserved_collision` が true の知見、終了コードが 0 以外だった場合はその旨。示し方は各経路の手順に従う。
- **予約名:** `_root`（リポジトリ直下）・`_general`（特定のファイルに結び付かない）・`_structures`・`_constants`・`_flows`・`_cochange`。

#### `upsert`（置き場所を決めて制約のエントリを書く）

```
PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/knowledge_place.py upsert --docs {DOCS} --repo {repo} --repo-root {REPOS_MAP[repo] の値} --workspace-root {WORKSPACE_ROOT} [--input {入力 JSON のファイル}] [--batch-cr {CR_NUMBER} | --batch-survey {SURVEY_FILE}] [--dry-run]
```

- `--input` の扱い・JSON の書き方・1回の呼び出しで repo の知見をまとめて渡すことは `place` と同じ。入力は空のリストでもよい。`--repo cross` は終了コード 2（制約は `{XKNOW}` に置かない）。
- **入力**: `[{"id", "targets", "subjects", "fallback", "section", "title", "fields", "source", "key", "replace"}, …]`
  - `id`・`targets`・`fallback`: `place` と同じ。置き場所は `targets` だけから決める。`fallback` は書き先のディレクトリになるので、`_general`・`_root`、
    またはリポジトリのルートからの相対パス（`/` 区切り。`.`・`..`・先頭の `/`・ドライブ名・`\` を含まず、`_structures` 等の予約名で始まらない）に限る。
  - `subjects`（任意）: 置き場所の決定に使わず、`**対象:**` に表示だけする対象の表記（手での登録の自由記述の「対象」）。
  - `section`: `constraint`（既知の制約・落とし穴）／`assumption`（仕様上の暗黙の前提）／`performance`（パフォーマンス・非機能特性）。
  - `title`: 見出し。`fields`: 節ごとのキーをすべて持つオブジェクト（`constraint`: `content`＝内容・`workaround`＝回避策、`assumption`: `premise`＝前提・`reason`＝理由、
    `performance`: `observation`＝観察・`implication`＝示唆）。値は文字列（空なら `—` と書かれる）。
  - `source`: 出典の表示（下の「経路ごとの鍵と出典」）。
  - `fields`・`source` は改行・タブを書いてよい。フェンスのコードブロックの外に、見出しの形の行（`#` で始まる）や `<!-- key:` で始まる行があれば終了コード 2（コード片はフェンスで囲む）。
  - `key`: 元の文書の中での項目の鍵（下の「経路ごとの鍵と出典」）。`--batch-cr`・`--batch-survey`（以下 `--batch`）のときは必須、それ以外は指定できない。
  - `replace`（`--batch` でないときだけ）: 置き換える書き先の既存のエントリの `CK-NNN`（手での登録で人が選んだとき）。鍵の行の無いエントリも指定できる。
- **鍵**（見出しの次の行の `<!-- key: … -->`。スクリプトが書く）: `--batch-cr` は `cr:{CR_NUMBER}:{key}`、`--batch-survey` は `survey:{SURVEY_FILE の WORKSPACE_ROOT からの相対パス}:{key}`、
  `--batch` が無ければ `manual:{file}:{CK-NNN}`（`replace` で置き換えたときも新しい `manual:` の鍵）。経路の名前空間を固定の接頭辞で分けるので、CR 名によらず混ざらない。
- **処理:**
  - 同じ鍵のエントリを `{KNOW}` の下のすべての `constraints.md` から探し、同じファイルの同じ節なら `[CK-NNN]` を保って置き換える（`replaced`）。
    同じファイルの別の節なら `[CK-NNN]` を保って新しい節の末尾へ移す（`moved`）。別のファイルなら、そこから消し、書き先のファイルの最大の番号＋1 で足す（`moved`）。
    無ければ書き先のファイルの最大の番号＋1 で足す（`added`。ファイルが無ければテンプレートの見出し・更新ルール・3つの節の見出しで作り、`001`）。
  - 鍵の行の無いエントリ（人が直接書いたもの）は、鍵による照合と `not_written` の対象にせず、消さない（`replace` で人が指定したときだけ置き換える）。
    自動の経路で書いたエントリを人が直接書き直すときは鍵の行も消す（消さないと、同じ CR のクローズ・同じ SURVEY の昇格をやり直したときに上書きされる）。
  - `--batch` のときは、鍵がその接頭辞（`cr:{CR_NUMBER}:`・`survey:{相対パス}:`）で始まり、今回の入力に無いエントリを `not_written` に返す。消さない（消すかは人が決める）。
  - フェンスのコードブロックの中の行は見出しとして扱わない。`[CK-NNN]` で始まらない `### ` の見出しの範囲はエントリとして扱わず、そのまま残す。
  - すべての入力を検証し、書いた後の内容を決めてからファイルを書く。終了コード 2 のときはどのファイルも変えない。
- **出力**（stdout の JSON 1行）: `{"entries": […], "not_written": […], "emptied": […]}`。
  - `entries`: 入力の順に、`place` の出力の要素に `file`（`{KNOW}` からの相対パス）・`ck`・`action`（`added`／`replaced`／`moved`）と、`moved` のときは `moved_from`（移す前の `file`・`ck`）を足したもの。
  - `not_written`: `--batch` の接頭辞の鍵で、今回の入力に無いエントリの `file`・`ck`・`key`・`title`。
  - `emptied`: 移動でエントリが1件も無くなった `constraints.md`（消さない）。
  - `--dry-run`: 何も書かず、書いたらそうなる値と、書き先ごとの既存のエントリ `existing`（`{"{file}": [{"ck", "title", "key"}, …]}`）を返す。
- **終了コード:** 0＝成功、1＝`--repo-root` のディレクトリ・テンプレートが無い、2＝引数・入力の誤り（上の各検査、鍵・`replace` の重なり、書き先に無い `replace`、ワークスペースの外の `--batch-survey`）。
- **人に示すもの:** `place` と同じものに加え、`not_written`・`emptied`（前回書いたが今回は書かなかった制約・エントリが無くなったファイル）。示し方は各経路の手順に従う。

#### 経路ごとの鍵と出典

| 経路 | 元 | `section` | `key` | 出典 |
|---|---|---|---|---|
| xddp-close Step C3.6（`--batch-cr {CR_NUMBER}`） | SPO §5.6 の行（影響度 高・中） | `performance` | `SPO-5.6:{行の順番}`（表のデータ行の順番。影響度で絞る前に数える） | `{CR_NUMBER} / SPO §5.6` |
| 〃 | LL `#リスク`・`#見落とし` | `constraint` | `{LL の ID}:constraint` | `{LL の ID}` |
| 〃 | LL `#仕様定義` | `assumption` | `{LL の ID}:assumption` | `{LL の ID}` |
| 〃 | TRS の NG | `constraint` | `{TRS のファイル名の拡張子を除いた部分}:{NG-NNN}` | `{CR_NUMBER} / {TRS のファイル名の拡張子を除いた部分} / {NG-NNN} / 発見日: {TODAY}` |
| xddp-survey の knowledge 昇格（`--batch-survey {SURVEY_FILE}`） | §2.6 の項目 | 項目ごとに `constraint`（制約）か `assumption`（前提） | `2.6:{項目の順番}`（§2.6 の最上位の箇条書きの項目の順番。箇条書きが無ければ段落の順番。入れ子の箇条書きは親の項目に含める） | `SURVEY-{TODAY} / {SURVEY_FILE のファイル名}` |
| xddp-update-knowledge（`--batch` なし） | 人の入力 | `constraint` | （書かない） | 人の入力のまま |

**出典の書式（code-knowledge のすべての知識種別）:** CR の経路（xddp-close）は `{CR_NUMBER}`（CR フォルダ名のまま。`CR-` を足さない）に元の文書を添える
（例: `{CR_NUMBER} / SPO §3`）。xddp-survey は `SURVEY-{TODAY} / {SURVEY_FILE のファイル名}`（`TODAY` は YYYY-MM-DD）。手での登録（xddp-update-knowledge）は人の入力のまま。

### 読む側

**ファイル F（リポジトリのルートからの相対パス）に当てはまる置き場所**は、次のすべて:
- `_general`
- F がリポジトリ直下なら `_root`
- F の所在ディレクトリと、そのすべての祖先ディレクトリ（ディレクトリ境界で区切る。`src/auth/login/a.c` なら `src/auth/login`・`src/auth`・`src`。`src/au` は当てはまらない）

**列挙:** `{KNOW}` の下の `constraints.md`（入れ子を含む）のうち、`{KNOW}` からの相対パスの第1要素が `_structures`・`_constants`・`_flows`・`_cochange` でないもの。
置き場所は `constraints.md` の親ディレクトリの `{KNOW}` からの相対パス（第2要素以降に同名のディレクトリがあっても除かない）。
スクリプトは `knowledge_place.py` の関数 `list_places(know_dir)`・`applicable_places(rel_file)` を使う。

### 宛先への当てはめ

| 知識種別 | 宛先 |
|---|---|
| 制約・落とし穴 | `{KNOW}/{MODULE}/constraints.md`（`cross` の `{XKNOW}` には置かない） |
