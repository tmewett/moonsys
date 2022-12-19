local D = require 'ldata'

local M = {}
local ml = require 'ml'

M.ndarray = D.struct {
    shape = D.table,
    strides = D.table,
    offsets = D.table,
    data = D.table,
    size = D.number,
}

M.slice = D.struct {
    D.number,
    D.number,
}

function M.new_array(tbl, opts)
    opts = opts or {}
    local shape = opts.shape or {#tbl}
    local prod = 1
    local auto_dim
    for i, s in ipairs(shape) do
        if s == -1 then
            assert(auto_dim == nil, "cannot have more than one -1 in shape array")
            auto_dim = i
        else
            prod = prod * s
        end
    end
    if auto_dim ~= nil then
        shape[auto_dim] = #tbl // prod
    end
    local strides = {}
    local offsets = {}
    prod = 1
    for i=#shape,1,-1 do
        strides[i] = prod
        offsets[i] = 0
        prod = prod * shape[i]
    end
    return M.ndarray{
        shape = shape,
        strides = strides,
        offsets = offsets,
        data = tbl,
        size=prod,
    }
end

local function fill_index(a, spec)

end

M.etc = {}

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
        local i = 0
        for dim, stride in ipairs(a.strides) do
            i = i + a.offsets[dim] + stride * index[dim]
        end
        return a.data[i+1]
    else
        local shape = {}
        local offsets = {}
        for i=1,#a.shape do
            if type(index[i]) == 'number' then
                shape[i] = 1
                offsets[i] = a.offsets[i] + (index[i] - 1) * a.strides[i]
            else
                shape[i] = index[i][2] - index[i][1] + 1
                offsets[i] = a.offsets[i] + (index[i][1] - 1) * a.strides[i]
            end
        end
        return M.ndarray{
            shape = shape,
            strides = a.strides,
            offsets = offsets,
            data = a.data,
        }
    end
end

function M.unravel(a)
    local ra={}
    -- i//shape_mods[d] is the unwrapped index into dim d we are at unravelled index i.
    local shape_mods={}
    local prod=1
    for d=#a.shape,1,-1 do
        shape_mods[d] = prod
        prod=prod*a.shape[d]
    end
    for ri=1,prod do
        local i=0
        for d, m in ipairs(shape_mods) do
            -- ((ri-1)//m) is an unwrapped counter for how many steps into dim d we are.
            -- Mod it by the shape to wrap it and obtain the index for that dim.
            i = i + a.offsets[d] + ((ri-1)//m) % a.shape[d] * a.strides[d]
        end
        ra[ri] = a.data[i+1]
    end
    return ra
end

function M.matmul(a, b)
    -- assuming column-major: dim 1 is horiz, dim 2 is vert
    assert(#a.shape == #b.shape and #a.shape == 2)
    assert(a.shape[1] == b.shape[2])
    local ra = M.unravel(a)
    local rb = M.unravel(b)
    local rab = {}
    local acl = a.shape[2] -- column length for a
    local brl = b.shape[1] -- row length for b
    local depth = a.shape[1]
    for i=0,acl*brl-1 do
        rab[i+1]=0
        local fir=i%acl -- first ra index of element in relevant row
        local fic=i//depth*depth -- first rb index of element in relevant column
        -- print("firsts", fir, fic)
        for d=0,depth-1 do
            -- print("indices", fir+d*acl, fic+d)
            rab[i+1]=rab[i+1]+ra[fir+d*acl+1]*rb[fic+d+1]
        end
    end
    return M.new_array(rab, {shape={brl, acl}})
end

function M.cross(a, b)
    local ra = M.unravel(a)
    local rb = M.unravel(b)
    return M.new_array({
        ra[2]*rb[3]-ra[3]*rb[2],
        ra[3]*rb[1]-ra[1]*rb[3],
        ra[1]*rb[2]-ra[2]*rb[1],
    })
end

function M.length(a)
    local l=0
    for _, x in ipairs(a) do
        l = l + x*x
    end
    return math.sqrt(l)
end

function M.normal(a)
    local v={}
    local l = M.length(a)
    for i, x in ipairs(a) do
        v[i] = x / l
    end
    return v
end

function M.sub(a,b)
    local v={}
    for i, x in ipairs(a) do
        v[i] = x - b[i]
    end
    return v
end

function M.look_at_T(opts)
    local zhat = M.normal(M.sub(opts.at, opts.from))
    local xhat = M.normal(M.cross(opts.up or {0,1,0}, zhat))
    local yhat = M.cross(zhat, xhat)
    local rot_T = M.new_array({
        xhat[1], xhat[2], xhat[3], 0,
        yhat[1], yhat[2], yhat[3], 0,
        zhat[1], zhat[2], zhat[3], 0,
        0, 0, 0, 1,
    }, {shape={-1, 4}})
    local tl_T = M.new_array({
        1,0,0,0,
        0,1,0,0,
        0,0,1,0,
        -from[1],-from[2],-from[3], 1,
    }, {shape={-1, 4}})
    return M.matmul(rot_T, tl_T)
end

local function see(a)
    print(ml.tstring(M.unravel(a)))
end

local function test()
    local a=M.new_array({1,2,3,4})
    print(ml.tstring(a))
    a=M.new_array({1,0,0,2}, {shape={-1,2}})
    a=M.matmul(a,a)
    see(a)
end

test()

return M
