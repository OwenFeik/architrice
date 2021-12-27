import os

from . import target


class Generic(target.Target):
    NAME = "Generic"
    SHORT = "G"
    DECK_FILE_EXTENSION = ".txt"

    def __init__(self):
        super().__init__(
            Generic.NAME, Generic.SHORT, Generic.DECK_FILE_EXTENSION
        )

    def canonical_name(self, name, card_info_map):
        return card_info_map[name].name

    def _save_deck(self, deck, path, include_maybe, card_info_map):

        deck_string = ""
        for quantity, name in deck.get_main_deck():
            deck_string += (
                f"{quantity} {self.canonical_name(name, card_info_map)}\n"
            )
        deck_string += "\n"
        for quantity, name in deck.get_sideboard(include_maybe=include_maybe):
            deck_string += (
                f"{quantity} {self.canonical_name(name, card_info_map)}\n"
            )

        with open(path, "w") as f:
            f.write(deck_string)
