local ck = require 'ckit'

local mod = ck.new_module()
mod.before = [[
    #include <stdlib.h>
    #include <stdio.h>
]]
ck.add_func(mod, ck.func {
    "exit", ck.void, {ck.int},
})
ck.add_func(mod, ck.func {
    "puts", ck.int, {ck.czstr},
})

print(ck.c_source(mod))

local m = ck.load(mod)
m.puts("Hello there")
m.exit(33)
