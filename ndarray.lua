local D = require 'ldata'

local M = {}

M.ndarray_t = D.struct {
    shape = D.table,
    strides = D.table,
    offsets = D.table,
    data = D.table,
}

M.slice = D.struct {
    D.number,
    D.number,
}

function M.array(tbl)
    return M.ndarray_t{
        shape = {#tbl},
        strides = {1},
        offsets = {0},
        data = tbl,
    }
end

function M.index(a, spec)
    local index = {}
    local scalar = true
    for i=1,#a.shape do
        local s = spec[i] or {}
        if type(s) == 'table' then
            scalar = false
            s[1] = s[1] or 1
            s[2] = s[2] or a.shape[i]
        end
        index[i] = s
    end
    if scalar then
        local i = a.offset
        for dim, stride in ipairs(a.strides) do
            i = i + stride * index[dim]
        end
        return a.data[i]
    else
        local shape = {}
        local offsets = {}
        for i=1,#a.shape do
            if type(index[i]) == 'number' then
                shape[i] = 1
                offsets[i] = a.offsets[i] + index[i] * a.strides[i]
            else
                shape[i] = index[i][2] - index[i][1] + 1
                offsets[i] = a.offsets[i] + index[i][1] * a.strides[i]
            end
        end
        return M.ndarray_t{
            shape = shape,
            strides = a.strides,
            offsets = offsets,
            data = a.data,
        }
    end
end

local ml = require 'ml'
a=M.array({1,2,3})

return M
