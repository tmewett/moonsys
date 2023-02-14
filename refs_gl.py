from dataclasses import dataclass, field
from time import time

import pyglet
from pyglet.math import Vec2

from refs import as_ref, computed, DataRef, Ref, WriteableComputed

def clear(*, color, depth):
    from pyglet.gl import glClear, glClearColor, glClearDepth, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
    glClearColor(*color)
    glClearDepth(depth)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

def tween(ctx, target, duration=0.2, curve=lambda t: t):
    start = target()
    start_time = 0.0
    @WriteableComputed
    def tweened():
        t = ctx[FrameTimeContext]() - start_time
        # Only depend on frame time to avoid race condition between watchers.
        return start + (target.quiet_get() - start)*curve(min(t / duration, 1.0))
    @target.watch
    def change():
        nonlocal start, start_time
        start = tweened()
        start_time = ctx[FrameTimeContext]()
    change()
    @tweened.setter
    def force(value):
        nonlocal start
        start = value
        target.set(value)
        return value
    return tweened

class DraggableView:
    def __init__(self, ctx, origin, *, scroll_factor=5/3):
        coords_target = Ref(origin)
        zoom_target = Ref(1.0)
        # coords = coords_target
        # zoom = zoom_target
        coords = tween(ctx, coords_target)
        zoom = tween(ctx, zoom_target)
        @ctx['mouse_diff'].watch
        def _():
            if not ctx[LeftMouseContext](): return
            md = ctx['mouse_diff']()
            coords.map(lambda x: x - md/zoom())
            # Stop tweening when dragged.
            # zoom_target.set(zoom())
        @ctx['scroll_diff'].watch
        def _():
            amount = ctx['scroll_diff']().y
            from_center = (ctx[MousePositionContext]() - ctx[RegionContext].size / 2) / zoom()
            factor = 1.0 - 1/scroll_factor if amount > 0 else scroll_factor - 1.0
            new_coords = coords() + from_center*factor*amount
            new_zoom = zoom() * scroll_factor**amount
            coords_target.set(new_coords)
            zoom_target.set(new_zoom)
        self.coords = coords
        self.zoom = zoom

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
        ctx[GLContext].shader.set(self.shader)
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
            print(name)
            @ref.watch
            def set_uniform(name=name, ref=ref):
                self._program[name] = ref()
                # print(f"set uniform {name!r} to {ref()}")
            self._program[name] = ref()

class GLContextData:
    def __init__(self):
        self.shader = DataRef(None)
        @self.shader.watch
        def use():
            self.shader()._program.use()
class GLContext: pass
class Region:
    def __init__(self, size):
        self.size = size
class RegionContext: pass
class FrameTimeContext: pass
class MousePositionContext: pass
class LeftMouseContext: pass

class Context:
    def __init__(self, data):
        self._data = data
    def provide(self, data):
        child = self._data.copy()
        child.update(data)
        return Context(child)
    def __getitem__(self, key):
        return self._data[key]

def run_window(f):
    window = pyglet.window.Window()
    start_time = time()

    v_GLContext = GLContextData()
    v_RegionContext = Region(Vec2(window.width, window.height))
    v_FrameTimeContext = Ref(0.0)
    mouse_pos = Ref(None)
    lmb = Ref(False)
    mouse_diff = Ref(Vec2(0, 0))
    scroll_diff = Ref(Vec2(0, 0))
    ctx = Context({
        GLContext: v_GLContext,
        RegionContext: v_RegionContext,
        FrameTimeContext: v_FrameTimeContext,
        MousePositionContext: mouse_pos,
        LeftMouseContext: lmb,
        'mouse_diff': mouse_diff,
        'scroll_diff': scroll_diff,
    })
    f(ctx)
    @window.event
    def on_draw():
        v_FrameTimeContext.set(time() - start_time)
    @window.event
    def on_mouse_motion(x, y, dx, dy):
        mouse_pos.set(Vec2(x, y))
        mouse_diff.set(Vec2(dx, dy))
    @window.event
    def on_mouse_drag(x, y, dx, dy, *_):
        mouse_pos.set(Vec2(x, y))
        mouse_diff.set(Vec2(dx, dy))
    @window.event
    def on_mouse_press(x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            lmb.set(True)
    @window.event
    def on_mouse_release(x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            lmb.set(False)
    @window.event
    def on_mouse_scroll(x, y, sx, sy):
        scroll_diff.set(Vec2(sx, sy))
    pyglet.app.run()
