"""試作: 名前ベース BFS（現行 LLM の振る舞いを再現）と、関数内スライス BFS の比較。"""
import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from slicer import Repo, judge_hit, EXT_LANG, DEFAULT_EXCLUDES  # noqa: E402

UNKNOWN_SUMM = {"returns": True, "out": set(), "globals": set(), "side": True}


class TokenIndex:
    """リポジトリ全体の識別子の転置インデックス（識別子 → 出現行）。'root.field' の組も索引する。
    grep の代わりに使う（1回作れば、各波の検索は辞書の参照だけで済む）。"""
    _TOK = re.compile(rb"[A-Za-z_]\w*")
    _FLD = re.compile(rb"(?=\b([A-Za-z_]\w*)\s*(?:\.|->)\s*([A-Za-z_]\w*))")

    def __init__(self, repo: Repo):
        from array import array
        self.files = repo.code_files()
        self.idx = {}
        for fid, rel in enumerate(self.files):
            try:
                data = open(os.path.join(repo.root, rel), "rb").read()
            except OSError:
                continue
            for ln, line in enumerate(data.split(b"\n"), 1):
                seen = set(self._TOK.findall(line))
                for m in self._FLD.finditer(line):
                    seen.add(m.group(1) + b"." + m.group(2))
                key = (fid << 21) | ln
                for t in seen:
                    a = self.idx.get(t)
                    if a is None:
                        self.idx[t] = a = array("Q")
                    a.append(key)

    def count(self, sym):
        a = self.idx.get(sym.encode())
        return len(a) if a is not None else 0

    def lines(self, sym):
        for key in self.idx.get(sym.encode(), ()):
            yield self.files[key >> 21], key & ((1 << 21) - 1)


_INDEX = {}


def token_index(repo: Repo):
    if repo.root not in _INDEX:
        _INDEX[repo.root] = TokenIndex(repo)
    return _INDEX[repo.root]


def count_hits(repo: Repo, symbols):
    """シンボルごとのヒット行数。優先順位づけ用。"""
    ti = token_index(repo)
    return {x: ti.count(x) for x in symbols}


def grep_hits(repo: Repo, symbols):
    """frontier シンボルの出現行 [(path, line, symbol)]。"""
    ti = token_index(repo)
    return [(p, ln, x) for x in sorted(symbols) for p, ln in ti.lines(x)]


def select_by_budget(counts, symbols, budget, kinds=None):
    """予算内で処理するシンボルを選ぶ。残りは打ち切り。
    優先順位: 関数シンボル（呼び出し関係の伝播）→ 値シンボル（グローバルの読み手）、各々ヒットの少ない順。"""
    kinds = kinds or {}
    order = sorted(symbols, key=lambda x: (kinds.get(x) != "func", counts.get(x, 0), x))
    chosen, deferred, used = [], [], 0
    for x in order:
        c = counts.get(x, 0)
        if used + c <= budget:
            chosen.append(x)
            used += c
        else:
            deferred.append((x, c))
    return chosen, deferred


