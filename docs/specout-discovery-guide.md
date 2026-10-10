# スペックアウト（波紋検索）詳細ガイド

`/xddp-04-specout` が内部で行う Discovery BFS（波紋検索）の仕組みを説明する。
基本的なコマンド引数・成果物一覧は [README.md](../README.md) の「フェーズ一覧」を参照。
本ドキュメントは内部挙動・コンテキスト管理・実行方法の詳細を扱う。

実装の正本は以下のファイル。本ドキュメントの記述と食い違う場合はコードを正とする。

- [ClaudeCode/.claude/skills/xddp-04-specout/SKILL.md](../ClaudeCode/.claude/skills/xddp-04-specout/SKILL.md)（オーケストレーション。Step A-Prelim・Step A-Seed・`init`・波ループ）
- [ClaudeCode/.claude/agents/xddp-specout-prelim-agent.md](../ClaudeCode/.claude/agents/xddp-specout-prelim-agent.md)（下調べ。母体を読んで資料とシード候補を作る）
- [ClaudeCode/.claude/agents/xddp-specout-agent.md](../ClaudeCode/.claude/agents/xddp-specout-agent.md)（discovery-setup。Wave 0 のシード候補表の作成）
- [ClaudeCode/.claude/agents/xddp-specout-classifier-agent.md](../ClaudeCode/.claude/agents/xddp-specout-classifier-agent.md)（Discovery BFS の hits 意味判定・classification 作成。関数の範囲を決定的に取れない言語〔C / C++ / Python 以外〕のヒットだけを受け取る）
- [ClaudeCode/.claude/skills/xddp-04-specout/scripts/specout_bfs.py](../ClaudeCode/.claude/skills/xddp-04-specout/scripts/specout_bfs.py)（BFS 帳簿エンジン本体。visited/frontier管理・検索の実行〔既定は識別子索引〕・1波の予算と打ち切り記録・状態遷移・discovery-log書き出しはこちらが担う）
- [ClaudeCode/.claude/skills/xddp-04-specout/scripts/specout_slice.py](../ClaudeCode/.claude/skills/xddp-04-specout/scripts/specout_slice.py)（C / C++ / Python のヒットを LLM を使わずに判定するエンジン。スライス判定〔tree-sitter〕と規則判定〔標準ライブラリのみ〕）

判定エンジン・1波の予算・打ち切り記録・波数上限での自動完了の設計根拠は [ADR-0019](adr/ADR-0019-specout-static-slicer.md) を参照。

---

## 1. 実行方法

### 1.1 トリガーフレーズ

スキル定義上の起動フレーズは「スペックアウトして」「母体調査して」「影響範囲を調べて」
（`xddp-04-specout/SKILL.md` フロントマター `description`）。
「波紋検索して」は登録フレーズではないが、意味が近いため Claude が意図を汲んで起動する可能性はある（保証はない）。

### 1.2 確実な実行方法（推奨）

CR番号とエントリポイント（探索起点シンボル）を明示したスラッシュコマンドが最も確実。

```
/xddp-04-specout {CR番号} {エントリポイント...}
```

エントリポイントは省略可能（省略時は下調べのシード候補と CRS の SP 項目から候補表を作る。2.1節参照）。

### 1.3 CR番号の解決

CR番号を省略した場合、`xddp-common/SKILL.md` の CR Resolution ロジックが自動検出する。

| `{XDDP_DIR}/` 配下の CR候補数 | 動作 |
|---|---|
| 0件 | エラーで停止（「CRフォルダが見つかりません」） |
| 1件のみ進行中 | 自動検出して続行 |
| 複数が進行中 | 「CR番号を引数に指定してください」と聞き返される |

specout は CR ワークフローの工程4であり、**工程3（`/xddp-03-req`）で CRS が作成済みであること**が前提。
CRS が無い状態では Wave 0 の初期シンボル抽出が成立しない。

---

## 2. 検索対象シンボルの決定方法

### 2.1 Wave 0（初期シンボル）

Wave 0 の初期シンボルは、波紋調査の前に作る**シード候補表**（`{CR_PATH}/04_specout/{repo}/work/seed-candidates.md`）で
人が確定する。初回実行（`work/bfs-state.json` が無い repo）は次の順に進む。

