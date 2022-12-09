import ctypes
from array import array

import pyglet
from pyglet.graphics.vertexbuffer import BufferObject
from pyglet.graphics.shader import Shader, ShaderProgram
from pyglet.gl import *

_keys = dict()

def array_bytelen(a):
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

def use_program(**types):
    shaders = [
        use_memo(src, lambda: Shader(src, type))
        for type, src in types.items()
    ]
    return use_memo(frozenset(types.values()), lambda: ShaderProgram(*shaders))

def _to_buffer(data):
    buf = BufferObject(array_bytelen(data))
    buf.set_data(data.tobytes())
    return buf

def use_attributes(spec, data):
    buf = use_memo(id(data), lambda: _to_buffer(data))
    vao = GLuint()
    glGenVertexArrays(1, vao)
    glBindVertexArray(vao)
    buf.bind(GL_ARRAY_BUFFER)
    stride = sum(s[1] for s in spec)
    offset = 0
    for i, (name, vlen) in enumerate(spec):
        glVertexAttribPointer(i, vlen, GL_FLOAT, False, stride * ctypes.sizeof(GLfloat), offset * ctypes.sizeof(GLfloat))
        glEnableVertexAttribArray(0)
        offset += vlen


def set_state(**opts):


# def draw_arrays(prim, start, n)

# def use_buffer(data, *, key=None):
#     key = key if key is not None else data
#     def new():
#         return pyglet.graphics.BufferObject()

window = pyglet.window.Window()

vertices = array('f', [
    -0.5, -0.5, 0.0, 1.0,
     0.5, -0.5, 0.0, 1.0,
     0.0,  0.5, 0.0, 1.0,
])

buf = GLuint()
glGenBuffers(1, buf)
glBindBuffer(GL_ARRAY_BUFFER, buf)
glBufferData(GL_ARRAY_BUFFER, array_bytelen(vertices), array_ptr(vertices), GL_STATIC_DRAW)

vao = GLuint()
glGenVertexArrays(1, vao)
glBindVertexArray(vao)
glVertexAttribPointer(0, 4, GL_FLOAT, False, 0, 0)
glEnableVertexAttribArray(0)

# vertex_s = glCreateShader(GL_VERTEX_SHADER)
# glShaderSource(vertex_s, 1, (ctypes.c_char_p * 1)(ctypes.c_char_p("""
# #version 330 core
# layout(location=0) in vec2 position;
# void main()
# {
#     gl_Position = vec4(position, 0.0, 1.0);
# }
# """.encode())), None)
# glCompileShader(vertex_s)

# frag_s = glCreateShader(GL_FRAGMENT_SHADER)
# glShaderSource(frag_s, 1, (ctypes.c_char_p * 1)(ctypes.c_char_p("""
# #version 330 core
# out vec4 outColor;
# void main()
# {
#     outColor = vec4(1.0, 1.0, 1.0, 1.0);
# }
# """.encode())), None)
# glCompileShader(frag_s)

# shaderProgram = glCreateProgram()
# glAttachShader(shaderProgram, vertex_s)
# glAttachShader(shaderProgram, frag_s)
# # glBindFragDataLocation(shaderProgram, 0, "outColor")
# glLinkProgram(shaderProgram)
# glUseProgram(shaderProgram)

@window.event
def on_draw():
    window.clear()
    use_program(
        vertex="""
            #version 330 core
            layout(location=0) in vec2 position;
            void main()
            {
                gl_Position = vec4(position, 0.0, 1.0);
            }
        """,
        fragment="""
            #version 330 core
            out vec4 outColor;
            void main()
            {
                outColor = vec4(1.0, 1.0, 1.0, 1.0);
            }
        """,
    ).use()
    glDrawArrays(GL_TRIANGLES, 0, 3)

pyglet.app.run()
