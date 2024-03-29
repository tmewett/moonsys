import ctypes
from array import array
from dataclasses import dataclass
from time import time

import pyglet
import pyglet.math as pm
import reactivex
from pyglet.graphics.vertexbuffer import BufferObject
from pyglet.graphics.shader import Shader, ShaderProgram
from pyglet.gl import *

def array_sizeof(a):
    return a.buffer_info()[1] * a.itemsize

def array_ptr(a):
    return a.buffer_info()[0]

_keys = dict()
_provided = dict()

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

def obtain(name):
    return _provided.get(name)

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

def use_element_buffer(data, *, key=None):
    if key is None: key = id(data)
    arr = array('H', data)
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

def set_state(*, attributes, vertex_shader, fragment_shader, passthrough=[], uniforms={}):
    attr_lengths = dict(attributes.spec)
    uniform_header = [f"uniform {_uniform_types[type(value)]} {name};" for name, value in uniforms.items()]
    vertex_src = "\n".join([
        "#version 330 core",
        *uniform_header,
        *[f"layout(location={loc}) in vec{n} {name};" for loc, (name, n) in enumerate(attributes.spec)],
        *[f"out vec{attr_lengths[name]} attr_{name};" for name in passthrough],
        vertex_shader,
        "void main() { doStage();",
        *[f"attr_{name} = {name};" for name in passthrough],
        "}",
    ])
    fragment_src = "\n".join([
        "#version 330 core",
        *uniform_header,
        *[f"in vec{attr_lengths[name]} attr_{name};" for name in passthrough],
        fragment_shader,
        "void main() { doStage(); }",
    ])
    program = use_program(vertex=vertex_src, fragment=fragment_src)
    for name, value in uniforms.items():
        program[name] = value
    program.use()

def clear_window():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

_modes = {
    'triangles': GL_TRIANGLES,
}

def draw_elements(ebuf, mode, count=None, offset=0):
    if count is None:
        count = ebuf.size // ctypes.sizeof(GLushort)
    ebuf.bind(GL_ELEMENT_ARRAY_BUFFER)
    glDrawElements(_modes[mode], count, GL_UNSIGNED_SHORT, offset)

def run_window(f):
    draws = reactivex.Subject()
    _provided['draws'] = draws
    window = pyglet.window.Window()
    f()
    @window.event
    def on_draw():
        draws.on_next({'time': time()})
    glEnable(GL_DEPTH_TEST)
    # def on_update(dt):
    #     ctx.updates.on_next(time() - ctx._start_time)
    # ctx._start_time = time()
    # ctx.updates.on_next(0.0)
    # pyglet.clock.schedule_interval(on_update, 0.1)
    pyglet.app.run()