def run(repo: Repo, seeds, mode, seed_summary="computed", max_waves=10, max_hits=40000, log=print,
        globals_as_up=False):
    frontier = {}
    for s in seeds:
        if repo.is_function(s):
            if seed_summary == "computed":      # 書きうる副作用すべてが変わる
                summ = repo.summary(s)
            elif seed_summary == "interface":   # 戻り値・出力引数だけが変わる
                c = repo.summary(s)
                summ = {"returns": True, "out": set(c["out"]), "globals": set(), "side": False}
            else:                               # 不明（baseline 相当）
                summ = UNKNOWN_SUMM
            frontier[s] = ("func", summ)
            if mode == "slice" and summ:
                for g in summ["globals"]:
                    frontier.setdefault(g, ("value", None))
        else:
            frontier[s] = ("value", None)
    visited = dict(frontier)
    confirmed = {}
    waves = []
    truncated = []   # [(wave, 理由, [(symbol, ヒット数)])]
    for w in range(max_waves):
        if not frontier:
            break
        t0 = time.time()
        counts = count_hits(repo, frontier.keys())
        chosen, deferred = select_by_budget(counts, frontier.keys(), max_hits,
                                            {k: v[0] for k, v in frontier.items()})
        hits = grep_hits(repo, chosen)
        st = {"wave": w, "frontier": len(frontier), "hits": len(hits), "fp": 0, "selfdef": 0,
              "filescope": 0, "stop": 0, "up": 0, "val": 0, "error_units": 0,
              "deferred": len(deferred), "deferred_hits": sum(c for _, c in deferred)}
        truncated.append((w, "ヒット予算", deferred))
        seed_summ = {s: v[1] for s, v in frontier.items() if v[0] == "func" and v[1] is not None}
        nxt_func = {}   # name -> summary（集約）
        nxt_val = set()
        for path, ln, sym in hits:
            try:
                v = judge_hit(repo, path, ln, sym, seed_summ=seed_summ if mode == "slice" else None) \
                    if mode == "slice" else _baseline(repo, path, ln, sym)
            except Exception as e:  # 試作: 解析失敗は保守的に上へ
                v = None
                st.setdefault("exceptions", 0)
                st["exceptions"] += 1
                log(f"    ! {path}:{ln} {sym}: {type(e).__name__}: {e}")
                continue
            if v.status == "fp":
                st["fp"] += 1
                continue
            confirmed.setdefault(path, w)
            if v.status == "self-def":
                st["selfdef"] += 1
                continue
            if v.status == "write-only":
                st.setdefault("writeonly", 0)
                st["writeonly"] += 1
                continue
            if v.status == "file-scope":
                st["filescope"] += 1
                if not globals_as_up:
                    nxt_val |= v.push_values
                continue
            if mode == "baseline":
                st["up"] += 1
                nxt_func.setdefault(v.func, UNKNOWN_SUMM)
                continue
            if v.result is not None and v.result.has_error:
                st["error_units"] += 1
            if globals_as_up and v.push_values:
                # 剪定フィルタ方式: グローバルの読み手は追わず、呼び出し元への伝播に読み替える
                v.push_up, v.push_values = True, set()
            if v.push_up:
                st["up"] += 1
                agg = nxt_func.setdefault(v.func, {"returns": False, "out": set(),
                                                   "globals": set(), "side": False})
                r = v.result
                agg["returns"] |= r.returns
                agg["out"] |= r.out
                agg["side"] |= r.side
                agg.setdefault("closure", set()).update(r.closure)
            if v.push_values:
                st["val"] += 1
                nxt_val |= v.push_values
            if not v.push_up and not v.push_values:
                st["stop"] += 1
        frontier = {}
        for name, summ in nxt_func.items():
            old = visited.get(name)
            if old is None or (old[0] == "func" and old[1] is not None and _grows(old[1], summ)):
                merged = summ if old is None or old[1] is None else _merge(old[1], summ)
                visited[name] = ("func", merged)
                frontier[name] = ("func", merged)
        for name in nxt_val:
            if name not in visited:
                visited[name] = ("value", None)
                frontier[name] = ("value", None)
        st["next"] = len(frontier)
        st["sec"] = round(time.time() - t0, 1)
        waves.append(st)
        log(f"  wave {w}: " + " ".join(f"{k}={v}" for k, v in st.items() if k != "wave"))
    if frontier:   # 波数上限で未処理のまま残ったシンボル
        c = count_hits(repo, frontier.keys())
        truncated.append((len(waves), "波数上限", sorted(((x, c.get(x, 0)) for x in frontier),
                                                    key=lambda t: t[1])))
    return {"waves": waves, "confirmed": confirmed, "visited": visited, "left": len(frontier),
            "truncated": [t for t in truncated if t[2]]}


def _grows(a, b):
    return (b["returns"] and not a["returns"]) or (b["side"] and not a["side"]) or \
        bool(set(b["out"]) - set(a["out"]))


def _merge(a, b):
    return {"returns": a["returns"] or b["returns"], "out": set(a["out"]) | set(b["out"]),
            "globals": set(), "side": a["side"] or b["side"],
            "closure": set(a.get("closure", ())) | set(b.get("closure", ()))}


class _BV:
    def __init__(self, status, func=None, push_values=()):
        self.status, self.func, self.push_values = status, func, set(push_values)


def _baseline(repo, path, ln, sym):
    """現行 LLM の観測された振る舞い: 偽陽性以外は含む関数名を次のシンボルにする。"""
    from slicer import _nodes_on_line, SEED_TYPES, txt
    sf = repo.file(path)
    row = ln - 1
    from slicer import find_occurrences, foreign_module_attr
    occ = [x for x in find_occurrences(sf, row, sym) if not foreign_module_attr(repo, sf, x, sym)]
    if not occ:
        return _BV("fp")
    f = sf.func_at(occ[0])
    if f is None:
        return _BV("file-scope")
    if occ[0].start_byte < f.body.start_byte:
        return _BV("self-def", f.name)
    return _BV("sliced", f.name)


