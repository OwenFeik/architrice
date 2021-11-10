import logging

from .. import caching

from . import common


class Mode:
    ARGUMENT_RESOLUTION_ORDER = [
        "source",
        "target",
        "user",
        "path",
        "include_maybe",
        "name",
        "profile",
        "profiles",
    ]

    def __init__(self, flag, name, explanation, required_args=None):
        self.short = flag
        self.name = name
        self.help = explanation

        # Sort args so that missing args are resolved in the right order.
        self.required_args = sorted(
            required_args or [],
            key=lambda arg: Mode.ARGUMENT_RESOLUTION_ORDER.index(arg),
        )

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

    def resolve_missing_arg(self, cache, arg, args):
        if arg == "source":
            return common.get_source(args.source, args.interactive)
        elif arg == "target":
            return common.get_target(args.target, args.interactive)
        elif arg == "user":
            return common.get_verified_user(
                args.source, args.user, args.interactive
            )
        elif arg == "path":
            return common.get_output_path(
                cache, args.interactive, args.target, args.path
            )
        elif arg == "include_maybe":
            return True  # Defaults to True
        elif arg == "name":
            return None  # Always optional
        elif arg == "profile":
            return common.get_profile(cache, args.interactive)
        elif arg == "profiles":
            return cache.profiles
        else:
            raise ValueError(f"Can't resolve missing argument: {arg}.")

    def arg_is_optional(self, arg):
        return arg == "name"

    def ensure_all_args(self, cache, args):
        for arg in self.required_args:
            if getattr(args, arg, None) is None:
                value = self.resolve_missing_arg(cache, arg, args)
                if value is None and not self.arg_is_optional(arg):
                    logging.error(
                        f"Missing argument: {arg}."
                        f' Unable to complete action "{self.name}".'
                    )
                    return False
                setattr(args, arg, value)
        return True

    def action(self, cache, args):
        raise NotImplementedError()

    def load_cache(self, args):
        return caching.Cache.load()

    def main(self, args):
        cache = self.load_cache(args)
        if self.ensure_all_args(cache, args):
            self.action(cache, args)
        cache.save()


class FilterArgsMode(Mode):
    def load_cache(self, args):
        return caching.Cache.load(
            args.source,
            args.target,
            args.user,
            args.path,
            args.name,
        )
