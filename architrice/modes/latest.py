from . import mode

class Latest(mode.Mode):
    def __init__(self):
        super().__init__("l", "latest", "download latest deck for user")
