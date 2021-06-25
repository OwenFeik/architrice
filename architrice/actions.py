import asyncio
import concurrent.futures
import datetime
import logging
import os

import architrice.archidekt as archidekt
import architrice.cockatrice as cockatrice
import architrice.utils as utils

source = archidekt
target = cockatrice

# The reason for this "source" and "target" setup is that it allows future
# drop in replacements for other sources (different deck hosting websites)
# and targets (different mtg clients).
#
# To facilitate this, generic intermediate formats for decks and lists
# thereof are defined as follows.
#
# Generic deck format:
#   {
#       "name": "Deck Title",
#       "file_name": "deck_title.file",
#       "description": "Description of deck",
#       "main": [
#           (quantity, card_name, is_dfc) ... for card in main deck
#       ],
#       "side": [
#           (quantity, card_name, is_dfc) ... for card in sideboard
#       ]
#   }
#
# Generic list of decks format:
#   [
#       {
#           "id": "ARCHIDEKT_DECK_ID",
#           "updated": UTC_TIMESTAMP
#       } ... for each deck
#   ]

THREAD_POOL_MAX_WORKERS = 12


def download_deck(deck_id, path, dir_cache):
    if deck_id in dir_cache:
        logging.debug(f"Updating existing deck {deck_id}.")
        deck_cache = dir_cache[deck_id]
    else:
        logging.debug(f"Downloading new deck {deck_id}.")
        dir_cache[deck_id] = deck_cache = {"name": None, "updated": 0}

    deck = source.get_deck(deck_id)

    if deck_cache["name"]:
        deck["file_name"] = deck_cache["name"]
    else:
        deck_cache["name"] = deck["file_name"] = target.create_file_name(
            deck["name"]
        )

    target.save_deck(deck, os.path.join(path, deck["file_name"]))
    deck_cache["updated"] = datetime.datetime.utcnow().timestamp()
    logging.info(f"Successfully downloaded {deck['name']} ({deck_id}).")


def decks_to_update(username, dir_cache):
    decks = source.get_deck_list(username)
    logging.info(f"Total decks: {len(decks)}.")

    to_download = []
    for deck in decks:
        if (
            deck["id"] not in dir_cache
            or deck["updated"] > dir_cache[deck["id"]]["updated"]
        ):
            to_download.append(deck["id"])

    logging.info(f"To update: {len(to_download)}.")

    return to_download


def download_latest(username, path, dir_cache):
    to_download = decks_to_update(username, dir_cache)
    if len(to_download) == 0:
        logging.info("All decks up to date.")
    else:
        download_deck(
            max(to_download, key=lambda d: d["updated"])["id"], path, dir_cache
        )


# This is asynchronous so that it can use a ThreadPoolExecutor to speed up
# perfoming many deck requests.
async def download_decks_pool(loop, decks, path, dir_cache):
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=THREAD_POOL_MAX_WORKERS
    ) as executor:
        futures = [
            loop.run_in_executor(
                executor, download_deck, deck_id, path, dir_cache
            )
            for deck_id in decks
        ]
        return await asyncio.gather(*futures)


def download_all(username, path, dir_cache):
    logging.info(f"Updating all decks for {username}.")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        download_decks_pool(
            loop, decks_to_update(username, dir_cache), path, dir_cache
        )
    )

    logging.info(f"Successfully updated all decks for {username}.")


def setup_wizard():
    cache = utils.DEFAULT_CACHE
    cache["user"] = input("Archidekt username > ")
    cache["path"] = utils.expand_path(input("Output directory > "))
    return cache
