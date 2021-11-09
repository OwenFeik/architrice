import architrice

from . import mode


class Version(mode.Mode):
    def __init__(self):
        super().__init__("v", "version", "print version and exit")

    def main(self, args):
        print(architrice.__version__)
