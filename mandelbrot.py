import math
from pathlib import Path

import pyglet
from pyglet.math import Vec2

import refs_gl
from refs import Ref, computed

def csin(x):
    return math.sin(x)/2 + 0.5

@refs_gl.run_window
def setup(ctx):
    ctx = ctx | {refs_gl.FrameTime: refs_gl.video_time(ctx, fps=60)}
    fractal_time = refs_gl.time_control(ctx)
    time = ctx[refs_gl.FrameTime]
    view = refs_gl.DraggableView(ctx)
    img = refs_gl.ShaderImage(
        Path("shaders/mandelbrot.glsl").read_text(),
        uniforms={
            'resolution': ctx[refs_gl.Region].size,
            'offset': view.center,
            'zoom': view.zoom,
            'time': fractal_time,
        },
    )
    @time.watch
    def draw():
        img.draw(ctx)
