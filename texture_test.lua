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

local win = window(640, 480, "Hello")

local data = gl.pack('float', {
    -0.5, -0.5, 0.0, 1.0, 0.0, 0.0,
     0.5, -0.5, 0.0, 1.0, 2.0, 10.0,
     0.0,  0.5, 0.0, 1.0, 7.0, 8.0,
})

local sizeof_float = gl.sizeof('float')
local buf = gl.new_buffer('array')
gl.buffer_data('array', data, 'static draw')
local vao = gl.new_vertex_array()
gl.vertex_attrib_pointer(0, 4, 'float', false, 6*sizeof_float, 0)
gl.enable_vertex_attrib_array(0)
gl.vertex_attrib_pointer(1, 2, 'float', false, 6*sizeof_float, 4*sizeof_float)
gl.enable_vertex_attrib_array(1)

gl.active_texture(0)
local texture = gl.new_texture('2d')
gl.texture_parameter('2d', 'wrap s', 'repeat')
gl.texture_parameter('2d', 'wrap t', 'repeat')
gl.texture_parameter('2d', 'min filter', 'nearest')
gl.texture_parameter('2d', 'mag filter', 'nearest')
gl.pixel_store('unpack alignment', 1)
gl.texture_image('2d', 0, 'rgb', 'rgb', 'ubyte', gl.pack('ubyte', {
    -- 255, 0, 0, 255,
    255, 255, 255, 0,0,0,
    0,0,0, 255,255,255,
}), 2, 2)
gl.generate_mipmap('2d')

local prog, vsh, fsh = gl.make_program_s('vertex', [[
    #version 330 core
    layout(location=0) in vec4 position;
    layout(location=1) in vec2 tex_v;
    out vec2 tex;

    void main() {
       gl_Position = position;
       tex = tex_v;
    }
]], 'fragment', [[
    #version 330 core
    in vec2 tex;
    out vec4 out_Color;

    uniform sampler2D smpl;

    void main() {
        out_Color = texture(smpl, tex);
    }
]])
gl.delete_shaders(vsh, fsh)
gl.use_program(prog)
gl.uniform(gl.get_uniform_location(prog, "smpl"), 'int', 0)

while drawing_window(win) do
    gl.clear_color(0.0, 0.0, 0.0, 1.0)
    gl.clear("color", "depth")

    -- gl.use_program(prog)
    -- gl.bind_vertex_array(vao)
    gl.draw_arrays('triangles', 0, 3)
end
