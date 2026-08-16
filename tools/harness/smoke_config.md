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
認証変数の探索順は**送信先によって切り替わる**（`smoke_full._resolve_auth_env`）。

| `ANTHROPIC_BASE_URL` | 探索順 |
|---|---|
| 未設定（Anthropic 公式） | `CLAUDE_CODE_OAUTH_TOKEN` → `ANTHROPIC_API_KEY` → `ANTHROPIC_AUTH_TOKEN` |
| 設定済み（第三者エンドポイント） | `ANTHROPIC_AUTH_TOKEN` → `ANTHROPIC_API_KEY`（**OAuth は候補外**） |

`CLAUDE_CODE_OAUTH_TOKEN`（`claude setup-token` で発行。Claude Pro/Max 契約のサブスク枠を消費し
追加課金なし）は Anthropic サブスクの資格情報であり、第三者エンドポイント指定時は
**意図的に候補から外す**（誤送信の防止。第三者側では認証にも使えない）。
探索順のいずれにも該当がない場合は `smoke_full.py` が明示エラー（exit 5）で停止する。
（「追加課金なし」は Anthropic 公式ドキュメントに基づく妥当な推論であり、公式文書で明言された
事実そのものではない点に留意すること）

### Anthropic互換の第三者エンドポイント利用（`ANTHROPIC_BASE_URL` 等）

`ANTHROPIC_AUTH_TOKEN` を使う構成は通常、`ANTHROPIC_BASE_URL`（独自APIサーバのURL）と
`ANTHROPIC_DEFAULT_SONNET_MODEL`（`sonnet` エイリアスの上書き先モデルID）を組み合わせて使う
（例: Sakura AI の Anthropic 互換エンドポイント経由で Kimi 系モデルを利用する構成）。
`smoke_full.py` の `_invoke_phase` は `PASSTHROUGH_ENV_KEYS`（`ANTHROPIC_BASE_URL` /
`ANTHROPIC_MODEL` / `ANTHROPIC_DEFAULT_SONNET_MODEL` / `ANTHROPIC_DEFAULT_OPUS_MODEL` /
`ANTHROPIC_DEFAULT_HAIKU_MODEL`）のうち実行環境で設定済みの変数だけを隔離 HOME の
サブプロセスへ自動転送する。実行例:

```bash
export ANTHROPIC_BASE_URL="https://api.ai.sakura.ad.jp"
export ANTHROPIC_AUTH_TOKEN="..."
export ANTHROPIC_DEFAULT_SONNET_MODEL="preview/Kimi-K2.6"
export ANTHROPIC_DEFAULT_OPUS_MODEL="preview/Kimi-K2.6"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="preview/Kimi-K2.6"

# 1) 当該プロバイダのゴールデンを確定（初回のみ。平坦ゴールデンは壊さない）
python3 tools/harness/smoke_full.py --phase 04 --update-golden
# 2) 以降は通常どおり assert
make smoke-full PHASE=04
```

第三者エンドポイントでは USD 予算の供給は不要（下記「予算ガードは適用せず、計測のみ行う」）。

`ANTHROPIC_BASE_URL` に完全な messages エンドポイント（`.../v1/messages`）を設定した場合は
転送前に自動で正規化する（CLI がベースURLに `/v1/messages` を連結するため、そのままでは
二重連結になる）。末尾 `/v1` 単独は剥がさない。

`ClaudeCode/.claude/` の agents・skills には `model:` フロントマターが無いため、サブエージェントは
親の `--model` を継承する（＝上記のエイリアス上書きが工程全体に効く。2026-08-16 grep 実測）。

**ゴールデンのプロファイル分離:** ゴールデンはモデル依存のため、`ANTHROPIC_BASE_URL` 設定時は
`test-fixtures/golden/providers/{host}__{実モデルID}/` へ分離して読み書きする（Sonnet 校正済みの
平坦ゴールデンは上書きされない）。初回 assert は `golden_missing`（exit 8）で停止するので、
上記手順1で当該プロファイルのゴールデンを先に確定すること。詳細は
[test-fixtures/golden/README.md](../../test-fixtures/golden/README.md)。

