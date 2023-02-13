from refs import Ref, Computed

x = Ref(1)
xx = Computed(lambda: 2*x())
