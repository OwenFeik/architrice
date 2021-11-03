import argparse

class Mode(argparse.Action):
    def __init__(self, flag, name, explanation, required_args = None):
        self.short = flag
        self.name = name
        self.help = explanation
        self.required_args = required_args or []

    @property
    def flag(self):
        return "-" + self.short

    @property
    def long(self):
        return "--" + self.name

    def has_all_args(self, args):
        for arg in self.required_args:
            if getattr(args, arg) is None:
                return False
        return True