**予算ガードは適用せず、計測のみ行う:** 第三者エンドポイントでは Anthropic の USD 単価に基づく
上限が意味を持たない（応答が `total_cost_usd` を返さない場合もある）ため、`--budget` を明示
しない限り**上限なし（計測のみ）**で動作し、実効予算ゲート（exit 6）も予算超過中断（exit 7）も
適用しない。暴走防止は工程数上限 `SMOKE_MAX_PHASES`（13）が担う。
上限を付けたい場合は `--budget` を明示すれば従来どおりのガードが効く。

計測は上限の有無にかかわらず常に記録する。工程別に `input_tokens` / `output_tokens` /
`cache_read_input_tokens` / `cache_creation_input_tokens` / `total_cost_usd` /
`duration_ms` / `num_turns` を収集し、テキストレポートの各行と末尾の累計、`--json` の
`results[].usage` ・ `budget` に出力する。エンドポイントが `usage` もコストも返さなかった
工程は `reported: false` として記録され、`⚠️ N/M 工程で usage/total_cost_usd が返りません
でした` と警告する（＝計測できたのか空振りしたのかが区別できる）。

ラン間で比較したい場合は `--metrics-out PATH` を付けると工程別1行の JSONL を**追記**する。

```bash
python3 tools/harness/smoke_full.py --phase 04 \
  --metrics-out tools/harness/metrics/third-party.jsonl
```

**未確認事項（実測が必要）:**
- CLI の `--model` と `ANTHROPIC_MODEL` の優先関係。本ハーネスは常に `--model`（既定 `sonnet`）を
  渡すため、`ANTHROPIC_MODEL` のみを設定する構成では意図しないモデルになりうる。
  `ANTHROPIC_DEFAULT_*_MODEL` でのエイリアス上書き、または `--model` へ実モデルIDを直接指定する
  運用を推奨する。
- `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` 等は転送対象外（env はホワイトリスト）。プロキシ配下では
  接続できない。必要になったら `PASSTHROUGH_ENV_KEYS` へ追加すること。

## トークン予算

- `SMOKE_TOKEN_BUDGET`: 30.0  # ← C バッチ実測で確定（USD）。工程別実測 $0.44〜$3.85・合計 ~$18.6、
  # 全通し上限 = 合計 × 安全係数1.5 ≒ $28 → 余裕を見て 30.0。単一工程 assert（`make smoke-full PHASE=NN`）
  # は最大 ~$3.85 なので本値で十分。実効予算ゲート（exit 6）を通過し assert ランを起動する。
  # 注: サブスクのセッション上限（1窓 ~6工程）により `--all` 全通しは単一窓で完走しない場合がある
  # （途中で is_error → exit 9・ゴールデン未書込で安全に中断。上限リセット後に再実行）。
  # ⚠️ 未再算定: 工程04の並列 classifier 導入（PLAN-20260806-specout-phase3-parallel-classification.md
  # Stage 2）後、工程04の実測 $/起動が変わりうる（下表参照）。本セッションは API 認証未設定のため
  # 校正ランを実施できず、30.0 は Stage 2 導入前の実測に基づく暫定値のまま据え置いている。
  # 次回校正ラン後、工程04の実測を反映して本値と下表を更新すること。
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
| 04 | sonnet | ~0.55 ⚠️要再校正 | ✅ | specout（母体解決）。この値は波内 classification のチャンク並列化（PLAN-20260806-specout-phase3-parallel-classification.md Stage 2。`SPECOUT_CLASSIFY_CHUNK_SIZE`/`SPECOUT_CLASSIFY_PARALLEL`）導入**前**の実測であり、並列 classifier 起動込みの値ではない。次回校正ラン（`make smoke-full PHASE=04`）で実測し直し、本値と下記 `SMOKE_TOKEN_BUDGET` を更新すること |
| 05 | sonnet | ~1.91 | ✅ | |
| 06 | sonnet | ~2.51 | ✅ | |
| 07 | sonnet | ~2.19 | ✅ | code＋静的検証 |
| 09 | sonnet | ~2.12 | ✅ | |
| 10 | sonnet | ~1.45 | ✅ | |
| 11 | sonnet | ~3.85 | ✅ | latest-specs |
| close | sonnet | ~0.44 | ⚠️ 除外 | 成果物 glob が CR 全体で close の実出力（baseline_docs）を見ない → **手動検証**（advisory 対象外） |

