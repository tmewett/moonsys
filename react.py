from inspect import signature

class Component:
    def __init__(self, *a, **kw):
        self.set_props(*a, **kw)
    def set_props(self, *a, **kw):
        # self.__class__._define_props(*a, **kw)
        self.props = signature(self.__class__._define_props).bind(*a, **kw).arguments
    def do(self):
        pass
    def refresh(self):
        self.undo()
        self.do()
    def undo(self):
        pass

class Debug(Component):
    def set_props(self, **props):
        self.props = props
    def do(self):
        print(f"     do {id(self)} props={self.props}")
    def refresh(self):
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
    def refresh(self):
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
    def use(self, c, **props):
        if self._slot_i is None:
            self._slots.append(c(**props))
            self._slots[-1].do()
            return self._slots[-1].get_value()
        else:
            old = self._slots[self._slot_i]
            if not issubclass(c, type(old)):
                raise RuntimeError()
            old.props = props
            old.refresh()
            self._slot_i += 1
            return old.get_value()

class With(DelegatedComponent):
    def _define_props(component, then):
        pass
    def do(self):
        self._component = self.props['component']
        self._component.do()
        super().do()
    def refresh(self):
        new = self.props['component']
        if isinstance(new, type(self._component)):
            self._component.props = new.props
            self._component.refresh()
        else:
            self._component.undo()
            new.do()
            self._component = new
        super().refresh()
    def undo(self):
        super().undo()
        self._component.undo()
    def get_children(self):
        return self.props['then'](self._component.get_value())

class Memo(Component):
    def _define_props(f, deps=None):
        pass
    def do(self):
        self._last_deps = self.props['deps']
        self._value = self.props['f']()
    # TODO refresh
    def get_value(self):
        if self.props['deps'] is not None and self._last_deps != self.props['deps']:
            self._last_deps = self.props['deps']
            self._value = self.props['f']()
            print("reran memo")
        return self._value

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

def use(c, **props):
    return FunctionComponent._current.use(c, **props)

@component
def func(n):
    nn = use(Memo, f=lambda: n*2, deps=[n])
    return Debug(n=nn)

f = func(n=1)
f.do()
f.props['n'] = 1
f.refresh()
f.props['n'] = 2
f.refresh()
f.undo()
