# scratch-workspace-survey-flat

`xddp.survey` の縮退モード（module-catalog 不在時）のモジュール解決を検証するための最小フィクスチャ。
`PLAN-20260905-survey-flat-module-fallback` の確認項目専用。

## 構成

`REPOS: flat-svc: ./flat-svc`（シングルリポジトリ・`module-catalog.md` は意図的に未生成＝常に縮退モード）

| パス | 用途 |
|---|---|
| `flat-svc/moduleA/handler.py` | ディレクトリ単位モジュール（既存のディレクトリ一致経路の回帰確認用。`module moduleA`） |
| `flat-svc/src/parser.py` ／ `flat-svc/legacy/parser.py` | 同一ファイル名（拡張子除く）が複数ディレクトリに存在するケース（ファイル名一致フォールバックの複数候補確認用。`module parser`） |
| `flat-svc/src/SensorReader.java` | CamelCase ファイル名（`NORMALIZE()` の CamelCase 分割確認用。`module sensor-reader`） |

## 使い方（例）

```
cd test-fixtures/scratch-workspace-survey-flat
/xddp.survey flat-svc module moduleA        # ディレクトリ一致（回帰確認）
/xddp.survey flat-svc module parser         # ファイル名一致・複数候補
/xddp.survey flat-svc module sensor-reader  # ファイル名一致・CamelCase
/xddp.survey flat-svc module nonexistent    # 一致なしのエラーメッセージ確認
```

いずれも Step 4.5 では **(a) 調査のみ** を選ぶこと（`baseline_docs/` が存在しないため、
(b)/(c) を選ぶ場合は事前に `mkdir -p baseline_docs` が必要）。
