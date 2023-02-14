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

class _ReadableRef:
    def __call__(self, *args):
        if _current_tracker is not None: _current_tracker.add(self)
        if not args: return self._value
        v = self._value
        for i in args: v = v[i]
        return v
    def watch(self, f):
        self._watchers.append(f)
        return f
    def quiet_get(self):
        return self._value

class _WriteableRef:
    def set(self, x):
        self._value = x
        for w in self._watchers: w()
    def map(self, f):
        self.set(f(self()))

def as_ref(x):
    if isinstance(x, _ReadableRef):
        return x
    return Ref(x)

class Ref(_ReadableRef, _WriteableRef):
    def __init__(self, value):
        self._value = value
        self._watchers = []

class DataRef(Ref):
    def set(self, x):
        if x == self._value:
            return
        super().set(x)

def computed(*args):
    def builder(f):
        return Computed(f, *args)
    return builder

class Computed(_ReadableRef):
    def __init__(self, function, deps=None):
        if deps is None:
            deps = set()
            with _track_into(deps):
                self._value = function()
        else:
            self._value = function()
        for ref in deps:
            ref.watch(self._expire)
        self._expired = False
        self._function = function
        self._watchers = []
    def _expire(self):
        self._expired = True
        for w in self._watchers: w()
    def __call__(self, *args):
        if self._expired:
            # Do not track when updating to avoid picking up transitive deps.
            with _track_into(None):
                self._value = self._function()
            self._expired = False
        return super().__call__(*args)

class WriteableComputed(Computed, _WriteableRef):
    def setter(self, f):
        self._set_transform = f
        return f
    def set(self, value):
        return super().set(self._set_transform(value))
