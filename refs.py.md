# refs.py

refs.py is an FRP library for Python.

## Basics

`Ref(value)` creates a reactive variable. It is callable; when called it returns the current value.

Call `.set(new_value)` to change it. Changes only propagate after calling `tick`:

    from refs import Ref, tick

    x = Ref(2)
    print(x())  # 2
    x.set(3)
    print(x())  # 2
    tick()
    print(x())  # 3

A Ref can be "driven" by another reactive: `ref << reactive` causes `ref` to mirror `reactive`'s value. This can be used to basically "declare" a Ref early: you create one with a default value, do things with it, then set its actual value. You can create certain kinds of cycles e.g. with `integrate`.

`tick()` causes all changed reactives to update.

`@computed` creates derived values. They aren't settable with `.set`. Pass the dependencies in an array to the decorator; the values are passed in that order to the decorated function.

    from refs import computed

    @computed([x])
    def squared(x):
        return x * x

    # or squared = computed([x])(lambda x: x * x)

    print(squared())  # 9

## Events

Reactives can also be classified as events.

`Ref` takes a keyword argument `is_event` which defaults to `False`. When set to `True`, the ref's values are considered to be discrete events. You call `.set` on them like normal; but after the next tick, they are set back to `None`. They are essentially values which last for one tick only.

You can use event reactives in computeds.

## Changes

You can't subscribe to reactives, so other types of reactives exist to deal with changes.

`sample(r, event)` updates with `r`'s value every time `event` triggers.

`reduce_event(f, event, initial)` starts as `initial` and updates with values from `event` by a reduction/fold with `f`.

`integrate(r, time, initial=0.0)` is the live integral of `r` with respect to `time`, starting at `initial`. `time` must be a reactive float which never decreases. Note: this reactive does not depend on `r`, so `r` can be recursively defined with its own integral:

    l_paddle_pos = ref(Vec2(50, 200))
    @computed([
        ctx[refs_gl.KeyMap]['UP'],
        ctx[refs_gl.KeyMap]['DOWN'],
        l_paddle_pos,
    ])
    def l_paddle_vel(up, down, pos):
        if up and pos.y < 450:
            return Vec2(0, 200)
        if down and pos.y > 50:
            return Vec2(0, -200)
        return Vec2(0, 0)
    l_paddle_pos << integrate(l_paddle_vel, ctx[refs_gl.FrameTime], l_paddle_pos())

`gate(open, r)` only updates with `r`'s value while `open` is `True`.
