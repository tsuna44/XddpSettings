import copy
import pickle
import struct

from model import M, S, X


def to_msg(s: S, m: M) -> None:
    m.a = s.a
    m.b = s.b
    m.c = s.c
    m.d = s.d


def relay(m: M) -> bytes:
    m2 = copy.copy(m)
    return pickle.dumps(m2)


def dump(m2: M, fp) -> None:
    fp.write(struct.pack("<iiii", m2.a, m2.b, m2.c, m2.d))


def only_one(s: S) -> int:
    return s.a + 1


def x_dump(x: X, fp) -> None:
    print(x.a, x.b, x.c, x.d, file=fp)
