import datetime
import json
import logging
import os
import re
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_FILE = os.path.join(DATA_DIR, "cache.json")
LOG_FILE = os.path.join(DATA_DIR, "log")

DEFAULT_CACHE = {"user": None, "deck": None, "path": None, "dirs": {}}


def set_up_logger(verbosity=1):
    handlers = [logging.FileHandler(LOG_FILE)]

    if verbosity != 0:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(
            logging.Formatter("%(levelname)s: %(message)s")
        )
        stdout_handler.setLevel(
            logging.INFO if verbosity == 1 else logging.DEBUG
        )
        handlers.append(stdout_handler)

    logging.basicConfig(level=logging.DEBUG, handlers=handlers)


# Cache format:
#   {
#       "user": "archidekt username",
#       "deck": "last deck downloaded",
#       "path": "output directory",
#       "dirs": {
#           "PATH_TO_DIR": {
#               "ARCHIDEKT_DECK_ID": {
#                   "updated": timestamp
#                   "name": "file name"
#               } ... for each deck downloaded
#           } ... for each deck directory
#       }
#   }
def load_cache():
    if os.path.isfile(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    else:
        return DEFAULT_CACHE


def save_cache(cache):
    if not os.path.isdir(DATA_DIR):
        os.mkdir(DATA_DIR)

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=4)


def cache_exists():
    return os.path.isfile(CACHE_FILE)


def create_file_name(deck_name):
    return re.sub("[^a-z0-9_ ]+", "", deck_name.lower()).replace(" ", "_")


def parse_iso_8601(time_string):
    return datetime.datetime.strptime(
        time_string, "%Y-%m-%dT%H:%M:%S.%fZ"
    ).timestamp()


def expand_path(path):
    return os.path.abspath(os.path.expanduser(path))
