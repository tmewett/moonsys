import ctypes
from array import array
from dataclasses import dataclass
from time import time

import pyglet
import pyglet.math as pm
from pyglet.graphics.vertexbuffer import BufferObject
from pyglet.graphics.shader import Shader, ShaderProgram
from pyglet.gl import *

_keys = dict()

def array_sizeof(a):
    return a.buffer_info()[1] * a.itemsize

def array_ptr(a):
    return a.buffer_info()[0]

_start_time = time()
def get_elapsed_time():
    return time() - _start_time

def use_memo(key, f):
    if key in _keys:
        return _keys[key]
    print("new key")
    x = f()
    _keys[key] = x
    return x

def use_program(**stages):
    def new():
        shaders = [
            use_memo(src, lambda: Shader(src, stage))
            for stage, src in stages.items()
        ]
        print(stages)
        return ShaderProgram(*shaders)
    return use_memo(frozenset(stages.values()), new)

def _to_buffer(data):
    buf = BufferObject(array_sizeof(data))
    # buf.set_data(data.tobytes())
    glBufferData(GL_ARRAY_BUFFER, array_sizeof(data), array_ptr(data), GL_DYNAMIC_DRAW)
    return buf

@dataclass
class VAO():
    id: int
    spec: list
    buffer: BufferObject

def new_attributes(spec, data):
    buf = _to_buffer(data)
    buf.bind(GL_ARRAY_BUFFER)
    vao = GLuint()
    glGenVertexArrays(1, vao)
    glBindVertexArray(vao)
    stride = sum(s[1] for s in spec)
    offset = 0
    for i, (name, vlen) in enumerate(spec):
        glVertexAttribPointer(i, vlen, GL_FLOAT, False, stride * ctypes.sizeof(GLfloat), offset * ctypes.sizeof(GLfloat))
        glEnableVertexAttribArray(i)
        offset += vlen
    return VAO(id=vao, spec=spec, buffer=buf)

_uniform_types = {
    float: "float",
    pm.Mat4: "mat4",
}

def set_state(*, attributes, vertex_shader, fragment_shader, uniforms={}):
    uniform_header = [f"uniform {_uniform_types[type(value)]} {name};" for name, value in uniforms.items()]
    vertex_src = "\n".join([
        "#version 330 core",
        *uniform_header,
        *[f"layout(location={loc}) in vec{n} {name};" for loc, (name, n) in enumerate(attributes.spec)],
        vertex_shader,
    ])
    fragment_src = "\n".join([
        "#version 330 core",
        *uniform_header,
        fragment_shader,
    ])
    program = use_program(vertex=vertex_src, fragment=fragment_src)
    for name, value in uniforms.items():
        program[name] = value
    program.use()

window = pyglet.window.Window()

cube_vs = [
    0.0, 0.0, 0.0,
    0.0, 0.0, 1.0,
    0.0, 1.0, 0.0,
    0.0, 1.0, 1.0,
    1.0, 0.0, 0.0,
    1.0, 0.0, 1.0,
    1.0, 1.0, 0.0,
    1.0, 1.0, 1.0,

    0.0, 0.0, 0.0,
    0.0, 0.0, 1.0,
    0.0, 1.0, 0.0,
    0.0, 1.0, 1.0,
    1.0, 0.0, 0.0,
    1.0, 0.0, 1.0,
    1.0, 1.0, 0.0,
    1.0, 1.0, 1.0,

    0.0, 0.0, 0.0,
    0.0, 0.0, 1.0,
    0.0, 1.0, 0.0,
    0.0, 1.0, 1.0,
    1.0, 0.0, 0.0,
    1.0, 0.0, 1.0,
    1.0, 1.0, 0.0,
    1.0, 1.0, 1.0,
]

attributes = new_attributes(
    [('pos', 3)],
    array('f', [
        -0.5, -0.5, -0.5,
        0.5, -0.5, -0.5,
        0.0,  0.5, -0.5,
    ]),
)

@window.event
def on_draw():
    proj = pm.Mat4.look_at(pm.Vec3(0., 0., 0.), pm.Vec3(get_elapsed_time(), 0., -1.), pm.Vec3(0., 1., 0.))
    window.clear()
    set_state(
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
    glDrawArrays(GL_TRIANGLES, 0, 3)

pyglet.app.run()
