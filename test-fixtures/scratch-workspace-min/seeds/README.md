# seeds（full-run スモークの工程別入口状態スナップショット）

`tools/harness/smoke_full.py` をフェーズ単位で起動するための、各工程の**入口状態**
（前工程まで完了した最小ワークスペース）を格納する。工程 NN のスモークは工程 NN のみ
課金される（トークン戦略の中核）。

> **生成状況（2026-08-09 更新）:** single 版（`phase02-single/`〜`phaseClose-single/`）と
> `phase04-multi/` は生成済み（既存 `phaseNN-single/` と同様、`960`/`961` 相当の手動最小化
> フィクスチャとして直接作成したものであり、校正ランの生成物からの自動起こしではない）。
> **`phase11-multi/` のみ未生成（校正待ち）。** シード自体を校正ランの生成物から起こし、
> 人が最小化して確定する方針（plan 3.2「シード自体も校正ランの生成物から起こす」）自体は
> 引き続き有効だが、`phase04-multi/` は
> [PLAN-20260806-specout-phase3-parallel-classification.md](../../../plans/PLAN-20260806-specout-phase3-parallel-classification.md)
> Stage 2 の意味層検証（マルチリポジトリでの波ループ並列度確認）が本シードを前提条件として要求していたため、
> 校正ラン完了を待たずに手動最小化フィクスチャとして先行生成した。

## レイアウト

```
seeds/
├── phase02-single/  … phase11-single/, phaseClose-single/   # single 版（工程02〜11＋close）
└── phase04-multi/,  phase11-multi/                           # cross 生成が絡む工程のみ multi 版
```

各 `phaseNN-single/` は「工程 NN の直前まで完了した状態」（前工程までの成果物 md・
progress.md、および前工程が状態ファイルを生成する場合は `bfs-state.json` 等）を持つ。
工程04入口のように specout 未実行で状態ファイルが未生成の工程では含まれない。

- 規模: single 約10状態 + multi 2状態（04/11）= 計約12スナップショット。
  各々 UR1本・SP1本の極小構成（既存 960/961 と同粒度）。
- 工程01（init）は前工程シードから起こせないため `--phase` 対象外（`--all` 専用）。
- 工程08は xddp.07 に統合済み（独立シードなし）。

## `--phase` 解決とステージ後レイアウト（母体解決規則）

`smoke_full.py --phase NN` は `seeds/phaseNN-single/`（`--multi` 指定時は `phaseNN-multi/`、
04/11 のみ受理）を一時ディレクトリへ複製して起動する。single 版シードの
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
