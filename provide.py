from contextlib import contextmanager

_provided = dict()

@contextmanager
def provide(d):
    global _provided
    old = _provided
    try:
        _provided = _provided.copy()
        _provided.update(d)
        yield
    finally:
        _provided = old

def obtain(name):
    return _provided.get(name)
