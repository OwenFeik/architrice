from architrice.targets.card_info import CARD_LIST_UPDATE_INTERVAL
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
    SHORTCUT_NAME = "Cockatrice.lnk"
    EXECUTABLE_NAME = "cockatrice"
    SUPPORTS_RELNK = True

    def __init__(self):
        super().__init__(
            Cockatrice.NAME,
            Cockatrice.SHORT,
            Cockatrice.DECK_FILE_EXTENSION,
        )

    def suggest_directory(self):
        return Cockatrice.DECK_DIRECTORY

    def _save_deck(self, deck, path, include_maybe=False, card_info_map=None):
        self.deck_to_xml(deck, path, include_maybe, card_info_map)

    def deck_to_xml(self, deck, outfile, include_maybe, card_info_map=None):
        root = et.Element("cockatrice_deck", version="1")

        et.SubElement(root, "deckname").text = deck.name
        et.SubElement(root, "comments").text = deck.description

        main = et.SubElement(root, "zone", name="main")
        side = et.SubElement(root, "zone", name="side")

        for quantity, name in deck.get_main_deck():
            et.SubElement(
                main,
                "card",
                number=str(quantity),
                name=self.front_face_name(name, card_info_map),
            )
        for quantity, name in deck.get_sideboard(include_maybe=include_maybe):
            et.SubElement(
                side,
                "card",
                number=str(quantity),
                name=self.front_face_name(name, card_info_map),
            )

        et.ElementTree(root).write(
            outfile, xml_declaration=True, encoding="UTF-8"
        )
