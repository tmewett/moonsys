import pyglet

from react import Component, component, use, Context, Provider, Memo

@component
def Window(children):
    window = use(Memo(lambda: pyglet.window.Window()))
    return Provider(pyglet.window.Window, window, children)

class _OnEvent(Component):
    def _define_props(window, event, f): pass
    def do(self):
        self.props['window'].set_handler(self.props['event'], self.props['f'])
    def undo(self):
        self.props['window'].remove_handler(self.props['event'], self.props['f'])
