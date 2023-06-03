import pyglet
from pyglet.math import Vec2

import refs
import refs_gl
from refs import ref, computed, ReadableReactive

def sample_reduce(f, t, s):
    out = ref(None)
    tp = t()
    @refs.global_time._watch
    def _():
        nonlocal tp, s
        v, s = f(t(), s)
        out.set(v)
    return out

# this is hold . reduce_event . changes ? LOL
class sample_reduce(ReadableReactive):
    def __init__(self, reduce, time, state):
        self._reduce = reduce
        self._time = time
        self._time.links.add(self)
        self._state = state
        super().__init__(self._reduce(0.0, self._state), is_event=False)
    def update(self):
        self._next_value, self._state = self._reduce(self._time._next_value - self._time(), self._state)

# Problem with this: r can only be sampled at the current global time, so time input isn't really meaningful
def integrate(r, time, offset=0.0):
    def f(dt, total):
        # The new total integral is the previous one plus the last value of r
        # over the duration.
        new_total = total + r() * dt
        return new_total, new_total
    return sample_reduce(f, time, offset)
    #     r_prev, total = state
    #     # The new total integral is the previous one plus the last value of r
    #     # over the duration.
    #     new_total = total + r_prev * dt
    #     return new_total, (r(), new_total)
    # return sample_reduce(f, time, (r(), offset))

def setup(on, ctx):
    # The left paddle initial position.
    l_paddle_pos = ref(Vec2(50, 200))
    r_paddle_pos = ref(Vec2(550, 200))
    # Declaratively define its velocity with a computed; it's automatically
    # updated when its dependencies change.
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
    # Set the position to be the integral of the velocity over time, starting at
    # the initial position. (The `<<` operator continuously "drives" the left ref
    # with the values from the right one.)
    l_paddle_pos << integrate(l_paddle_vel, ctx[refs_gl.FrameTime], l_paddle_pos())

    # ball1_pos = ref()
    # @computed_event()
    # def bounce():
    #     pos = ball1_pos()
    #     if pos >= 1.0:
    #         return -1.0
    #     if pos <= 0.0:
    #         return 1.0
    # ball1_vel = bounce.value
    # ball1_pos << integrate(ball1_vel, 5.0)

    batch = pyglet.graphics.Batch()
    paddle_dims = Vec2(10, 50)
    l_paddle_obj = pyglet.shapes.Rectangle(0, 0, paddle_dims.x, paddle_dims.y, color=(255, 255, 255), batch=batch)
    r_paddle_obj = pyglet.shapes.Rectangle(0, 0, paddle_dims.x, paddle_dims.y, color=(255, 255, 255), batch=batch)
    ball_obj = pyglet.shapes.Rectangle(0, 0, 20, 20, color=(255, 255, 255), batch=batch)
    def draw():
        l_paddle_obj.x, l_paddle_obj.y = l_paddle_pos()
        r_paddle_obj.x, r_paddle_obj.y = r_paddle_pos()
        refs_gl.clear()
        batch.draw()
    ctx[refs_gl.Draws].add(on, draw)

refs_gl.define_window(setup)
pyglet.app.run()