1. **下調べ（Step A-Prelim。`xddp-specout-prelim-agent`）**：CRS から変更対象の振る舞いを列挙し、それを実装している
   母体コードを探して読む（手がかりは CRS のコード表記・ENTRY_POINTS・モジュールカタログ・既存仕様書・Grep/Glob。
   調査範囲に上限はなく、`CR_PROFILE=quick` でも full と同一）。読んだファイルは `SPO-{CR}.md`・`modules/` に
   波紋調査に依存する節（§4〜§7・§9〜§10）を除いて直接書き、`work/documented-files.md`（文書化済みファイル台帳）・
   `work/observation-memo.md`（累積観察メモ）に記録する。最後に `work/prelim-index.md` へ、定義行を確認し
   振る舞いを実装していると確認できた識別子だけを**シード候補**として、識別子を特定できなかった振る舞いは
   一般語で代用せず「識別子を特定できなかった振る舞い」として書く。下調べが完了しなかった場合は下調べなしで続行する。
2. **候補表の作成（discovery-setup。`xddp-specout-agent`）**：以下を統合して候補表を書く（同一シンボルは
   ENTRY_POINTS ＞ CRS SP項目 ＞ 下調べ ＞ 母体コードから補完 ＞ 継承展開 の優先順で1行にまとめ、「由来」列に記録する）。
   - **ENTRY_POINTS 引数**：コマンドで明示的に渡したシンボル・ファイルパス（解決できなかったものは「## 解決できなかった ENTRY_POINT」へ）
   - **CRS の SP 項目から抽出**：コードブロック内の識別子、および「変更対象」「追加」「削除」等の動詞に続く名詞句のコード表記。
     インスタンスフィールドの場合は `self.{field}` / `this.{field}` 等の属性参照パターンも追加
   - **下調べのシード候補**（根拠付き）。下調べがない場合に限り、母体コードを確認して補った識別子（由来「母体コードから補完」）
   - **継承伝播**：変更対象クラスのサブクラス・実装クラスを言語別パターンで検索し追加（由来「継承展開」）
   - **モジュール再エクスポート検索**：`export { Symbol }` 形式の re-export ファイル等の grep 未対応パターンは
     discovery-setup が `seed-input.json` に入れ、`write-seed-candidates` が `work/seed-unsupported.json` に書き、
     `init --unsupported-patterns` が discovery-log に記録する
3. **シード確認（Step A-Seed）**：`specout_bfs.py seed-preview` が採用シンボルを `search` と同じバックエンド・フィルタで
   試算し、候補表の「ヒット（ファイル数）」「警告」（未ヒット＝誤字・旧名称の可能性／フィルタ後0件／ヒット過多＝一般語の疑い／
   予算超過＝1波の予算 `SPECOUT_WAVE_HIT_BUDGET` を超えるため、第0波で丸ごと打ち切られる）列を書き換える。候補の表の直前には、
   採用シンボルの合計ヒット数の注記行が書かれる（合計が1波の予算を超える場合は、採用するシンボルを分けて実行する〔一部を
   除外して実行し、残りを `--re-discover` で投入する〕よう案内する）。SKILL は全 repo の候補表を提示し、`SPECOUT_SEED_GATE: true`（既定）なら人の応答を待つ。
   - **確定** → 波紋調査へ（採用が0件の repo が残っている場合は確定できない）
   - **編集した／指示した** → 候補表の「採否」列（☑／☐＋除外理由）や追加行（由来「人が追加」）を反映して再試算・再提示
   - **下調べ資料で止める** → 波紋調査を行わずに終了（CR 単位。⏸ 中断として記録し、工程4b へ進まない）。
     `/xddp-04-specout {CR}` の再実行で、下調べ資料と候補表をそのまま使って Step A-Seed から再開する
     （エントリポイントを引数で指定した場合は候補表に追記される。候補表で除外済みのシンボルは再採用されず、提示で知らされる）

   `SPECOUT_SEED_GATE: false` なら提示のみで続行する。ただし採用が0件、または採用した全候補がヒット過多か予算超過の repo が
   ある場合は設定によらず確認を求める。
4. **`init`**：SKILL が `specout_bfs.py init --seed-candidates` を実行し、候補表の採用行（☑）から初期シンボルを、
   由来「ENTRY_POINTS」「人が追加」の行から `entry_point_symbols`（Wave 1 以降の未ヒット検出の対象）を作る。
   discovery-log の「## 投入シンボルの由来」の全9行（ENTRY_POINTS／CRS SP項目／下調べ／母体コードから補完／継承展開／
   確認時に人が追加／確認時に人が除外／解決できなかった ENTRY_POINT／シンボル不明）も候補表から決定的に書かれる。
   あわせて、判定エンジン（2.2節）・1波の予算・波数上限（4.2節）・除外パターン（2.4節）の設定を `bfs-state.json` に保存する。
   これらは再開を含むその CR の探索で固定され、CR の途中で設定を変えても反映されない（波数上限の引き上げだけは例外。4.2節）。

