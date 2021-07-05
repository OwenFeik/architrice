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

To add another download target beyond this first one, run {APP_NAME} -n.

To delete an existing download target, run {APP_NAME} -d, which will launch a
wizard to do so.

To download only the most recently updated decklist for each target, run
{APP_NAME} -l.

To set up a new target or delete a target without CLI, use the flags for source,
user and path as in 
{APP_NAME} -s SOURCE -u USER -p PATH -n
Replace -n with -d to delete instead of creating. 
"""

def get_source(name, picker=False):
    if name:
        name = name.lower()
        for s in sources.sourcelist:
            if s.SOURCE_NAME.lower() == name or s.SOURCE_SHORT.lower() == name:
                return s
    if picker:
        return source_picker()
    return None


def source_picker():
    return cli.get_choice(
        [s.SOURCE_NAME for s in sources.sourcelist],
        "Download from which supported decklist website?",
        sources.sourcelist,
    )


def add_source(cache, source=None, user=None, path=None):
    source = get_source(source, True)
    target = cockatrice

    if user:
        logging.info("Verifying " + source.SOURCE_NAME + f" user {user}.")
        if not source.verify_user(user):
            logging.error(f"Couldn't verify user {user}. Ignoring new target.")
            return
        logging.info("Verified user.")
    else:
        while not source.verify_user(
            (user := cli.get_string(source.SOURCE_NAME + " username"))
        ):
            print("Couldn't find any public decks for this user. Try again.")

    if path:
        if not utils.check_dir(path):
            logging.error(
                f"A file exists at {path} so it can't be used as an output "
                "directory."
            )
    else:
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

    if cache["sources"].get(source.SOURCE_NAME) is None:
        cache["sources"][source.SOURCE_NAME] = []
    cache["sources"][source.SOURCE_NAME].append({"user": user, "dir": path})


def delete_source(cache, source=None, user=None, path=None):
    source = get_source(source)

    options = []
    for s in cache["sources"]:
        if source and not source.SOURCE_NAME == s:
            continue

        for t in cache["sources"][s]:
            t_user = t["user"]
            t_path = t["dir"]

            if user and t_user != user:
                continue
            if path and not os.path.samefile(t_path, path):
                continue
            options.append(f"{s}: {t_user} ({t_path})")

    if not options:
        logging.info("No targets exist, ignoring delete option.")
        return
    elif len(options) == 1:
        logging.info("One target matches criteria, deleting this.")
        target = options[0]
    else:
        target = cli.get_choice(options, "Delete which target?")

    m = re.match(r"^(?P<source>\w+): (?P<user>\w+) \((?P<path>.+)\)$", target)
    source = m.group("source")
    user = m.group("user")
    path = m.group("path")
    for t in cache["sources"][source]:
        if t["user"] == user and t["dir"] == path:
            cache["sources"][source].remove(t)
            break

    if not cache["sources"][source]:
        del cache["sources"][source]


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
        help="launch wizard to add a new target",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--delete",
        dest="delete",
        help="launch wizard or use options to delete a target",
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
        help="disable log output",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    utils.set_up_logger(
        0 if args.quiet else args.verbosity + 1 if args.verbosity else 1
    )

    cache = utils.load_cache()
    if len(sys.argv) == 1 and not cache["sources"]:
        add_source(cache)
    elif args.new:
        add_source(cache, args.source, args.user, args.path)

    if args.source and args.path and args.user:
        logging.info(
            f"Adding new source: {args.user} on {args.source} outputting to "
            + args.path
        )
    elif args.source or args.path or args.user:
        logging.info(
            "To add a new source with command line options, source, user and"
            " path must be specified."
        )

    if args.delete:
        delete_source(cache, args.source, args.user, args.path)

    for source in cache["sources"]:
        api = get_source(source)
        for target in cache["sources"][source]:
            path = target["dir"]
            user = target["user"]

            if not utils.check_dir(path):
                logging.error(
                    f"Output directory {path} already exists and is a file."
                    f"Skipping {source} user {user} download."
                )
                continue

            if args.latest:
                actions.download_latest(
                    api,
                    cockatrice,
                    user,
                    path,
                    utils.get_dir_cache(cache, path),
                )
            else:
                actions.download_all(
                    api,
                    cockatrice,
                    user,
                    path,
                    utils.get_dir_cache(cache, path),
                )

    utils.save_cache(cache)


if __name__ == "__main__":
    main()
