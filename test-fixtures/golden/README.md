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

参照: plans/PLAN-20260725-p2-test-harness.md Section 3.2, 3.5