`work/bfs-state.json` が既にある repo の再開・`--re-discover` では、下調べ・シード確認は行われない。
波紋調査の完了後、資料の確定（`xddp-specout-document-agent`）は `specout_bfs.py doc-targets` が返す
「確定ファイルのうち台帳に無いもの」だけを対象にし、下調べ済みのファイルは読み直さない。

### 2.1.1 資料の確定の材料と上限

確定ファイルは完全スライスで数百件になりうるため、資料の確定（Step A-Document）は1つのエージェントにまとめて読ませず、次の流れで行う。

1. `doc-targets --auto-assign`: どのモジュールにも属さないファイルを親ディレクトリへ機械的に割り当てる（下調べで決めたモジュールはそのまま。人は `work/module-assignments.json` を直して再実行できる）。
2. `assemble-spo --layout-only`: 配置判定（成長型）と統合→分割の移し替え。
3. `doc-digest`: LLM が読む材料を `work/digest/` に作る。`index.md`＝機能（モジュール）一覧・打ち切りの要約・grep 未対応パターン、`modules/{モジュール}.md`＝ファイル → 関数ごとの経路・判定・関数本文の抜粋（行番号つき）・テストファイルの候補。
4. `xddp-specout-document-agent`（`DOC_MODE: module`）をモジュールごとに並列起動する（同時に `SPECOUT_DOC_PARALLEL` 件まで）。材料の抜粋だけを読み、抜粋で分からない項目は「材料外（未確認）」と書く。
5. `assemble-spo`: モジュール資料の差し込みと、SPO のスクリプトが書く欄（§1.x 調査の打ち切り・§5.0 機能一覧・§5.1・§5.2・§5.5 のテストファイルの候補・§8・§9）の記述。
6. `xddp-specout-document-agent`（`DOC_MODE: summary`）: SPO サマリーの記述部分と funcmap。
7. `verify-sweep`: 検証スイープ。未記録ヒットがあれば終了コード 7 で人の判断を待つ（件数不一致の終了コード 3 とは別）。

| 上限 | 設定（既定） | 超えた場合 |
|---|---|---|
| 1モジュールの抜粋の合計行数 | `SPECOUT_DOC_LINE_BUDGET`（`2000`・暫定） | 同じモジュール内で発見波の浅い順・ヒットの多い順に抜粋を入れ、入らなかった関数は名前と行範囲だけを書く。理由 `doc-limit` で打ち切り記録に残す |
| 材料を作るモジュール数 | `SPECOUT_DOC_MAX_MODULES`（`30`・暫定） | 発見波の浅い順・確定ファイルの多い順に選び、超えたモジュールは `index.md` と SPO §5.0 に一覧だけ載せる。理由 `doc-limit` で打ち切り記録に残す |

- 直接影響（第0波）のファイルを含むモジュールは `SPECOUT_DOC_MAX_MODULES` の対象外で、行数上限でも第0波の関数を最優先で抜粋に入れる。
- `doc-limit` は資料化の上限であり、波の検索後の件数ではないため、件数一致検証（`specout_verify_counts.py`）の対象外。
- SPO レビュー（Step A2）の LLM のチェックは影響範囲の十分性（L1）と設計への申し送り（L2）の2項目だけで、突き合わせ・存在確認・件数の照合は `artifact_lint.py --doc-type SPO` と `verify-sweep` が行う。LLM に渡すのは要求書・CRS・`work/digest/index.md`・直接影響のモジュールの資料だけ。
- 設計根拠は [ADR-0020](adr/ADR-0020-specout-doc-digest-and-review.md) を参照。

### 2.2 Wave 1以降（自動拡張）と判定先

人が追加指定するのではなく、各波のヒットを判定し、その結果から機械的に次波のシンボルを導出する（伝播ルール）。
ヒットの判定先は、ヒットしたファイルの拡張子で決まる（`search` が判定先ごとにチャンクを分ける）。

