_to_update = set()

def tick():
    """Update all reactives based on changes to refs."""
    topo_sort = []
    loud_reachable = set(_to_update)
    for seed in _to_update:
        stack = [seed]
        current_sort = []
        enumerated = set()
        # Where the inner sort will be inserted into the outer sort; the minimum index of all reactives
        insert_point = 0
        while len(stack):
            r = stack.pop()
            topo_i = insert_point
            # Is the reactive already in the outer sort?
            try:
                topo_i = topo_sort.index(r)
            except ValueError:
                # No? Continue down tree, depth-first.
                e = r in enumerated
                if e or len(r.links) + len(r.quiet_links) == 0:
                    if r not in current_sort: current_sort.append(r)
                    if e: enumerated.remove(r)
                    continue
                stack.append(r)
                stack += r.links
                #
                if r in loud_reachable:
                    loud_reachable |= r.links
                stack += r.quiet_links
                enumerated.add(r)
            else:
                # Yes? No need to process it.
                # Move insertion point to before r.
                insert_point = max(topo_i, insert_point)
        topo_sort[insert_point + 1:insert_point + 1] = current_sort

    # Clear the update set before running any external code, so any changes are
    # correctly remembered for next tick.
    _to_update.clear()
    update_order = [r for r in reversed(topo_sort) if r in loud_reachable]
    for r in update_order:
        r.update()
        for f in r._flags: f._value = True
    for r in update_order:
        if r.log:
            print(f"{r.log!r} <- {r.next_value}")
        r.finish_update()

class Reactive:
    """Base class for a reactive value.

    Reactives cover both continuous values and event streams; they are
    distinguished with the `is_event` boolean.

    To create a custom reactive, subclass this and:

    -   call Reactive.setup() at the end of your own initialiser
    -   set self.is_event, self._value
    -   override update() to set self.next_value to the new value

    To make a reactive B depend on another one A, do `A.links.add(B)`. Note that
    to use A's new value, B needs to refer to A.next_value in its update
    method, not A().
    """
    def setup(self):
        self.links = set()
        self.quiet_links = set()
        self._flags = set()
        # We require an initial value because otherwise we'd need a safe
        # .get(default) for uninitialised reactives, and in Python you can't
        # pick default values in type-generic cases. In a language with
        # type-infering `zero` or other default value functions, this may be
        # possible.
        self.log = None
        self._origin = None
    def set_origin(self):
        import inspect
        frame = inspect.currentframe()
        tb = inspect.getframeinfo(frame.f_back.f_back.f_back)
        self._origin = f"{tb.function}:{tb.lineno}"
    def __str__(self):
        name = f"{self.log!r} " if self.log is not None else ""
        origin = f"at {self._origin} " if self._origin is not None else ""
        return f"<{name}{origin}{self.__class__.__name__}: {self._value}>"
    def __call__(self):
        return self._value
    def finish_update(self):
        self._value = self.next_value

def as_ref(x):
    """Turns a value into a reactive, if it isn't already."""
    if isinstance(x, Reactive):
        return x
    return Ref(x)

class Ref(Reactive):
    """Settable input reactive."""
    def __init__(self, value, is_event=False):
        Reactive.setup(self)
        self._value = self.next_value = value
        self.is_event = is_event
        self._driver = None
    def update(self):
        if self._driver:
            self.next_value = self._driver.next_value
    def set(self, x):
        self.next_value = x
        _to_update.add(self)
    def __lshift__(self, r):
        # We can have circularity in reference to reactives even without circularity in deps (pull sampling).
        if self.is_event != r.is_event:
            raise ValueError()
        if self._driver:
            self._driver.links.remove(self)
        self._driver = r
        self._driver.links.add(self)

ref = Ref

class read_only(Reactive):
    def __init__(self, ref):
        Reactive.setup(self)
        self._value = self.next_value = ref()
        self.is_event = ref.is_event
        self._ref = ref
        ref.links.add(self)
    def update(self):
        self.next_value = self._ref.next_value

