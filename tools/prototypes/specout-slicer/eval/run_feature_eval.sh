#!/bin/bash
# 機能（モジュール）単位の評価: baseline と 完全・computed を、1波のヒット予算ごとに比べる
#   出力の「波ごとの累積」表から、波数上限 1〜WAVES の結果を読み取る
set -u
D=$(cd "$(dirname "$0")/.." && pwd)
U1_EVAL=${U1_EVAL:-/Users/tsuna/Documents/src/git-work/u1-eval}
PY=${PY:-$D/.venv/bin/python}
WAVES=${WAVES:-5}; BUDGETS=${BUDGETS:-"1000 3000 10000"}
cd "$U1_EVAL" || exit 1
SIM="$PY -u $D/bfs_sim.py --max-waves $WAVES"
FRR_MAIN=bgpd/bgp_zebra.c,isisd/isis_route.c,isisd/isis_zebra.c,ripd/rip_zebra.c
RED_MAIN=src/module.c,src/server.c,src/server.h,src/t_hash.c
RED_IGN='serverLog\w*|_serverLog\w*|serverAssert\w*|_serverAssert\w*|serverPanic|_serverPanic|zmalloc\w*|zcalloc\w*|zrealloc\w*|zfree\w*|ztrymalloc\w*|latencyAdd\w*'
FRR_IGN='zlog\w*|_zlog\w*|vzlog\w*|flog\w*|XMALLOC|XCALLOC|XREALLOC|XFREE|XSTRDUP|qmalloc|qcalloc|qrealloc|qfree|qstrdup|assert|frrtrace'
redis() { $SIM --repo ws-redis/redis --extra-excludes deps/ --truth truth/redis-15695.txt --main $RED_MAIN --module-level file --ignore-calls "$RED_IGN" "$@"; }
frr()   { $SIM --repo ws-frr/frr --truth truth/frr-22411.txt --main $FRR_MAIN --module-level dir1 --ignore-calls "$FRR_IGN" "$@"; }
for sc in "frr ISIS_ROUTE_FLAG_ZEBRA_SYNCED,isis_zebra_route_add_route" \
          "frr isis_zebra_route_add_route,bgp_zebra_connected,rip_zebra_connected" \
          "redis spopWithCountCommand" "redis alsoPropagate,propagatePendingCommands"; do
  set -- $sc; fn=$1; seeds=$2
  echo "######## $fn $seeds / baseline"
  $fn --seeds $seeds --modes baseline --max-hits 100000
  for b in $BUDGETS; do
    echo "######## $fn $seeds / full-computed budget=$b"
    $fn --seeds $seeds --modes slice --seed-summary computed --max-hits $b
  done
done
echo "######## ALL DONE"
