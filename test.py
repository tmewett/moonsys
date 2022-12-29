import math

import numpy as np
import pyglin as pl
import pyglet.math as pm
import trimesh

mesh = trimesh.creation.icosahedron()

data = np.block([mesh.vertices, mesh.vertex_normals])

def describe(*, draws, **_):
    persp = pm.Mat4.perspective_projection(1.5, 0.1, 100.)
    @draws.subscribe
    def draw(opts):
        t = opts['time']
        look = pm.Mat4.look_at(pm.Vec3(3.*math.sin(t), 0., 3.*math.cos(t)), pm.Vec3(0., 0., 0.), pm.Vec3(0., 1., 0.))
        attributes = pl.use_once(lambda: pl.new_attributes(
            [('pos', 3), ('norm', 3)],
            pl.use_array_buffer(data.ravel()),
        ))
        pl.clear_window()
        pl.set_state(
            attributes=attributes,
            vertex_shader="""
                out vec3 normV;
                void main() {
                    gl_Position = proj * vec4(pos, 1.0);
                    normV=norm;
                }
            """,
            fragment_shader="""
                in vec3 normV;
                out vec4 outColor;
                void main() {
                    outColor = vec4((normV.x + 1.0)/2, 0.1, 0.5, 1.0);
                }
            """,
            uniforms={
                'proj': look @ persp,
            }
        )
        pl.draw_elements(pl.use_element_buffer(mesh.faces.ravel()), 'triangles')

pl.run_window(describe)
