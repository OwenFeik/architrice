import logging
import os
import xml.etree.cElementTree as et
import time

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
            utils.expand_path(
                os.path.join(os.getenv("USERPROFILE"), "Documents", "Decks")
            ),
        ]
        if os.name == "nt"
        else []
    )
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


def mtgo_id(card):
    card_info.find(card.name).mtgo_id


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