def computed(*args):
    """Reactive function."""
    def builder(f):
        return Computed(f, *args)
    return builder

# we could still do auto-detecting dependencies, we'd just have to swap out () to next value during execution. it that safe?
class Computed(Reactive):
    def __init__(self, function, deps, *, is_event=False, data=None):
        self._function = function
        self._deps = deps
        self._data = data
        for ref in deps:
            ref.links.add(self)
        Reactive.setup(self)
        self._cached = self._cached_next = (True, None)
        self.is_event = False
    def update(self):
        self._cached_next = (True, None)
    def finish_update(self):
        self._cached = self._cached_next
    def __call__(self):
        if self._cached[0]:
            args = [r() for r in self._deps]
            if self._data is not None:
                args.append(self._data)
            self._cached = (False, self._function(*args))
        return self._cached[1]
    @property
    def next_value(self):
        if self._cached_next[0]:
            args = [r.next_value for r in self._deps]
            if self._data is not None:
                args.append(self._data)
            self._cached_next = (False, self._function(*args))
        return self._cached_next[1]

class gate(Reactive):
    def __init__(self, open, reactive):
        self._open = open
        self._open.links.add(self)
        self._reactive = reactive
        if self._open():
            self._reactive.links.add(self)
        Reactive.setup(self)
        self._value = self.next_value = reactive() if open() else None
        self.is_event = reactive.is_event
    def update(self):
        if self._open():
            self._reactive.links.add(self)
            self.next_value = self._reactive.next_value
        else:
            self._reactive.links.remove(self)

def gate_context(ctx, open, keys):
    return ctx.add({key: gate(open, ctx[key]) for key in keys})

class Flag:
    def __init__(self, reactive):
        reactive._flags.add(self)
        self._value = False
    def pop(self):
        value = self._value
        self._value = False
        return value

class sample(Reactive):
    def __init__(self, reactive, event):
        self._reactive = reactive
        self._event = event
        self._event.links.add(self)
        Reactive.setup(self)
        self._value = self.next_value = self._reactive()
        self.is_event = False
    def update(self):
        self.next_value = self._reactive()

class Reducer(Reactive):
    def __init__(self, initial):
        self.processors = []
        Reactive.setup(self)
        self._value = self.next_value = initial
        self.is_event = True
    def reduce(self, event, deps=[]):
        if not event.is_event:
            raise ValueError("first argument to reduce must be an event")
        event.links.add(self)
        for r in deps:
            r.quiet_links.add(self)
        def wrap(f):
            self.processors.append([event, deps, f])
        return wrap
    def update(self):
        for event, deps, reducer in self.processors:
            if event.next_value is not None:
                self.next_value = reducer(self.next_value, event.next_value, *[d.next_value for d in deps])

class process_event(Reactive):
    def __init__(self, f, event, state):
        self._f = f
        self._event = event
        self._event.links.add(self)
        self._state = state
        Reactive.setup(self)
        self._value = self.next_value = self._state
        self.is_event = True
    def update(self):
        if self._event.next_value is not None:
            self._state, self.next_value = self._f(self._state, self._event.next_value)

def reduce_event(f, event, init):
    def reduce(a, e):
        x = f(a, e)
        return x, x
    return process_event(reduce, event, init)

class Active: pass

class Context:
    def __init__(self, data):
        self._data = data
    @classmethod
    def initial(cls):
        return cls({
            Active: Ref(True),
        })
    def add(self, extra):
        return Context(self._data | extra)
    def __getitem__(self, k):
        return self._data[k]

class process_sample_unsafe(Reactive):
    def __init__(self, reduce, time, state):
        self._reduce = reduce
        self._time = time
        self._time.links.add(self)
        self._state = state
        Reactive.setup(self)
        self._value = self.next_value = self._state
        self.is_event = False
    def update(self):
        self._state, self.next_value = self._reduce(self._state, self._time.next_value - self._time())

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
