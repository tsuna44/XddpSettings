# golden（full-run スモークの構造性質ゴールデン）

`tools/harness/smoke_full.py`（L4/L5 full-run スモーク）が、隔離 HOME で工程スキルを
実起動して生成した成果物の**構造性質**を照合する期待値（ゴールデン）を格納する。

## 表現形式（保守コスト最小化）

ゴールデンは**構造性質の JSON** で表現し、LLM 生成の散文は byte 固定しない
（実行ごとに変わるため）。1工程1ファイル（`phase{NN}-{single,multi}.json`）を想定。

```jsonc
{
  "required_headings": ["4. トレーサビリティマトリクス", ...],  // 必須見出し（部分集合検査）
  "frontmatter_keys": ["version", "last-updated-cr", ...],       // 必須フロントマターキー
  "unreplaced_tokens": []                                        // 常に空であるべき（C2）
}
```

日付・絶対パス・トークン数等の環境/実行依存フィールドは
`smoke_full.normalize_properties` で正規化してから照合する。

ID（UR・SR・SP）はゴールデンに持たない。毎回シードの CRS から期待値を求めて照合する
（下の「ID の追跡照合」）。

## ブートストラップ・更新手順（鶏卵回避）

ゴールデンは**校正ラン（plan 3.5）で確定するまで空**である（推測で置かない）。順序は固定:

1. 既知の正しいツリーに対し各工程を1回起動し `--update-golden` で構造性質を収集
2. 人が diff を確認してゴールデンを確定（→ このディレクトリへコミット）
3. 確定ゴールデンに対して偽失敗率を N 回測定（rule of three: N=20/30・0失敗必須）

更新: `python3 tools/harness/smoke_full.py --phase NN --update-golden`（diff は人が確認）。

`--update-golden` は次の実行からはゴールデンを書き出さず（既存のゴールデンも変えない）、`violations`
（終了コード 1）で終わる。

- 成果物ディレクトリが無い実行（工程によらない）。成果物ディレクトリが無いと構造性質の抽出は
  ワークスペースのルート（REQ・ANA・`xddp.config.md` 等のシードの入力）を走査するため、
  その値をゴールデンにしない。
- ID の追跡照合の strict 違反がある実行。

advisory だけの実行からは書き出し、advisory を表示する。

## プロバイダ別ゴールデン（`providers/`）

ゴールデンは**モデル依存**（見出しの展開粒度がモデルで変わる）ため、Anthropic 互換の
第三者エンドポイント経由で実行する場合は配置先を分離する。

| 実行環境 | 配置先 |
|---|---|
| `ANTHROPIC_BASE_URL` 未設定（Anthropic 公式） | `golden/phase{NN}-{variant}.json`（平坦・従来どおり） |
| `ANTHROPIC_BASE_URL` 設定済み（第三者） | `golden/providers/{host}__{実モデルID}/phase{NN}-{variant}.json` |

プロファイル名は `smoke_full.provider_slug()` が `ANTHROPIC_BASE_URL` のホスト名と
実モデルID（`ANTHROPIC_DEFAULT_{SONNET,OPUS,HAIKU}_MODEL` によるエイリアス解決後）から
生成する。例: `api.ai.sakura.ad.jp__preview-Kimi-K2.6`。

これにより、第三者モデルでの `--update-golden` が Sonnet で校正済みの平坦ゴールデンを
上書き破壊しない。第三者プロファイルは初回 assert 時に `golden_missing`（exit 8）で停止
するので、`--update-golden` で当該プロファイルのゴールデンを確定してから assert する。

参照: plans/PLAN-20260725-p2-test-harness.md Section 3.2, 3.5

## golden の正しさの検証方針（オラクル不要性による性質分類と担保レベル）

golden の `required_headings` は元々「1回の LLM 出力の目視確認」で確定した値であり、
その値自体の正しさを統計的に検証する計画（`plans/PLAN-20260725-p2-test-harness.md` Section 3.5
「確定 golden に対する偽失敗率の N 回実測」）はコスト・サブスクのセッション上限により実行不能と
判明し省略された（上記「D 再設計」節）。N 回実測は「golden に対する再現性」を測るだけで
「golden の値そのものの正しさ」は証明できない。

そこで golden が検査する性質を、正しさの検証可能性によって3種類に分類し、それぞれ異なる
担保レベルで扱う（`plans/PLAN-20260816-golden-oracle-free-checks.md`）。

