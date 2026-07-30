# smoke_config.md — full-run スモーク用ハーネスレベル設定

`smoke_full.py` が読む**ハーネスレベル**の設定ファイル。工程別実行モデル・
トークン予算上限・工程別シード対応表を保持する。

> **役割分担（重要）:** 本ファイルは `smoke_full.py`（ハーネス）だけが読む。
> スキルが実際に読む設定（`REVIEW_MAX_ROUNDS=1` 等、スキル挙動を変えるもの）は
> **各シードの `xddp.config.md`** に置く。`smoke_config.md` はスキルからは読まれない。
> （plan Section 2 / 3.2「設定の役割分担」）

> **D 再設計（2026-07-26 実測反映・軽量 advisory 採用）:** 当初の厳密校正（N=20〜30 × 約10工程 ×
> 2モデル＝400〜600起動）は、実測で判明した **$2/工程** と **サブスクのセッション利用上限**
> （1窓 ~6工程・リセット4〜5h）により単一窓で実行不能（$800超・数週間）。よって D を
> **「軽量 advisory」** に再定義する:
> - **モデルは Sonnet 単一**（C のゴールデンも Sonnet 生成）。Haiku 校正は行わない。
> - **`SMOKE_TOKEN_BUDGET` は C バッチの実測コストから確定**（下記）。厳密な偽失敗率 N 回測定は行わず、
>   smoke は **構造の advisory チェック**（違反は人が解釈）と位置付ける。任意で後日 N=2〜3 の再現性
>   確認を窓ごとに少量実施してよい。
> - **phaseClose は成果物 glob が CR 全体で close の実出力（`baseline_docs`）を見ない**ため、
>   advisory 対象から除外（手動検証）。詳細は `PLAN-20260726-smoke-full-runner-enablement` §9。

## 実行要件（認証）

`smoke-full*`／`smoke-calibrate` は隔離 HOME 実行のため非対話認証用の環境変数が必須（OAuth/セッション
認証は隔離 HOME に引き継がれない。PLAN-20260725-smoke-full-api-key-auth 参照）。
`CLAUDE_CODE_OAUTH_TOKEN`（`claude setup-token` で発行。Claude Pro/Max 契約のサブスク枠を消費し
追加課金なし）を優先し、未設定時のみ `ANTHROPIC_API_KEY`（API従量課金）にフォールバックする。
両方とも未設定の場合は `smoke_full.py` が明示エラー（exit 5）で停止する。
（「追加課金なし」は Anthropic 公式ドキュメントに基づく妥当な推論であり、公式文書で明言された
事実そのものではない点に留意すること）

## トークン予算

- `SMOKE_TOKEN_BUDGET`: 30.0  # ← C バッチ実測で確定（USD）。工程別実測 $0.44〜$3.85・合計 ~$18.6、
  # 全通し上限 = 合計 × 安全係数1.5 ≒ $28 → 余裕を見て 30.0。単一工程 assert（`make smoke-full PHASE=NN`）
  # は最大 ~$3.85 なので本値で十分。実効予算ゲート（exit 6）を通過し assert ランを起動する。
  # 注: サブスクのセッション上限（1窓 ~6工程）により `--all` 全通しは単一窓で完走しない場合がある
  # （途中で is_error → exit 9・ゴールデン未書込で安全に中断。上限リセット後に再実行）。
- `SMOKE_CALIBRATE_BUDGET`: 5.0  # ← ブートストラップ（B/C/D）用の実効予算上限（USD）。
  # **暫定値（未実測）。** B の試走1件で1起動単価を把握後、D で実測に基づく確定値へ更新する。
  # `--all --harvest`／`--phase NN --harvest`／`--update-golden`／`--calibrate` はこの値（または
  # CLI `--budget`）で exit 6 を通過し、上限内で起動する。低すぎれば途中で残予算不足（budget_skip）
  # や超過中断（exit 7）になるため、必要に応じ `--budget` で明示上書きする。
- `SMOKE_MAX_PHASES`: 13       # --all 暴走防止の工程数上限（init 1 + single約10 + multi2）

## 工程別実行モデル（advisory = Sonnet 単一）＋ C 実測コスト

D 再設計（軽量 advisory）により、全工程 **Sonnet 単一**で運用する（Haiku 校正は行わない）。
下表の実測コストは C バッチ（`--update-golden`・Sonnet）で計測した1起動あたりの `total_cost_usd`。
`SMOKE_TOKEN_BUDGET` はこの合計 × 安全係数から確定済み（上記）。

| 工程 | モデル | C 実測 $/起動 | ゴールデン | 備考 |
|---|---|---|---|---|
| 02 | sonnet | ~1.82 | ✅ | 分析器が UR/SR/SP を実行裁量で展開 → ID 数が変動しうる（advisory） |
| 03 | sonnet | ~1.76 | ✅ | |
| 04 | sonnet | ~0.55 | ✅ | specout（母体解決） |
| 05 | sonnet | ~1.91 | ✅ | |
| 06 | sonnet | ~2.51 | ✅ | |
| 07 | sonnet | ~2.19 | ✅ | code＋静的検証 |
| 09 | sonnet | ~2.12 | ✅ | |
| 10 | sonnet | ~1.45 | ✅ | |
| 11 | sonnet | ~3.85 | ✅ | latest-specs |
| close | sonnet | ~0.44 | ⚠️ 除外 | 成果物 glob が CR 全体で close の実出力（baseline_docs）を見ない → **手動検証**（advisory 対象外） |

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
