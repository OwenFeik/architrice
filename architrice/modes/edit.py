from . import mode

class Edit(mode.Mode):
    def __init__(self):
        super().__init__("e", "edit", "edit a profile as JSON")
