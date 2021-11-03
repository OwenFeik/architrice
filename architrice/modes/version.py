import architrice

from . import mode


class Version(mode.Mode):
    def main():
        print(architrice.__version__)