| 判定先 | 対象 | 判定する主体 | 次波へ追加するもの |
|---|---|---|---|
| スライス判定（`slice`） | C / C++ / Python のヒット（tree-sitter が使える場合） | `specout_slice.py classify`（LLM を使わない） | 影響が関数の外へ出る場合はその行を含む関数名（呼び出し元を追う）、書き込んだグローバル変数（構造体はフィールド単位の `root.field`。読み手を追う）、関数の外の値（マクロ定義の本体ならマクロ名、グローバルの初期化子なら変数名、Python のモジュール・クラス本体の代入なら代入先） |
| 規則判定（`rule`） | C / C++ / Python のヒット（tree-sitter が使えない場合、または `SPECOUT_SLICE: off`） | `specout_slice.py classify`（標準ライブラリのみ。LLM を使わない） | コメント・文字列の中・goto のラベル名・プロトタイプ宣言の引数名のヒットは偽陽性。それ以外はヒット行を含む関数名（関数の外・関数の宣言部のヒットは伝播させない） |
| LLM 分類 | 上記以外の言語のヒット（関数の範囲を決定的に取れない言語） | `xddp-specout-classifier-agent`（チャンク単位で並列起動） | 下表の伝播ルール |

- スライス判定・規則判定の対象はスライス用チャンク `work/waves/wave-{N}-hits-chunk-S.json`（毎波1件。ヒット0件でも作る）、
  LLM 分類の対象は LLM 用チャンク `wave-{N}-hits-chunk-{K}.json`（LLM に回るヒットがある場合だけ作る）に入る。
  SKILL は波ループの b-0 でスライス用チャンクを `specout_slice.py classify` で判定し、b-1 で LLM 用チャンクだけを
  classifier に渡す（LLM 用チャンクが無い波では classifier を起動しない）。
- 判定エンジン（`slice` / `rule`）は `SPECOUT_SLICE`（`auto`＝tree-sitter があればスライス判定、無ければ規則判定／`off`＝常に
  規則判定）と、`SPECOUT_SLICE_PYTHON_BIN` の Python で tree-sitter を import できるかで決まり、`init` 時に `bfs-state.json`
  に保存される。tree-sitter で始めた CR を tree-sitter の無い環境で再開すると、SKILL は「tree-sitter を使える Python を
  指定して再実行する／残りの波を規則判定に切り替えて続ける／最初から規則判定で探索する」を人に尋ねる（黙って切り替えない）。
  切り替えた場合は discovery-log に「## 判定エンジンの切り替え（Wave N から rule）」が残る。
- 次の波のシンボル名は修飾を外した識別子にする（C++ の `ns::Class::method` → `method`、`f<T>` → `f`、コンストラクタは
  クラス名）。デストラクタ・演算子オーバーロード・関数ポインタ経由の呼び出しは呼び出し箇所に名前が現れないため伝播させず、
  「## grep未対応パターン（手動確認必要）」に記録する。
- スライス判定で影響なしとみなす呼び出し（例: ログ出力・メモリ確保・assert の関数名）は `SPECOUT_SLICE_IGNORE_CALLS`
  （正規表現。関数名に完全一致）で指定できる。`.h` を C / C++ のどちらで解析するかは `SPECOUT_SLICE_H_AS` で決める。

LLM 分類の伝播ルール（classifier が判定する。discovery-log の「伝播種別」には分類の値がそのまま記録される）:

| 伝播種別 | 検出条件 | 次波へ追加するもの | 確信度 |
|---|---|---|---|
| `propagation-direct`（制御フロー） | 任意のヒット行 | その行を含む関数/メソッド/クラス名 | HIGH |
| `propagation-direct`（データフロー・代入） | `lhs = ... symbol ...` | lhs | HIGH |
| `propagation-argument`（引数伝播） | `func(..., symbol, ...)` | 対応する仮引数名（スコープ付き） | MEDIUM |

スライス判定・規則判定の行は HIGH（全域）だけで追い、MEDIUM（スコープ限定）は出ない。前倒し縮退（noise-collapse）と
高ノイズによる波及停止（ADR-0009）は、LLM 分類に回るヒットにだけ適用される（スライス判定・規則判定のヒットは
1波の予算が代わりを担う。2.3節）。

grep では追跡できないパターン（リフレクション・動的ディスパッチ・ジェネリクス等）は
「grep未対応パターン」として記録され、自動探索の対象にはならず人手確認を要求する。

#### シード要約の取り込み（スライス判定のみ）

スライス判定では、人が入れたシード（第0波の初期シンボル・`--re-discover` で加えたシンボル）の関数について、
副作用の要約（戻り値・出力引数・書くグローバル・その他の副作用）を求め、シード関数が書くグローバルを最初の波から追う。

