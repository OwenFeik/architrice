import dataclasses
import functools
import logging

import requests

from .. import database
from .. import utils

SCRYFALL_BULK_DATA_URL = "https://api.scryfall.com/bulk-data/all-cards"
# Scryfall updates its card list every 24 hours.
# We will update no more frequently than this as it is a large download.
CARD_LIST_UPDATE_INTERVAL = 60 * 60 * 24


@dataclasses.dataclass
class CardInfo:
    name: str
    mtgo_id: int
    is_dfc: bool
    collector_number: str
    edition: str


# Note: this should only be called from one thread at a time.
@functools.cache  # cache to save repeated db queries
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

    logging.info(
        "Downloading Scryfall card list for card data. Download size: "
        + str(download_info["compressed_size"])
        + " bytes."
    )
    # ~12MB download, ~90MB uncompressed
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

    # Relatively slow way to do it but as it only needs to happen rarely and
    # is paired with a download anyway it isn't really worth optimising.
    names = []
    mtgo_ids = []
    is_dfcs = []
    collector_numbers = []
    sets = []
    for card in data:
        if card["layout"] in disallowed_layouts:
            continue

        if card["name"] in names:
            continue

        if "mtgo_id" in card:
            names.append(card["name"])
            mtgo_ids.append(card["mtgo_id"])
            is_dfcs.append("card_faces" in card)
            collector_numbers.append(card["collector_number"])
            sets.append(card["set"])

    database.insert_many(
        "cards",
        name=names,
        mtgo_id=mtgo_ids,
        is_dfc=is_dfcs,
        collector_number=collector_numbers,
        edition=sets,
    )
    database.commit()

    logging.info("Card database update complete.")


def find(name, update_if_necessary=True):
    if tup := database.select_one("cards", name=name):
        _, name, mtgo_id, is_dfc, collector_number, edition = tup
        return CardInfo(name, str(mtgo_id), is_dfc, collector_number, edition)
    elif update_if_necessary:
        logging.info(f"Missing card info for {name}. Updating database.")
        update_card_list()
        return find(name, False)
    else:
        logging.error(f"Unable to find card info for {name}.")
        return None


def find_many(names):
    """Returns a {name: CardInfo} map with all cards in names."""
    database.disable_logging()
    card_info_map = {name: find(name) for name in names}
    database.enable_logging()
    return card_info_map


def map_from_deck(deck):
    """Returns a card info map from a sources.Deck."""
    return find_many([card.name for card in deck.get_all_cards()])


def map_from_decks(decks):
    """Return a card info map with all cards that appear in decks."""
    card_names = set()
    for deck in decks:
        for card in deck.get_all_cards():
            card_names.add(card.name)

    return find_many(card_names)
