from .core import SEED as seed_alias


def uses_alias_in_function(x):
    from .core import SEED as local_alias
    return local_alias(x)


def plain_import_then_call(x):
    from .core import SEED
    return x
