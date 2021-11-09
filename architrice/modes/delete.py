from . import mode


class DeleteProfile(mode.FilterArgsMode):
    def __init__(self):
        super().__init__(
            "d",
            "delete",
            "launch wizard or use options to delete a profile",
            ["profile"],
        )

    def action(self, cache, args):
        cache.remove_profile(args.profile)