1. シードを入れる処理（`init`・`re-discover`・`merge-frontier --reset-wave-origin`）が、入れたシンボルに
   「シード要約の取り込み待ち」（state の `seed_summary_pending`）の印を付ける。
2. 印が残っていると、`search` は検索せずに終了コード 6 で止まる。
3. SKILL は `specout_slice.py seed-summary` で要約とシードが書くグローバルを求め、`merge-frontier --summaries-file`
   （グローバルがあれば `--as-seed-globals` も付けて frontier に加える）で取り込んでから、`search` をやり直す。
   関数定義の見つからないシンボル（値シンボル・マクロ名・外部関数等）も、取り込みで印が外れる。

シードが書くグローバルのヒットは、ヒット表の「派生元」に `seed-global(X)` と書かれ、未ヒット・ヒット過多などの
投入シンボルの診断には含めない。規則判定では要約を使わないため、この手順は行われない。

#### 要約の拡大による再訪（スライス判定のみ）

visited 済みの関数シンボルでも、後の波の判定でその関数の要約が広がった（戻り値・副作用が新たに影響を受ける、または
影響する出力引数が増えた）場合は、次の波で再び検索して呼び出し元を判定し直す（分類済みロケーションの dedup の鍵に要約を
含めるため、呼び出し元の行は除外されない）。再訪したシンボルは discovery-log の「## 要約の拡大による再訪（Wave N）」に、
件数は `metrics.jsonl` の `revisit_count` に記録される。要約の各項目は和集合で単調に広がるため、再訪の回数には上限がある。

### 2.3 1波の予算と打ち切り記録

`search` は、その波の frontier をすべて検索したうえで、dedup・保守的フィルタ（と LLM 分類に回るヒットの前倒し縮退）の
後のヒット数に次の上限をかける。

| 上限 | 設定（既定） | 超えた場合 |
|---|---|---|
| 1波のヒット予算 | `SPECOUT_WAVE_HIT_BUDGET`（`10000`。`0` で無制限） | エントリ（HIGH はシンボル、MEDIUM は「シンボル＋スコープ」）を「関数シンボル → 値シンボル（グローバル・`root.field`）」の順、各群の中ではヒットの少ない順（同数ならシンボル名の順）に並べ、累計が予算に収まるエントリを採る。収まらないエントリは丸ごと外し、理由 `hit-budget` で打ち切り記録に残す |
| LLM 分類の上限 | `SPECOUT_LLM_HIT_BUDGET`（`160`。`0` で無制限） | 採ったエントリのうち LLM 分類に回るヒットの合計が上限を超える場合、同じ順で収まるエントリの LLM 分類分だけを残し、外したエントリの LLM 分類分を理由 `llm-budget` で打ち切り記録に残す（同じエントリのスライス判定・規則判定のヒットは残す） |

- どちらの上限も、判定エンジン（tree-sitter の有無）・検索ツールによらず同じ値で適用される。
- 予算で除いた行は「## フィルタ除外一覧」に1行ずつは書かず、エントリ単位で「## 打ち切り記録」に書く。件数一致検証では
  「フィルタ除外」列に含めて照合する（4.1節）。
- 打ち切ったエントリは検索済みとして visited に入り、後の波で frontier に戻らない。追う場合は、打ち切り記録のシンボル名を
  `/xddp-04-specout {CR} --re-discover {シンボル}` に渡す。
- 投入シンボル（第0波のシード、第1波以降は人が `--re-discover` で入れたシンボル）を丸ごと打ち切った場合は、
  「## 予算で打ち切った投入シンボル（Wave N）」にも記録され、SKILL が人に知らせる（CR の変更対象そのものが一度も
  追われないまま進むことを防ぐため）。
- 外した件数は `metrics.jsonl` の per-wave の `hit_budget_removed` / `llm_budget_removed` に記録される。

「## 打ち切り記録」は `| 波 | 理由 | シンボル | ヒット数 |` の表で、`bfs-state.json` の `truncated` から毎回作り直される。
理由は `hit-budget` / `llm-budget` のほか、`doc-limit`（資料の確定の上限。2.1.1節）、`wave-limit`（波数上限。4.2節）がある。`wave-limit` は
検索していないため、ヒット数は `-` になる。

### 2.4 除外パターン（`SPECOUT_EXCLUDE_PATTERNS`）

各エントリの意味は、検索ツール（`index` / `grep` / `rg`）によらず同じ。

