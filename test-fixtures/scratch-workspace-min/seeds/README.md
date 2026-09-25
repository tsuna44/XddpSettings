# seeds（full-run スモークの工程別入口状態スナップショット）

`tools/harness/smoke_full.py` をフェーズ単位で起動するための、各工程の**入口状態**
（前工程まで完了した最小ワークスペース）を格納する。工程 NN のスモークは工程 NN のみ
課金される（トークン戦略の中核）。

> **生成状況（2026-09-26 更新）:** single 版（`phase02-single/`〜`phaseClose-single/`）と
> multi 版（`phase04/05/06/09/11-multi/`）はすべて生成済み（既存 `phaseNN-single/` と同様、`960`/`961` 相当の手動最小化
> フィクスチャとして直接作成したものであり、校正ランの生成物からの自動起こしではない）。
> シード自体を校正ランの生成物から起こし、
> 人が最小化して確定する方針（plan 3.2「シード自体も校正ランの生成物から起こす」）自体は
> 引き続き有効だが、`phase04-multi/` は
> [PLAN-20260806-specout-phase3-parallel-classification.md](../../../plans/PLAN-20260806-specout-phase3-parallel-classification.md)
> Stage 2 の意味層検証（マルチリポジトリでの波ループ並列度確認）が本シードを前提条件として要求していたため、
> 校正ラン完了を待たずに手動最小化フィクスチャとして先行生成した。
>
> **quick 版（2026-08-16 追加）:** `phase02-single-quick/`・`phase04-single-quick/`・
> `phase05-single-quick/`・`phase06-single-quick/`・`phase04-multi-quick/` の5件は、対応する
> `phaseNN-single/`・`phase04-multi/` を複製し `xddp.config.md` に `CR_PROFILE: quick` を追加、
> `progress.md` の状態遷移（工程3スキップ・`phase06` は工程5も対象外スキップ・DSN 不在）を quick の
> 実際の分岐に合わせて手直しした手動フィクスチャ（校正ラン生成物からの起こしではない）。**ゴールデン
> （`golden/phaseNN-{variant}-quick.json`）は未確定**のため、そのまま
> `make smoke-full PHASE=NN [MULTI=1] PROFILE=quick` を実行すると `golden_missing`（exit 8）で
> 止まる。advisory 照合が必要な場合は先に `--update-golden` で確定すること。
> quick で成果物構造が変わらない工程（07/09/10/11/close）と、quick では工程自体が実行されない
> 工程03 は quick 版シードの対象外（`smoke_full.py` の `QUICK_PHASES`）。
>
> **重要:** `CR_PROFILE: quick` は `REPOS:`（マルチリポジトリ）件数と無関係な独立の軸であり、
> 実際の XDDP ツールに「quick は multi 不可」という制約は無い（`/xddp-01-init`・`xddp-set-profile`
> は `IS_MULTI` を参照しない）。むしろ quick は `HAS_CROSS=true` 時に固有の分岐（per-repo 比較を
> 省略しつつ cross の SPO レビュー／DSN／CHD は生成する）を持つため、multi 版シードでしか
> 検証できない quick の挙動がある。
>
> **05/06 の multi 版（2026-08-16 追加）:** `phase05-multi/`・`phase06-multi/`（および各
> `-quick`）は `phase04-multi/` の CR-2026-991（svc-a: `validate()` ／ svc-b: `notify()`。
> 元々は互いに独立した要求）を土台に、「svc-b の `notify()` は送信前に svc-a の `POST /validate`
> を呼ぶ既存インタフェースを specout が発見した」という想定を追加した新規構築フィクスチャ
> （`phase04-multi/` からの単純複製ではない）。この cross SPO/DSN の存在により工程05以降で
> `HAS_CROSS=true` が解決され、cross 分岐を持つ経路をすべて検証できる:
> - `phase05-multi/`: per-repo DSN（svc-a・svc-b）+ cross DSN（`xddp-05-arch` full の cross 分岐）
> - `phase05-multi-quick/`: per-repo 方式比較を省略し **cross DSN のみ**生成（quick の cross 分岐）
> - `phase06-multi/`: 上記 full 版 DSN 一式を入力に工程6へ進む状態
> - `phase06-multi-quick/`: 上記 quick 版（cross DSN のみ）を入力に工程6へ進む状態
>
> この前提に合わせ、05/06-multi（各 `-quick` 含む）の母体 `svc-b/src/mod_b.py` は `notify()` から
> 受け取った文字列の値を数値へ変換し、cross DSN の契約（`{ "value": <number> }`）どおり
> svc-a の `POST /validate` を標準ライブラリ（`urllib.request`）で呼ぶ既存コードを持つ（09/11-multi は
> その前段に空文字列検証を加えた実装後コード）。提供側 svc-a の HTTP 受け口はフィクスチャ外の想定で
> 置かない。`phase04-multi/` は本前提の導入前の入口状態のため呼び出しを持たない。
>
> single 版の quick シード（`HAS_CROSS=false`）ではこれらの cross 分岐を一切通らないため、
> single・multi は互いに代替できない。この4件も含め **ゴールデンは未確定**（full 版含む）。
>
> **09 の multi 版（2026-09-26 追加）:** `phase09-multi/` は `phase06-multi/` を土台に、工程6a〜8
> 完了状態（per-repo CHD〔svc-a: UR-001／svc-b: UR-002〕＋ cross CHD〔`POST /validate` 契約不変・
> breaking=false〕・per-repo CODING・per-repo＋cross VERIFY・progress.md）を追加した手動フィクスチャ。
> 工程9は cross CHD の存在で `HAS_CROSS=true` を再解決するため、cross TSP 生成分岐を検証できる。
> single 版（母体 `../multi/` を共有し未実装のまま）と異なり、シード内の母体コード
> （`svc-a/src/mod_a2.py`・`svc-b/src/mod_b.py`）は CHD どおり**実装後の状態**に揃えてある。
> **ゴールデンは未確定**（初回は `--update-golden` で確定すること）。
>
> **11 の multi 版（2026-09-26 追加）:** `phase11-multi/` は `phase09-multi/` を土台に、工程9・10完了
> 状態（per-repo TSP・TRS〔svc-a・svc-b〕＋ cross TSP・TRS〔`POST /validate` 契約維持の結合テスト〕、
> 全TC PASS・不具合なし、progress.md）を追加した手動フィクスチャ。工程11は cross SPO の存在で
> `HAS_CROSS=true` を解決し、cross CHD「インタフェース変更サマリ」から `latest-specs/cross/` を
> 生成する分岐を検証できる。母体コードは phase09-multi と同じく実装後の状態。
> **ゴールデンは未確定**（初回は `--update-golden` で確定すること）。

