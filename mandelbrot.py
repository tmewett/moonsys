import math
from pathlib import Path

import pyglet
from pyglet.math import Vec2

import refs_gl
from refs import Ref, Computed

def csin(x):
    return math.sin(x)/2 + 0.5

@refs_gl.run_window
def setup(ctx):
    ctx = ctx.provide({refs_gl.FrameTimeProvider: refs_gl.video_time(ctx, fps=60)})
    time = ctx[refs_gl.FrameTimeProvider]
    view = refs_gl.DraggableView(ctx)
    # view = refs_gl.DraggableView(ctx, center=Vec2(-208.61060767044705, 30.294525500086095), zoom=165)
    img = refs_gl.ShaderImage(
        Path("shaders/mandelbrot.glsl").read_text(),
        uniforms={
            'resolution': ctx[refs_gl.RegionProvider].size,
            'offset': view.center,
            'zoom': view.zoom,
            'time': time,
        },
    )
    @time.watch
    def draw():
        img.draw(ctx)
