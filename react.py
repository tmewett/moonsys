class Component:
    def __init__(self, **props):
        self.props = props
    def set_props(self):
        pass
    def refresh(self):
        pass

class Debug(Component):
    def do(self):
        print(f"  do {id(self)} props={self.props}")
    def undo(self):
        print(f"undo {id(self)} props={self.props}")

class DelegatedComponent(Component):
    def do(self):
        self.setup()
        self._slots = []
        self._slot_i = None
        self._delegate = self.get_children()
        self._delegate.do()
    def refresh(self):
        self._slot_i = 0
        new = self.get_children()
        if isinstance(new, type(self._delegate)):
            self._delegate.props = new.props
            self._delegate.refresh()
        else:
            self._delegate.undo()
            new.do()
            self._delegate = new
    def undo(self):
        self._delegate.undo()
        for h in reversed(self._slots):
            h.undo()
    def use(self, c, **props):
        def get_value(x):
            nonlocal value
            value = x
        use_props = props | {'then': get_value}
        if self._slot_i is None:
            self._slots.append(c(**use_props))
            self._slots[-1].do()
            return value
        else:
            old = self._slots[self._slot_i]
            if not issubclass(c, type(old)):
                raise RuntimeError()
            old.props = use_props
            old.refresh()
            self._slot_i += 1
        return value

class Memo(DelegatedComponent):
    def do(self):
        self._last_deps = None
        self._value = None
        super().do()
    def get_children(self):
        if self._last_deps != self.props['deps']:
            self._value = self.props['f']()
        return self.props['then'](self._value)

def use_memo(f, deps):
    if len(_current_component._slots) == _current_component._next_key:
        store = {'value':None, 'deps':None}
        _current_component._slots.append(store)
    else:
        store = _current_component._slots[_current_component._next_key]
    _current_component._next_key += 1
    if deps is None or deps != store['deps']:
        store['value'] = f()
        store['deps'] = deps
    return store['value']

class Ref:
    def __init__(self, value, element):
        self._value = value
        self._element = element
    def __call__(self):
        return self._value
    def set(self, x):
        self._value = x
        self._element.refresh()

def use_state(initial):
    return use_memo(lambda: Ref(initial, _current_component))

class FunctionComponent(DelegatedComponent):
    _current = None
    def __init__(self, f, props):
        super().__init__(**props)
        self._function = f
    def get_children(self):
        FunctionComponent._current = self
        c = self._function(**self.props)
        FunctionComponent._current = None
        return c

def component(f):
    return lambda **props: FunctionComponent(f, props)

def use(c, **props):
    return FunctionComponent._current.use(c, **props)

@component
def func(id):
    return Debug(id=id)

f = func(id=1)
f.do()
f.props['id'] = 2
f.refresh()
f.undo()
