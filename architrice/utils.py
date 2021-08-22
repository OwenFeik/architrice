import datetime
import itertools
import logging
import os
import re
import sys

DEBUG = False


def get_data_dir():
    if DEBUG:
        return os.path.join(os.path.dirname(__file__), "data")

    if os.name == "nt":
        return os.path.join(os.getenv("LOCALAPPDATA", "architrice"))
    else:
        DATA_HOME_ENV_VAR = "XDG_DATA_HOME"
        DATA_HOME_FALLBACK = "~/.local/share"

        return os.path.join(
            os.path.expanduser(
                os.getenv(DATA_HOME_ENV_VAR) or DATA_HOME_FALLBACK
            ),
            "architrice",
        )


DATA_DIR = get_data_dir()
LOG_FILE = os.path.join(DATA_DIR, "architrice.log")


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


def create_file_name(deck_name):
    return re.sub("[^a-z0-9_ ]+", "", deck_name.lower()).replace(" ", "_")


def time_now():
    return int(datetime.datetime.utcnow().timestamp())


def timestamp_to_utc(timestamp):
    return int(datetime.datetime.utcfromtimestamp(timestamp).timestamp())


def parse_iso_8601(time_string):
    return int(
        datetime.datetime.strptime(
            time_string, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).timestamp()
    )


def expand_path(path):
    if path is None:
        return None
    return os.path.abspath(os.path.expanduser(path))


def check_dir(path):
    if not path:
        return False
    if os.path.isfile(path):
        return False
    if not os.path.isdir(path):
        os.makedirs(path)
        logging.info(f"Created output directory {path}.")
    return True


# Chunk an iterable into n size chunks
# source: https://docs.python.org/3/library/itertools.html#itertools-recipes
def group_iterable(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)
