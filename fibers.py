from contextlib import contextmanager

current_fiber = None

@contextmanager
def fork_current(key):
    global current_fiber
    old = current_fiber
    try:
        current_fiber = old.fork(key)
        yield
    finally:
        current_fiber.finish()
        current_fiber = old

def component(f):
    def wrapped(*args, key=None, **kwargs):
        with fork_current(key):
            f(*args, **kwargs)
    return wrapped

def use_mount(maker):

def use_memo(f, deps):
    def memo():
        yield {'value':None, 'deps':None}
    memo = current_fiber.install(memo, type=use_memo)
    if deps != memo['deps']:
        memo['value'] = f()
    return memo['value']

def _fork(f, *, key):
    def make_subfiber():
        subfiber = Fiber(current_fiber)
        yield subfiber
        subfiber.dispose()
    subfiber = current_fiber.install(make_subfiber, type=f, key=key)
    global current_fiber
    old = current_fiber
    try:
        current_fiber = subfiber
        f()
    finally:
        current_fiber.reconcile()
        current_fiber = old

class Fiber:
    def __init__(self, function, parent=None):
        if parent is not None:
            self.globals = parent.globals
        else:
            self.globals = {}
        self._function = function
        self._slots = {}
        self._last_slots = {}
        self._next_key = 0
    def install(*, type, key=None):
        def installer(manager):
            if key is None:
                key = self._next_key
                self._next_key += 1
            store_key = (type, key)
            if store_key in self._last_slots:
                store = self._last_slots[store_key]
            else:
                resource = manager.__enter__()
                store = self._last_slots.setdefault(store_key, [resource, manager])
            self._slots[store_key] = store
            return resource
        return installer
    def __call__(self, *args, **kwargs):
        global current_fiber
        old = current_fiber
        try:
            current_fiber = self
            self._function(*args, **kwargs)
        finally:
            current_fiber.finish()
            current_fiber = old
