#!/bin/python3

import argparse
import logging
import os
import sys

import architrice.actions as actions
import architrice.utils as utils

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


def parse_args():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-d", "--deck", dest="deck", help="set deck id to download"
    )
    parser.add_argument(
        "-u", "--user", dest="user", help="set username to download decks of"
    )
    parser.add_argument(
        "-p", "--path", dest="path", help="set deck file output directory"
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

    if len(sys.argv) == 1 and not utils.cache_exists():
        cache = actions.setup_wizard()
    else:
        cache = utils.load_cache()

    user = args.user or cache["user"]
    deck = args.deck or cache["deck"]
    path = utils.expand_path(args.path) if args.path else cache["path"]

    if os.path.isfile(path):
        logging.error(
            f"Fatal: Output directory {path} already exists and is a file."
        )
        exit()

    if not os.path.isdir(path):
        os.makedirs(path)
        logging.info(f"Created output directory {path}.")

    cache.update({"user": user, "deck": deck, "path": path})

    if cache["dirs"].get(path) is None:
        cache["dirs"][path] = dir_cache = {}
    else:
        dir_cache = cache["dirs"][path]

    if path is None:
        print(
            f"No output file specified. Set one with {APP_NAME} -p"
            " OUTPUT_DIRECTORY."
        )
    elif args.latest:
        if not user:
            print(
                f"No Archidekt user set. Set one with {APP_NAME} -u"
                " ARCHIDEKT_USERNAME to download their latest deck."
            )
        else:
            print(f"Downloading latest deck for Archidekt user {user}.")
            actions.download_latest(user, path, dir_cache)
    elif user:
        print(f"Updating all decks for Archidekt user {user}.")
        actions.download_all(user, path, dir_cache)
    elif deck:
        print(f"Updating deck with Archidekt id {deck}.")
        actions.download_deck(deck, path, dir_cache)
    elif args.path:
        print(f'Set output directory to "{path}".')
    else:
        print("No action specified. Nothing to do.")

    utils.save_cache(cache)


if __name__ == "__main__":
    main()