| 性質 | 内容 | 担保レベル |
|---|---|---|
| (a) オラクル不要の不変条件 | golden を参照せず、ツール仕様から常に真偽が決まる性質。例: `unreplaced_tokens`（未置換トークン残存はゴールデンによらず常に違反。`compare_to_golden()`）、CRS 構造チェック（`artifact_lint._lint_crs()` の error issue。`smoke_full.lint_crs_if_present()` が phase03/04/06 の assert/calibrate 時に合流）、ID の追跡（strict）: シードの CRS の SP（04・09 は CRS の SP 項目、06 は §2〔見出しが無ければ全文〕）が、ツールの仕様が追跡を義務づける欄（04 funcmap・06 CHD §4・09 TSP §4.1）にある。`smoke_full.py` が update-golden・assert・calibrate で検査 | **機械的に絶対検証**。golden の正しさを問う必要がない最も信頼できる種類 |
| (b) テンプレート由来の性質 | 各工程のテンプレート（`templates/*.md`）が固定して持つ見出し構造。`required_headings` | **テンプレートとの自動突合**。`smoke_full.verify_golden_required_headings()` が golden の `required_headings` をテンプレートの H2 見出し集合の部分集合として検査する回帰テスト（`tools/harness/tests/test_smoke_full.py`。`make test` で毎回無料検証） |
| (c) LLM の裁量に依存する内容 | UR・SR の追跡、04・06・09 以外の SP の追跡、接頭辞の無い ID。独立したオラクルが存在せず、集合の完全一致を求める照合は本質的に脆い | **advisory（`⚠`）として表示し、失敗にしない。人が見て判断する**。統計的検証は行わない（上記のとおり実行不能と判明） |

(b) の突合は「golden に required_headings を設定した場合の今後の乖離」を防ぐ手段であり、
未設定の工程（phase03/09/10 等）へ値を新規に埋めることまでは強制しない。乖離が実際に見つかった
場合、golden とテンプレートのどちらを正とするかは乖離内容を見てから人が判断する。

## ID の追跡照合

`smoke_full.trace_ids()` が、シード（工程の入口状態）の CRS の ID が工程の成果物まで追跡できているかを
照合する。ゴールデンには依存しない。

- **走るモード:** update-golden・assert・calibrate（harvest では行わない）。assert／calibrate でゴールデンが
  無い組み合わせは起動前に `golden_missing` で止まるので照合も走らない。
- **期待値:** 実行後の CRS ではなくシードの CRS（`{XDDP_DIR}/{CR}/03_change-requirements/CRS-*.md`。
  CR はシードの `{XDDP_DIR}/CR-*` のソート順の先頭）。工程4・6 が CRS を更新しても、工程が SP を消したことを
  検出できる。工程が追加した SP は照合しない。
  - advisory: CRS の「## 2.」節から形式B（`{CR}-UR-…`・`{CR}-SR-…`・`{CR}-SP-…-….…`）の ID を取る
    （変更履歴等の旧 ID を入れない）。
  - strict: 各工程の根拠のツールと同じ規則。04・09 は `artifact_lint._parse_crs` の SP 項目（F1 と同じ）、
    06 は §2（見出しが無ければ全文）から `chd_sp_coverage._sp_id_re` で取る。
- **strict（失敗にする）:** 04・06・09 の SP だけ。欄に無い SP があれば違反。
  | 工程 | 欄 |
  |---|---|
  | 04 | 各 repo の `SPO-{CR}-funcmap.md` の「機能ID」列（cross/ を除く） |
  | 06 | 各 repo（cross を含む）の CHD 内容ファイルの「## 4. トレーサビリティマトリクス」で変更ファイル列が `-` でない行 |
  | 09 | 各 repo の `TSP-*.md` の「4.1 SP網羅マトリックス」の第1列（網羅状況が `❌` の行を除く）。§4.1 に無くても TSP の §2 に書かれた SP は advisory |

  欄は repo の和集合で見る。接頭辞の無い ID は追跡とみなさない。
- **advisory（失敗にしない）:** strict 以外の種別（工程ごとの表 `PHASE_ID_TRACE`）。成果物ディレクトリ配下の
  `*.md`（`review/`・`.review-brief.md`・`spo-backup/`・`work/`・CRS の写し `crs-scope-*.md` を除く）を走査し、
  形式B または接頭辞の無い形で書かれていない ID と、接頭辞の無い ID の出現を知らせる。
- **照合できない場合:** 成果物ディレクトリが無い、シードに CR ディレクトリ・CRS が無い場合は、strict の工程
  （04・06・09）では違反、それ以外では advisory。期待する SP が 0 件（SP の行の書式が CRS の SP 項目の形でない等）
  なら strict の照合を行わず advisory、CRS §2 から ID を取れなければ advisory の照合を行わず advisory を出す。
- **照合しない工程・シード:** 02・03・close。`phase05-single-quick`（`ID_TRACE_EXCLUDED_SEEDS`）は、quick で
  cross SPO が無いと工程5 が `05_architecture/` を作らない（仕様どおり）ため照合しない。このシードは
  `--update-golden` でゴールデンを作れず、何を照合するかは別途決める。
