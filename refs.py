from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable

_current_tracker = None

@contextmanager
def _track_into(t):
    global _current_tracker
    old = _current_tracker
    try:
        _current_tracker = t
        yield
    finally:
        _current_tracker = old

_to_update = set()

def tick():
    to_reset = set()
    topo_sort = []
    for seed in _to_update:
        if seed.is_event:
            to_reset.add(seed)
        stack = [seed]
        current_sort = []
        # Where the inner sort will be inserted into the outer sort; the minimum index of all reactives
        insert_point = len(topo_sort)
        while len(stack):
            r = stack.pop()
            # Is the reactive already in the outer sort?
            try:
                topo_i = topo_sort.index(r)
            except ValueError:
                # No? Continue down tree, depth-first.
                current_sort.append(r)
                stack += r.links
            else:
                # Yes? Move the insertion point back to before that reactive.
                # Skip processing it in the current sort since it's already been
                # done.
                insert_point = min(topo_i, insert_point)
        topo_sort[insert_point:insert_point] = current_sort
    # Clear the update set before running any external code, so any changes are
    # correctly remembered for next tick.
    _to_update.clear()
    for r in topo_sort:
        r.update()
    for r in topo_sort:
        if r.log:
            print(f"{r.log}: {r._value} <- {r._next_value}")
        r._value = r._next_value
    for r in to_reset:
        r.set(None)

class UNINITIALIZED:
    pass

class ReadableReactive:
    def __init__(self, initial_value, *, is_event):
        self._watchers = set()
        self.links = set()
        # We require an initial value because otherwise we'd need a safe
        # .get(default) for uninitialised reactives, and in Python you can't
        # pick default values in type-generic cases. In a language with
        # type-infering `zero` or other default value functions, this may be
        # possible.
        self._value = self._next_value = initial_value
        self.is_event = is_event
        self.log = None
        _to_update.add(self)
    def set_origin(self):
        import inspect
        frame = inspect.currentframe()
        tb = inspect.getframeinfo(frame.f_back.f_back)
        self._origin = f"{tb.function}:{tb.lineno}"
    def __repr__(self):
        return f"<{self.__class__.__name__}({self._value})>"
    def __call__(self):
        if _current_tracker is not None: _current_tracker.add(self)
        return self._value
    def get(self, default):
        return default if isinstance(self._value, UNINITIALIZED) else self._value
    def watch(self, active=None):
        if active is None:
            return lambda f: self._watch(f)
        return lambda f: _watch_ref(active, self, f)
    def _watch(self, f):
        print(f"watch {self} {f}")
        self._watchers.add(f)
        return f
    def touch(self):
        for w in self._watchers: w()
    def quiet_get(self):
        return self.getter()

class Reactive(ReadableReactive):
    def set(self, x):
        self.setter(x)
        _to_update.add(self)
    def map(self, f):
        self.set(f(self()))

def as_ref(x):
    if isinstance(x, ReadableReactive):
        return x
    return Ref(x)

class Ref(Reactive):
    def __init__(self, value, is_event=False):
        super().__init__(value, is_event=is_event)
        self._value = value
        self._driver = None
    def update(self):
        if self._driver:
            self._next_value = self._driver._next_value
    def setter(self, x):
        self._next_value = x
    def __lshift__(self, r):
        # We can have circularity in reference to reactives even without circularity in deps (pull sampling).
        if self.is_event != r.is_event:
            raise ValueError()
        if self._driver:
            self._driver.links.remove(self)
        self._driver = r
        self._driver.links.add(self)

ref = Ref

class read_only(ReadableReactive):
    def __init__(self, ref):
        super().__init__(ref(), is_event=ref.is_event)
        self._ref = ref
        ref.links.add(self)
    def update(self):
        self._next_value = self._ref._next_value

def computed(*args):
    def builder(f):
        return Computed(f, *args)
    return builder

def writeable_computed(*args):
    def builder(f):
        return WriteableComputed(f, *args)
    return builder

class Computed(ReadableReactive):
    def __init__(self, function, deps):
        self._function = function
        self._deps = deps
        for ref in deps:
            ref.links.add(self)
        super().__init__(self._function(*[r._next_value for r in self._deps]), is_event=False)
    def update(self):
        self._next_value = self._function(*[r._next_value for r in self._deps])

class WriteableComputed(Computed, Reactive):
    def on_set(self, f):
        self._on_set = f
        return f
    def setter(self, value):
        self._on_set(value)

def effect(active):
    def wrap(gen):
        last = False
        it = None
        @active._watch
        def update():
            nonlocal last, it
            if active() and not last:
                it = gen()
                next(it)
                last = True
            elif not active() and last:
                try:
                    next(it)
                except StopIteration:
                    pass
                last = False
        update()
    return wrap

def _watch_ref(active, ref, f):
    @effect(active)
    def _():
        ref._watchers.add(f)
        print(f"watch {ref} {f}")
        yield
        ref._watchers.remove(f)
    return f
