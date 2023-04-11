import math
import pyglet

import refs_gl
from refs import Ref, computed, Sequence

def csin(x):
    return math.sin(x)/2 + 0.5

def setup(active, ctx):
    c = computed()(lambda: csin(ctx[refs_gl.FrameCount]() / 60))
    refs_gl.draw_shader_image(active,
        ctx,
        """
            #version 330
            uniform float c;
            void main() {
                gl_FragColor = vec4(c,c,c, 1.0);
            }
        """,
        uniforms={'c': c},
    )

refs_gl.define_window(setup)
pyglet.app.run()
