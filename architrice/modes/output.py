from architrice import caching
from . import common
from . import mode


class AddOutput(mode.Mode):
    def __init__(self):
        super().__init__(
            "o",
            "add-output",
            "add an output to a profile",
            ["target", "path", "include_maybe", "profile"],
        )

    def action(self, cache, args):
        common.add_output(
            cache,
            args.interactive,
            args.profile,
            args.target,
            args.path,
            args.include_maybe,
        )

    def load_cache(self, args):
        return caching.Cache.load(
            source=args.source, user=args.user, name=args.name
        )
