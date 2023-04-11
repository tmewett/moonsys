import math
from dataclasses import dataclass, field
from collections import defaultdict
from functools import partial
from time import time
from typing import Callable

import pyglet
from pyglet.gl import Config
from pyglet.math import Vec2

from refs import as_ref, computed, DataRef, Ref, read_only, writeable_computed, effect

def clear(*, color, depth):
    from pyglet.gl import glClear, glClearColor, glClearDepth, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
    glClearColor(*color)
    glClearDepth(depth)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

# TODO Rewrite as a custom Reactive to see if WriteableComputed adds anything.
def tween(active, ctx, target, duration=0.1, curve=lambda t: t**0.7):
    start = target()
    start_time = 0.0
    # Only depend on frame time - the target change watcher needs to run
    # first. (But I tried without and it worked?)
    @writeable_computed({ctx[FrameTime]})
    def tweened():
        t = ctx[FrameTime]() - start_time
        return start + (target() - start)*curve(min(t / duration, 1.0))
    @tweened.on_set
    def force(value):
        nonlocal start
        start = value
        target.set(value)
    @target.watch(active)
    def change():
        nonlocal start, start_time
        start = tweened()
        start_time = ctx[FrameTime]()
    change()
    return tweened

class DraggableView:
    def __init__(self, active, ctx, *, center=Vec2(0.0, 0.0), zoom=1.0, scroll_factor=5/3):
        self.center = as_ref(center)
        s_target = as_ref(math.log(zoom, scroll_factor))
        s = tween(ctx, s_target)
        self.anchor = self.center()
        self.s_0 = Vec2(0.0, 0.0)
        self.zoom = computed()(lambda: scroll_factor ** s())
        self.center = computed()(lambda: self.anchor + self.s_0 * 1 / self.zoom())
        @ctx['mouse_diff'].watch(active)
        def on_mouse():
            if not ctx[LeftMouse](): return
            self.anchor = self.center() - ctx['mouse_diff']() / self.zoom()
            self.s_0 = Vec2(0.0, 0.0)
            s.touch()
        @ctx['scroll_diff'].watch(active)
        def on_scroll():
            amount = ctx['scroll_diff']().y
            m = (ctx[MousePosition]() - ctx[Region].size / 2)
            self.anchor = self.center() + m / self.zoom()
            self.s_0 = -m
            s_target.map(lambda x: x + amount)
        self.wire = Sequence([self.zoom.wire, s.wire, self.center.wire, on_mouse, on_scroll])

def draw_shader_image(active, ctx, fragment_src, *, uniforms):
    _program = pyglet.graphics.shader.ShaderProgram(
        pyglet.graphics.shader.Shader("#version 330\nin vec2 pos; void main() { gl_Position = vec4(pos, 0.0, 1.0); }", 'vertex'),
        pyglet.graphics.shader.Shader(fragment_src, 'fragment'),
    )
    uniform_refs = {
        name: as_ref(value) for name, value in uniforms.items()
        if name in _program.uniforms
    }
    _new_uniforms = {}
    def set_uniform(name, ref):
        _new_uniforms[name] = ref()
        # print(f"set uniform {name!r} to {ref()}")
    for name, ref in uniform_refs.items():
        _program[name] = ref()
        ref.watch(active)(partial(set_uniform, name, ref))
    _vlist = _program.vertex_list_indexed(4, pyglet.gl.GL_TRIANGLES,
        (0, 1, 2, 0, 2, 3),
        pos=('f', (-1.0,1.0, -1.0,-1.0, 1.0,-1.0, 1.0,1.0)))
    def draw():
        _program.use()
        for name, value in _new_uniforms.items():
            _program[name] = value
        _new_uniforms.clear()
        _vlist.draw(pyglet.gl.GL_TRIANGLES)
    on_event(active, ctx, 'on_draw', draw)

class GLState:
    def __init__(self):
        self.shader = DataRef(None)
        @self.shader.watch
        def use():
            self.shader()._program.use()
class Region:
    def __init__(self, size):
        self.size = size
class FrameCount: pass
class FrameTime: pass
class MousePosition: pass
class LeftMouse: pass
class DrawnImage: pass
class KeyMap: pass

class Context:
    def __init__(self, data):
        self._data = data
    def __or__(self, data):
        child = self._data.copy()
        child.update(data)
        return Context(child)
    def __getitem__(self, key):
        return self._data[key]

