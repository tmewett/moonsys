_to_update = set()
_to_reset = set()

def tick():
    """Update all reactives based on changes to refs."""
    topo_sort = []
    quiet_seeds = set()
    for seed in _to_update:
        stack = [seed]
        current_sort = []
        # Where the inner sort will be inserted into the outer sort; the minimum index of all reactives
        insert_point = len(topo_sort)
        while len(stack):
            r = stack.pop()
            topo_i = insert_point
            # Is the reactive already in the outer sort?
            try:
                topo_i = topo_sort.index(r)
            except ValueError:
                # No? Continue down tree, depth-first.
                current_sort.append(r)
                stack += r.links
            # Yes? No need to process it.
            quiet_seeds.update(r.quiet_links)
            # Move insertion point to before r.
            insert_point = min(topo_i, insert_point)
        # Repeat for quiet links.
        stack = list(quiet_seeds)
        while len(stack):
            r = stack.pop()
            topo_i = insert_point
            try:
                topo_i = topo_sort.index(r)
            except ValueError:
                stack += r.links
                stack += r.quiet_links
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
    """Base class for a reactive value.

    Reactives cover both continuous values and event streams; they are
    distinguished with the `is_event` boolean.

    To create a custom reactive, subclass this and:

    -   call its __init__ at the end of your own initialiser
    -   override update() to set self._next_value to the new value

    To make a reactive B depend on another one A, do `A.links.add(B)`. Note that
    to use A's new value, B needs to refer to A._next_value in its update
    method, not A().
    """
    def __init__(self, initial_value, *, is_event):
        self.links = set()
        self.quiet_links = set()
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
    """Turns a value into a reactive, if it isn't already."""
    if isinstance(x, ReadableReactive):
        return x
    return Ref(x)

class Ref(Reactive):
    """Settable input reactive."""
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
    """Reactive function."""
    def builder(f):
        return Computed(f, *args)
    return builder

# we could still do auto-detecting dependencies, we'd just have to swap out () to next value during execution. it that safe?
class Computed(ReadableReactive):
    def __init__(self, function, deps, *, is_event=False, data=None):
        self._function = function
        self._deps = deps
        self._data = data
        for ref in deps:
            ref.links.add(self)
        super().__init__(self._get_next_value(), is_event=False)
    def update(self):
        self._next_value = self._get_next_value()
    def _get_next_value(self):
        if self._data is not None:
            return self._function(*[r._next_value for r in self._deps], self._data)
        return self._function(*[r._next_value for r in self._deps])

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

def gate_context(ctx, open, keys):
    return ctx | {key: gate(open, ctx[key]) for key in keys}

class Flag:
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

class Reducer(ReadableReactive):
    def __init__(self, initial):
        self.processors = []
        super().__init__(initial, is_event=False)
    def reduce(self, event, deps=[]):
        event.links.add(self)
        for r in deps:
            r.quiet_links.add(self)
        def wrap(f):
            self.processors.append([event, deps, f])
        return wrap
    def update(self):
        for event, deps, reducer in self.processors:
            if event._next_value is not None:
                self._next_value = reducer(self._next_value, event._next_value, *[d._next_value for d in deps])

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

def integrate(r, time, initial=0.0):
    def f(total, dt):
        # The new total integral is the previous one plus the last value of r
        # over the duration.
        new_total = total + r() * dt
        return new_total
    return reduce_sample_unsafe(f, time, initial)

# TODO not rate-independent?
def toggle(r, initial=False):
    @computed([r], data={'last': r(), 'out': initial})
    def toggle(r, data):
        if r() != data['last']:
            data['out'] = not data['out']
        return data['out']
    return toggle

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
