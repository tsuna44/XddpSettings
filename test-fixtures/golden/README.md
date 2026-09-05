# golden（full-run スモークの構造性質ゴールデン）

`tools/harness/smoke_full.py`（L4/L5 full-run スモーク）が、隔離 HOME で工程スキルを
実起動して生成した成果物の**構造性質**を照合する期待値（ゴールデン）を格納する。

## 表現形式（保守コスト最小化）

ゴールデンは**構造性質の JSON** で表現し、LLM 生成の散文は byte 固定しない
（実行ごとに変わるため）。1工程1ファイル（`phase{NN}-{single,multi}.json`）を想定。

```jsonc
{
  "required_headings": ["4. トレーサビリティマトリクス", ...],  // 必須見出し（部分集合検査）
  "ids": ["SP-001", "UR-001"],                                  // 期待 ID 集合
  "frontmatter_keys": ["version", "last-updated-cr", ...],       // 必須フロントマターキー
  "unreplaced_tokens": []                                        // 常に空であるべき（C2）
}
```

日付・絶対パス・トークン数等の環境/実行依存フィールドは
`smoke_full.normalize_properties` で正規化してから照合する。

## ブートストラップ・更新手順（鶏卵回避）

ゴールデンは**校正ラン（plan 3.5）で確定するまで空**である（推測で置かない）。順序は固定:

1. 既知の正しいツリーに対し各工程を1回起動し `--update-golden` で構造性質を収集
2. 人が diff を確認してゴールデンを確定（→ このディレクトリへコミット）
3. 確定ゴールデンに対して偽失敗率を N 回測定（rule of three: N=20/30・0失敗必須）

更新: `python3 tools/harness/smoke_full.py --phase NN --update-golden`（diff は人が確認）。

## プロバイダ別ゴールデン（`providers/`）

ゴールデンは**モデル依存**（見出し・ID の展開粒度がモデルで変わる）ため、Anthropic 互換の
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

golden の `required_headings` / `ids` は元々「1回の LLM 出力の目視確認」で確定した値であり、
その値自体の正しさを統計的に検証する計画（`plans/PLAN-20260725-p2-test-harness.md` Section 3.5
「確定 golden に対する偽失敗率の N 回実測」）はコスト・サブスクのセッション上限により実行不能と
判明し省略された（上記「D 再設計」節）。N 回実測は「golden に対する再現性」を測るだけで
「golden の値そのものの正しさ」は証明できない。

そこで golden が検査する性質を、正しさの検証可能性によって3種類に分類し、それぞれ異なる
担保レベルで扱う（`plans/PLAN-20260816-golden-oracle-free-checks.md`）。

| 性質 | 内容 | 担保レベル |
|---|---|---|
| (a) オラクル不要の不変条件 | golden を参照せず、ツール仕様から常に真偽が決まる性質。例: `unreplaced_tokens`（未置換トークン残存はゴールデンによらず常に違反。`compare_to_golden()`）、CRS 構造チェック（`artifact_lint._lint_crs()` の error issue。`smoke_full.lint_crs_if_present()` が phase03/04/06 の assert/calibrate 時に合流） | **機械的に絶対検証**。golden の正しさを問う必要がない最も信頼できる種類 |
| (b) テンプレート由来の性質 | 各工程のテンプレート（`templates/*.md`）が固定して持つ見出し構造。`required_headings` | **テンプレートとの自動突合**。`smoke_full.verify_golden_required_headings()` が golden の `required_headings` をテンプレートの H2 見出し集合の部分集合として検査する回帰テスト（`tools/harness/tests/test_smoke_full.py`。`make test` で毎回無料検証） |
| (c) LLM の裁量に依存する内容 | `ids`（要求分解の粒度で変わる）等。独立したオラクルが存在せず、集合の完全一致を求める照合は本質的に脆い | **人によるトレーサビリティ監査が必要**。統計的検証は行わない（上記のとおり実行不能と判明） |

(b) の突合は「golden に required_headings を設定した場合の今後の乖離」を防ぐ手段であり、
未設定の工程（phase03/09/10 等）へ値を新規に埋めることまでは強制しない。乖離が実際に見つかった
場合、golden とテンプレートのどちらを正とするかは乖離内容を見てから人が判断する。
