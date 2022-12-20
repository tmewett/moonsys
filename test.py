import numpy as np
import pyglin as pl
import pyglet.math as pm
import trimesh
from pyglet.gl import glDrawArrays, GL_TRIANGLES

box = trimesh.creation.box((1.,1.,1.))
tris = box.triangles.ravel()
print(tris, len(tris))

def draw():
    proj = pm.Mat4.look_at(pm.Vec3(0., 0., 0.), pm.Vec3(pl.get_elapsed_time(), 0., -1.), pm.Vec3(0., 1., 0.))
    attributes = pl.use_once(lambda: pl.new_attributes(
        [('pos', 3)],
        pl.use_array_buffer(tris),
    ))
    pl.clear_window()
    pl.set_state(
        attributes=attributes,
        vertex_shader="""
            void main() {
                gl_Position = proj * vec4(pos, 1.0);
            }
        """,
        fragment_shader="""
            out vec4 outColor;
            void main() {
                outColor = vec4(1.0, 1.0, 1.0, 1.0);
            }
        """,
        uniforms={
            'proj': proj,
        }
    )
    glDrawArrays(GL_TRIANGLES, 0, len(tris)//3)

pl.run_window(draw)
