import logging

from . import mode


class Sync(mode.FilterArgsMode):
    def __init__(self):
        super().__init__("s", "sync", "sync decklists", ["profiles"])

    def action(self, cache, args):
        if args.profiles:
            for profile in args.profiles:
                profile.download_all()
        else:
            logging.info(
                "No matching profiles to sync."
                ' Add one with "python -m architrice -a"'
            )
