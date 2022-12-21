import numpy as np
import pyglin as pl
import pyglet.math as pm
import trimesh
from pyglet.gl import glDrawArrays, GL_TRIANGLES

mesh = trimesh.creation.icosphere(1)


def draw():
    look = pm.Mat4.look_at(pm.Vec3(pl.get_elapsed_time(), 0., 1.0), pm.Vec3(0., 0., 0.), pm.Vec3(0., 1., 0.))
    persp = pm.Mat4.perspective_projection(1., 0.1, 100.)
    attributes = pl.use_once(lambda: pl.new_attributes(
        [('pos', 3)],
        pl.use_array_buffer(mesh.vertices.ravel()),
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
            'proj': look @ persp,
        }
    )
    pl.draw_elements(pl.use_element_buffer(mesh.faces.ravel()), 'triangles')

pl.run_window(draw)
