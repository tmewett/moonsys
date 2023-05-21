from functools import cache
from inspect import signature

class Component:
    def __init__(self, *a, **kw):
        self.set_props(*a, **kw)
    def set_props(self, *a, **kw):
        """Set props based on values given to constructor.

        You may override this method and set self.props as you require. Default
        implementation assigns props based on the signature of a static method
        _define_props.
        """
        # self.__class__._define_props(*a, **kw)
        # TODO empty kw to _define_props don't show up
        self.props = signature(self.__class__._define_props).bind(*a, **kw).arguments
    def on_activate(self):
        pass
    def on_refresh(self):
        self.deactivate()
        self.activate()
    def on_deactivate(self):
        pass
    # TODO manage transitions
    def activate(self):
        self.on_activate()
    def deactivate(self):
        self.on_deactivate()
    def refresh(self):
        self.on_refresh()

class Debug(Component):
    def set_props(self, **props):
        self.props = props
    def on_activate(self):
        print(f"     do {id(self)} props={self.props}")
    def on_refresh(self):
        print(f"refresh {id(self)} props={self.props}")
    def on_deactivate(self):
        print(f"   undo {id(self)} props={self.props}")

class DelegatedComponent(Component):
    """Base class to manage another Component dynamically.

    To use, subclass this and define get_children to return a Component.
    Whenever your class is refreshed, get_children will be called and the
    resulting Component compared with the previous one. If it's of the same
    type, the new props will be copied into the old instance and the old
    instance refreshed. If not, the old one will be undone and the new one done
    in its place.
    """
    def on_activate(self):
        self._slots = []
        self._slot_i = None
        self._delegate = self.get_children()
        self._delegate.parent = self
        self._delegate.activate()
    def on_refresh(self):
        self._slot_i = 0
        new = self.get_children()
        if isinstance(new, type(self._delegate)):
            self._delegate.props = new.props
            self._delegate.refresh()
        else:
            self._delegate.deactivate()
            self._delegate = new
            self._delegate.parent = self
            self._delegate.activate()
    def on_deactivate(self):
        self._delegate.deactivate()
        for h in reversed(self._slots):
            h.deactivate()
    def use(self, c, *a, **kw):
        """Activate a Component and use its called-back value.

        Let c be an instance of a Component with a 'then' prop, which is a
        function called by c after it is activated. (Think of this like c
        creating a resource then passing it to its 'then' callback.) Calling
        self.use(c, ...) within get_children() will activate or refresh c as
        necessary and return the value it passes to its 'then' prop.
        """
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
            self._slots[-1].activate()
            return value
        else:
            old = self._slots[self._slot_i]
            if not issubclass(c, type(old)):
                raise RuntimeError()
            old.set_props(*a, then=set_value, **kw)
            old.refresh()
            self._slot_i += 1
            return value

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
    """Do a child tree of components with the result of a Component's callback.

    Let C be a Component with a 'then' prop, which is a function called by C
    after it is activated. (Think of this like C creating a resource then
    passing it to its 'then' callback.) With(C) is a Component which accepts the
    same props as C, except for its 'then', which is passed the same value(s) as
    C's but which returns a Component that is activated along with With(C).
    """
    return type(f"With({cls.__name__})", (_WithBase,), {'_hook': cls})

class Memo(Component):
    def _define_props(f, deps=None, *, then):
        pass
    def on_activate(self):
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

# TODO No, each f needs to be different class, like With.
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
f.activate()
f.props['n'] = 1
f.refresh()
f.props['n'] = 2
f.refresh()
f.deactivate()
