import os

from . import target


class Generic(target.Target):
    NAME = "Generic"
    SHORT = "G"
    DECK_FILE_EXTENSION = ".txt"

    def __init__(self):
        super().__init__(
            Generic.NAME,
            Generic.SHORT,
            Generic.DECK_FILE_EXTENSION,
            False,
        )

    def save_deck(self, deck, path):
        deck_string = ""
        for quantity, name in deck.get_main_deck():
            deck_string += f"{quantity} {name}\n"
        deck_string += "\n"
        for quantity, name in deck.get_sideboard():
            deck_string += f"{quantity} {name}\n"

        with open(path, "w") as f:
            f.write(deck_string)

    def save_decks(self, deck_tuples):
        for deck, path in deck_tuples:
            self.save_deck(deck, path)
