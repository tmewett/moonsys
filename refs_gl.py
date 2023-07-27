import math
from dataclasses import dataclass, field
from collections import defaultdict
from functools import partial
from time import time

import pyglet
from pyglet.gl import Config
from pyglet.math import Vec2

from refs import as_ref, computed, Ref, ReadableReactive, read_only, tick, gate, reduce_event, sample, integrate, flag

def clear(*, color=(0, 0, 0, 255), depth=0):
    from pyglet.gl import glClear, glClearColor, glClearDepth, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
    glClearColor(*color)
    glClearDepth(depth)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

class drag_zoom_view:
    def __init__(self, active, ctx, *, center=Vec2(0.0, 0.0), zoom=1.0, scroll_factor=5/3):
        g_ScrollChange = gate(active, ctx[ScrollChange])
        g_MousePosition = gate(active, ctx[MousePosition])
        s = reduce_event(lambda s, sc: s + sc.y, g_ScrollChange, 0.0)
        self.zoom = computed([s])(lambda s: scroll_factor ** s)
        self.center = Ref(center)
        mouse_world = computed([g_MousePosition, ctx[Region].size, self.zoom, self.center])(
            lambda m, s, z, c: c + (m - s/2) / z if m is not None else Vec2(0, 0)
        )
        target = sample(mouse_world, g_ScrollChange)
        s0 = computed([target])(lambda t: (self.center() - t) * self.zoom())
        self.center << computed([target, s0, self.zoom])(lambda t, s0, z: t + s0 / z)

def draw_shader_image(active, ctx, fragment_src, *, uniforms):
    _program = pyglet.graphics.shader.ShaderProgram(
        pyglet.graphics.shader.Shader("#version 330\nin vec2 pos; void main() { gl_Position = vec4(pos, 0.0, 1.0); }", 'vertex'),
        pyglet.graphics.shader.Shader(fragment_src, 'fragment'),
    )
    uniform_refs = []
    for name, value in uniforms.items():
        if name not in _program.uniforms: continue
        if isinstance(value, ReadableReactive):
            uniform_refs.append((name, value, flag(value)))
            _program[name] = value()
        else:
            print(name, value)
            _program[name] = value
    _vlist = _program.vertex_list_indexed(4, pyglet.gl.GL_TRIANGLES,
        (0, 1, 2, 0, 2, 3),
        pos=('f', (-1.0,1.0, -1.0,-1.0, 1.0,-1.0, 1.0,1.0)))
    def draw():
        _program.use()
        for name, value, flag in uniform_refs:
            if flag.pop():
                _program[name] = value()
        _vlist.draw(pyglet.gl.GL_TRIANGLES)
    ctx[Draws].add(active, draw)

def video_time(ctx, *, fps):
    return computed([ctx[FrameCount]])(lambda fc: fc / fps)

def warped_time(time, *, speed):
    return integrate(speed, time)

def time_control(on, ctx):
    def r(prev, k):
        if k == 'SPACE':
            return 0.0 if prev != 0.0 else 1.0
        elif k == 'LEFT':
            return prev - 3.0 if prev < 0.0 else -3.0
        elif k == 'RIGHT':
            return prev + 3.0 if prev > 0.0 else 3.0
        else:
            return prev
    speed = reduce_event(r, ctx[KeyPress], 1.0)
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

class gatherer:
    def __init__(self):
        self._all = []
    def add(self, on, x):
        self._all.append([on, x])
    def get(self):
        return [x for on, x in self._all if on()]

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
class KeyPress: pass
class Draws: pass
class Region:
    def __init__(self, size):
        self.size = size

def define_window(setup):
    window = pyglet.window.Window()
    # Load empty handler frame for on_event.
    window._event_stack = [{}]
    frames = 0
    v_FrameCount = Ref(0)
    start_time = time()
    v_FrameTime = Ref(0.0)
    v_MousePosition = Ref(None)
    v_MousePositionChange = Ref(Vec2(0, 0))
    v_ScrollChange = Ref(Vec2(0, 0), is_event=True)
    v_LeftMouse = Ref(False)
    v_KeyMap = defaultdict(lambda: Ref(False))
    v_KeyPress = Ref(None, is_event=True)
    v_Draws = gatherer()
    v_Region = Region(Ref(Vec2(window.width, window.height)))
    ctx = {
        type(window): window,
        FrameCount: v_FrameCount,
        FrameTime: v_FrameTime,
        MousePosition: v_MousePosition,
        MousePositionChange: v_MousePositionChange,
        ScrollChange: v_ScrollChange,
        LeftMouse: v_LeftMouse,
        KeyMap: v_KeyMap,
        KeyPress: v_KeyPress,
        Draws: v_Draws,
        Region: v_Region,
    }
    active = Ref(True)
    @window.event
    def on_draw():
        nonlocal frames
        v_FrameCount.set(frames)
        frames += 1
        v_FrameTime.set(time() - start_time)
        tick()
        for f in v_Draws.get(): f()
    @window.event
    def on_mouse_motion(x, y, dx, dy):
        v_MousePosition.set(Vec2(x, y))
        v_MousePositionChange.set(Vec2(dx, dy))
        tick()
    @window.event
    def on_mouse_drag(x, y, dx, dy, *_):
        v_MousePosition.set(Vec2(x, y))
        v_MousePositionChange.set(Vec2(dx, dy))
        tick()
    @window.event
    def on_mouse_scroll(x, y, sx, sy):
        v_ScrollChange.set(Vec2(sx, sy))
        tick()
    @window.event
    def on_mouse_press(x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            v_LeftMouse.set(True)
            tick()
    @window.event
    def on_mouse_release(x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            v_LeftMouse.set(False)
            tick()
    @window.event
    def on_key_press(symbol, modifiers):
        str_symbol = pyglet.window.key.symbol_string(symbol)
        v_KeyMap[str_symbol].set(True)
        v_KeyPress.set(str_symbol)
        tick()
    @window.event
    def on_key_release(symbol, modifiers):
        v_KeyMap[pyglet.window.key.symbol_string(symbol)].set(False)
        tick()
    setup(read_only(active), ctx)
