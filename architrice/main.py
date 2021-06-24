#!/bin/python3

import argparse
import os
import json

import actions

APP_NAME = "archtrice"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_FILE = os.path.join(DATA_DIR, "cache.json")

DESCRIPTION = f"""
Download archidekt decks to a local directory. To set output path:
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

parser = argparse.ArgumentParser(
    description=DESCRIPTION,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("-d", "--deck", dest="deck", help="set deck id to download")
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
args = parser.parse_args()

# Load cached data
if os.path.isfile(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)
else:
    cache = {"user": None, "deck": None, "path": None, "dirs": {}}

# Cache format:
#   {
#       "user": "archidekt username",
#       "deck": "last deck downloaded",
#       "path": "output directory",
#       "dirs": {
#           "PATH_TO_DIR_1": {
#               "ARCHIDEKT_DECK_ID": {
#                   "last_updated": timestamp
#                   "name": "file name"
#               } ... for each deck downloaded
#           } ... for each deck directory
#       }
#   }

# TODO: may be better to use user id?
user = args.user or cache["user"]
deck = args.deck or cache["deck"]
path = os.path.abspath(args.path) if args.path else cache["path"]

if os.path.isfile(path):
    print(f"Fatal error: Output directory {path} already exists and is a file.")
    exit()
if not os.path.isdir(path):
    os.makedirs(path)

cache.update({"user": user, "deck": deck, "path": path})

if cache["dirs"].get(path) is None:
    cache["dirs"][path] = dir_cache = {}
else:
    dir_cache = cache["dirs"][path]

if path is None:
    # TODO: tempfile
    print(
        f"No output file specified. Set one with {APP_NAME} -p"
        " OUTPUT_DIRECTORY."
    )
elif args.latest:
    if not user:
        print(
            f"No archidekt user set. Set one with {APP_NAME} -u"
            " ARCHIDEKT_USERNAME to download their latest deck."
        )
    else:
        print(f"Downloading latest deck for archidekt user {user}.")
        actions.download_latest(user, path, dir_cache)
elif user:
    print(f"Updating all decks for archidekt user {user}.")
    actions.download_all(user, path, dir_cache)
elif deck:
    print(f"Updating deck with archidekt id {deck}.")
    actions.download_deck(deck, path, dir_cache)
elif args.path:
    print(f'Set output directory to "{path}".')
else:
    print("No action specified. Nothing to do.")

# Cache arguments for use in next usage.
if not os.path.isdir(DATA_DIR):
    os.mkdir(DATA_DIR)

with open(CACHE_FILE, "w") as f:
    json.dump(cache, f, indent=4)
