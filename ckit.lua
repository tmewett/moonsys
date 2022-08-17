local M = {}

M.double = {}

M.double.c_name = "double"

function M.double:load_c(var, i)
    return "double "..var.." = (double)luaL_checknumber(L, "..i..");"
end

M.int = {}

function M.int:load_c(var, i)
    return "int "..var.." = (int)luaL_checkinteger(L, "..i..");"
end

M.ptr = {}

function M.ptr:load_c(var, i)
    return "void *"..var.." = lua_touserdata(L, "..i..");"
end

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
        items={},
    }
end

function M.add(m, x)
    m.items[x] = true
end

function M.c_source(m)
    local c_funcs = {}
    local s={}
    s[#s+1] = [[
        #include <lua.h>
        #include <lauxlib.h>
    ]]
    for item,_ in pairs(m.items) do
        if ld.is_type(item, M.func) then
            s[#s+1] = ret_type.." "..name.."(lua_State *L) {"

        end
    end
end

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
