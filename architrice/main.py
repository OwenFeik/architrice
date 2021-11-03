#!/bin/python3

import argparse
import json
import logging
import os
import subprocess
import sys

import architrice

from . import modes

from . import caching
from . import cli
from . import database
from . import sources
from . import targets
from . import utils

APP_NAME = utils.APP_NAME

DESCRIPTION = f"""
{APP_NAME} is a tool to download decks from online sources to local directories.
To set up, run {APP_NAME} with no arguments. This will run a wizard to set up a
link between an online source and a local directory. Future runs of {APP_NAME}
will then download all decklists that have been updated or created since the
last run to that directory. 

To add another download profile beyond this first one, run {APP_NAME} -a.

To delete an existing profile, run {APP_NAME} -d, which will launch a wizard to
do so.

To download only the most recently updated decklist for each profile, run
{APP_NAME} -l.

To set up a new profile or delete a profile without CLI, specify
non-interactivity with the -i or --non-interactive flag and use the flags for
source, user, target, path and name as in 
{APP_NAME} -i -s SOURCE -u USER -t TARGET -p PATH -n NAME -a
Replace -a with -d to delete instead of creating. 

To skip updating decklists while using other functionality, include the -k flag.

To add shortcuts to launch {APP_NAME}, run {APP_NAME} -r.
"""


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


def verify_output_json(output, i="\b"):
    if not "target" in output:
        logging.error(f"Output {i} is missing a target.")
        return False
    elif not isinstance(output["target"], str):
        logging.error("Output targets must be strings.")
        return False

    try:
        targets.get(output["target"], True)
    except ValueError as e:
        logging.error(str(e))
        return False

    if not "output_dir" in output:
        logging.error(f"Output {i} is missing an output directory.")
        return False
    elif not isinstance(output["output_dir"], str):
        logging.error("Output directories must be strings.")
        return False

    output["output_dir"] = utils.expand_path(output["output_dir"])
    if not utils.check_dir(output["output_dir"]):
        logging.error(f"Output directory {i} already exists and is a file.")
        return False

    if "include_maybe" in output:
        if not isinstance(output["include_maybe"], bool):
            logging.error(
                "The include_maybe flag of an Output must be a string."
            )
            return False
    else:
        output["include_maybe"] = False

    return True


def verify_profile_json(data):
    if not "source" in data:
        logging.error("Profile is missing a source.")
        return False
    elif not isinstance(data["source"], str):
        logging.error("Source must be a string.")
        return False

    try:
        source = sources.get(data["source"], True)
    except ValueError as e:
        logging.error(str(e))
        return False

    if not "user" in data:
        logging.error("Profile is missing a user.")
        return False
    elif not isinstance(data["user"], str):
        logging.error("User must be a string.")
        return False

    if get_verified_user(source, data.get("user")) is None:
        return False

    if "name" in data and not (
        data["name"] is None or isinstance(data["name"], str)
    ):
        logging.error("Name must be a string.")
        return False

    if not "outputs" in data:
        data["outputs"] = []

    if not isinstance(data["outputs"], list):
        logging.error("Outputs must be in a list.")
        return False

    for i, output in enumerate(data.get("outputs")):
        if not verify_output_json(output, i):
            return False

    return True


def edit_profile_json(cache):
    profile = get_profile(cache, "Edit which profile as JSON?")
    if profile is None:
        return

    editing = json.dumps(profile.to_json(), indent=4)

    while True:
        try:
            editing = cli.get_text_editor(editing, "profile.json")
            edited_json = json.loads(editing)
            if verify_profile_json(edited_json):
                break
        except json.JSONDecodeError:
            logging.error("Failed to parse edited JSON.")

        if not cli.get_decision("Try again?"):
            return

    new_profile = cache.build_profile(
        sources.get(edited_json["source"]),
        edited_json["user"],
        edited_json["name"],
    )

    # In the case that the new profile is redundant wtih an existing profile,
    # the same object is reused, so we don't want to remove it.
    if new_profile is not profile:
        cache.remove_profile(profile)

    for output in edited_json["outputs"]:
        cache.build_output(
            new_profile,
            targets.get(output["target"]),
            output["output_dir"],
            output["include_maybe"],
        )
    logging.info("Successfully updated profile.")


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

    existing_output_dirs = caching.OutputDir.get_all()
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


