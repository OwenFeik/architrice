import abc
import os

from .. import utils

from . import card_info


class Target(abc.ABC):
    SUPPORTED_OS = ["posix", "nt"]

    def __init__(self, name, short, file_extension, needs_card_info=True):
        self.name = name
        self.short = short
        self.file_extension = file_extension
        self.needs_card_info = needs_card_info

    def suggest_directory(self):
        if os.name == "nt":
            return utils.expand_path(
                os.path.join(os.getenv("USERPROFILE"), "Documents", "Decks")
            )
        else:
            return utils.expand_path(os.path.join("~", "Decks"))

    def save_deck(self, deck, path, card_info_map=None):
        """Writes deck to path in format using card_info_map."""

    def save_decks(self, deck_tuples, card_info_map=None):
        if card_info_map is None:
            card_info_map = card_info.map_from_decks(
                [d for d, _ in deck_tuples]
            )

        # TODO test this, if slow can use a ThreadPoolExecutor
        for deck, path in deck_tuples:
            self.save_deck(deck, path, card_info_map)

    def create_file_name(self, deck_name):
        return utils.create_file_name(deck_name) + self.file_extension
