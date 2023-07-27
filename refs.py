_to_update = set()
_to_reset = set()

def tick():
    topo_sort = []
    for seed in _to_update:
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
        for f in r._flags: f._value = True
    for r in topo_sort:
        if r.log:
            print(f"{r.log}: {r._value} <- {r._next_value}")
        r._value = r._next_value
    for r in _to_reset:
        r.set(None)
    _to_reset.clear()

class ReadableReactive:
    def __init__(self, initial_value, *, is_event):
        self.links = set()
        self._flags = set()
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
        return self._value

class Reactive(ReadableReactive):
    def set(self, x):
        self.setter(x)
        _to_update.add(self)

def as_ref(x):
    if isinstance(x, ReadableReactive):
        return x
    return Ref(x)

class Ref(Reactive):
    def __init__(self, value, is_event=False):
        super().__init__(value, is_event=is_event)
        self._driver = None
    def update(self):
        if self._driver:
            self._next_value = self._driver._next_value
    def setter(self, x):
        self._next_value = x
        if self.is_event and x is not None:
            _to_reset.add(self)
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

# we could still do auto-detecting dependencies, we'd just have to swap out () to next value during execution. it that safe?
class Computed(ReadableReactive):
    def __init__(self, function, deps):
        self._function = function
        self._deps = deps
        for ref in deps:
            ref.links.add(self)
        super().__init__(self._function(*[r._next_value for r in self._deps]), is_event=False)
    def update(self):
        self._next_value = self._function(*[r._next_value for r in self._deps])

class gate(ReadableReactive):
    def __init__(self, open, reactive):
        self._open = open
        self._open.links.add(self)
        self._reactive = reactive
        if self._open():
            self._reactive.links.add(self)
        super().__init__(reactive() if open() else None, is_event=reactive.is_event)
    def update(self):
        if self._open():
            self._reactive.links.add(self)
            self._next_value = self._reactive._next_value
        else:
            self._reactive.links.remove(self)

class flag:
    def __init__(self, reactive):
        reactive._flags.add(self)
        self._value = False
    def pop(self):
        value = self._value
        self._value = False
        return value

class sample(ReadableReactive):
    def __init__(self, reactive, event):
        self._reactive = reactive
        self._event = event
        self._event.links.add(self)
        super().__init__(self._reactive(), is_event=False)
    def update(self):
        self._next_value = self._reactive()

class process_event(ReadableReactive):
    def __init__(self, f, event, state):
        self._f = f
        self._event = event
        self._event.links.add(self)
        self._state = state
        super().__init__(self._state, is_event=False)
    def update(self):
        if self._event._next_value is not None:
            self._state, self._next_value = self._f(self._state, self._event._next_value)

def reduce_event(f, event, init):
    def reduce(a, e):
        x = f(a, e)
        return x, x
    return process_event(reduce, event, init)

class process_sample_unsafe(ReadableReactive):
    def __init__(self, reduce, time, state):
        self._reduce = reduce
        self._time = time
        self._time.links.add(self)
        self._state = state
        super().__init__(self._state, is_event=False)
    def update(self):
        self._state, self._next_value = self._reduce(self._state, self._time._next_value - self._time())

def reduce_sample_unsafe(f, time, init):
    def reduce(a, e):
        x = f(a, e)
        return x, x
    return process_sample_unsafe(reduce, time, init)

def integrate(r, time, offset=0.0):
    def f(total, dt):
        # The new total integral is the previous one plus the last value of r
        # over the duration.
        new_total = total + r() * dt
        return new_total
    return reduce_sample_unsafe(f, time, offset)

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
