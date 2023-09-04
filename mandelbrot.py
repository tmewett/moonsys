import math
from pathlib import Path

import pyglet
from pyglet.math import Vec2

import refs_gl
from refs import Ref, computed

def setup(on, ctx):
    time = refs_gl.video_time(ctx, fps=60)
    ctx = ctx | {refs_gl.FrameTime: time}
    fractal_time = refs_gl.time_control(on, ctx)
    # fractal_time.log = 'fract'
    view = refs_gl.drag_zoom_view(on, ctx)
    refs_gl.draw_shader_image(on, ctx,
        Path("shaders/mandelbrot.glsl").read_text(),
        uniforms={
            'resolution': ctx[refs_gl.Region].size,
            'offset': view.center,
            'zoom': view.zoom,
            # 'time': ctx[refs_gl.FrameTime],
            'time': fractal_time,
        },
    )
    refs_gl.record(on, ctx)

refs_gl.define_window(setup)
pyglet.app.run()
