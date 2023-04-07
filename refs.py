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

class ReadableReactive:
    def __init__(self):
        self._watchers = set()
    def __call__(self):
        if _current_tracker is not None: _current_tracker.add(self)
        return self.getter()
    def Watch(self, f):
        return _Watch(self, f)
    def watch(self, f):
        self._watchers.add(f)
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
        self._function = function
        if deps is None:
            deps = set()
            with _track_into(deps):
                self._value = function()
            self._expired = False
            self._dep_watchers = [ref.Watch(self.touch) for ref in deps]
        else:
            self._expired = True
        super().__init__()
    def touch(self):
        self._expired = True
        super().touch()
    def do(self):
        self.touch()
        for e in self._dep_watchers: e.do()
    def undo(self):
        for e in self._dep_watchers: e.undo()
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

class Effect:
    pass

@dataclass
class _Watch:
    ref: Ref
    f: Callable
    def do(self):
        self.ref._watchers.add(self.f)
    def undo(self):
        self.ref._watchers.remove(self.f)

@dataclass
class Sequence:
    # ctx: dict
    effects: list
    def do(self):
        for e in self.effects: e.do()
    def undo(self):
        for e in self.effects: e.undo()

@dataclass
class Nothing:
    def do(self):
        pass
    def undo(self):
        pass

@dataclass
class _EffectRef:
    ref: Ref
    def _redo(self):
        self.undo()
        self.do()
    def do(self):
        self._effect = self.ref()
        self._effect.do()
    def undo(self):
        self._effect.undo()

def EffectRef(ref):
    er = _EffectRef(ref)
    return Sequence([er, ref.Watch(er._redo)])

def If(ref, e):
    t = computed()(lambda: e if ref() else Nothing())
    return Sequence([t, EffectRef(t)])