def add_profile(
    cache,
    interactive,
    source=None,
    target=None,
    user=None,
    path=None,
    include_maybe=None,
    name=None,
):
    source = get_source(source, interactive)
    if not source:
        logging.error("No source specified. Unable to add profile.")
        return

    user = get_verified_user(source, user, interactive)
    if not user:
        logging.error("No user provided. Unable to add profile.")
        return

    if name is None and interactive and cli.get_decision("Name this profile?"):
        name = cli.get_string("Profile name")

    profile = cache.build_profile(source, user, name)

    add_output(cache, interactive, profile, target, path, include_maybe)

    return profile


def delete_profile(cache, interactive):
    profile = get_profile(cache, interactive, "Delete which profile?")

    if profile:
        cache.remove_profile(profile)
    else:
        return


def set_up_shortcuts(interactive, target):
    pass # moved to mdoes/relnk.py

def add_data_args(parser):
    # These arguments are prefixed with an underscore because they are
    # processed into non-underscored replacements with application objects.
    parser.add_argument(
        "-u", "--user", dest="_user", help="set username to download decks of"
    )
    parser.add_argument(
        "-s", "--source", dest="_source", help="set source website"
    )
    parser.add_argument(
        "-t", "--target", dest="_target", help="set target program"
    )
    parser.add_argument(
        "-p", "--path", dest="_path", help="set deck file output directory"
    )
    parser.add_argument(
        "-m",
        "--maybeboard",
        dest="_include_maybe",
        help="include maybeboard in output sideboard",
        nargs="?",
        const=1,
    )
    # Any string is admissable for a profile name.
    parser.add_argument("-n", "--name", dest="name", help="set profile name")
    # various flags    
    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        action="store_true",
        help="add an output to a profile",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        action="store_true",
        help="disable logging to stdout",
    )
    parser.add_argument(
        "-i",
        "--non-interactive",
        dest="interactive",
        action="store_false",
        help="disable interactivity (for scripts)",
    )
    parser.add_argument(
        "-k",
        "--skip-update",
        dest="skip_update",
        action="store_true",
        help="skip updating decks",
    )

def process_args(args):
    args.source = sources.get(args._source)
    args.target = targets.get(args._target)
    args.user = args.user and args._user.strip()
    args.path = utils.expand_path(args._path)
    args.include_maybe = args._include_maybe and bool(args._include_maybe)

    return args

def main():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    add_data_args(parser)

    for mode in modes.modelist:
        parser.add_argument(
            mode.flag,
            mode.long,
            dest=mode.name,
            action="store_true",
            help=mode.help
        )

    args = process_args(parser.parse_args())

    selected_modes = []

    for mode in modes.modelist:
        if getattr(args, mode.name):
            selected_modes.append(mode)


def main_old():
    args = parse_args()
    source = sources.get(args.source)
    target = targets.get(args.target)
    user = args.user and args.user.strip()
    path = utils.expand_path(args.path)
    include_maybe = args.include_maybe and bool(args.include_maybe)

    print(args)
    exit()

    utils.set_up_logger(0 if args.quiet else 1)

    if args.version:
        print(architrice.__version__)
        exit()

    if args.output:
        cache = caching.Cache.load(source, None, user, None, None, args.name)
    else:
        cache = caching.Cache.load(
            source, target, user, path, include_maybe, args.name
        )

    if args.relink:
        set_up_shortcuts(args.interactive, target)

    if len(sys.argv) == 1 and not cache.profiles:
        profile = add_profile(cache, args.interactive)

        if profile.outputs[0].target.SUPPORTS_RELNK and cli.get_decision(
            "Set up shortcuts to run Architrice?"
        ):
            set_up_shortcuts(args.interactive, profile.outputs[0].target)
    elif args.add:
        add_profile(
            cache,
            args.interactive,
            source,
            target,
            user,
            path,
            include_maybe,
            args.name,
        )

    if args.output:
        add_output(cache, args.interactive, None, target, path, include_maybe)

    if args.edit:
        if not args.interactive:
            logging.info(
                "Interactivity required to edit as JSON. Ignoring -e flag."
            )
        else:
            edit_profile_json(cache)

    if args.delete:
        delete_profile(cache, args.interactive)
        exit()

    if not args.skip_update:
        for profile in cache.profiles:
            profile.update(args.latest)

    cache.save()


if __name__ == "__main__":
    main()
