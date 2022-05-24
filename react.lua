local M = {}

function M.new_root(comp)
end

--[[
    render comp to vnode
        if vnode type is different, delete the whole subtree
        copy props into vnode
        if no updates (?), skip
        call render method
        render each child to corresponding vnode, creating as needed
    reconcile new node with old
        if different type, unmount old and mount new
        call did_update
        unmount removed children from new
        mount added children
        reconcile common children
]]

--[[ Build a component into a full virtual node. ]]
function M.build(comp, vnode)
    if ld.type(vnode.comp) ~= ld.type(comp) then
        reset_node(vnode, comp)
    end
    vnode.comp.props = comp.props
    vnode.comp:did_update()
    local tree = vnode.comp:build()
    for k,v in pairs(vnode.children) do
        if not tree[k] then
            unmount(vnode, k)
        end
    end
    for k,v in pairs(tree) do
        local child_node = vnode.children[k] or new_node()
        M.build(v, child_node)
        if vnode.children[k] == nil
            v.comp:did_mount()
            vnode.children[k] = child_node
        end
    end
end

return M
