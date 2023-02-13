from dataclasses import dataclass, field
from time import time

import pyglet

from refs import as_ref, Computed, DataRef, Ref

def clear(*, color, depth):
    from pyglet.gl import glClear, glClearColor, glClearDepth, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
    glClearColor(*color)
    glClearDepth(depth)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

def tween(ctx, ref):


class DraggableView:
    def __init__(self, ctx, origin, *, scroll_factor=4/3):
        coords_target = Ref(origin)
        zoom_target = Ref(1.0)
        @ctx['mouse_diff'].watch
        def _():
            if not ctx[LeftMouseContext](): return
            # Stop tweening when dragged.
            coords_target.set(coords())
            zoom_target.set(zoom())
            mx, my = ctx['mouse_diff']()
            coords_target.map(lambda x: (x[0] + mx / zoom(), x[1] + my / zoom()))
        @ctx['scroll_diff'].watch
        def _():
            zoom_target.map(lambda x: x * scroll_factor**ctx['scroll_diff']()[1])
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
    v_RegionContext = Region((window.width, window.height))
    v_FrameTimeContext = Ref(0.0)
    mouse_pos = Ref(None)
    lmb = Ref(False)
    mouse_diff = Ref((0, 0))
    scroll_diff = Ref((0, 0))
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
        mouse_pos.set((x, y))
        mouse_diff.set((dx, dy))
    @window.event
    def on_mouse_drag(x, y, dx, dy, *_):
        mouse_pos.set((x, y))
        mouse_diff.set((dx, dy))
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
        scroll_diff.set((sx, sy))
    pyglet.app.run()
