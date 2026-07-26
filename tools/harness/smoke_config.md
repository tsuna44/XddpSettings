# smoke_config.md — full-run スモーク用ハーネスレベル設定

`smoke_full.py` が読む**ハーネスレベル**の設定ファイル。工程別実行モデル・
トークン予算上限・工程別シード対応表を保持する。

> **役割分担（重要）:** 本ファイルは `smoke_full.py`（ハーネス）だけが読む。
> スキルが実際に読む設定（`REVIEW_MAX_ROUNDS=1` 等、スキル挙動を変えるもの）は
> **各シードの `xddp.config.md`** に置く。`smoke_config.md` はスキルからは読まれない。
> （plan Section 2 / 3.2「設定の役割分担」）

> **未確定（校正待ち）:** 下記の工程別モデル・`SMOKE_TOKEN_BUDGET` は
> **校正ラン（plan 3.5）で実測して確定する**まで暫定値である。推測で確定値を置かない。
> 校正手順: (0) 前提スパイク → (1) ゴールデン確定 → (2) 偽失敗率 N 回測定
> （rule of three: 上側95%≤15%→N=20／重要工程≤10%→N=30・0失敗必須）→
> (3) 工程別最安モデル確定 → (4) 実測 usage × 安全係数で上限確定。

## 実行要件（認証）

`smoke-full*`／`smoke-calibrate` は隔離 HOME 実行のため非対話認証用の環境変数が必須（OAuth/セッション
認証は隔離 HOME に引き継がれない。PLAN-20260725-smoke-full-api-key-auth 参照）。
`CLAUDE_CODE_OAUTH_TOKEN`（`claude setup-token` で発行。Claude Pro/Max 契約のサブスク枠を消費し
追加課金なし）を優先し、未設定時のみ `ANTHROPIC_API_KEY`（API従量課金）にフォールバックする。
両方とも未設定の場合は `smoke_full.py` が明示エラー（exit 5）で停止する。
（「追加課金なし」は Anthropic 公式ドキュメントに基づく妥当な推論であり、公式文書で明言された
事実そのものではない点に留意すること）

## トークン予算

- `SMOKE_TOKEN_BUDGET`: 0.0   # ← 校正ランで確定（USD）。0 = 未校正（LLM 起動を許可しない）
- `SMOKE_MAX_PHASES`: 12       # --all 暴走防止の工程数上限（single約10 + multi2）

## 工程別実行モデル（暫定既定 = 安全側 Sonnet）

校正で「偽失敗率がほぼ0になる最安モデル」を工程ごとに確定するまで、暫定既定は Sonnet。
単純工程は Haiku 候補、specout BFS・TM生成・SPカバレッジ等の複雑工程は Sonnet を想定。

| 工程 | 暫定モデル | 校正後モデル | 上側信頼要件 |
|---|---|---|---|
| 02 | sonnet | （校正待ち） | ≤15% / N=20 |
| 03 | sonnet | （校正待ち） | ≤15% / N=20 |
| 04 | sonnet | （校正待ち） | ≤10% / N=30（cross・BFS 重工程） |
| 05 | sonnet | （校正待ち） | ≤15% / N=20 |
| 06 | sonnet | （校正待ち） | ≤10% / N=30（SPカバレッジ） |
| 07 | sonnet | （校正待ち） | ≤15% / N=20 |
| 09 | sonnet | （校正待ち） | ≤15% / N=20 |
| 10 | sonnet | （校正待ち） | ≤15% / N=20 |
| 11 | sonnet | （校正待ち） | ≤10% / N=30（cross・latest-specs） |
| close | sonnet | （校正待ち） | ≤15% / N=20 |

## 工程別シード対応表（`--phase` → seeds ディレクトリ・正準受理値一覧）

| PHASE | single シード | multi シード |
|---|---|---|
| 02 | seeds/phase02-single/ | — |
| 03 | seeds/phase03-single/ | — |
| 04 | seeds/phase04-single/ | seeds/phase04-multi/ |
| 05 | seeds/phase05-single/ | — |
| 06 | seeds/phase06-single/ | — |
| 07 | seeds/phase07-single/ | — |
| 09 | seeds/phase09-single/ | — |
| 10 | seeds/phase10-single/ | — |
| 11 | seeds/phase11-single/ | seeds/phase11-multi/ |
| close | seeds/phaseClose-single/ | — |

- 工程01（init）は `--all` 専用（前工程シードから起こせないため `--phase` 対象外）。
- 工程08は xddp.07 に統合済み（独立工程シードなし）。
