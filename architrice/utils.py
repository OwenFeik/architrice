import datetime
import json
import logging
import os
import re
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_FILE = os.path.join(DATA_DIR, "cache.json")
LOG_FILE = os.path.join(DATA_DIR, "log")

DEFAULT_CACHE = {"sources": {}, "dirs": {}}


def ensure_data_dir():
    if not os.path.isdir(DATA_DIR):
        os.mkdir(DATA_DIR)


def set_up_logger(verbosity=1):
    ensure_data_dir()
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
#       "sources": [
#           "SOURCE_NAME": [
#               {
#                   "user": "USER_NAME",
#                   "dir": "PATH_TO_DIR"
#               } ... for each user
#           ] ... for each source
#       ],
#       "dirs": {
#           "PATH_TO_DIR": {
#               "DECK_ID": {
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
    return None


def get_dir_cache(cache, path):
    if path not in cache["dirs"]:
        cache["dirs"][path] = {}
    return cache["dirs"][path]


def save_cache(cache):
    ensure_data_dir()
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


def check_dir(path):
    if os.path.isfile(path):
        return False
    if not os.path.isdir(path):
        os.makedirs(path)
        logging.info(f"Created output directory {path}.")
    return True
