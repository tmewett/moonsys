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
    time = ctx[refs_gl.FrameTimeContext]
    view = refs_gl.DraggableView(ctx, Vec2(0, 0))
    img = refs_gl.ShaderImage(
        Path("shaders/mandelbrot.glsl").read_text(),
        uniforms={
            'resolution': ctx[refs_gl.RegionContext].size,
            'offset': view.coords,
            'zoom': view.zoom,
            'time': time,
        },
    )
    @time.watch
    def draw():
        img.draw(ctx)
