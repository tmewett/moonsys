import math
from dataclasses import dataclass, field
from time import time

import pyglet
from pyglet.gl import Config
from pyglet.math import Vec2

from refs import as_ref, Computed, DataRef, Ref, WriteableComputed

def clear(*, color, depth):
    from pyglet.gl import glClear, glClearColor, glClearDepth, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
    glClearColor(*color)
    glClearDepth(depth)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

def tween(ctx, target, duration=0.1, curve=lambda t: t**0.7):
    start = target()
    start_time = 0.0
    @WriteableComputed
    def tweened():
        t = ctx[FrameTimeProvider]() - start_time
        # Only depend on frame time to avoid race condition between watchers.
        return start + (target.quiet_get() - start)*curve(min(t / duration, 1.0))
    @tweened.set_value
    def force(value):
        nonlocal start
        start = value
        target.quiet_set(value)
        return value
    @target.watch
    def change():
        nonlocal start, start_time
        start = tweened()
        start_time = ctx[FrameTimeProvider]()
    change()
    return tweened

class DraggableView:
    def __init__(self, ctx, *, center=Vec2(0.0, 0.0), zoom=1.0, scroll_factor=5/3):
        self.center = as_ref(center)
        s_target = as_ref(math.log(zoom, scroll_factor))
        s = tween(ctx, s_target)
        self.anchor = self.center()
        self.s_0 = Vec2(0.0, 0.0)
        self.zoom = Computed(lambda: scroll_factor ** s())
        self.center = Computed(lambda: self.anchor + self.s_0 * 1 / self.zoom())
        @ctx['mouse_diff'].watch
        def _():
            if not ctx[LeftMouseProvider](): return
            self.anchor = self.center() - ctx['mouse_diff']() / self.zoom()
            self.s_0 = Vec2(0.0, 0.0)
            s.map(lambda x: x)
        @ctx['scroll_diff'].watch
        def _():
            amount = ctx['scroll_diff']().y
            m = (ctx[MousePositionProvider]() - ctx[RegionProvider].size / 2)
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
        ctx[GLStateProvider].shader.set(self.shader)
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

class GLState:
    def __init__(self):
        self.shader = DataRef(None)
        @self.shader.watch
        def use():
            self.shader()._program.use()
class GLStateProvider: pass
class Region:
    def __init__(self, size):
        self.size = size
class RegionProvider: pass
class FrameCountProvider: pass
class FrameTimeProvider: pass
class MousePositionProvider: pass
class LeftMouseProvider: pass
class DrawnImageProvider: pass

class Context:
    def __init__(self, data):
        self._data = data
    def provide(self, data):
        child = self._data.copy()
        child.update(data)
        return Context(child)
    def __getitem__(self, key):
        return self._data[key]

def provide_wall_time(ctx):
    start_time = time()
    wall_time = Ref(start_time)
    @ctx[FrameCountProvider].watch
    def clock():
        wall_time.set(time() - start_time)
    return ctx.provide({
        FrameTimeProvider: wall_time,
    })

def provide_video_time(ctx, *, fps):
    return ctx.provide({
        FrameTimeProvider: Computed(lambda: ctx[FrameCountProvider]() / fps),
    })

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

    v_GLStateProvider = GLState()
    v_RegionProvider = Region(Vec2(window.width, window.height))
    v_FrameCountProvider = Ref(0)
    # v_FrameTimeProvider = Ref(0.0)
    v_MousePositionProvider = Ref(None)
    v_LeftMouseProvider = Ref(False)
    v_DrawnImageProvider = Ref(False)
    mouse_diff = Ref(Vec2(0, 0))
    scroll_diff = Ref(Vec2(0, 0))
    ctx = Context({
        GLStateProvider: v_GLStateProvider,
        RegionProvider: v_RegionProvider,
        FrameCountProvider: v_FrameCountProvider,
        # FrameTimeProvider: v_FrameTimeProvider,
        MousePositionProvider: v_MousePositionProvider,
        LeftMouseProvider: v_LeftMouseProvider,
        DrawnImageProvider: v_DrawnImageProvider,
        'mouse_diff': mouse_diff,
        'scroll_diff': scroll_diff,
    })
    f(ctx)
    @window.event
    def on_draw():
        v_FrameCountProvider.map(lambda x: x + 1)
        v_DrawnImageProvider.set(buffer_manager.get_color_buffer())
    @window.event
    def on_mouse_motion(x, y, dx, dy):
        v_MousePositionProvider.set(Vec2(x, y))
        mouse_diff.set(Vec2(dx, dy))
    @window.event
    def on_mouse_drag(x, y, dx, dy, *_):
        v_MousePositionProvider.set(Vec2(x, y))
        mouse_diff.set(Vec2(dx, dy))
    @window.event
    def on_mouse_press(x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            v_LeftMouseProvider.set(True)
    @window.event
    def on_mouse_release(x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            v_LeftMouseProvider.set(False)
    @window.event
    def on_mouse_scroll(x, y, sx, sy):
        scroll_diff.set(Vec2(sx, sy))
    pyglet.app.run()
