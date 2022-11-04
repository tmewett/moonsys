require 'init'
local glfw = require("moonglfw")
local gl = require("moongl")

local function reshape(_, w, h)
    gl.viewport(0, 0, w, h)
end
function window(w, h, title)
    glfw.window_hint('context version major', 3)
    glfw.window_hint('context version minor', 3)
    glfw.window_hint('opengl profile', 'core')
    local win = glfw.create_window(w, h, title)
    glfw.set_framebuffer_size_callback(win, reshape)
    glfw.make_context_current(win)
    gl.init()
    return win
end

function drawing_window(w)
    if glfw.window_should_close(w) then
        return false
    end
    glfw.swap_buffers(w)
    glfw.poll_events()
    return true
end

C.buffers = {}
function buffer(data, opts)
    if not C.buffers[data] then
        local vbo = gl.new_buffer('array')
        gl.buffer_data('array', data, 'static draw')
        C.buffers[data] = vbo
    end
    return C.buffers[data]
end

C.vaos = {}
function vao(attribs)
    if not C.vaos[attribs] then
        local vao = {}
        vao.id = gl.new_vertex_array()
        for i, attrib in pairs(attribs) do
            gl.bind_buffer('array', attrib.buffer)
            gl.vertex_attrib_pointer(i-1, attrib.vlen, 'float', false, attrib.stride or 0, attrib.offset or 0)
            gl.enable_vertex_attrib_array(i-1)
        end
        C.vaos[attribs] = vao
    end
    return C.vaos[attribs]
end

C.progs = {}
function program(t)
    local key = t.vertex .. t.fragment
    if not C.progs[key] then
        local prog, vsh, fsh = gl.make_program_s('vertex', t.vertex, 'fragment', t.fragment)
        gl.delete_shaders(vsh, fsh)
        C.progs[key] = prog
    end
    return C.progs[key]
end

function draw_arrays(prim, start, n, opts)
    gl.use_program(opts.program)
    gl.bind_vertex_array(opts.vao.id)
    gl.draw_arrays(prim, start, n)
end


local win = window(640, 480, "Hello")

-- Positions and colors for the triangle's vertices:
local positions = gl.pack('float', {
    -0.5, -0.5, 0.0, 1.0, -- bottom left
     0.5, -0.5, 0.0, 1.0, -- bottom right
     0.0,  0.5, 0.0, 1.0, -- middle top
})

local colors = gl.pack('float', {
    1.0, 0.0, 0.0, 1.0, -- red
    0.0, 1.0, 0.0, 1.0, -- green
    0.0, 0.0, 1.0, 1.0, -- blue
})

local arrays = {
    {
        buffer=buffer(positions),
        vlen=4,
    },
    {
        buffer=buffer(colors),
        vlen=4,
    },
}

while drawing_window(win) do
    gl.clear_color(0.0, 0.0, 0.0, 1.0)
    gl.clear("color", "depth")

    draw_arrays('triangles', 0, 3, {
        vao = vao(arrays),
        program = program({
            vertex = [[
                #version 330 core
                layout(location=0) in vec4 position;
                layout(location=1) in vec4 color;
                out vec4 Color;

                void main() {
                   gl_Position = position;
                   Color = color;
                }
            ]],
            fragment = [[
                #version 330 core
                in vec4 Color;
                out vec4 out_Color;

                void main() {
                   out_Color = Color;
                }
            ]],
        }),
    })
end
