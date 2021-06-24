import os
import time

import archidekt
import cockatrice


def download_latest(username, path, dir_cache):
    pass


def download_all(username, path, dir_cache):
    pass


def download_deck(deck_id, path, dir_cache):
    if deck_id in dir_cache:
        deck_cache = dir_cache[deck_id]
    else:
        dir_cache[deck_id] = deck_cache = {"name": None, "last_updated": 0}

    deck = archidekt.get_deck(deck_id)

    if deck_cache["name"]:
        name = deck_cache["name"]
    else:
        name = deck_cache["name"] = cockatrice.create_file_name(deck["name"])

    cockatrice.deck_to_xml(deck, os.path.join(path, name))
    deck_cache["last_updated"] = time.time()
