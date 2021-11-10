import logging

from . import mode


class Latest(mode.FilterArgsMode):
    def __init__(self):
        super().__init__("l", "latest", "download latest deck for user")

    def action(self, cache, args):
        if args.profiles:
            for profile in args.profiles:
                profile.download_latest()
        else:
            logging.info(
                "No matching profiles to sync."
                ' Add one with "python -m architrice -a".'
            )
