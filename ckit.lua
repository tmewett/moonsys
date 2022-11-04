local ld = require 'ldata'

local M = {}

M.double = {}

M.double.c_name = "double"

function M.double:load_c(var, i)
    return "double "..var.." = (double)luaL_checknumber(L, "..i..");\n"
end

local integer_type = ld.struct {
    c_name = ld.string,
}

function integer_type:load_c(var, i)
    return self.c_name.." "..var.." = ("..self.c_name..")luaL_checkinteger(L, "..i..");\n"
end

function integer_type:push_c(var)
    return "lua_pushinteger(L, "..var..");\n"
end

M.int = integer_type {
    c_name="int",
}
M.uint = integer_type {
    c_name="unsigned int",
}

M.ptr = {}

function M.ptr:load_c(var, i)
    return "void *"..var.." = lua_touserdata(L, "..i..");\n"
end

function M.ptr:push_c(var)
    return "lua_pushlightuserdata(L, "..var..");\n"
end

M.czstr = {}

function M.czstr:load_c(var, i)
    return "const char *"..var.." = luaL_checkstring(L, "..i..");\n"
end

function M.czstr:push_c(var)
    return "lua_pushstring(L, "..var..");\n"
end

M.void = {}

M.struct = ld.struct {
    ld.string,
    ld.table,
}
M.func = ld.struct {
    ld.string,
    ld.any,
    ld.table,
}

function M.new_module()
    return {
        funcs={},
    }
end

function M.add_func(m, x)
    m.funcs[x] = true
end

function M.c_source(m)
    local c_funcs = {}
    local s={}
    s[#s+1] = [[
        #include <lua.h>
        #include <lauxlib.h>
    ]]
    s[#s+1] = m.before or ""
    for func,_ in pairs(m.funcs) do
        s[#s+1] = "static int _ckit_"..func[1].."(lua_State *L) {\n"
        local vi=1
        for i,arg_type in ipairs(func[3]) do
            s[#s+1] = arg_type:load_c("v"..vi, i)
            vi=vi+1
        end
        if func[2] ~= M.void then
            s[#s+1] = func[2].c_name.." retval = "
        end
        s[#s+1] = func[1].."("
        local call_args = {}
        for arg=1,vi-1 do
            call_args[#call_args+1] = "v"..arg
        end
        s[#s+1] = table.concat(call_args, ",")
        s[#s+1] = ");\n"
        if func[2] ~= M.void then
            -- push retval
        end
        s[#s+1] = "return "
        s[#s+1] = func[2] == M.void and "0" or "1"
        s[#s+1] = ";\n}\n"
    end
    s[#s+1] = [[
        int luaopen_test(lua_State *L) {
            lua_newtable(L);
    ]]
    for func,_ in pairs(m.funcs) do
        s[#s+1] = "lua_pushstring(L, \""..func[1].."\");\nlua_pushcfunction(L, _ckit_"..func[1]..");\nlua_settable(L, -3);\n"
    end
    s[#s+1] = "return 1;\n}\n"
    return table.concat(s)
end

function M.load(m)
    local src = io.open("/tmp/ckit_src.c", "w")
    src:write(M.c_source(m))
    src:close()
    if os.execute("cc -shared -O2 -Werror=implicit /tmp/ckit_src.c -o /tmp/ckit_mod.so") == nil then
        error("failed to compile C source")
    end
    return package.loadlib("/tmp/ckit_mod.so", "luaopen_test")()
end

return M

--[[
a module is
structs; set of {name, type, luaname}
functions; {rettype, name, argtypes}

struct accessors
fieldN(ptr)
with type conversion

wrap funcs
convert all Lua args to C according to declared types
call
convert return value

converting types
Lua index to C variable
push C variable
]]
