from . import common
from . import cli
from . import mode


class AddProfile(mode.Mode):
    def __init__(self):
        super().__init__(
            "a",
            "add-profile",
            "launch wizard to add a new profile",
            ["source", "target", "user", "path", "include_maybe", "name"],
        )

    def action(self, cache, args):
        name = args.name
        if (
            name is None
            and args.interactive
            and cli.get_decision("Name this profile?")
        ):
            name = cli.get_string("Profile name")

        profile = cache.build_profile(args.source, args.user, name)

        common.add_output(
            cache,
            args.interactive,
            profile,
            args.target,
            args.path,
            args.include_maybe,
        )

        return profile
