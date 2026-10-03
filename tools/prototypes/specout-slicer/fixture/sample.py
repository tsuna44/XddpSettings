CACHE = {}
def ret_flow(x):
    y = SEED + x
    return y
def local_only(x):
    tmp = [SEED]
    tmp.append(x)
    n = len(tmp)
def mutate_param(obj):
    obj.value = SEED
def write_global(k):
    CACHE[k] = SEED
class K:
    def m(self):
        self.v = SEED
def gen(xs):
    for x in xs:
        if x == SEED:
            yield x
def raise_it(x):
    if x == SEED:
        raise ValueError()
def calls_mutator(lst):
    v = SEED
    helper_append(lst, v)
def helper_append(l, v):
    l.append(v)
def with_ctx(path):
    with open(path) as fh:
        data = fh.read() + SEED
    return None
DERIVED = SEED + 1
def outer_fn(x):
    acc = []
    count = 0
    def inner(v):
        nonlocal count
        count += v
        acc.append(v)
    inner(SEED)
    return None