| 書き方 | 意味 |
|---|---|
| `/` で終わり、途中に `/` を含まない（`tests/`） | パスのどの階層でも、その名前のディレクトリの配下を除く |
| `/` で終わり、途中に `/` を含む（`lib/legacy/`） | リポジトリのルートからのパスが、そのディレクトリの配下なら除く（ディレクトリ境界で前方一致） |
| `/` で終わらない（`*.pb.c`、`gen/*.c`） | `/` を含まなければファイル名に、含めばルートからのパスに対する glob で除く |

`index` は除外したファイルを索引に入れない。`grep` / `rg`（`index` からの委譲を含む）は、検索の後に同じ規則で
ヒットを除く。除外したヒットは件数照合の「生ヒット」に含めない。一致するファイルが無いエントリは、discovery-log の
「## 探索設定」に `> ⚠️ 除外パターン警告: …` として残る（書き間違いに気づけるようにするため）。

---

## 3. リポジトリ単位 vs シンボル単位の分離

| 分離単位 | 状態 | 効果 |
|---|---|---|
| リポジトリ（下調べ・discovery-setup フェーズ） | 分離（独立 Agent コンテキスト。マルチリポ時は並列呼び出し） | 下調べ・シード候補表の作成時、リポジトリ間でコンテキストが混ざらない |
| 波ループ（search / commit-wave） | 分離しない（SKILL 側オーケストレータが全リポジトリ分を単一コンテキストで駆動） | 決定的処理（search・チャンク分割・スライス判定／規則判定〔`specout_slice.py classify`〕・merge_classification.py・commit-wave）は Bash 呼び出しのままリポジトリ横断で進行を管理できる |
| classification（LLM 意味判定） | チャンク単位で分離（独立 classifier サブエージェント。波ごとに全リポジトリの LLM 用チャンクを合算してバッチ並列起動。対象は C / C++ / Python 以外の言語のヒットだけ） | 1波のヒット数が多い場合の壁時計レイテンシを短縮する（トークン総量はほぼ不変。並列化は時間短縮であってトークン削減ではない） |
| 検索対象シンボル | 分離しない（波単位で1コマンドに統合。`index` は索引の参照、`grep` / `rg` は複合パターン） | コマンド呼び出し数を抑制し、コンテキスト消費を削減 |

マルチリポジトリ構成では、下調べ（Step A-Prelim）と discovery-setup（シード候補表の作成）を各リポジトリが
独立した Agent コンテキストで並列実行する。シード確認（Step A-Seed）は全リポジトリ分をまとめて提示し、
`init`（BFS state 初期化）は SKILL がリポジトリごとに実行する。Wave 0 構築後の波ループ（search → スライス判定・規則判定 → 並列 classifier 起動 → merge_classification.py → commit-wave）は
SKILL 側オーケストレータが単一コンテキストで全リポジトリ分を駆動し、「1波あたり全リポジトリの LLM 用チャンクを
合算してバッチ起動する classifier」によってリポジトリ間の並列度を維持する
（PLAN-20260806-specout-phase3-parallel-classification.md Stage 2）。
各リポジトリは独立した `discovery-log.md` / `work/bfs-state.json` を持ち、書き手は
`commit-wave`（Bash・単一）に集約される。単一リポジトリ内では「1波 = 原則1コマンド」で検索する。既定の `index`
（`SPECOUT_BACKEND: auto`）は起動のたびにリポジトリ全体の識別子と `root.field` の索引を作って辞書の参照で答え、
索引で引けない形のシンボル（`Foo::bar`・`$var`・ファイルパス等）だけを rg（無ければ grep）に委譲する。
`grep` / `rg` を明示した場合は、複数シンボルを正規表現の OR パターンに結合して検索する。

---

## 4. 中断耐性（チェックポイント機構）

真実の状態は `{CR_PATH}/04_specout/{repo}/work/bfs-state.json`（`specout_bfs.py` が読み書きする）。
同じディレクトリの `bfs-state.md` はこの JSON から自動生成される人可読ビューであり、直接編集しない
（`merge-frontier`/`re-discover`/`extend`/`switch-engine` 等の専用サブコマンド経由でのみ状態を変更する）。

- `search` 実行時：状態の `wave_write_complete` を `false` に更新する（検索結果を
  `work/waves/wave-{N}-hits.json` と判定先ごとのチャンクに出力するのみで、discovery-log.md はまだ書かない）
- スライス用チャンクを `specout_slice.py classify` が、LLM 用チャンクを classifier が判定し、
  `merge_classification.py` が結合して `work/waves/wave-{N}-class.json` を作成
