# Specout Doc Levels

> xddp-common の共通プロシージャ。SPO を書くスキル（xddp-04-specout・xddp-investigate・xddp-05-arch）から apply される。

## Specout Doc Levels

スペックアウト資料（下調べ・追加下調べ・SPO）の記載量を `CR_PROFILE` から決める。

**Input:** `CR_PROFILE`, `SPECOUT_DIAGRAM_LEVEL`, `SPECOUT_SEQUENCE_LEVELS`

**Output:** `EFFECTIVE_DIAGRAM_LEVEL`, `EFFECTIVE_SEQUENCE_LEVELS`, `EFFECTIVE_SPO_DETAIL_LEVEL`

**Process:**

If `CR_PROFILE` = `quick`:
  Let `EFFECTIVE_DIAGRAM_LEVEL` = `SPECOUT_DIAGRAM_LEVEL` が `minimal` の場合は `minimal`、それ以外は `standard`
    （quick は記載量を**下げることはあっても上げない**。運用者が `minimal` を明示している場合に
    `standard` へ引き上げると quick の方が `full` より重い SPO を生成する逆転が起きる）
  Let `EFFECTIVE_SEQUENCE_LEVELS` = `SPECOUT_SEQUENCE_LEVELS` の要素のうち `module` のみを残した値
    （`module` を含まない設定の場合は `SPECOUT_SEQUENCE_LEVELS` をそのまま使う。quick が粒度を
    上げないための規則。既定値 `module, class` では `module` に絞られる）
  Let `EFFECTIVE_SPO_DETAIL_LEVEL` = `brief`
Else:
  Let `EFFECTIVE_DIAGRAM_LEVEL` = `SPECOUT_DIAGRAM_LEVEL`
  Let `EFFECTIVE_SEQUENCE_LEVELS` = `SPECOUT_SEQUENCE_LEVELS`
  Let `EFFECTIVE_SPO_DETAIL_LEVEL` = `full`
