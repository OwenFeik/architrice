import os
import xml.etree.cElementTree as et

from .. import utils

from . import target

# TODO Desktop/cockatrice_portable/data/decks
class Cockatrice(target.Target):
    NAME = "Cockatrice"
    SHORT = "C"
    DECK_DIRECTORY = (
        utils.expand_path(
            os.path.join(
                os.getenv("LOCALAPPDATA"), "Cockatrice/Cockatrice/decks"
            )
        )
        if os.name == "nt"
        else utils.expand_path("~/.local/share/Cockatrice/Cockatrice/decks")
    )
    DECK_FILE_EXTENSION = ".cod"

    def __init__(self):
        super().__init__(
            Cockatrice.NAME, Cockatrice.SHORT, Cockatrice.DECK_FILE_EXTENSION
        )

    def suggest_directory(self):
        return Cockatrice.DECK_DIRECTORY

    def save_deck(self, deck, path):
        deck_to_xml(deck, path)

    def save_decks(self, deck_tuples):
        for deck, path in deck_tuples:
            self.save_deck(deck, path)


def cockatrice_name(card):
    # Cockatrice implements dfcs as a seperate card each for the front and
    # back face. By adding just the front face, the right card will be in the
    # deck.
    if card.is_dfc:
        return card.name.split("//")[0].strip()
    return card.name


def deck_to_xml(deck, outfile):
    root = et.Element("cockatrice_deck", version="1")

    et.SubElement(root, "deckname").text = deck.name
    et.SubElement(root, "comments").text = deck.description

    main = et.SubElement(root, "zone", name="main")
    side = et.SubElement(root, "zone", name="side")

    for card in deck.get_main_deck():
        et.SubElement(
            main,
            "card",
            number=str(card.quantity),
            name=cockatrice_name(card),
        )
    for card in deck.get_sideboard():
        et.SubElement(
            side, "card", number=str(card.quantity), name=cockatrice_name(card)
        )

    et.ElementTree(root).write(outfile, xml_declaration=True, encoding="UTF-8")