- `commit-wave` 実行時：discovery-log.md への Wave セクション書き出し・次波 frontier の算出・
  状態更新（`wave_write_complete: true`）を一括して行う

再開時、`status` が `wave_write_complete: false` を返す場合（`commit-wave` 前にクラッシュした場合）、
同じ `work/waves/wave-{N}-hits.json` を使って classification を作り直し `commit-wave` を再実行すればよい
（スライス用チャンクの判定は決定的なので、復旧時は必ず判定し直す。手順は `recovery-procedures.md` の
「## Wave 途中失敗からの再開（経路統一）」）。
discovery-log.md の書きかけ Wave セクションは `commit-wave` が自動的に切り捨てて再構築するため
（重複防止）、二重記録は発生しない。visited/frontier は波開始前の状態が bfs-state.json に
保存されているため、クラッシュで途中まで進んだ波をやり直しても探索対象シンボルが失われることはない。

波ごとの一時ファイル（`wave-{N}-*.json`）は `work/waves/`、それ以外の中間ファイルは `work/` に置かれ、`{repo}/` 直下には最終成果物（`SPO-{CR}.md`・`SPO-{CR}-funcmap.md`・`modules/`・`review/`）と証跡の `discovery-log.md` だけが残る。

件数一致検証（4.1節）は `commit-wave` が全ヒット行の classification 存在を構造的に検証したうえで
discovery-log.md へ書き出すため、書き込み自体が1トランザクションとして完結する
（旧方式にあった「検証テーブルのみ欠落する」ギャップは解消済み）。

最大探索波数（`SPECOUT_MAX_WAVE_DEPTH`）に達した場合は一時停止せず、打ち切り記録を残して自動完了する（4.2節）。

---

## 4.1 シンボル混在防止策（追跡可能性）

1波内で複数シンボルを複合パターン検索するため、結果の出自を追跡する仕組みが用意されている。

- **行ID・コマンドID**：全ヒット行に `W{wave}-R{n}`、実行コマンドに `W{wave}-C{n}` を付与
- **検索シンボル列**：ヒット行ごとに、複合検索パターンのうち実際にマッチしたシンボル名
  （MEDIUM の場合は `symbol[MEDIUM:scope_file]`）を明示する。1コマンドで複数シンボルを
  複合検索した場合でも、行を読むだけでどのシンボルのヒットかが分かる
- **SYMBOL_ORIGIN_MAP**：新規発見シンボルがどの行（＝どの元シンボル）から伝播したかを波ごとに記録・継承
- **visited セットのスコープ分離**：HIGH（全域）と MEDIUM（`(symbol, scope_file)` ペア）を別管理し、同名シンボルが異なるスコープで混同されないようにする
- **件数一致検証**：検索コマンドのヒット数と discovery-log.md に記録された行数を波ごとに突合し（生 = 記録 + dedup除外 + フィルタ除外 +
  noise-collapse除外。「フィルタ除外」には1波の予算で除いた件数を含む）、不一致があれば `⚠️ mismatch(raw=…,recorded=…,excluded=…)` を記録

不一致マーカーは自動停止ではなく可視化止まり（人レビュー時に気づく前提）。
長時間の specout 実行後は discovery-log.md の「件数一致検証」セクションに `⚠️` が残っていないか確認すると安全。
（SKILL は波ループの終了時に `specout_verify_counts.py --wave all --strict` で全波を自動検証し、不一致なら
`recovery-procedures.md` の「## Count Mismatch Handling」へ振り分ける。）

---

## 4.2 波数上限と自動完了・延長

`SPECOUT_MAX_WAVE_DEPTH`（既定 `6`）は「探索の起点の波（state の `wave_origin`）から調べる波の数」である。
初回の起点は第0波なので、既定の `6` なら第0〜5波を調べ、第6波の `search` で打ち切る。

- **上限に達したら自動完了する。** 一時停止せず、残りの frontier（低優先度の frontier を含む）を「## 打ち切り記録」に
  理由 `wave-limit` で記録し、状態を `complete` にする。波紋調査の目的は影響する機能の特定であり、調べきる必要はない。
  件数一致検証と `prelim-metrics` は、自動完了した場合も実行される。