## 工程別シード対応表（`--phase` → seeds ディレクトリ・正準受理値一覧）

| PHASE | single シード | multi シード | quick シード（single, `--profile quick`） | quick シード（multi, `--multi --profile quick`） |
|---|---|---|---|---|
| 02 | seeds/phase02-single/ | — | seeds/phase02-single-quick/ | — （multi 版シード自体が未整備） |
| 03 | seeds/phase03-single/ | — | — （quick では工程2に統合され実行されない） | — |
| 04 | seeds/phase04-single/ | seeds/phase04-multi/ | seeds/phase04-single-quick/ | seeds/phase04-multi-quick/ |
| 05 | seeds/phase05-single/ | seeds/phase05-multi/ | seeds/phase05-single-quick/ | seeds/phase05-multi-quick/ |
| 06 | seeds/phase06-single/ | seeds/phase06-multi/ | seeds/phase06-single-quick/ | seeds/phase06-multi-quick/ |
| 07 | seeds/phase07-single/ | — | — （quick でも成果物構造は full と同一） | — |
| 09 | seeds/phase09-single/ | — | — （quick でもレビュー基準のみ変わり構造は同一） | — |
| 10 | seeds/phase10-single/ | — | — | — |
| 11 | seeds/phase11-single/ | seeds/phase11-multi/ | — | — |
| close | seeds/phaseClose-single/ | — | — | — |

`CR_PROFILE: quick` と `REPOS:` 件数（multi）は実際の XDDP ツールでは独立した軸であり、
`/xddp.01.init`・`/xddp.set-profile` のどちらも `IS_MULTI` を参照しない（quick は multi
不可という制約は存在しない）。上表の空欄は「このフィクスチャがまだ用意していない」ことを表す
だけで、実運用の制約ではない。

`HAS_CROSS = IS_MULTI`（工程04時点。以降は直前工程の cross 成果物の存在で再解決）のため、quick
でも cross まわりの分岐（04: cross SPO レビュー・`QUICK_PROFILE: true`・1ラウンド／05: per-repo
比較スキップ・cross DSN のみ生成／06: cross CHD 生成）は multi 版シードでしか経由しない
（single 版は `HAS_CROSS=false` のため通らない。05 は工程自体が丸ごとスキップされる）。
`phase05-multi/`・`phase06-multi/`（および各 `-quick`）は `phase04-multi/` の CR-2026-991
（svc-a: `validate()` ／ svc-b: `notify()`）を土台に、svc-b→svc-a の `POST /validate` という
既存インタフェースを specout が発見した想定で `04_specout/cross/SPO-CR-2026-991-cross.md` 以降を
新規構築したフィクスチャ。詳細は
[test-fixtures/scratch-workspace-min/seeds/README.md](../../test-fixtures/scratch-workspace-min/seeds/README.md)
を参照。

- 工程01（init）は `--all` 専用（前工程シードから起こせないため `--phase` 対象外）。
- 工程08は xddp.07 に統合済み（独立工程シードなし）。
- `--profile quick` は `QUICK_PHASES`（02/04/05/06）のみ受理・`--phase` 単体指定限定（`--all` との併用は
  exit 2）。例: `make smoke-full PHASE=04 PROFILE=quick` / `python3 tools/harness/smoke_full.py --phase 04 --profile quick`。
  quick シードは既存 `phaseNN-single/` を手動複製し `CR_PROFILE: quick` を反映したフィクスチャで、
  **ゴールデン（`golden/phaseNN-single-quick.json`）は未確定**（`--update-golden` で先に確定するまで
  `golden_missing` / exit 8）。詳細・生成方針は
  [test-fixtures/scratch-workspace-min/seeds/README.md](../../test-fixtures/scratch-workspace-min/seeds/README.md) を参照。
