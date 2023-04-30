import math
from dataclasses import dataclass, field
from collections import defaultdict
from functools import partial
from time import time

import pyglet
from pyglet.gl import Config
from pyglet.math import Vec2

from refs import as_ref, computed, DataRef, Ref, read_only, writeable_computed, effect

def clear(*, color, depth):
    from pyglet.gl import glClear, glClearColor, glClearDepth, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
    glClearColor(*color)
    glClearDepth(depth)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

def tween(ctx, target, duration=0.1, curve=lambda t: t**0.7):
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
    @target.watch(tweened.active)
    def change():
        nonlocal start, start_time
        start = tweened()
        start_time = ctx[FrameTime]()
    change()
    return tweened

class drag_zoom_view:
    def __init__(self, active, ctx, *, center=Vec2(0.0, 0.0), zoom=1.0, scroll_factor=5/3):
        self.center = as_ref(center)
        s_target = as_ref(math.log(zoom, scroll_factor))
        s = tween(ctx, s_target)
        self.anchor = self.center()
        self.s_0 = Vec2(0.0, 0.0)
        self.zoom = computed()(lambda: scroll_factor ** s())
        self.center = computed()(lambda: self.anchor + self.s_0 * 1 / self.zoom())
        @ctx[MousePositionChange].watch(active)
        def on_mouse():
            if not ctx[LeftMouse](): return
            self.anchor = self.center() - ctx[MousePositionChange]() / self.zoom()
            self.s_0 = Vec2(0.0, 0.0)
            s.set(s())
        @ctx[ScrollChange].watch(active)
        def on_scroll():
            amount = ctx[ScrollChange]().y
            m = (ctx[MousePosition]() - ctx[Region].size / 2)
            self.anchor = self.center() + m / self.zoom()
            self.s_0 = -m
            s_target.map(lambda x: x + amount)

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
                return False
            window._event_stack[0][name] = do_all
            _handler_sets[name] = hset
        else:
            _handler_sets[name].add(handler)
        yield
        _handler_sets[name].remove(handler)

class GLState:
    def __init__(self):
        self.shader = DataRef(None)
        @self.shader.watch
        def use():
            self.shader()._program.use()
class FrameCount: pass
class FrameTime: pass
class MousePosition: pass
class MousePositionChange: pass
class ScrollChange: pass
class LeftMouse: pass
class KeyMap: pass
class Region:
    def __init__(self, size):
        self.size = size

def define_window(setup):
    window = pyglet.window.Window()
    # Load empty handler frame for on_event.
    window._event_stack = [{}]
    v_FrameCount = Ref(0)
    # TODO default FrameTime to wall time
    v_MousePosition = Ref(None)
    v_MousePositionChange = Ref(Vec2(0, 0))
    v_ScrollChange = Ref(Vec2(0, 0))
    v_LeftMouse = Ref(False)
    v_KeyMap = defaultdict(lambda: Ref(False))
    v_Region = Region(Vec2(window.width, window.height))
    ctx = {
        type(window): window,
        FrameCount: v_FrameCount,
        MousePosition: v_MousePosition,
        MousePositionChange: v_MousePositionChange,
        ScrollChange: v_ScrollChange,
        LeftMouse: v_LeftMouse,
        KeyMap: v_KeyMap,
        Region: v_Region,
    }
    active = Ref(True)
    on_event(active, ctx, 'on_refresh', lambda dt: v_FrameCount.set(v_FrameCount() + 1))
    def on_mouse_motion(x, y, dx, dy):
        v_MousePosition.set(Vec2(x, y))
        v_MousePositionChange.set(Vec2(dx, dy))
    on_event(active, ctx, 'on_mouse_motion', on_mouse_motion)
    def on_mouse_drag(x, y, dx, dy, *_):
        v_MousePosition.set(Vec2(x, y))
        v_MousePositionChange.set(Vec2(dx, dy))
    on_event(active, ctx, 'on_mouse_drag', on_mouse_drag)
    def on_mouse_scroll(x, y, sx, sy):
        v_ScrollChange.set(Vec2(sx, sy))
    on_event(active, ctx, 'on_mouse_scroll', on_mouse_scroll)
    def on_mouse_press(x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            v_LeftMouse.set(True)
    on_event(active, ctx, 'on_mouse_press', on_mouse_press)
    def on_mouse_release(x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            v_LeftMouse.set(False)
    on_event(active, ctx, 'on_mouse_release', on_mouse_release)
    def on_key_press(symbol, modifiers):
        v_KeyMap[pyglet.window.key.symbol_string(symbol)].set(True)
    on_event(active, ctx, 'on_key_press', on_key_press)
    def on_key_release(symbol, modifiers):
        v_KeyMap[pyglet.window.key.symbol_string(symbol)].set(False)
    on_event(active, ctx, 'on_key_release', on_key_release)
    on_event(active, ctx, 'on_close', lambda: active.set(False))
    setup(read_only(active), ctx)
