local D = require 'ldata'
local nd = require 'ndarray'

local M={}

M.mesh = D.struct{
    vertices=nd.ndarray,
    faces=D.table,
    -- normals=nd.ndarray,
}

function M.cube()
    return M.mesh{
        vertices=nd.new_array({
            0.0, 0.0, 0.0,
            0.0, 0.0, 1.0,
            0.0, 1.0, 0.0,
            0.0, 1.0, 1.0,
            1.0, 0.0, 0.0,
            1.0, 0.0, 1.0,
            1.0, 1.0, 0.0,
            1.0, 1.0, 1.0,

            0.0, 0.0, 0.0,
            0.0, 0.0, 1.0,
            0.0, 1.0, 0.0,
            0.0, 1.0, 1.0,
            1.0, 0.0, 0.0,
            1.0, 0.0, 1.0,
            1.0, 1.0, 0.0,
            1.0, 1.0, 1.0,

            0.0, 0.0, 0.0,
            0.0, 0.0, 1.0,
            0.0, 1.0, 0.0,
            0.0, 1.0, 1.0,
            1.0, 0.0, 0.0,
            1.0, 0.0, 1.0,
            1.0, 1.0, 0.0,
            1.0, 1.0, 1.0,
        }, {shape={-1,3}}),
        -- normals=nd.new_array({
        --     -1.0,0.0,0.0,
        --     -1.0,0.0,0.0,
        --     -1.0,0.0,0.0,
        --     -1.0,0.0,0.0,
        --     1.0,0.0,0.0,
        --     1.0,0.0,0.0,
        --     1.0,0.0,0.0,
        --     1.0,0.0,0.0,
        -- }, {shape={-1,3}}),
        faces={
            {1,2,4,3},
            {1+8,5+8,6+8,2+8},
            {1+16,3+16,7+16,5+16},
            {8,5,7,6},
            {8+8,3+8,4+8,7+8},
            {8+16,2+16,6+16,4+16},
        },
    }
end

function M.triangulate(m)
    local t={}
    for _, face in ipairs(m.faces) do
        for i=1,#face-2 do
            t[#t+1] = face[1]
            t[#t+1] = face[i+1]
            t[#t+1] = face[i+2]
        end
    end
    return t
end

return M
