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

function M.type(x)
end

return M
