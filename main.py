import ctypes
from array import array
from dataclasses import dataclass

import pyglet
from pyglet.graphics.vertexbuffer import BufferObject
from pyglet.graphics.shader import Shader, ShaderProgram
from pyglet.gl import *

_keys = dict()

def array_sizeof(a):
    return a.buffer_info()[1] * a.itemsize

def array_ptr(a):
    return a.buffer_info()[0]

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

def new_attributes(spec, data):
    buf = _to_buffer(data)
    buf.bind(GL_ARRAY_BUFFER)
    vao = GLuint()
    glGenVertexArrays(1, vao)
    glBindVertexArray(vao)
    stride = sum(s[1] for s in spec)
    offset = 0
    for i, (name, vlen) in enumerate(spec):
        print(i, vlen, GL_FLOAT, False, stride * ctypes.sizeof(GLfloat), offset * ctypes.sizeof(GLfloat))
        glVertexAttribPointer(i, vlen, GL_FLOAT, False, stride * ctypes.sizeof(GLfloat), offset * ctypes.sizeof(GLfloat))
        glEnableVertexAttribArray(i)
        offset += vlen
    return VAO(id=vao, spec=spec)

def set_state(*, attributes, vertex_shader, fragment_shader):
    vertex_src = "\n".join([
        "#version 330 core",
        *[f"layout(location={loc}) in vec{n} {name};" for loc, (name, n) in enumerate(attributes.spec)],
        vertex_shader,
    ])
    fragment_src = "\n".join([
        "#version 330 core",
        fragment_shader,
    ])
    program = use_program(vertex=vertex_src, fragment=fragment_src)
    program.use()

window = pyglet.window.Window()

attributes = new_attributes(
    [('pos', 4)],
    array('f', [
        -0.5, -0.5, 0.0, 1.0,
        0.5, -0.5, 0.0, 1.0,
        0.0,  0.5, 0.0, 1.0,
    ]),
)

@window.event
def on_draw():
    window.clear()
    set_state(
        attributes=attributes,
        vertex_shader="""
            void main() {
                gl_Position = pos;
            }
        """,
        fragment_shader="""
            out vec4 outColor;
            void main() {
                outColor = vec4(1.0, 1.0, 1.0, 1.0);
            }
        """,
    )
    glDrawArrays(GL_TRIANGLES, 0, 3)

pyglet.app.run()
