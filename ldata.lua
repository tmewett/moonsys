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
    return t._test(x)
end

function M.struct(desc)
    local function construct(args)
        for name, type in pairs(desc) do
            if not M.is_type(args[name], type) then
                error("wrong type for field "..name)
            end
        end
        return args
    end
    local index = {}
    return setmetatable({}, {__call=construct, __index=index, __newindex=index})
end

return M
