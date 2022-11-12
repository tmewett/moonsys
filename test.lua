require 'init'
local glfw = require("moonglfw")
local gl = require("moongl")
local ml = require 'ml'

function memo(t, key, f)
    if not t[key] then
        t[key] = f()
    end
    return t[key]
end

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
    opts = opts or {}
    if not C.buffers[data] then
        local vbo = {}
        vbo.id = gl.new_buffer('array')
        vbo.dtype = opts.dtype or 'float'
        gl.buffer_data('array', gl.pack(vbo.dtype, data), 'static draw')
        C.buffers[data] = vbo
    end
    return C.buffers[data]
end

C.vaos = {}
function vao(attribs, opts)
    local key = opts.key or attribs
    if not C.vaos[key] then
        local vao = {}
        vao.id = gl.new_vertex_array()
        for i, at in pairs(attribs) do
            local dtype_size = gl.sizeof(at.buffer.dtype)
            gl.bind_buffer('array', at.buffer.id)
            gl.vertex_attrib_pointer(i, at.vlen, 'float', false, (at.stride or 0) * dtype_size, (at.offset or 0) * dtype_size)
            gl.enable_vertex_attrib_array(i)
        end
        C.vaos[key] = vao
    end
    return C.vaos[key]
end

C.textures = {}
-- Create a texture for binding to the GL_TEXTURE_2D target.
function texture2D(data, opts)
    local key = data
    return memo(C.textures, key, function ()
        local texture = gl.new_texture('2d')
        gl.texture_parameter('2d', 'wrap s', 'repeat')
        gl.texture_parameter('2d', 'wrap t', 'repeat')
        gl.texture_parameter('2d', 'min filter', 'nearest')
        gl.texture_parameter('2d', 'mag filter', 'nearest')
        gl.pixel_store('unpack alignment', 1)
        gl.texture_image('2d', opts.lod or 0, 'rgb', 'rgb', 'ubyte', gl.pack('ubyte', data), opts.w, opts.h)
        return texture
    end)
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
    local by_loc = {}
    for var, def in pairs(opts.attribs) do
        local loc = gl.get_attrib_location(opts.program, var)
        assert(loc >= 0, "invalid attribute")
        by_loc[loc] = def
    end
    local v = vao(by_loc, {key=opts.program})
    for unit, targets in pairs(opts.textures or {}) do
        gl.active_texture(unit)
        for t, tex in pairs(targets) do
            gl.bind_texture(t, tex)
        end
    end
    gl.use_program(opts.program)
    for name, spec in pairs(opts.uniforms or {}) do
        local loc = gl.get_uniform_location(opts.program, name)
        gl.uniform(loc, spec[1], spec[2])
    end
    gl.bind_vertex_array(v.id)
    gl.draw_arrays(prim, start, n)
end

local win = window(640, 480)

local data = {
    -0.5, -0.5, 0.0, 1.0, 0.,0.,
     0.5, -0.5, 0.0, 1.0, 7.,3.,
     0.0,  0.5, 0.0, 1.0, 5.,7.,
}

local checkerboard = {
    255,255,255, 0,0,0,
    0,0,0, 255,255,255,
}

local arrays = {
    position = {
        buffer=buffer(data),
        vlen=4,
        stride=6,
    },
    tc = {
        buffer=buffer(data),
        vlen=2,
        stride=6,
        offset=4,
    },
}

while drawing_window(win) do
    gl.clear_color(0.0, 0.0, 0.0, 1.0)
    gl.clear("color", "depth")

    draw_arrays('triangles', 0, 3, {
        attribs = arrays,
        program = program({
            vertex = [[
                #version 330 core
                in vec4 position;
                in vec2 tc;
                out vec2 tc_f;

                void main() {
                   gl_Position = position;
                   tc_f = tc;
                }
            ]],
            fragment = [[
                #version 330 core
                uniform sampler2D tex;
                in vec2 tc_f;
                out vec4 color;

                void main() {
                   color = texture(tex, tc_f);
                }
            ]],
        }),
        textures={
            {['2d']=texture2D(checkerboard, {w=2, h=2})}
        },
        uniforms={
            tex={'int', 0}
        },
    })
end
