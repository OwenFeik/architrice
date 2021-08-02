#!/bin/python3

from architrice import database
from architrice.targets import mtgo
import argparse
import logging
import os
import subprocess
import sys

from . import caching
from . import cli
from . import sources
from . import targets
from . import utils

APP_NAME = "architrice"

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

To add shortcuts to launch {APP_NAME} alongside Cockatrice, run {APP_NAME} -r.
"""


def get_source(name, picker=False):
    if name is not None:
        if not isinstance(name, str):
            return name

        try:
            if source := sources.get_source(name):
                return source
        except ValueError:
            logging.error(f"Invalid source name: {name}.")
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
            if target := targets.get_target(name):
                return target
        except ValueError:
            logging.error(f"Invalid target name: {name}.")
    if picker:
        return target_picker()
    return None


def target_picker():
    return cli.get_choice(
        [t.NAME for t in targets.targetlist],
        "For which supported MtG client?",
        targets.targetlist,
    )()


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
                return
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


def add_output(cache, interactive, profile, target=None, path=None):
    if profile is None:
        return

    if not (target := get_target(target, interactive)):
        logging.error("No target specified. Unable to add profile.")
        return

    cache.build_output(
        profile, target, get_output_path(cache, interactive, target, path)
    )


def add_profile(
    cache,
    interactive,
    source=None,
    target=None,
    user=None,
    path=None,
    name=None,
):
    if not (source := get_source(source, interactive)):
        logging.error("No source specified. Unable to add profile.")
        return

    if not (user := get_verified_user(source, user, interactive)):
        logging.error("No user provided. Unable to add profile.")
        return

    if name is None and interactive and cli.get_decision("Name this profile?"):
        name = cli.get_string("Profile name")

    profile = cache.build_profile(source, user, name) 

    add_output(
        cache,
        interactive,
        profile,
        target,
        path,
    )

    return profile

def delete_profile(
    cache,
    interactive,
    source=None,
    user=None,
    name=None,
):
    options = cache.profiles

    if not options:
        logging.info("No matching profiles exist, ignoring delete option.")
        return
    elif len(options) == 1:
        logging.info("One profile matches criteria, deleting this.")
        profile = options[0]
    elif interactive:
        profile = cli.get_choice(
            [str(p) for p in options], "Delete which profile?", options
        )
    else:
        logging.error("Multiple profiles match criteria. Skipping delete.")
        return

    cache.remove_profile(profile)


def set_up_shortcuts(interactive, target):
    if not (target or (target := get_target(None, interactive))):
        logging.info(
            "Unable to set up shortcuts as no target has been provided."
        )
        return

    if os.name == "nt":
        from . import relnk

        relnk.relink_shortcuts(
            target.SHORTCUT_NAME,
            not cli.get_decision("Automatically update all shortcuts?"),
        )
    elif os.name == "posix":
        APP_PATH = f"/usr/bin/{APP_NAME}"
        if cli.get_decision(
            f"Add script to run Cockatrice and {target.name} to path?"
        ):
            script_path = os.path.join(utils.DATA_DIR, APP_NAME)
            with open(script_path, "w") as f:
                f.write(
                    f"{target.EXECUTABLE_NAME} > /dev/null 2>&1 &\n"
                    f"{sys.executable} -m {APP_NAME}"
                )
            os.chmod(script_path, 0o755)
            subprocess.call(["sudo", "mv", script_path, APP_PATH])
            logging.info(
                f'Running "{APP_NAME}" will now launch '
                f"{target.name} and run {APP_NAME}."
            )
    else:
        logging.error("Unsupported operating system.")


def parse_args():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-u", "--user", dest="user", help="set username to download decks of"
    )
    parser.add_argument(
        "-s", "--source", dest="source", help="set source website"
    )
    parser.add_argument(
        "-t", "--target", dest="target", help="set target program"
    )
    parser.add_argument(
        "-p", "--path", dest="path", help="set deck file output directory"
    )
    parser.add_argument("-n", "--name", dest="name", help="set profile name")
    parser.add_argument(
        "-a",
        "--add",
        dest="add",
        help="launch wizard to add a new profile",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--delete",
        dest="delete",
        help="launch wizard or use options to delete a profile",
        action="store_true",
    )
    parser.add_argument(
        "-l",
        "--latest",
        dest="latest",
        action="store_true",
        help="download latest deck for user",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        dest="verbosity",
        action="count",
        help="increase output verbosity",
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
    parser.add_argument(
        "-r",
        "--relink",
        dest="relink",
        action="store_true",
        help="create shortcuts for architrice",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    source = sources.get_source(args.source)
    target = targets.get_target(args.target)
    user = args.user and args.user.strip()
    path = utils.expand_path(args.path)

    utils.set_up_logger(
        0 if args.quiet else args.verbosity + 1 if args.verbosity else 1
    )

    cache = caching.Cache.load(source, target, user, path, args.name)

    if args.relink:
        set_up_shortcuts(args.interactive, target)

    if len(sys.argv) == 1 and not cache.profiles:
        profile = add_profile(cache, args.interactive)
        if cli.get_decision(
            "Set up shortcuts to run Architrice?"
        ):
            set_up_shortcuts(args.interactive, profile.outputs[0].target)
    elif args.add:
        add_profile(
            cache, args.interactive, source, target, user, path, args.name
        )

    if args.delete:
        delete_profile(cache, args.interactive, source, user, args.name)

    if not args.skip_update:
        for profile in cache.profiles:
            profile.update(args.latest)

    cache.save()


if __name__ == "__main__":
    main()
