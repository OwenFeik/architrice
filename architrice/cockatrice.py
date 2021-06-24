import xml.etree.cElementTree as et
import re

COCKATRICE_DECK_FILE_EXTENSION = ".cod"
SIDEBOARD_CATEGORIES = {"Commander", "Maybeboard", "Sideboard"}


def cockatrice_card_name(oracle_card):
    # Cockatrice implements dfcs as a seperate card each for the front and
    # back face. By adding just the front face, the right card will be in the
    # deck.
    if "dfc" in oracle_card["layout"]:
        return oracle_card["name"].split("//")[0].strip()
    return oracle_card["name"]


def belongs_in_sideboard(categories):
    return bool(SIDEBOARD_CATEGORIES.intersection(categories))


def deck_to_xml(deck, outfile):
    root = et.Element("cockatrice_deck", version="1")

    et.SubElement(root, "deckname").text = deck["name"]
    et.SubElement(root, "comments").text = deck["description"]

    main = et.SubElement(root, "zone", name="main")
    side = et.SubElement(root, "zone", name="side")

    for card in deck["cards"]:
        et.SubElement(
            side if belongs_in_sideboard(card["categories"]) else main,
            "card",
            number=str(card["quantity"]),
            name=cockatrice_card_name(card["card"]["oracleCard"]),
        )

    et.ElementTree(root).write(outfile, xml_declaration=True, encoding="UTF-8")


def create_file_name(deck_name):
    return (
        re.sub("[^a-z_ ]+", "", deck_name.lower()).replace(" ", "_")
        + COCKATRICE_DECK_FILE_EXTENSION
    )
