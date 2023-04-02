from contextlib import contextmanager

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

class ReadableReactive:
    def __init__(self):
        self._watchers = []
    def __call__(self):
        if _current_tracker is not None: _current_tracker.add(self)
        return self.getter()
    def watch(self, f):
        self._watchers.append(f)
        return f
    def touch(self):
        for w in self._watchers: w()
    def quiet_get(self):
        return self.getter()

class Reactive(ReadableReactive):
    def set(self, x):
        self.setter(x, self.touch)
    def quiet_set(self, x):
        self.setter(x, lambda: None)
    def map(self, f):
        self.set(f(self()))

def as_ref(x):
    if isinstance(x, ReadableReactive):
        return x
    return Ref(x)

class Ref(Reactive):
    def __init__(self, value):
        self._value = value
        super().__init__()
    def getter(self):
        return self._value
    def setter(self, x, touch):
        self._value = x
        touch()

class read_only(ReadableReactive):
    def __init__(self, ref):
        self._ref = ref
        self._ref.watch(self.touch)
        super().__init__()
    def getter(self):
        # Don't call ref; we don't want to pick it up in a computed.
        return self._ref._value

class DataRef(Ref):
    def set(self, x):
        if x == self._value:
            return
        super().set(x)

def computed(*args):
    def builder(f):
        return Computed(f, *args)
    return builder

def writeable_computed(*args):
    def builder(f):
        return WriteableComputed(f, *args)
    return builder

class Computed(ReadableReactive):
    def __init__(self, function, deps=None):
        if deps is None:
            deps = set()
            with _track_into(deps):
                self._value = function()
        else:
            self._value = function()
        for ref in deps:
            ref.watch(self.touch)
        self._expired = False
        self._function = function
        super().__init__()
    def touch(self):
        self._expired = True
        super().touch()
    def getter(self):
        if self._expired:
            # Do not track when updating to avoid picking up transitive deps.
            with _track_into(None):
                self._value = self._function()
            self._expired = False
        return self._value

class WriteableComputed(Computed, Reactive):
    def on_set(self, f):
        self._on_set = f
        return f
    def setter(self, value, touch):
        self._on_set(value)
        touch()
