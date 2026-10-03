import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slicer import Repo, judge_hit
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixture")
EXPECT = {
 "sample.c": {"ret_flow": ("up", {"return"}), "local_only": ("stop", set()), "out_param": ("up", {"out"}),
              "global_write": ("val", {"global"}), "control_dep": ("val", {"global"}),
              "early_return": ("up", {"return"}), "macro_write": ("up", {"out"}),
              "local_struct": ("stop", set()), "static_state": ("up", {"state"}),
              "heap_ptr": ("up", {"heap"}), "void_early": ("up", {"return"}), "flow_order": ("stop", set()), "branch_exit": ("up", {"out"}), "check_only": ("stop", set()), "DERIVED": ("val", set())},
 "sample.cpp": {"set": ("up", {"out"}), "calc": ("up", {"out"}), "pure_cpp": ("stop", set()),
                "throws": ("up", {"exception"}), "sum_all": ("up", {"return"})},
 "sample.py": {"ret_flow": ("up", {"return"}), "local_only": ("stop", set()), "mutate_param": ("up", {"out"}),
               "write_global": ("val", {"global"}), "m": ("up", {"out"}), "gen": ("up", {"return"}),
               "raise_it": ("up", {"exception"}), "calls_mutator": ("up", {"out"}), "with_ctx": ("stop", set()), "outer_fn": ("stop", set()),
               "DERIVED": ("val", set())},
}
ok = ng = 0
for policy in ("optimistic", "strict"):
    repo = Repo(FIX, excludes=[], h_as="c", policy=policy)
    print(f"=== policy={policy}")
    for fn, exp in EXPECT.items():
        lines = open(os.path.join(FIX, fn)).read().split("\n")
        for i, l in enumerate(lines, 1):
            if "SEED" not in l:
                continue
            v = judge_hit(repo, fn, i, "SEED")
            key = v.func or (sorted(v.push_values)[0] if v.push_values else "?")
            kinds = {k for k, _, _ in v.escapes}
            got = "up" if v.push_up else ("val" if v.push_values else "stop")
            e = exp.get(key)
            res = e is not None and got == e[0] and e[1] <= kinds
            if policy == "strict" and e and e[0] == "stop" and got == "up":
                res = None  # strict は外部関数で保守的に上へ伝播しうる
            mark = {True: "OK", False: "NG", None: "--"}[res]
            ok += res is True; ng += res is False
            print(f"{mark} {fn}:{i:<3} {key:<14} got={got:<4} kinds={sorted(kinds)} push={sorted(v.push_values)} {v.note} expect={e}")
print(f"OK={ok} NG={ng}")