def provide_wall_time(ctx):
    start_time = time()
    wall_time = Ref(start_time)
    @ctx[FrameCount].watch
    def clock():
        wall_time.set(time() - start_time)
    return ctx | {
        FrameTime: wall_time,
    }

def video_time(ctx, *, fps):
    return computed()(lambda: ctx[FrameCount]() / fps)

def warped_time(time, *, speed):
    base_source = base = 0.0
    speed = as_ref(speed)
    controlled = computed({time})(lambda: base + (time() - base_source) * speed())
    @speed.watch
    def rebase():
        nonlocal base, base_source
        base = controlled()
        base_source = time()
    rebase()
    return controlled

def time_control(ctx):
    speed = Ref(1.0)
    key_press(ctx, 'SPACE').watch(lambda: speed.set(0.0 if speed() != 0.0 else 1.0))
    key_press(ctx, 'LEFT').watch(lambda: speed.set(-3.0))
    key_press(ctx, 'RIGHT').watch(lambda: speed.set(3.0))
    return warped_time(ctx[FrameTime], speed=speed)

_handler_sets = {}
def on_event(active, ctx, name, handler):
    @effect(active)
    def _():
        if name not in _handler_sets:
            window = ctx[pyglet.window.Window]
            hset = {handler}
            def do_all(*a, **kw):
                for h in hset.copy(): h(*a, **kw)
                return True
            window._event_stack[0][name] = do_all
            _handler_sets[name] = hset
        else:
            _handler_sets[name].add(handler)
        yield
        _handler_sets[name].remove(handler)

def provide(ctx, args):
    return ctx | {type(x): x for x in args}

def define_window(setup):
    window = pyglet.window.Window()
    window._event_stack = [{}]
    v_FrameCount = Ref(0)
    ctx = {
        type(window): window,
        FrameCount: v_FrameCount,
    }
    active = Ref(True)
    on_event(active, ctx, 'on_refresh', lambda dt: v_FrameCount.set(v_FrameCount() + 1))
    # on_event(active, ctx, 'on_close', lambda: active.set(False))
    setup(read_only(active), ctx)

# def run_window1(f):
#     window = pyglet.window.Window()
#     buffer_manager = pyglet.image.get_buffer_manager()
#     print(window.config)
#     start_time = time()

#     v_GLState = GLState()
#     v_Region = Region(Vec2(window.width, window.height))
#     v_FrameCount = Ref(0)
#     # v_FrameTime = Ref(0.0)
#     v_MousePosition = Ref(None)
#     v_LeftMouse = Ref(False)
#     v_DrawnImage = Ref(False)
#     v_KeyMap = defaultdict(lambda: Ref(False))
#     mouse_diff = Ref(Vec2(0, 0))
#     scroll_diff = Ref(Vec2(0, 0))
#     ctx = Context({
#         GLState: v_GLState,
#         Region: v_Region,
#         FrameCount: v_FrameCount,
#         # FrameTime: v_FrameTime,
#         MousePosition: v_MousePosition,
#         LeftMouse: v_LeftMouse,
#         DrawnImage: v_DrawnImage,
#         KeyMap: v_KeyMap,
#         'mouse_diff': mouse_diff,
#         'scroll_diff': scroll_diff,
#     })
#     f(ctx)
#     @window.event
#     def on_draw():
#         v_FrameCount.map(lambda x: x + 1)
#         v_DrawnImage.set(buffer_manager.get_color_buffer())
#     @window.event
#     def on_key_press(symbol, modifiers):
#         v_KeyMap[pyglet.window.key.symbol_string(symbol)].set(True)
#     @window.event
#     def on_key_release(symbol, modifiers):
#         v_KeyMap[pyglet.window.key.symbol_string(symbol)].set(False)
#     @window.event
#     def on_mouse_motion(x, y, dx, dy):
#         v_MousePosition.set(Vec2(x, y))
#         mouse_diff.set(Vec2(dx, dy))
#     @window.event
#     def on_mouse_drag(x, y, dx, dy, *_):
#         v_MousePosition.set(Vec2(x, y))
#         mouse_diff.set(Vec2(dx, dy))
#     @window.event
#     def on_mouse_press(x, y, button, modifiers):
#         if button == pyglet.window.mouse.LEFT:
#             v_LeftMouse.set(True)
#     @window.event
#     def on_mouse_release(x, y, button, modifiers):
#         if button == pyglet.window.mouse.LEFT:
#             v_LeftMouse.set(False)
#     @window.event
#     def on_mouse_scroll(x, y, sx, sy):
#         scroll_diff.set(Vec2(sx, sy))
#     pyglet.app.run()
