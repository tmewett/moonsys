import math
from pathlib import Path

import pyglet
from pyglet.math import Vec2
from pyglet.gl import glViewport

import refs_gl
from refs import Ref, computed, Active

def setup(ctx):
    time = refs_gl.video_time(ctx, fps=60)
    ctx = ctx.add({refs_gl.FrameTime: time})
    fractal_time = refs_gl.time_control(ctx)
    # fractal_time.log = 'fract'
    view = refs_gl.drag_zoom_view(ctx)

    tex = pyglet.image.Texture.create(1080, 1920)
    fbo = pyglet.image.buffer.Framebuffer()
    fbo.attach_texture(tex)

    def bind():
        fbo.bind()
        glViewport(0, 0, 1080, 1920)
    ctx[refs_gl.Draws].add(ctx[Active], bind)

    refs_gl.draw_shader_image(ctx,
        Path("shaders/mandelbrot.glsl").read_text(),
        uniforms={
            'resolution': (1080, 1920),
            'offset': view.center,
            'zoom': view.zoom,
            # 'time': ctx[refs_gl.FrameTime],
            'time': fractal_time,
        },
    )

    def draw_fb():
        fbo.unbind()
        w, h = ctx[refs_gl.Region].size()
        glViewport(0, 0, w, h)
        # ctx[refs_gl.Region].size.log = 'rs'
        tex.blit(0, 0, width=w, height=h)
    ctx[refs_gl.Draws].add(ctx[Active], draw_fb)

    # refs_gl.record_image(ctx, tex)

refs_gl.define_window(setup, 480, 854)
pyglet.app.run()
