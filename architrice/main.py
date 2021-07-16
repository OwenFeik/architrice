#!/bin/python3

import argparse
import logging
import os
import re
import subprocess
import sys

from . import caching
from . import cli
from . import utils

# Sources
from . import sources

# Targets
from . import cockatrice

target = cockatrice

APP_NAME = "architrice"

DESCRIPTION = f"""
{APP_NAME} is a tool to download decks from online sources to local directories.
To set up, run {APP_NAME} with no arguments. This will run a wizard to set up a
link between an online source and a local directory. Future runs of {APP_NAME}
will then download all decklists that have been updated or created since the
last run to that directory. 

To add another download profile beyond this first one, run {APP_NAME} -n.

To delete an existing profile, run {APP_NAME} -d, which will launch a wizard to
do so.

To download only the most recently updated decklist for each profile, run
{APP_NAME} -l.

To set up a new profile or delete a profile without CLI, specify
non-interactivity with the -i or --non-interactive flag and use the flags for
source, user and path as in 
{APP_NAME} -i -s SOURCE -u USER -p PATH -n
Replace -n with -d to delete instead of creating. 

To skip updating decklists while using other functionality, include the -k flag.

To add shortcuts to launch {APP_NAME} alongside Cockatrice, run {APP_NAME} -r.
"""


def get_source(name, picker=False):
    if name is not None:
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


def get_verified_user(source, user, interactive=False):
    if not user:
        if interactive:
            user = cli.get_string(source.name + " username")
        else:
            return None

    if not source.verify_user(user):
        if interactive:
            print("Couldn't find any public decks for this user. Try again.")
            return get_verified_user(source, None, True)
        else:
            return None
    return user


def add_profile(cache, interactive, source=None, user=None, path=None):
    if not (source := get_source(source, interactive)):
        logging.error("No source specified. Unable to add profile.")
        return

    if not (user := get_verified_user(source, user, interactive)):
        logging.error("No user provided. Unable to add profile.")
        return

    if path and not utils.check_dir(path):
        logging.error(
            f"A file exists at {path} so it can't be used as an output "
            "directory."
        )
        if not interactive:
            return
        path = None

    if not path:
        if cache.dir_caches and cli.get_decision(
            "Use existing output directory?"
        ):
            if len(cache.dir_caches) == 1:
                path = cache.dir_caches[0].path
                logging.info(
                    f"Only one existing directory, defaulting to {path}."
                )
            else:
                path = cli.get_choice(
                    [d.path for d in cache.dir_caches],
                    "Which existing directory should be used for these decks?",
                )
        else:
            path = target.suggest_directory()
            if not (
                (os.path.isdir(path))
                and cli.get_decision(
                    f"Found Cockatrice deck directory at {path}."
                    " Output decklists here?"
                )
            ):
                path = cli.get_path("Output directory")

    cache.build_profile(source, user, path)


def delete_profile(cache, interactive, source=None, user=None, path=None):
    source = get_source(source)

    options = cache.filter_profiles(source, user, path)

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


def update_decks(cache, latest=False, source=None, user=None, path=None):
    profiles = cache.filter_profiles(source, user, path)
    if not profiles:
        logging.info("No profiles match filters, nothing to do.")
    for profile in profiles:
        if not utils.check_dir(profile.path):
            logging.error(
                f"Output directory {profile.path} already exists and is a file."
                f"Skipping {profile.user_string} download."
            )
            continue

        profile.update(latest)


def set_up_shortcuts():
    if os.name == "nt":
        from . import relnk

        relnk.relink_shortcuts(
            "Cockatrice.lnk",
            not cli.get_decision("Automatically update all shortcuts?"),
        )
    elif os.name == "posix":
        ARCHITRICE_PATH = f"/usr/bin/{APP_NAME}"
        if cli.get_decision(
            "Add script to run Cockatrice and Architrice to path?"
        ):
            script_path = os.path.join(utils.DATA_DIR, APP_NAME)
            with open(script_path, "w") as f:
                f.write(f"cockatrice &\n{sys.executable} -m {APP_NAME} -q")
            os.chmod(script_path, 0o755)
            subprocess.call(["sudo", "mv", script_path, ARCHITRICE_PATH])
            logging.info(
                f'Running "{APP_NAME}" will now launch '
                f"Cockatrice and run {APP_NAME}."
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
        "-p", "--path", dest="path", help="set deck file output directory"
    )
    parser.add_argument(
        "-n",
        "--new",
        dest="new",
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
    path = utils.expand_path(args.path) if args.path else None

    utils.set_up_logger(
        0 if args.quiet else args.verbosity + 1 if args.verbosity else 1
    )

    cache = caching.Cache.load()

    if args.relink:
        set_up_shortcuts()

    if len(sys.argv) == 1 and not cache.profiles:
        add_profile(cache, args.interactive)
        if cli.get_decision(
            "Set up shortcuts to run Architrice when launching Cockatrice?"
        ):
            set_up_shortcuts()
    elif args.new:
        add_profile(
            cache,
            args.interactive,
            args.source,
            args.user,
            path,
        )

    if args.delete:
        delete_profile(
            cache,
            args.interactive,
            args.source,
            args.user,
            path,
        )

    if not args.skip_update:
        update_decks(cache, args.latest, args.source, args.user, path)

    cache.save()


if __name__ == "__main__":
    main()
