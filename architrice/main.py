#!/bin/python3

import argparse
import logging
import os
import re
import sys

import architrice.actions as actions
import architrice.cli as cli
import architrice.utils as utils

# Sources
import architrice.archidekt as archidekt
import architrice.moxfield as moxfield

# Targets
import architrice.cockatrice as cockatrice

APP_NAME = "architrice"

DESCRIPTION = f"""
Download Archidekt decks to a local directory. To set output path:
{APP_NAME} -p OUTPUT_DIRECTORY
This is cached and will be used until a different path is set.

To download a single deck to the set output path:
{APP_NAME} -d ARCHIDEKT_DECK_ID
This deck id is cached, and if the command is run again without argument, the
same deck will be downloaded.

To download all decks for a specific user name:
{APP_NAME} -u ARCHIDEKT_USERNAME
This username is cached, and if the command is run again without argument, the
same user's decks will be downloaded.

To download the most recently updated deck for a specific user:
{APP_NAME} -l
If no user has been set, the user will need to be specified as well through -u.
"""

SOURCES = {
    "Archidekt": {
        "name": "Archidekt",
        "names": ["Archidekt", "A"],
        "api": archidekt,
    },
    "Moxfield": {
        "name": "Moxfield",
        "names": ["Moxfield", "M"],
        "api": moxfield,
    },
}


def source_picker():
    return SOURCES[
        cli.get_choice(
            list(SOURCES.keys()),
            "Download from which supported decklist website?",
            [s["names"] for s in SOURCES.values()],
        )
    ]


def add_source(cache):
    source = source_picker()
    target = cockatrice

    while not source["api"].verify_user(
        (user := cli.get_string(source["name"] + " username"))
    ):
        print("Couldn't find any public decks for this user. Try again.")

    if cache["dirs"] and cli.get_decision("Use existing output directory?"):
        if len(cache["dirs"]) == 1:
            path = list(cache["dirs"].keys())[0]
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

    if cache["sources"].get(source["name"]) is None:
        cache["sources"][source["name"]] = []
    cache["sources"][source["name"]].append({"user": user, "dir": path})

def delete_source(cache):
    options = []
    for s in cache["sources"]:
        for t in cache["sources"][s]:
            user = t["user"]
            path = t["dir"]
            options.append(f"{s}: {user} ({path})")

    if not options:
        logging.info("No targets exist, ignoring delete option.")
        return

    target = cli.get_choice(options, "Delete which target?")
    m = re.match(r"^(?P<source>\w+): (?P<user>\w+) \((?P<path>.+)\)$", target)
    source = m.group("source")
    user = m.group("user")
    path = m.group("path")
    for t in cache["sources"][source]:
        if t["user"] == user and t["dir"] == path:
            cache["sources"][source].remove(t)
            return

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
        "-n", "--new", dest="new", help="launch wizard to add a new target", action="store_true"
    )
    parser.add_argument(
        "-d", "--delete", dest="delete", help="launch wizard or use options to delete a target", action="store_true"
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
        cache = utils.DEFAULT_CACHE 
        add_source(cache)
    elif args.new:
        add_source(cache)

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
        delete_source(cache)

    for source in cache["sources"]:
        api = SOURCES[source]["api"]
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
