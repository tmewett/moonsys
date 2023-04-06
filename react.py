from functools import cache
from inspect import signature

class Component:
    def __init__(self, *a, **kw):
        self.set_props(*a, **kw)
    def set_props(self, *a, **kw):
        # self.__class__._define_props(*a, **kw)
        # TODO empty kw to _define_props don't show up
        if hasattr(self, 'props'):
            self._last_props = self.props
        self.props = signature(self.__class__._define_props).bind(*a, **kw).arguments
    def do(self):
        pass
    def should_refresh(self):
        return (
            not hasattr(self, '_last_props')
            or set(self.props.keys()) != set(self._last_props.keys())
            or any(self.props[p] is not self._last_props[p] for p in self.props.keys())
        )
    def refresh(self):
        if self.should_refresh():
            self.on_refresh()
    def on_refresh(self):
        self.undo()
        self.do()
    def undo(self):
        pass

class Debug(Component):
    def set_props(self, **props):
        self.props = props
    def do(self):
        print(f"     do {id(self)} props={self.props}")
    def on_refresh(self):
        print(f"refresh {id(self)} props={self.props}")
    def undo(self):
        print(f"   undo {id(self)} props={self.props}")

class DelegatedComponent(Component):
    def do(self):
        self._slots = []
        self._slot_i = None
        self._delegate = self.get_children()
        self._delegate.parent = self
        self._delegate.do()
    def on_refresh(self):
        self._slot_i = 0
        new = self.get_children()
        if isinstance(new, type(self._delegate)):
            self._delegate.props = new.props
            self._delegate.refresh()
        else:
            self._delegate.undo()
            self._delegate = new
            self._delegate.parent = self
            self._delegate.do()
    def undo(self):
        self._delegate.undo()
        for h in reversed(self._slots):
            h.undo()
    def use(self, c, *a, **kw):
        # There's so much *a, **kw stuff in the hooks parts because we are
        # trying to ergonomically override an callable's argument. We could have
        # `props={.} then=.` but that would be less neat.
        if 'then' in kw:
            raise ArgumentError()
        value = None
        def set_value(x):
            nonlocal value
            value = x
        if self._slot_i is None:
            self._slots.append(c(*a, then=set_value, **kw))
            self._slots[-1].do()
            return value
        else:
            old = self._slots[self._slot_i]
            if not issubclass(c, type(old)):
                raise RuntimeError("different component type given to corresponding use() in last run")
            old.set_props(*a, then=set_value, **kw)
            old.refresh()
            self._slot_i += 1
            return value

class Sequence(Component):
    def _define_props(components):
        pass
    def do(self):
        self._last = self.props['components'][:]
        for c in self.props['components']: c.do()
    def on_refresh(self):
        unmounting = False
        for (old, new), i in enumerate(zip(self._last, self.props['components'])):
            if not isinstance(new, type(old)):
                # -1 so i is the index of the last of same type.
                i -= 1
                break
            old.props = new.props
            old.refresh()
        for c in reversed(self._last[i+1:]):
            c.undo()
        for c in self.props['components'][i+1:]:
            c.parent = self
            c.do()
        self._last = self.props['components'][:]
    def undo(self):
        for c in self.props['components']: c.undo()

class Defer(DelegatedComponent):
    def _define_props(f):
        pass
    def get_children(self):
        return self.props['f']()

class _WithBase(DelegatedComponent):
    def _define_props(*a, then, **kw):
        pass
    def get_children(self):
        if 'a' not in self.props:
            self.props['a'] = []
        if 'kw' not in self.props:
            self.props['kw'] = {}
        value = self.use(self.__class__._hook, *self.props['a'], **self.props['kw'])
        return self.props['then'](value)

@cache
def With(cls):
    return type(f"With({cls.__name__})", (_WithBase,), {'_hook': cls})

class Memo(Component):
    def _define_props(f, deps=None, *, then):
        pass
    def do(self):
        if not hasattr(self, '_last_deps') or (self.props['deps'] is not None and self._last_deps != self.props['deps']):
            self._last_deps = self.props['deps']
            self._value = self.props['f']()
        self.props['then'](self._value)

class Provider(DelegatedComponent):
    def _define_props(key, value, children):
        pass
    def get_children(self):
        return self.props['children']

def _find_provider(key, c):
    if isinstance(c, Provider) and c.props['key'] == key:
        return c.props['value']
    else:
        return _find_provider(key, c.parent)

class Context(Component):
    def _define_props(key, *, default=None):
        pass
    def get_value(self):
        return _find_provider(self.props['key'], self.parent)

class Ref:
    def __init__(self, value, element):
        self._value = value
        self._element = element
    def __call__(self):
        return self._value
    def set(self, x):
        self._value = x
        self._element.refresh()

# TODO No, each f needs to be different class.
class FunctionComponent(DelegatedComponent):
    _current = None
    def __init__(self, f, *a, **kw):
        self._function = f
        super().__init__(*a, **kw)
    def set_props(self, *a, **kw):
        self.props = signature(self._function).bind(*a, **kw).arguments
    def get_children(self):
        FunctionComponent._current = self
        c = self._function(**self.props)
        FunctionComponent._current = None
        return c

def component(f):
    return lambda *a, **kw: FunctionComponent(f, *a, **kw)

def use(*a, **kw):
    return FunctionComponent._current.use(*a, **kw)

@component
def func(n):
    return With(Memo)(lambda: n*2, [n], then=lambda nn: Debug(n=nn))

f = func(n=1)
f.do()
f.props['n'] = 1
f.refresh()
f.props['n'] = 2
f.refresh()
f.undo()
