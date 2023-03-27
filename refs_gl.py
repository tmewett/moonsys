import math
from dataclasses import dataclass, field
from time import time

import pyglet
from pyglet.gl import Config
from pyglet.math import Vec2

from refs import as_ref, computed, DataRef, Ref, writeable_computed

def clear(*, color, depth):
    from pyglet.gl import glClear, glClearColor, glClearDepth, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
    glClearColor(*color)
    glClearDepth(depth)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

# TODO Rewrite as a custom Reactive to see if WriteableComputed adds anything.
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
    @target.watch
    def change():
        nonlocal start, start_time
        start = tweened()
        start_time = ctx[FrameTime]()
    change()
    return tweened

class DraggableView:
    def __init__(self, ctx, *, center=Vec2(0.0, 0.0), zoom=1.0, scroll_factor=5/3):
        self.center = as_ref(center)
        s_target = as_ref(math.log(zoom, scroll_factor))
        s = tween(ctx, s_target)
        self.anchor = self.center()
        self.s_0 = Vec2(0.0, 0.0)
        self.zoom = computed()(lambda: scroll_factor ** s())
        self.center = computed()(lambda: self.anchor + self.s_0 * 1 / self.zoom())
        @ctx['mouse_diff'].watch
        def _():
            if not ctx[LeftMouse](): return
            self.anchor = self.center() - ctx['mouse_diff']() / self.zoom()
            self.s_0 = Vec2(0.0, 0.0)
            s.map(lambda x: x)
        @ctx['scroll_diff'].watch
        def _():
            amount = ctx['scroll_diff']().y
            m = (ctx[MousePosition]() - ctx[Region].size / 2)
            self.anchor = self.center() + m / self.zoom()
            self.s_0 = -m
            s_target.map(lambda x: x + amount)

class ShaderImage:
    def __init__(self, fragment_src, *, uniforms):
        self.shader = Shader(sources={
            'vertex': "#version 330\nin vec2 pos; void main() { gl_Position = vec4(pos, 0.0, 1.0); }",
            'fragment': fragment_src,
        }, uniforms=uniforms)
        self._vlist = self.shader._program.vertex_list_indexed(4, pyglet.gl.GL_TRIANGLES,
            (0, 1, 2, 0, 2, 3),
            pos=('f', (-1.0,1.0, -1.0,-1.0, 1.0,-1.0, 1.0,1.0)))
    def draw(self, ctx):
        ctx[GLState].shader.set(self.shader)
        self._vlist.draw(pyglet.gl.GL_TRIANGLES)

class Shader:
    def __init__(self, *, sources, uniforms):
        self._program = pyglet.graphics.shader.ShaderProgram(
            *[pyglet.graphics.shader.Shader(src, type) for type, src in sources.items()]
        )
        self.uniforms = {
            name: as_ref(value) for name, value in uniforms.items()
            if name in self._program.uniforms
        }
        for name, ref in self.uniforms.items():
            @ref.watch
            def set_uniform(name=name, ref=ref):
                self._program[name] = ref()
                # print(f"set uniform {name!r} to {ref()}")
            self._program[name] = ref()

def just_value(ref, value):
    f = Ref(ref())
    @ref.watch
    def _():
        if ref() == value:
            f.set(ref())
    return f

def key_toggle(ctx, key, init=False):
    t = Ref(init)
    @just_value(ctx[KeyPress], key).watch
    def _():
        t.set(not t())
    return t

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
class KeyPress: pass

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

def run_window(f):
    # window = pyglet.window.Window(config=Config(
        # double_buffer=True,
        # sample_buffers=1,
        # samples=8,
    # ))
    window = pyglet.window.Window()
    buffer_manager = pyglet.image.get_buffer_manager()
    print(window.config)
    start_time = time()

    v_GLState = GLState()
    v_Region = Region(Vec2(window.width, window.height))
    v_FrameCount = Ref(0)
    # v_FrameTime = Ref(0.0)
    v_MousePosition = Ref(None)
    v_LeftMouse = Ref(False)
    v_DrawnImage = Ref(False)
    v_KeyPress = Ref(None)
    mouse_diff = Ref(Vec2(0, 0))
    scroll_diff = Ref(Vec2(0, 0))
    ctx = Context({
        GLState: v_GLState,
        Region: v_Region,
        FrameCount: v_FrameCount,
        # FrameTime: v_FrameTime,
        MousePosition: v_MousePosition,
        LeftMouse: v_LeftMouse,
        DrawnImage: v_DrawnImage,
        KeyPress: v_KeyPress,
        'mouse_diff': mouse_diff,
        'scroll_diff': scroll_diff,
    })
    f(ctx)
    @window.event
    def on_draw():
        v_FrameCount.map(lambda x: x + 1)
        v_DrawnImage.set(buffer_manager.get_color_buffer())
    @window.event
    def on_key_press(symbol, modifiers):
        v_KeyPress.set(pyglet.window.key.symbol_string(symbol))
    @window.event
    def on_mouse_motion(x, y, dx, dy):
        v_MousePosition.set(Vec2(x, y))
        mouse_diff.set(Vec2(dx, dy))
    @window.event
    def on_mouse_drag(x, y, dx, dy, *_):
        v_MousePosition.set(Vec2(x, y))
        mouse_diff.set(Vec2(dx, dy))
    @window.event
    def on_mouse_press(x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            v_LeftMouse.set(True)
    @window.event
    def on_mouse_release(x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            v_LeftMouse.set(False)
    @window.event
    def on_mouse_scroll(x, y, sx, sy):
        scroll_diff.set(Vec2(sx, sy))
    pyglet.app.run()
