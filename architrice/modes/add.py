from . import mode

class Add(mode.Mode):
    def __init__(self):
        super().__init__("a", "add", "launch wizard to add a new profile")
