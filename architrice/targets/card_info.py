import dataclasses
import functools
import logging

import requests

from .. import caching
from .. import database
from .. import utils

SCRYFALL_BULK_DATA_URL = "https://api.scryfall.com/bulk-data/default-cards"
# Scryfall updates its card list every 24 hours.
# We will update no more frequently than this as it is a large download.
CARD_LIST_UPDATE_INTERVAL = 60 * 60 * 24


# Note: this should only be called from one thread at a time.
def update_card_list():
    time, url = (
        database.select_one(
            "database_events",
            ["time", "data"],
            id=database.DatabaseEvents.CARD_LIST_UPDATE.value,
        )
        or (0, None)
    )
    if utils.time_now() - time < CARD_LIST_UPDATE_INTERVAL:
        return

    download_info = requests.get(SCRYFALL_BULK_DATA_URL).json()

    database.upsert(
        "database_events",
        id=database.DatabaseEvents.CARD_LIST_UPDATE.value,
        time=utils.time_now(),
        data=download_info["download_uri"],
    )

    if download_info["download_uri"] == url:
        logging.info("Latest Scryfall card list already downloaded.")
        return

    logging.info("This may take a couple of minutes.")
    logging.info(
        "Downloading Scryfall card list for card data. Download size: "
        + str(download_info["compressed_size"])
        + " bytes."
    )
    # ~30MB download, ~230MB uncompressed
    data = requests.get(download_info["download_uri"]).json()

    disallowed_layouts = [
        "art_series",
        "double_faced_token",
        "emblem",
        "planar",
        "scheme",
        "token",
        "vanguard",
    ]

    # Tuple format:
    # (name, mtgo_id, is_dfc, collector_number, edition, reprint)

    records = []

    # Relatively slow way to do it but as it only needs to happen rarely and
    # is paired with a download anyway it isn't really worth optimising.
    for card in data:
        if card["layout"] in disallowed_layouts:
            continue

        records.append(
            (
                card["name"],
                card.get("mtgo_id"),
                "card_faces" in card,
                card["collector_number"],
                card["set"],
                card["reprint"],
            )
        )

    database.insert_many_tuples(
        "cards",
        [
            "name",
            "mtgo_id",
            "is_dfc",
            "collector_number",
            "edition",
            "reprint",
        ],
        records,
        conflict="ignore",
    )
    database.commit()

    logging.info("Card database update complete.")


@functools.cache  # cache to save repeated db queries
def find(name, mtgo_id_required=False, update_if_necessary=True):
    matches = list(database.select("cards", name=name))
    if not matches:
        matches = list(
            database.execute(
                "SELECT * FROM cards WHERE name LIKE ?;", (name + "%",)
            )
        )

    # Try and get original printing
    for tup in matches:
        _, _, mtgo_id, *_, reprint = tup

        if not reprint and (mtgo_id or not mtgo_id_required):
            return caching.Card.from_record(tup)

    # Settle for any printing
    for tup in matches:
        _, _, mtgo_id, *_ = tup

        if mtgo_id or not mtgo_id_required:
            return caching.Card.from_record(tup)

    if update_if_necessary:
        logging.debug(f"Missing card info for {name}. Updating database.")
        update_card_list()
        return find(
            name, mtgo_id_required=mtgo_id_required, update_if_necessary=False
        )
    else:
        logging.debug(f"Unable to find suitable card info for {name}.")
        return None


def find_many(names, mtgo_id_required=False):
    """Returns a {name: CardInfo} map with all cards in names."""
    database.disable_logging()
    card_info_map = {
        name: find(name, mtgo_id_required=mtgo_id_required) for name in names
    }
    database.enable_logging()
    return card_info_map


def map_from_deck(deck, mtgo_id_required=False):
    """Returns a card info map from a sources.Deck."""
    return find_many(deck.get_all_card_names(), mtgo_id_required)


def map_from_decks(decks, mtgo_id_required=False):
    """Return a card info map with all cards that appear in decks."""
    card_names = set()
    for deck in decks:
        card_names.update(deck.get_all_card_names())

    return find_many(card_names, mtgo_id_required)
