#!/bin/python3

import argparse
import logging
import os
import re
import sys

from . import actions
from . import cli
from . import utils

# Sources
from . import sources

# Targets
from . import cockatrice

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
"""


def get_source(name, picker=False):
    if name:
        name = name.lower()
        for s in sources.sourcelist:
            if s.NAME.lower() == name or s.SHORT.lower() == name:
                return s()
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


def check_for_redundant_profile(cache, source, user, path):
    for profile in cache["profiles"].get(source.name, []):
        if profile["user"] == user and os.path.samefile(profile["dir"], path):
            return True
    return False


def add_profile(cache, interactive, source=None, user=None, path=None):
    target = cockatrice
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
        if cache["dirs"] and cli.get_decision("Use existing output directory?"):
            if len(cache["dirs"]) == 1:
                path = list(cache["dirs"].keys())[0]
                logging.info(
                    f"Only one existing directory, defaulting to {path}."
                )
            else:
                path = cli.get_choice(
                    list(cache["dirs"].keys()),
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

    if cache["profiles"].get(source.name) is None:
        cache["profiles"][source.name] = []

    if check_for_redundant_profile(cache, source, user, path):
        logging.info(
            f"A profile with identical details already exists, "
            "skipping creation."
        )
    else:
        cache["profiles"][source.name].append({"user": user, "dir": path})
        logging.info(
            f"Added new profile: {user} on {source.name} outputting to {path}"
        )


def delete_profile(cache, interactive, source=None, user=None, path=None):
    source = get_source(source)

    options = []
    for s in cache["profiles"]:
        if source and not source.name == s:
            continue

        for profile in cache["profile"][s]:
            p_user = profile["user"]
            p_path = profile["dir"]

            if user and p_user != user:
                continue
            if path and not os.path.samefile(p_path, path):
                continue
            options.append(f"{s}: {p_user} ({p_path})")

    if not options:
        logging.info("No matching profiles exist, ignoring delete option.")
        return
    elif len(options) == 1:
        logging.info("One profile matches criteria, deleting this.")
        profile = options[0]
    elif interactive:
        profile = cli.get_choice(options, "Delete which profile?")
    else:
        logging.error("Multiple profiles match criteria. Skipping delete.")
        return

    # Parse option string back to source, user, path
    m = re.match(
        r"^(?P<source>[\w ]+): (?P<user>\w+) \((?P<path>.+)\)$", profile
    )
    source = m.group("source")
    user = m.group("user")
    path = m.group("path")
    for profile in cache["profiles"][source]:
        if profile["user"] == user and profile["dir"] == path:
            cache["profiles"][source].remove(profile)
            break

    if not cache["profiles"][source]:
        del cache["profiles"][source]

    logging.info(f"Deleted profile {user} on {source} outputting to {path}")


def update_decks(cache, latest=False):
    target = cockatrice

    for source_name in cache["profiles"]:
        source = get_source(source_name)
        for profile in cache["profiles"][source_name]:
            path = profile["dir"]
            user = profile["user"]

            if not utils.check_dir(path):
                logging.error(
                    f"Output directory {path} already exists and is a file."
                    f"Skipping {source_name} user {user} download."
                )
                continue

            action = actions.download_latest if latest else actions.download_all
            action(
                source,
                target,
                user,
                path,
                utils.get_dir_cache(cache, path),
            )


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
    return parser.parse_args()


def main():
    args = parse_args()

    utils.set_up_logger(
        0 if args.quiet else args.verbosity + 1 if args.verbosity else 1
    )

    cache = utils.load_cache()
    if len(sys.argv) == 1 and not cache["profiles"]:
        add_profile(cache, args.interactive)
    elif args.new:
        add_profile(
            cache,
            args.interactive,
            args.source,
            args.user,
            utils.expand_path(args.path),
        )

    if args.delete:
        delete_profile(
            cache,
            args.interactive,
            args.source,
            args.user,
            utils.expand_path(args.path),
        )

    if not args.skip_update:
        update_decks(cache, args.latest)

    utils.save_cache(cache)


if __name__ == "__main__":
    main()
