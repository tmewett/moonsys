require 'init'
local glfw = require("moonglfw")
local gl = require("moongl")
local ml = require 'ml'
local nd = require 'ndarray'
local mesh = require 'mesh'

function memo(t, key, f)
    if not t[key] then
        t[key] = f()
    end
    return t[key]
end

function make_key(...)
    local t={}
    for _, x in ipairs({...}) do
        t[#t+1] = tostring(x)
    end
    return ml.tstring(t)
end

function mat4mul(a, b)
    local ab={}
    for i=1,16 do
        ab[i]=0
        for c=1,4 do
            ab[i]=ab[i]+a[(i-1)%4+c*4]*b[(i-1)//4+c]
        end
    end
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
function use_buffer(data, opts)
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

function use_element_buffer(data, opts)
    opts = opts or {}
    if not C.buffers[data] then
        local buf = {}
        buf.id = gl.new_buffer('element array')
        buf.len = #data
        buf.dtype = 'ushort'
        gl.buffer_data('element array', gl.pack(buf.dtype, data), 'static draw')
        C.buffers[data] = buf
    end
    return C.buffers[data]
end

C.vaos = {}
function use_vao(attribs, opts)
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
function use_texture_2D(data, opts)
    local key = data
    return memo(C.textures, key, function ()
        local texture = {}
        texture.id = gl.new_texture('2d')
        texture.target = '2d'
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
function use_program(t)
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
    local v = use_vao(by_loc, {key=opts.program})
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

local texture_types = {
    ['2d']='sampler2D',
}

C.shader_builds = {}
function set_state(opts)
    local uniforms = opts.uniforms or {}
    local textures = opts.textures or {}
    local program = memo(C.shader_builds, make_key(opts.vertex_shader, opts.fragment_shader), function ()
        local s = {}
        for name, at in pairs(opts.attribs) do
            s[#s+1] = ml.expand("in vec$n $name;\n", {n=at.vlen, name=name})
        end
        local vertex_header = table.concat(s)
        s = {}
        for name, spec in pairs(uniforms) do
            s[#s+1] = ml.expand("uniform $type $name;\n", {type=spec[1], name=name})
        end
        local uniform_header = table.concat(s)
        s = {}
        for name, tex in pairs(textures) do
            s[#s+1] = ml.expand("uniform $type $name;\n", {type=texture_types[tex.target], name=name})
        end
        local sampler_header = table.concat(s)
        local vertex_source = "#version 330\n"..vertex_header..uniform_header..opts.vertex_shader
        local fragment_source = "#version 330\n"..sampler_header..uniform_header..opts.fragment_shader
        local prog, vsh, fsh = gl.make_program_s('vertex', vertex_source, 'fragment', fragment_source)
        gl.delete_shaders(vsh, fsh)
        return prog
    end)
    local by_loc = {}
    for name, at in pairs(opts.attribs) do
        local loc = gl.get_attrib_location(program, name)
        assert(loc >= 0, "invalid attribute")
        by_loc[loc] = at
    end
    local vao = use_vao(by_loc, {key=program})
    gl.use_program(program)
    for name, spec in pairs(uniforms) do
        local loc = gl.get_uniform_location(program, name)
        if spec[1] == 'mat4' then
            gl.uniform_matrix(loc, 'float', '4x4', false, table.unpack(np.unravel(spec[2])))
        else
            gl.uniform(loc, spec[1], spec[2])
        end
    end
    -- aliasing?
    local i=0
    for name, tex in pairs(textures) do
        gl.active_texture(i)
        gl.bind_texture(tex.target, tex.id)
        local loc = gl.get_uniform_location(program, name)
        gl.uniform(loc, 'int', i)
        i=i+1
    end
    gl.bind_vertex_array(vao.id)
end

function draw_elements(prim, elems, opts)
    set_state(opts)
    gl.bind_buffer('element array', elems.id)
    gl.draw_elements(prim, elems.len, elems.dtype, 0)
end

local checkerboard = {
    255,255,255, 0,0,0,
    0,0,0, 255,255,255,
}

local win = window(640, 480)

local cube = mesh.cube()
local cube_elems = use_element_buffer(mesh.triangulate(cube))

local arrays = {
    position = {
        buffer=use_buffer(cube.vertices.data),
        vlen=3,
    },
}

while drawing_window(win) do
    gl.clear_color(0.0, 0.0, 0.0, 1.0)
    gl.clear("color", "depth")

    local view_T = nd.look_at_T({
        at={0,0,0},
        from={2,2,0},
    })

    draw_elements('triangles', cube_elems, {
        attribs = arrays,
        vertex_shader = [[
            void main() {
                gl_Position = view_T * vec4(position, 1.0);
            }
        ]],
        fragment_shader = [[
            out vec4 color;
            void main() {
                color = vec4(1.0, 0.,0.,1.);
            }
        ]],
        uniforms={
            view_T={'mat4', view_T}
        }
    })
end
