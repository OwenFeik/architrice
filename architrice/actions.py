import asyncio
import concurrent.futures
import datetime
import os

import archidekt
import cockatrice
import utils

source = archidekt
target = cockatrice

def download_deck(deck_id, path, dir_cache):
    if deck_id in dir_cache:
        deck_cache = dir_cache[deck_id]
    else:
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


def download_latest(username, path, dir_cache):
    pass


async def download_decks_pool(loop, decks, path, dir_cache):
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = [
            loop.run_in_executor(
                executor, download_deck, deck_id, path, dir_cache
            )
            for deck_id in decks
        ]
        return await asyncio.gather(*futures)


def download_all(username, path, dir_cache):
    decks = source.get_deck_list(username)

    to_download = []
    for deck in decks:
        if (
            deck["id"] not in dir_cache
            or deck["updated"] > dir_cache[deck["id"]]["updated"]
        ):
            to_download.append(deck["id"])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        download_decks_pool(loop, to_download, path, dir_cache)
    )
