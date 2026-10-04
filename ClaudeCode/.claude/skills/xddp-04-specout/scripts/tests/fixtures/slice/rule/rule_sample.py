import os
SEED_ALIAS = SEED
class Holder:
    attr = SEED
    def method(self, x=SEED):
        return x
    @staticmethod
    def static_m():
        return SEED
def outer(a):
    @decorate(SEED)
    def inner(b,
              c=SEED):
        return b + SEED
    msg = "SEED"
    # SEED comment
    note = f"{SEED}"
    return inner
async def coro():
    await run(SEED)
def one_liner(): return SEED
text = """
SEED inside a triple-quoted string
"""
