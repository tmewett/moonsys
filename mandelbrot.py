import math
from pathlib import Path

import pyglet

import refs_gl
from refs import Ref, Computed

def csin(x):
    return math.sin(x)/2 + 0.5

@refs_gl.run_window
def setup(ctx):
    time = ctx[refs_gl.FrameTimeContext]
    offset, zoom = refs_gl.use_draggable_view(ctx, (0, 0))
    img = refs_gl.ShaderImage(
        Path("shaders/mandelbrot.glsl").read_text(),
        uniforms={
            'resolution': ctx[refs_gl.RegionContext].size,
            'offset': offset,
            'zoom': zoom,
            'time': time,
        },
    )
    print(offset._watchers, zoom._watchers)
    @time.watch
    def draw():
        img.draw(ctx)
