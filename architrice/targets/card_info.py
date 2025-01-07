import functools
import logging
import re

import requests

from .. import database
from .. import deckreprs
from .. import utils

SCRYFALL_BULK_DATA_URL = "https://api.scryfall.com/bulk-data/default-cards"
# Scryfall updates its card list every 24 hours.
# We will update no more frequently than this as it is a large download.
CARD_LIST_UPDATE_INTERVAL = 60 * 60 * 24

# Could consider Ascii normalising card names upon database insertion. This
# would make it easier to find cards with accents in names. However, some
# targets, like Cockatrice, need the accents in card names.
#
# ASCII_NORMALISATION_REGEX = re.compile(r"[^ !&'\(\),\-\./\?A-Z0-9_a-z]")
#
# def ascii_normalise_card_name(name):
#     return re.sub(ASCII_NORMALISATION_REGEX, r"_", name)


def wildcard_vowels(name):
    return re.sub(r"[aeiou]", r"_", name)


def card_info_tuple(card_json):
    dfc_layouts = ["meld", "modal_dfc", "transform"]
    return (
        card_json["name"],
        card_json.get("mtgo_id"),
        card_json["layout"] in dfc_layouts,
        card_json["collector_number"],
        card_json["set"],
        card_json["reprint"],
    )


def save_card_info(data):
    if not isinstance(data, list):
        if data["object"] == "card":
            data = [data]
        elif data["object"] == "list":
            data = data["data"]
        else:
            return

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

        records.append(card_info_tuple(card))

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


# Note: this should only be called from one thread at a time.
# Returns bool indicating whether the database was actually updated.
def update_card_list():
    time, url = database.select_one(
        "database_events",
        ["time", "data"],
        id=database.DatabaseEvents.CARD_LIST_UPDATE.value,
    ) or (0, None)
    if utils.time_now() - time < CARD_LIST_UPDATE_INTERVAL:
        return False

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
        + str(download_info.get("size"))
        + " bytes."
    )

    # ~30MB download, ~230MB uncompressed
    logging.info("This may take a couple of minutes.")
    data = requests.get(download_info["download_uri"]).json()

    save_card_info(data)

    logging.info("Card database update complete.")

    return True


def update_single(name):
    URL_BASE = "https://api.scryfall.com/cards/search"
    resp = requests.get(
        URL_BASE, params={"q": f'!"{name}"', "unique": "prints"}
    )

    if resp.status_code == 200:
        logging.info(f"Downloaded card data for {name}.")
        data = resp.json()
        save_card_info(data)
    elif resp.status_code != 404:
        logging.error(
            f"Failed to query card data for {name}. Status: {resp.status_code}."
        )


@functools.lru_cache(maxsize=None)  # cache to save repeated db queries
def find(name, mtgo_id_required=False, update_if_necessary=True):
    matches = list(database.select("cards", name=name))
    if not matches:
        # Some websites don't include the back face of cards in the name.
        # Luckily, card face names are unique, so we can simply match cards
        # whose name starts with the front face name.
        matches = list(
            database.execute(
                "SELECT * FROM cards WHERE name LIKE ?;", (name + " // %",)
            )
        )

    if not matches:
        # Card names like like Seance are sometimes normalised to ascii and
        # sometimes left with accents. If they're normalised to ascii, we might
        # be able to find them by replacing vowels with wildcards.
        matches = list(
            database.execute(
                "SELECT * FROM cards WHERE name LIKE ?;",
                (wildcard_vowels(name),),
            )
        )

    # Try and get original printing
    for tup in matches:
        _, _, mtgo_id, *_, reprint = tup

        if not reprint and (mtgo_id or not mtgo_id_required):
            return deckreprs.Card.from_record(tup)

    # Settle for any printing
    for tup in matches:
        _, _, mtgo_id, *_ = tup

        if mtgo_id or not mtgo_id_required:
            return deckreprs.Card.from_record(tup)

    if update_if_necessary:
        logging.debug(f"Missing card info for {name}. Updating database.")

        if not update_card_list():
            update_single(name)
        return find(
            name, mtgo_id_required=mtgo_id_required, update_if_necessary=False
        )
    else:
        logging.error(f"Unable to find card info for {name}.")
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
