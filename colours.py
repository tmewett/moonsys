import math
import pyglet

import refs_gl
from refs import Ref, computed, Sequence

def csin(x):
    return math.sin(x)/2 + 0.5

def App(ctx):
    c = computed()(lambda: csin(ctx[refs_gl.FrameCount]() / 60))
    img = refs_gl.ShaderImage(
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
    return Sequence([
        c,
        img,
    ])

refs_gl.Window(App).do()
pyglet.app.run()
