import asyncio
import concurrent.futures
import datetime
import logging
import os

from . import cockatrice
from . import utils

THREAD_POOL_MAX_WORKERS = 12


def download_deck(source, target, deck_id, path, dir_cache):
    if deck_id in dir_cache:
        logging.debug(f"Updating existing deck {deck_id}.")
        deck_cache = dir_cache[deck_id]
    else:
        logging.debug(f"Downloading new deck {deck_id}.")
        dir_cache[deck_id] = deck_cache = {"name": None, "updated": 0}

    deck = source.get_deck(deck_id)

    if deck_cache["name"]:
        file_name = deck_cache["name"]
    else:
        file_name = deck_cache["name"] = target.create_file_name(deck.name)

    target.save_deck(deck, os.path.join(path, file_name))
    deck_cache["updated"] = datetime.datetime.utcnow().timestamp()


def needs_update(dir_cache, deck):
    return (
        deck
        and deck.deck_id not in dir_cache
        or deck.updated > dir_cache[deck.deck_id]["updated"]
    )


def decks_to_update(source, username, dir_cache):
    decks = source.get_deck_list(username)

    to_download = []
    for deck in decks:
        if needs_update(dir_cache, deck):
            to_download.append(deck.deck_id)

    logging.info(f"To update: {len(to_download)}.")

    return to_download


def download_latest(source, target, username, path, dir_cache):
    latest = source.get_latest_deck(username)
    if needs_update(dir_cache, latest):
        download_deck(
            source,
            target,
            latest.deck_id,
            path,
            dir_cache,
        )
    else:
        logging.info("Latest deck is up to date.")


# This is asynchronous so that it can use a ThreadPoolExecutor to speed up
# perfoming many deck requests.
async def download_decks_pool(source, target, loop, decks, path, dir_cache):
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=THREAD_POOL_MAX_WORKERS
    ) as executor:
        futures = [
            loop.run_in_executor(
                executor,
                download_deck,
                source,
                target,
                deck_id,
                path,
                dir_cache,
            )
            for deck_id in decks
        ]
        return await asyncio.gather(*futures)


def download_all(source, target, username, path, dir_cache):
    logging.info(f"Updating all decks for {username} on {source.name}.")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        download_decks_pool(
            source,
            target,
            loop,
            decks_to_update(source, username, dir_cache),
            path,
            dir_cache,
        )
    )

    logging.info(f"Successfully updated all decks for {username}.")
