class Mode:
    def __init__(self, required_args):
        self.required_args = required_args

    def has_all_args(self, args):
        for arg in self.required_args:
            if getattr(args, arg) is None:
                return False
        return True
