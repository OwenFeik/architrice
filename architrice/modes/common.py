import logging
import os

from .. import database
from .. import sources
from .. import targets
from .. import utils

from . import cli


def get_source(name, picker=False):
    if name is not None:
        if not isinstance(name, str):
            return name

        try:
            return sources.get(name, True)
        except ValueError as e:
            logging.error(str(e))
    if picker:
        return source_picker()
    return None


def source_picker():
    return cli.get_choice(
        [s.NAME for s in sources.sourcelist],
        "Download from which supported decklist website?",
        sources.sourcelist,
    )()


def get_target(name, picker=False):
    if name is not None:
        if not isinstance(name, str):
            return name

        try:
            return targets.get(name)
        except ValueError as e:
            logging.error(str(e))
    if picker:
        return target_picker()
    return None


def target_picker():
    return cli.get_choice(
        [t.NAME for t in targets.targetlist],
        "For which supported MtG client?",
        targets.targetlist,
    )()


def get_profile(cache, interactive, prompt="Choose a profile"):
    if not cache.profiles:
        logging.error("No profiles, unable to select one.")
        return None

    if len(cache.profiles) == 1:
        logging.info("Defaulted to only profile which matches criteria.")
        return cache.profiles[0]
    elif interactive:
        return cli.get_choice(
            [str(p) for p in cache.profiles], prompt, cache.profiles
        )
    else:
        logging.error("Multiple profiles match criteria.")
        return None


def get_verified_user(source, user, interactive=False):
    if not user:
        if interactive:
            user = cli.get_string(source.name + " username")
        else:
            return None

    if not (
        database.select_one("users", source=source.short, name=user)
        or source.verify_user(user)
    ):
        if interactive:
            print("Couldn't find any public decks for this user. Try again.")
            return get_verified_user(source, None, True)
        else:
            return None
    return user


def get_output_path(cache, interactive, target, path):
    if path is not None:
        if utils.check_dir(path):
            return path
        else:
            logging.error(
                f"A file exists at {path} so it can't be used as an output "
                "directory."
            )
            if not interactive:
                return None
            path = None

    existing_output_dirs = cache.get_all_output_dirs()
    if existing_output_dirs and cli.get_decision(
        "Use existing output directory?"
    ):
        if len(existing_output_dirs) == 1:
            path = existing_output_dirs[0].path
            logging.info(f"Only one existing directory, defaulting to {path}.")
        else:
            path = cli.get_choice(
                [d.path for d in existing_output_dirs],
                "Which existing directory should be used for these decks?",
            )
    else:
        path = target.suggest_directory()
        if not (
            (os.path.isdir(path))
            and cli.get_decision(
                f"Found {target.name} deck directory at {path}."
                " Output decklists here?"
            )
        ):
            return get_output_path(
                cache, interactive, target, cli.get_path("Output directory")
            )
    return path


def add_output(
    cache, interactive, profile, target=None, path=None, include_maybe=None
):
    if profile is None:
        profile = get_profile(
            cache, interactive, "Add an output to which profile?"
        )
        if not profile:
            logging.error("No profile specified. Unable to add output.")
            return

    target = get_target(target, interactive)
    if not target:
        logging.error("No target specified. Unable to add output.")
        return

    path = get_output_path(cache, interactive, target, path)
    if not path:
        logging.error("No path specified. Unable to add output.")
        return

    if include_maybe is None:
        include_maybe = cli.get_decision(
            "Include maybeboards in the decks downloaded?"
        )

    cache.build_output(profile, target, path, include_maybe)
