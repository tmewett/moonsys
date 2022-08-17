require 'init'
local glfw = require("moonglfw")
local gl = require("moongl")

local function reshape(_, w, h)
    gl.viewport(0, 0, w, h)
end
function window(w, h, title)
    if not C.window then
        glfw.window_hint('context version major', 3)
        glfw.window_hint('context version minor', 3)
        glfw.window_hint('opengl profile', 'core')
        C.window = glfw.create_window(w, h, title)
        glfw.set_framebuffer_size_callback(C.window, reshape)
        glfw.make_context_current(C.window)
        gl.init()
    end
    if glfw.window_should_close(C.window) then
        return nil
    end
    glfw.swap_buffers(C.window)
    glfw.poll_events()
    return C.window
end

function vao(arrays)
    C.vao = C.vao or {
        objs = {},
        -- locations = {},
        -- n_locs = 0,
    }
    if not C.vao.objs[arrays] then
        local vao = {names={}}
        vao.id = gl.new_vertex_array()
        for name, data in pairs(arrays) do
            local vbo = gl.new_buffer('array')
            gl.buffer_data('array', data, 'static draw')
            gl.vertex_attrib_pointer(name-1, 4, 'float', false, 0, 0)
            gl.enable_vertex_attrib_array(name-1)
            gl.unbind_buffer('array')
            -- vao.names[name] = i
            -- i=i+1
        end
        C.vao.objs[arrays] = vao
    end
    return C.vao.objs[arrays]
end

function program(t)
    C.progs = C.progs or {}
    local key = t.vertex .. t.fragment
    if not C.progs[key] then
        local prog, vsh, fsh = gl.make_program_s('vertex', t.vertex, 'fragment', t.fragment)
        gl.delete_shaders(vsh, fsh)
        C.progs[key] = prog
    end
    return C.progs[key]
end

function draw(t)
    gl.use_program(t.program)
    gl.bind_vertex_array(t.vao.id)
    gl.draw_arrays('triangles', 0, 3)
end

-- Positions and colors for the triangle's vertices:
local positions = gl.pack('float', {
    -0.5, -0.5,  0.0, 1.0, -- bottom left
    0.5, -0.5,  0.0, 1.0, -- bottom right
    0.0,  0.5,  0.0, 1.0, -- middle top
})

local colors = gl.pack('float', {
    1.0, 0.0, 0.0, 1.0, -- red
    0.0, 1.0, 0.0, 1.0, -- green
    0.0, 0.0, 1.0, 1.0, -- blue
})

local arrays = {positions, colors}

while window(640, 480, "Hello") do
    gl.clear_color(0.0, 0.0, 0.0, 1.0)
    gl.clear("color", "depth")

    draw({
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
