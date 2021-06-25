import asyncio
import concurrent.futures
import datetime
import logging
import os

import archidekt
import cockatrice
import utils

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
    logging.info(f"Successfully downloaded {deck_id}.")


def download_latest(username, path, dir_cache):
    pass


# This is asynchronous so that it can use a ThreadPoolExecutor to speed up
# perfoming may deck requests.
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
    logging.info(f"Downloading all decks for {username}.")
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

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        download_decks_pool(loop, to_download, path, dir_cache)
    )

    logging.info(f"Successfully downloaded all decks for {username}.")