## レイアウト

```
seeds/
├── phase02-single/  … phase11-single/, phaseClose-single/   # single 版（工程02〜11＋close）
├── phase04-multi/, phase05-multi/, phase06-multi/,           # cross 生成が絡む工程の multi 版
│   phase09-multi/, phase11-multi/
├── phase02-single-quick/, phase04-single-quick/,             # CR_PROFILE: quick 版（02/04/05/06のみ）
│   phase05-single-quick/, phase06-single-quick/
└── phase04-multi-quick/, phase05-multi-quick/,                # quick かつ multi（04/05/06）
    phase06-multi-quick/
```

各 `phaseNN-single/` は「工程 NN の直前まで完了した状態」（前工程までの成果物 md・
progress.md、および前工程が状態ファイルを生成する場合は `bfs-state.json` 等）を持つ。
工程04入口のように specout 未実行で状態ファイルが未生成の工程では含まれない。

- 規模: single 約10状態 + multi 5状態（04/05/06/09/11）= 計約15スナップショット
  （＋ quick 版9件）。各々 UR1〜2本・SP1〜2本の極小構成（既存 960/961 と同粒度）。
- 工程01（init）は前工程シードから起こせないため `--phase` 対象外（`--all` 専用）。
- 工程08は xddp-07 に統合済み（独立シードなし）。

## `--phase` 解決とステージ後レイアウト（母体解決規則）

`smoke_full.py --phase NN` は `seeds/phaseNN-single/`（`--multi` 指定時は `phaseNN-multi/`、
04/05/06/09/11 のみ受理）を一時ディレクトリへ複製して起動する。single 版シードの
`xddp.config.md` は母体を二重管理しないため `REPOS: svc-a: ../multi/svc-a` と相対参照する。
`smoke_full.py` はステージ先で以下の**固定レイアウト**を組み立て、この相対参照を解決する:

```
{temp}/
├── ws/        ← seeds/phaseNN-single/ の中身を展開（＝ワークスペースルート）
└── multi/     ← multi/svc-a・multi/svc-b の src/ を同伴コピー（母体）
```

`{temp}/ws/xddp.config.md` の `../multi/svc-a` は `{temp}/multi/svc-a` へ解決する
（既存 `single/` が `../multi/` を見る depth=1 関係をステージ時に再現）。
multi 版シードは母体を内包する自己完結ワークスペースのため同伴コピー不要。

正準の受理値一覧・工程別シード対応表は `tools/harness/smoke_config.md` を参照。

参照: plans/PLAN-20260725-p2-test-harness.md Section 3.2