- **上限を上げて再実行すると続きから探索する。** `xddp.config.md` の `SPECOUT_MAX_WAVE_DEPTH` を上げて
  `/xddp-04-specout {CR}` を再実行すると、SKILL が `specout_bfs.py extend` を呼び、状態によらず state の上限を更新する。
  `complete` で `wave-limit` の打ち切りがある repo は、打ち切ったシンボルを frontier に戻して `in-progress` にし、
  打ち切った波から探索を続ける（discovery-log に「## 探索の延長（上限 M → N）」が残る）。予算（`hit-budget` /
  `llm-budget`）で打ち切ったシンボルは検索済みのため戻さない（`--re-discover` で追う。2.3節）。
- **上限を下げても、その CR の探索で使っている値のまま続ける**（調べ終えた波を取り消さない）。
- **`--re-discover` は起点を置き直す。** 人がシンボルを加えると、加えたシンボルも上限の波数まで調べられるよう、
  `complete` の repo（`re-discover`）では再開する波（最終完了波 + 1）を、`in-progress` の repo
  （`merge-frontier --reset-wave-origin`）では次に検索する波を、新しい起点にする。起点を置き直すと、frontier に残っていた
  伝播由来のシンボルの残りの波数も同じだけ延びる（延びる分は1波の予算で抑えられる）。`extend` は起点を変えない。

Step E の報告では、repo ごとに打ち切りの有無（理由別の件数）が示され、`wave-limit` があれば上限を上げて再実行する方法が、
予算の打ち切りがあれば `--re-discover` で追う方法が案内される。

---

## 4.3 discovery-log の読み方（凡例と英語の値）

discovery-log.md の表のセルに書く種別・派生元・判定の値は英語のコードで、日本語の説明は冒頭の「## 凡例」
（「## 探索設定」の後・「## 投入シンボルの由来」の前）にまとまっている。主な値は次のとおり（正本は discovery-log の凡例）。

| 箇所 | 値 |
|---|---|
| ヒット表「伝播種別」 | LLM 分類: `false-positive` / `propagation-direct` / `propagation-argument` / `propagation-return` / `out-of-scope-discard`。スライス判定: `slice(escape=return,global)` 等（影響が関数の外へ出る経路）・`slice(file-scope=macro-def)` 等（関数の外の値を伝播）・`slice(none=no-escape)` 等（伝播しない理由）。規則判定: `rule(enclosing)` / `rule(none=self-def\|file-scope)` |
| ヒット表「派生元」 | `seed(X)`（その波でシードとして投入したシンボル）／`seed-global(X)`（シード関数が書くグローバル）／`W{n}-R{m}`（前の波の行ID）／`unknown-origin` |
| 実行コマンド一覧「種別」 | `HIGH-compound` / `MEDIUM` |
| 件数一致検証「一致」 | `✅` / `✅ excluded(dedup=…,filter=…,noise-collapse=…)` / `⚠️ mismatch(raw=…,recorded=…,excluded=…)` / `➖ discarded(case-a)` |
| 同名 MEDIUM 重複ログ「ケース」「処置」 | `case-a` / `case-b` / `case-c`、`promote-high; discard=…` / `manual-check` / `keep-visited` |
| 打ち切り記録「理由」 | `hit-budget` / `llm-budget` / `wave-limit` |

「## 探索設定」には、実際に使った検索ツール（例: `index`）・最大波数・判定先の内訳（スライス判定／規則判定で判定する
拡張子と、LLM 分類に回る拡張子）が書かれ、tree-sitter を使えず規則判定で始めた場合は `> ⚠️ スライス判定エンジン警告: …` が残る。

---

## 5. 未確認・既知のギャップ

- bfs-state.json / discovery-log.md 自体のファイル書き込み操作は `specout_bfs.py` 内で逐次実行されるが、
  プロセス自体が書き込み途中で強制終了された場合の部分書き込みまでは保証しない（4節の再開手順で復旧する）
- `grep` / `rg`（明示指定時、および `index` からの委譲時）では、1波内で HIGH grep と MEDIUM grep 群を並列実行する設計だが、
  `specout_bfs.py` の現行実装は Bash 内で逐次実行している（結果の正しさに影響はないが、大規模リポジトリでは波あたりの
  実行時間がシンボル数・スコープファイル数に比例して伸びる点は留意）
- スライス判定は呼び出し先の要約の深さ・外部関数・関数ポインタ経由の呼び出し・マクロについて安全側でない仮定を置いている。
  関数ポインタ経由の呼び出し等は「## grep未対応パターン（手動確認必要）」に記録されるため、人が確認する
- C / C++ / Python 以外の言語のヒットは今どおり LLM 分類に回る（1波あたり `SPECOUT_LLM_HIT_BUDGET` で量を抑え、
  超えた分は打ち切り記録に残る）
