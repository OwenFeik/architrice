import logging
import os
import requests
import xml.etree.cElementTree as et
import time

from .. import database
from .. import utils

from . import target

SCRYFALL_BULK_DATA_URL = "https://api.scryfall.com/bulk-data/oracle-cards"
# Scryfall updates its card list every 24 hours.
# We will update no more frequently than this as it is a large download.
CARD_LIST_UPDATE_INTERVAL = 60 * 60 * 24


class Mtgo(target.Target):
    NAME = "MTGO"
    SHORT = "M"
    DECK_DIRECTORYS = [
        utils.expand_path(
            os.path.join(
                os.getenv("APPDATA"),
                "Wizards of the Coast",
                "Magic Online",
                "3.0",
                "Decks",
            )
        ),
        utils.expand_path(
            os.path.join(
                "C:",
                "Program Files",
                "Wizards of the Coast",
                "Magic Online",
                "Decks",
            )
        ),
        utils.expand_path(
            os.path.join(os.getenv("USERPROFILE"), "Documents", "Decks")
        ),
    ]
    DECK_FILE_EXTENSION = ".dek"

    def __init__(self):
        super().__init__(Mtgo.NAME, Mtgo.SHORT, Mtgo.DECK_FILE_EXTENSION)

    def suggest_directory(self):
        for directory in Mtgo.DECK_DIRECTORYS:
            if os.path.exists(directory):
                break
        return directory

    def save_deck(self, deck, path):
        return deck_to_xml(deck, path)


def mtgo_name(card):
    return card.name.partition("//")[0].strip()


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
    for card in data:
        if card["layout"] in disallowed_layouts:
            continue

        if card["name"] in names:
            continue

        names.append(card["name"])
        mtgo_ids.append(card.get("mtgo_id"))
        is_dfcs.append("card_faces" in card)

    database.insert_many("cards", name=names, mtgo_id=mtgo_ids, is_dfc=is_dfcs)
    database.upsert(
        "database_events",
        id=database.DatabaseEvents.CARD_LIST_UPDATE.value,
        time=utils.time_now(),
    )

    logging.info("Card database update complete.")


def mtgo_id(card):
    mtgo_id = database.select_one_column("cards", "mtgo_id", name=card.name)
    if (
        mtgo_id is None
        and (
            utils.time_now()
            - (
                database.select_one_column(
                    "database_events",
                    "last_time",
                    id=database.DatabaseEvents.CARD_LIST_UPDATE.value,
                )
                or 0
            )
        )
        >= CARD_LIST_UPDATE_INTERVAL
    ):
        logging.info(f"Missing MTGO id for {card.name}. Updating database.")
        update_card_list()
        mtgo_id = database.select_one_column("cards", "mtgo_id", name=card.name)
    return mtgo_id


def deck_to_xml(deck, outfile):
    root = et.Element("Deck")

    et.SubElement(root, "NetDeckID").text = "0"
    et.SubElement(root, "PreconstructedDeckID").text = "0"

    for card in deck.get_main_deck():
        et.SubElement(
            root,
            "Cards",
            CatID=mtgo_id(card),
            Quantity=str(card.quantity),
            Sideboard="false",
            Name=mtgo_name(card),
            Annotation="0",
        )
    for card in deck.get_sideboard():
        et.SubElement(
            root,
            "Cards",
            CatID=mtgo_id(card),
            Quantity=str(card.quantity),
            Sideboard="true",
            Name=mtgo_name(card),
            Annotation="0",
        )

    et.ElementTree(root).write(outfile, xml_declaration=True, encoding="utf-8")
