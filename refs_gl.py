import math
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from functools import partial
from pathlib import Path
from time import time

import pyglet
from pyglet.gl import Config
from pyglet.math import Vec2

from refs import as_ref, computed, Ref, ReadableReactive, read_only, tick, Reducer, gate, reduce_event, sample, integrate, Flag, gate_context

def clear(*, color=(0, 0, 0, 255), depth=0):
    from pyglet.gl import glClear, glClearColor, glClearDepth, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
    glClearColor(*color)
    glClearDepth(depth)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

class drag_zoom_view:
    def __init__(self, active, ctx, *, center=Vec2(0.0, 0.0), zoom=1.0, scroll_factor=5/3):
        ctx = gate_context(ctx, active, [ScrollChange, MousePosition, MouseDrag])
        # s is the level of scroll. +/- 1 per scroll increment.
        s = reduce_event(lambda s, sc: s + sc.y, ctx[ScrollChange], 0)
        # s is the logarithm of the zoom factor, so to find zoom, raise it to a power.
        self.zoom = computed([s])(lambda s: scroll_factor ** s)
        # target is the position of the mouse in world space when zooming.
        target = Reducer(center)
        # target updates when scrolling.
        @target.reduce(ctx[ScrollChange])
        def _(t, sc):
            if ctx[MousePosition]() is None: return t
            return self.center() + (ctx[MousePosition]() - ctx[Region].size() / 2) / self.zoom()
        # center is the center of the view in world space.
        self.center = Reducer(center)
        # It's draggable.
        @self.center.reduce(ctx[MouseDrag])
        def _(prev, drag):
            return prev - drag / self.zoom()
        # When zooming, we need to move center along the line passing through
        # target and the current center. So the new center is target + the
        # scaled target-to-center vector. We need to depend on target to ensure
        # we zoom into the right place.
        @self.center.reduce(s, [target])
        def _(prev, new_s, target):
            target_to_center = prev - target
            return target + target_to_center * scroll_factor ** (s() - new_s)

def draw_shader_image(active, ctx, fragment_src, *, uniforms={}):
    _program = pyglet.graphics.shader.ShaderProgram(
        pyglet.graphics.shader.Shader("#version 330\nin vec2 pos; void main() { gl_Position = vec4(pos, 0.0, 1.0); }", 'vertex'),
        pyglet.graphics.shader.Shader(fragment_src, 'fragment'),
    )
    uniform_refs = []
    for name, value in uniforms.items():
        if name not in _program.uniforms: continue
        if isinstance(value, ReadableReactive):
            uniform_refs.append((name, value, Flag(value)))
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

def record(on, ctx):
    take = datetime.now().strftime("refs_gl_%Y-%m-%d_%H-%M-%S")
    dir = Path(take)
    dir.mkdir()
    bm = pyglet.image.get_buffer_manager()
    color = bm.get_color_buffer()
    frames = 0
    def draw():
        nonlocal frames
        file = dir / f"{frames:06}.png"
        color.save(file)
        frames += 1
    ctx[Draws].add(on, draw)

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

class Gatherer:
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
class MouseDrag: pass
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
    v_MouseDrag = Ref(None, is_event=True)
    # v_MouseDrag.log = 'md'
    v_KeyMap = defaultdict(lambda: Ref(False))
    v_KeyPress = Ref(None, is_event=True)
    v_Draws = Gatherer()
    v_Region = Region(Ref(Vec2(window.width, window.height)))
    ctx = {
        type(window): window,
        FrameCount: v_FrameCount,
        FrameTime: v_FrameTime,
        MousePosition: v_MousePosition,
        MousePositionChange: v_MousePositionChange,
        ScrollChange: v_ScrollChange,
        LeftMouse: v_LeftMouse,
        MouseDrag: v_MouseDrag,
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
        if v_LeftMouse._next_value:
            v_MouseDrag.set(Vec2(dx, dy))
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
