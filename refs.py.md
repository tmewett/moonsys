# refs.py

refs.py is a work-in-progress FRP library for Python.

As far as I can tell, no reactivity library outside of functional languages implements a model of reactivity more powerful than observables with batching. I discuss this in [Real reactivity has never been tried (FRP vs observables)](https://tmewett.com/limitations-of-observables/). refs.py aims to implement more, namely:

-   safe stateful reactives, like integrals
-   cycles/feedback
-   reactive events, safely separated from continuous value refs
-   two-way data flow: reactives which dynamically "collect" values from "children"

This is a core API overview; TODO write:

-   how to use a refs.py-based library
-   how to write a refs.py-based library

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

A Ref can be "driven" by another reactive: `ref << reactive` causes `ref` to mirror `reactive`'s value. This can be used to basically "declare" a Ref early: you create one with a default value, create other reactives using it, then set its actual value. You can create certain kinds of cycles e.g. with `integrate`.

`tick()` causes all changed reactives to update.

`@computed` creates derived values. They aren't settable with `.set`. Pass the dependencies in an array to the decorator; the values are passed in that order to the decorated function.

    from refs import computed

    @computed([x])
    def squared(x):
        return x * x

    # or squared = computed([x])(lambda x: x * x)

    print(squared())  # 9

computeds **must** be pure functions (no side-effects).

You can refer to any other reactive in a computed, without depending on it, by calling it as usual. This allows you to create cycles.

## Events and reducers

Reactives can also be classified as events. Typical reactivity libraries don't properly support events, leaving that to your external, non-reactive code. Reactive events allow us to encapsulate and compose entire components, just like Web frameworks, but even more flexible.

`Ref` takes a keyword argument `is_event` which defaults to `False`. When set to `True`, the ref's values are considered to be a stream of discrete events. Events can be used anywhere non-events can (they evaluate to the most recent event value), but can also be used in some extra, powerful reactives.

The main one is `Reducer`. This lets you write fully reactive code in a natural way, just like you'd write with event handlers.

    # Calculate blackjack hand score, given a stream of card score events.

    card_scores = Ref(0, is_event=True)
    hand_score = Reducer(0)

    @hand_score.reduce(card_scores)
    def _(prev, card_score):
        if prev + card_score > 21:
            return 0
        return prev + card_score

You can add multiple reduce methods, from multiple events, onto one Reducer. Where multiple input events trigger on the same tick, the methods run in the order they are added.

Reducers are events themselves.

## Gatherers

TODO

## Misc

`sample(r, event)` updates with `r`'s value every time `event` triggers.

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
