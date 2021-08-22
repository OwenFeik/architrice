import logging
import os
import xml.etree.cElementTree as et

from .. import utils

from . import card_info
from . import target


class Mtgo(target.Target):
    SUPPORTED_OS = ["nt"]
    NAME = "MTGO"
    SHORT = "M"
    DECK_DIRECTORYS = (
        [
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
        ]
        if os.name == "nt"
        else []
    )
    DECK_FILE_EXTENSION = ".dek"
    SHORTCUT_NAME = "Magic The Gathering Online.lnk"
    SUPPORTS_RELNK = True

    def __init__(self):
        super().__init__(Mtgo.NAME, Mtgo.SHORT, Mtgo.DECK_FILE_EXTENSION)
        self.mtgo_id_required = True

    def suggest_directory(self):
        for directory in Mtgo.DECK_DIRECTORYS:
            if os.path.exists(directory):
                return directory
        return super().suggest_directory()

    def save_deck(self, deck, path, card_info_map=None):
        if card_info_map is None:
            card_info_map = card_info.map_from_deck(deck, mtgo_id_required=True)
        return deck_to_xml(deck, path, card_info_map)


def mtgo_name(name):
    return name.partition("//")[0].strip()


def add_card(root, quantity, name, card_info_map, in_sideboard=False):
    info = card_info_map.get(name)
    if info and info.mtgo_id:
        et.SubElement(
            root,
            "Cards",
            {
                "CatID": info.mtgo_id,
                "Quantity": str(quantity),
                "Sideboard": "true" if in_sideboard else "false",
                "Name": mtgo_name(name),
                "Annotation": "0",
            },
        )
    else:
        logging.info(
            f"Couldn't find MTGO data for {name}." " It may not exist on MTGO."
        )


def deck_to_xml(deck, outfile, card_info_map):
    root = et.Element(
        "Deck",
        {
            "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        },
    )  # xmlns declaration that MTGO writes in its .dek files.

    et.SubElement(root, "NetDeckID").text = "0"
    et.SubElement(root, "PreconstructedDeckID").text = "0"

    for quantity, name in deck.get_main_deck():
        add_card(root, quantity, name, card_info_map)
    for quantity, name in deck.get_sideboard():
        add_card(root, quantity, name, card_info_map, True)

    et.ElementTree(root).write(outfile, xml_declaration=True, encoding="utf-8")
