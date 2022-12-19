local M = {}

M.proto = {
    new = function (self, t)
        t = t or {}
        t._super = self
        local mt = {__index = self}
        setmetatable(t, mt)
        return t
    end
}

local function builtin_type(s)
    return {
        _test = function (x)
            return type(x) == s
        end
    }
end

M.any = {_test = function (x) return true end}
M.nil_ = {_test = function (x) return x == nil end}

M.string = builtin_type('string')
M.table = builtin_type('table')
M.number = builtin_type('number')
M.func = builtin_type('function')

function M.is_type(x, t)
    local mt = getmetatable(x)
    if mt ~= nil and mt.ldata_type == t then
        return true
    end
    return t._test(x)
end

function M.struct(desc)
    local index = {}
    local function construct(f, args)
        for name, type_ in pairs(desc) do
            if not M.is_type(args[name], type_) then
                error(type(args[name]).." is wrong type for field "..name)
            end
        end
        return setmetatable(args, {__index=index, ldata_type=f})
        -- f is the thing we called, in this case the struct type table we return below
    end
    return setmetatable({}, {__call=construct, __index=index, __newindex=index})
end

return M
