import xml.etree.cElementTree as et

import architrice.utils as utils

COCKATRICE_DECK_FILE_EXTENSION = ".cod"


def cockatrice_name(card_tuple):
    # Cockatrice implements dfcs as a seperate card each for the front and
    # back face. By adding just the front face, the right card will be in the
    # deck.
    _, name, is_dfc = card_tuple
    if is_dfc:
        return name.split("//")[0].strip()
    return name


def deck_to_xml(deck, outfile):
    root = et.Element("cockatrice_deck", version="1")

    et.SubElement(root, "deckname").text = deck["name"]
    et.SubElement(root, "comments").text = deck["description"]

    main = et.SubElement(root, "zone", name="main")
    side = et.SubElement(root, "zone", name="side")

    for card in deck["main"]:
        et.SubElement(
            main,
            "card",
            number=str(card[0]),
            name=cockatrice_name(card),
        )
    for card in deck["side"]:
        et.SubElement(
            side, "card", number=str(card[0]), name=cockatrice_name(card)
        )

    et.ElementTree(root).write(outfile, xml_declaration=True, encoding="UTF-8")


def save_deck(deck, path):
    deck_to_xml(deck, path)


def create_file_name(deck_name):
    return utils.create_file_name(deck_name) + COCKATRICE_DECK_FILE_EXTENSION
