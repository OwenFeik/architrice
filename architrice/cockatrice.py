import os
import xml.etree.cElementTree as et

from . import utils

COCKATRICE_DECK_FILE_EXTENSION = ".cod"
COCKATRICE_DECK_DIRECTORY = (
    os.path.abspath(
        os.path.join(os.getenv("LOCALAPPDATA"), "Cockatrice/Cockatrice/decks")
    )
    if os.name == "nt"
    else os.path.expanduser("~/.local/share/Cockatrice/Cockatrice/decks")
)


def suggest_directory():
    return COCKATRICE_DECK_DIRECTORY


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


def save_deck(deck, path):
    deck_to_xml(deck, path)


def create_file_name(deck_name):
    return utils.create_file_name(deck_name) + COCKATRICE_DECK_FILE_EXTENSION
