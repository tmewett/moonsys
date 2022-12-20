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

def get_elapsed_time():
    return time() - _start_time

def use_memo(f, *, key=None):
    if key is None: key = id(f)
    if key in _keys:
        return _keys[key]
    print("new key")
    x = f()
    _keys[key] = x
    return x

def use_once(f, *, key=None):
    return use_memo(f, key=key)

def use_program(**stages):
    def new():
        shaders = [
            use_once(lambda: Shader(src, stage), key=src)
            for stage, src in stages.items()
        ]
        print(stages)
        return ShaderProgram(*shaders)
    return use_once(new, key=frozenset(stages.values()))

def use_array_buffer(data, *, key=None):
    if key is None: key = id(data)
    arr = array('f', data)
    buffer = use_once(lambda: BufferObject(array_sizeof(arr)), key=key)
    buffer.set_data(arr.tobytes())
    return buffer

@dataclass
class VAO():
    id: int
    spec: list
    buffer: BufferObject

def new_attributes(spec, buf):
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

def clear_window():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

def run_window(f):
    global _start_time
    _start_time = time()
    window = pyglet.window.Window()
    window.on_draw = f
    pyglet.app.run()
