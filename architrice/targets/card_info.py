import dataclasses
import logging

import requests

from .. import database
from .. import utils

SCRYFALL_BULK_DATA_URL = "https://api.scryfall.com/bulk-data/oracle-cards"
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


# TODO PROBLEM: every thread will try to do this.
# need to figure out a way to do it once if needed either before hand
# or with other threads waiting on it.
def update_card_list():
    download_info = requests.get(SCRYFALL_BULK_DATA_URL).json()
    logging.info(
        "Downloading Scryfall card list for MTGO ids. Download size: "
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

        names.append(card["name"])
        mtgo_ids.append(card.get("mtgo_id"))
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
    database.upsert(
        "database_events",
        id=database.DatabaseEvents.CARD_LIST_UPDATE.value,
        time=utils.time_now(),
    )

    logging.info("Card database update complete.")


def find(name):
    if tup := database.select_one("cards", name=name):
        _, name, mtgo_id, is_dfc, collector_number, edition = tup
        return CardInfo(name, mtgo_id, is_dfc, collector_number, edition)
    elif (
        utils.time_now()
        - (
            database.select_one_column(
                "database_events",
                "last_time",
                id=database.DatabaseEvents.CARD_LIST_UPDATE.value,
            )
            or 0
        )
    ) >= CARD_LIST_UPDATE_INTERVAL:
        logging.info(f"Missing card info for {name}. Updating database.")
        update_card_list()
        return find(name)
    else:
        logging.error(f"Unable to find card info for {name}.")
        return None
