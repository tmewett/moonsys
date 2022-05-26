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

M['string'] = builtin_type('string')
M['table'] = builtin_type('table')
M['number'] = builtin_type('number')
M['function'] = builtin_type('function')

function M.is_type(x, t)
    return t:_test(x)
end

function M.struct(desc)
    return function (args)
        for name, type in pairs(desc) do
            if M.is_type(args[name], type) then
                error("wrong type")
            end
        end
    end
end

return M