def read_truth(p):
    out = []
    for l in open(p):
        l = l.strip()
        if l and not l.startswith("#") and not l.startswith("@"):
            out.append(l)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--truth")
    ap.add_argument("--main", default="")
    ap.add_argument("--policy", default="optimistic")
    ap.add_argument("--seed-summary", default="computed")
    ap.add_argument("--max-waves", type=int, default=10)
    ap.add_argument("--max-hits", type=int, default=15000)
    ap.add_argument("--globals-as-up", action="store_true")
    ap.add_argument("--modes", default="baseline,slice")
    ap.add_argument("--h-as", default="c")
    ap.add_argument("--extra-excludes", default="")
    ap.add_argument("--ignore-calls", default="", help="影響なしとみなす呼び出しの正規表現（完全一致）")
    ap.add_argument("--module-level", default="dir1", choices=["dir1", "file"],
                    help="機能（モジュール）の近似: dir1=最上位ディレクトリ / file=ファイル")
    a = ap.parse_args()
    ex = DEFAULT_EXCLUDES + [x for x in a.extra_excludes.split(",") if x]
    repo = Repo(a.repo, excludes=ex, h_as=a.h_as, policy=a.policy)
    if a.ignore_calls:
        repo.ignore_re = re.compile(a.ignore_calls)
    t0 = time.time()
    repo.build_index()
    ti = token_index(repo)
    print(f"index: {len(repo._index)} 関数, {len(repo._macros)} マクロ, "
          f"識別子 {len(ti.idx)} 種, {time.time()-t0:.1f}s")
    seeds = [s for s in a.seeds.split(",") if s]
    truth = read_truth(a.truth) if a.truth else []
    mains = set(x for x in a.main.split(",") if x)
    results = {}
    for mode in a.modes.split(","):
        print(f"== mode={mode} policy={a.policy} seed_summary={a.seed_summary} seeds={seeds}")
        t1 = time.time()
        r = run(repo, seeds, mode, seed_summary=a.seed_summary, max_waves=a.max_waves,
                max_hits=a.max_hits, globals_as_up=a.globals_as_up)
        r["sec"] = round(time.time() - t1, 1)
        results[mode] = r
        conf = r["confirmed"]
        rec = [t for t in truth if t in conf]
        recm = [t for t in truth if t in conf and t in mains]
        nfun = sum(1 for v in r["visited"].values() if v[0] == "func")
        print(f"  確定ファイル={len(conf)} 訪問シンボル={len(r['visited'])}(関数{nfun}) "
              f"未処理frontier={r['left']} 時間={r['sec']}s")
        if truth:
            print(f"  正解再現: 全{len(rec)}/{len(truth)} 主要{len(recm)}/{len(mains & set(truth))} "
                  f"見落とし={[t for t in truth if t not in conf]}")
            mod = (lambda p: p.split("/")[0] if "/" in p else p) if a.module_level == "dir1" \
                else (lambda p: p)
            tmods = {mod(t) for t in truth}
            mmods = {mod(t) for t in truth if t in mains}
            # 波ごとの累積（「N 波で止めたら」の読み取り用）
            print("  波 | 累積ヒット | 累積秒 | 確定ファイル | 正解ファイル(全/主要) | "
                  "確定モジュール | 正解モジュール(全/主要) | 打ち切り(シンボル/ヒット)")
            ch = cs = 0
            for st in r["waves"]:
                w = st["wave"]
                ch += st.get("hits", 0)
                cs += st.get("sec", 0)
                cf = [p for p, w0 in conf.items() if w0 <= w]
                cm = {mod(p) for p in cf}
                print(f"  {w:>2} | {ch:>9} | {cs:>6.1f} | {len(cf):>11} | "
                      f"{sum(1 for t in truth if t in cf)}/{len(truth)} "
                      f"{sum(1 for t in truth if t in cf and t in mains)}/{len(mains & set(truth))} | "
                      f"{len(cm):>13} | {len(tmods & cm)}/{len(tmods)} {len(mmods & cm)}/{len(mmods)} | "
                      f"{st.get('deferred', 0)}/{st.get('deferred_hits', 0)}")
            print(f"  正解モジュール見落とし: {sorted(tmods - {mod(p) for p in conf})}")
        for w, why, items in r.get("truncated", []):
            ex = ", ".join(f"{x}({c})" for x, c in items[:8])
            print(f"  打ち切り記録: 第{w}波 {why} {len(items)}シンボル 例: {ex}")
    if "baseline" in results and "slice" in results:
        b, s = set(results["baseline"]["confirmed"]), set(results["slice"]["confirmed"])
        print(f"== 比較: baseline確定={len(b)} slice確定={len(s)} 共通={len(b & s)} "
              f"sliceのみ={sorted(s - b)[:20]}")
    print("stats:", repo.stats)


if __name__ == "__main__":
    main()
