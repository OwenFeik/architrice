from . import mode

class AddProfile(mode.Mode):
    def __init__(self):
        super().__init__(
            "a",
            "add-profile",
            "launch wizard to add a new profile",
            [
                "source",
                "target",
                "user",
                "path",
                "include_maybe",
                "name"
            ]
        )
