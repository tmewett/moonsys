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
                current_sort.append(r)
                stack += r.links
            else:
                # Move the insertion point back to before that reactive, then
                # skip processing it in the current sort since it's already been
                # done.
                insert_point = min(topo_i, insert_point)
        topo_sort[insert_point:insert_point] = current_sort
    _to_update.clear()
    print(topo_sort)
    for r in topo_sort:
        r.update()
    for r in topo_sort:
        if r.log:
            print(f"{r.log}: {r._value} <- {r._next_value}")
        r._value = r._next_value
    for r in to_reset:
        r.set(None)

def set_origin(obj):
    import inspect
    frame = inspect.currentframe()

class UNINITIALIZED:
    pass

class ReadableReactive:
    # To get commit phases on .set ... remove watching public API, replace with
    # downstreams rdeps set; on .set, collect .touches from all downstreams;
    # only call on global refresh. Can get commit phases for outputs too, by saving into a next_value var.
    def __init__(self, *, is_event):
        self._watchers = set()
        self.links = set()
        # prev lets you read the pre-tick value of a ref, essentially breaking the dependency chain.
        self._value = self._next_value = UNINITIALIZED()
        self.is_event = is_event
        self.log = None
        _to_update.add(self)
        self.set_origin()
    def set_origin(self):
        import inspect
        frame = inspect.currentframe()
        tb = inspect.getframeinfo(frame.f_back.f_back)
        self._origin = f"{tb.function}:{tb.lineno}"
    def __repr__(self):
        return f"<{self.__class__.__name__}({self._value}) from {self._origin}>"
    # TODO .set
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
    def __init__(self, value=UNINITIALIZED(), is_event=False):
        super().__init__(is_event=is_event)
        self._value = value
        self._driver = None
        self.set_origin()
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
        super().__init__(is_event=ref.is_event)
        self._ref = ref
        ref.links.add(self)
        self.set_origin()
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
        super().__init__(is_event=False)
        self._function = function
        self._deps = deps
        for ref in deps:
            ref.links.add(self)
        self.set_origin()
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
