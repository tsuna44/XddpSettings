#!/bin/bash
# 評価シナリオ一括実行（u1-eval の frr / redis ワークスペースと正解データを使う）
#   U1_EVAL : u1-eval ディレクトリ（既定: ../../../../u1-eval 相当の絶対パスを環境に合わせて指定）
#   PY      : tree-sitter を入れた Python（既定: ../.venv/bin/python）
#   MODES   : 実行する方式（空白区切り）。baseline filter filter-computed filter-unknown full full-computed
#   WAVES / MAX_HITS : 波数の上限 / 1波あたりのヒット上限
set -u
D=$(cd "$(dirname "$0")/.." && pwd)
U1_EVAL=${U1_EVAL:-/Users/tsuna/Documents/src/git-work/u1-eval}
PY=${PY:-$D/.venv/bin/python}
MODES=${MODES:-"baseline filter filter-computed filter-unknown full full-computed"}
WAVES=${WAVES:-10}; MAX_HITS=${MAX_HITS:-10000}
cd "$U1_EVAL" || exit 1
SIM="$PY -u $D/bfs_sim.py --max-waves $WAVES --max-hits $MAX_HITS"
FRR_MAIN=bgpd/bgp_zebra.c,isisd/isis_route.c,isisd/isis_zebra.c,ripd/rip_zebra.c
RED_MAIN=src/module.c,src/server.c,src/server.h,src/t_hash.c
# 影響なしとみなす呼び出し（ログ出力・メモリ確保・assert 等）。プロジェクト固有の設定に相当する
RED_IGN='serverLog\w*|_serverLog\w*|serverAssert\w*|_serverAssert\w*|serverPanic|_serverPanic|zmalloc\w*|zcalloc\w*|zrealloc\w*|zfree\w*|ztrymalloc\w*|latencyAdd\w*'
FRR_IGN='zlog\w*|_zlog\w*|vzlog\w*|flog\w*|XMALLOC|XCALLOC|XREALLOC|XFREE|XSTRDUP|qmalloc|qcalloc|qrealloc|qfree|qstrdup|assert|frrtrace'
redis() { $SIM --repo ws-redis/redis --extra-excludes deps/ --truth truth/redis-15695.txt --main $RED_MAIN --ignore-calls "$RED_IGN" "$@"; }
frr()   { $SIM --repo ws-frr/frr --truth truth/frr-22411.txt --main $FRR_MAIN --ignore-calls "$FRR_IGN" "$@"; }
for sc in "frr ISIS_ROUTE_FLAG_ZEBRA_SYNCED,isis_zebra_route_add_route" \
          "frr isis_zebra_route_add_route,bgp_zebra_connected,rip_zebra_connected" \
          "redis spopWithCountCommand" "redis alsoPropagate,propagatePendingCommands"; do
  set -- $sc; fn=$1; seeds=$2
  for m in $MODES; do
    echo "######## $fn $seeds / $m"
    case $m in
      baseline)        $fn --seeds $seeds --modes baseline ;;
      filter)          $fn --seeds $seeds --modes slice --globals-as-up --seed-summary interface ;;
      filter-computed) $fn --seeds $seeds --modes slice --globals-as-up --seed-summary computed ;;
      filter-unknown)  $fn --seeds $seeds --modes slice --globals-as-up --seed-summary unknown ;;
      full)            $fn --seeds $seeds --modes slice --seed-summary interface ;;
      full-computed)   $fn --seeds $seeds --modes slice --seed-summary computed ;;
    esac
  done
done
echo "######## ALL DONE"
