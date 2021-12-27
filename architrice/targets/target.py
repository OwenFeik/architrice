import abc
import os

from .. import database
from .. import utils

from . import card_info


class Target(database.KeyStoredObject, abc.ABC):
    SUPPORTS_RELNK = False

    def __init__(self, name, short, file_extension):
        database.KeyStoredObject.__init__(self, short)

        self.name = name
        self.short = short
        self.file_extension = file_extension
        self.mtgo_id_required = False

    def suggest_directory(self):
        if os.name == "nt":
            return utils.expand_path(
                os.path.join(os.getenv("USERPROFILE"), "Documents", "Decks")
            )
        else:
            return utils.expand_path(os.path.join("~", "Decks"))

    @abc.abstractmethod
    def _save_deck(self, deck, path, include_maybe=False, card_info_map=None):
        """Writes deck to path in format using card_info_map."""

    def front_face_name(self, name, card_info_map=None):
        if card_info_map and name in card_info_map:
            card = card_info_map[name]
            if card.is_dfc:
                return name.partition("//")[0].strip()
        return name

    def save_deck(self, deck, path, include_maybe=False, card_info_map=None):
        if card_info_map is None:
            card_info_map = card_info.map_from_deck(deck)
        self._save_deck(deck, path, include_maybe, card_info_map)

    def save_decks(self, deck_tuples, include_maybe=False, card_info_map=None):
        if card_info_map is None:
            card_info_map = card_info.map_from_decks(
                [d for d, _ in deck_tuples],
                mtgo_id_required=self.mtgo_id_required,
            )

        for deck, path in deck_tuples:
            self.save_deck(deck, path, include_maybe, card_info_map)

    def create_file_name(self, deck_name):
        return utils.create_file_name(deck_name) + self.file_extension
