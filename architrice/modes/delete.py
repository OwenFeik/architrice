from . import mode

class Delete(mode.Mode):
    def __init__(self):
        super().__init__(
            "d", "delete", "launch wizard or use options to delete a profile"
        )
