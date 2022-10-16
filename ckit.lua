local ld = require 'ldata'

local M = {}

M.double = {}

M.double.c_name = "double"

function M.double:load_c(var, i)
    return "double "..var.." = (double)luaL_checknumber(L, "..i..");\n"
end

M.int = {}

function M.int:load_c(var, i)
    return "int "..var.." = (int)luaL_checkinteger(L, "..i..");\n"
end

M.ptr = {}

function M.ptr:load_c(var, i)
    return "void *"..var.." = lua_touserdata(L, "..i..");\n"
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
    for item,_ in pairs(m.funcs) do
        s[#s+1] = "static int _ckit_"..item[1].."(lua_State *L) {\n"
        local vi=1
        for i,arg_type in ipairs(item[3]) do
            s[#s+1] = arg_type:load_c("v"..vi, i)
            vi=vi+1
        end
        s[#s+1] = item[1].."("
        local call_args = {}
        for arg=1,vi-1 do
            call_args[#call_args+1] = "v"..arg
        end
        s[#s+1] = table.concat(call_args, ",")
        s[#s+1] = ");\nreturn 0;\n}\n"
    end
    s[#s+1] = [[
        int luaopen_test(lua_State *L) {
            lua_newtable(L);
    ]]
    for item,_ in pairs(m.funcs) do
        s[#s+1] = "lua_pushstring(L, \""..item[1].."\");\nlua_pushcfunction(L, _ckit_"..item[1]..");\nlua_settable(L, -3);\n"
    end
    s[#s+1] = "return 1;\n}\n"
    return table.concat(s)
end

function M.loader(m)
    local src = io.open("/tmp/ckit_src.c", "w")
    src:write(M.c_source(m))
    src:close()
    if os.execute("cc -shared -O2 -Werror=implicit /tmp/ckit_src.c -o /tmp/ckit_mod.so") == nil then
        error("failed to compile C source")
    end
    return package.loadlib("/tmp/ckit_mod.so", "luaopen_test")
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
