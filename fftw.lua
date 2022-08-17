local ck = require 'ckit'

local mod = ck.new_module()
ck.add(mod, ck.func {
    "fftw_plan_dft_r2c_1d",
    "fftw_plan", {ck.int, ck.ptr, ck.ptr},
})
