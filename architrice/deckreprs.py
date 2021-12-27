from . import database
from . import utils


class DeckDetails(database.StoredObject):
    """A DeckDetails object represents a deck in a source."""

    def __init__(self, deck_id, source, db_id=None):
        super().__init__("decks", db_id)
        self.deck_id: str = deck_id
        self.source: str = source

    def __hash__(self):
        return hash((self.deck_id, self.source))

    def __repr__(self):
        return (
            f"<DeckDetails deck_id={self.deck_id} source={self.source} "
            f"id={self._id}>"
        )


class Deck(DeckDetails):
    """A Deck object represents a deck downloaded from a source."""

    # The cards held by the deck are (quantity, name) tuples rather than Card
    # objects. They are parsed into Cards before saving.
    def __init__(self, deck_id, source, name, description, **kwargs):
        super().__init__(deck_id, source, db_id=kwargs.get("id"))
        self.name: str = name
        self.description: str = description
        self.main = kwargs.get("main", [])
        self.side = kwargs.get("side", [])
        self.maybe = kwargs.get("maybe", [])
        self.commanders = kwargs.get("commanders", [])

    def __repr__(self):
        return super().__repr__().replace("<DeckDetails", "<Deck")

    def sort_cards(self, cards):
        # Sort alphabetically by card name
        return sorted(cards, key=lambda c: c[1])

    def get_card_names(self, board):
        return [c[1] for c in self.get_board(board)]

    def get_all_card_names(self):
        return set(
            self.get_card_names("main")
            + self.get_card_names("side")
            + self.get_card_names("maybe")
            + self.get_card_names("commanders")
        )

    def get_main_deck(self, include_commanders=False):
        main_deck = self.main
        if include_commanders:
            main_deck += self.commanders

        return self.sort_cards(main_deck)

    def get_sideboard(self, include_commanders=True, include_maybe=True):
        sideboard = self.side[:]
        if include_commanders:
            sideboard += self.commanders
        if include_maybe:
            sideboard += self.maybe
        return self.sort_cards(sideboard)

    def get_board(self, board, default="main"):
        # Note: this is to be used to add cards, not to retrieve them, as it
        # doesn't return the cards in sorted order.

        board = board.strip().lower()
        if board == "commanders":
            return self.commanders
        elif board in ["maybe", "maybeboard"]:
            return self.maybe
        elif board in ["side", "sideboard"]:
            return self.side
        elif board in ["main", "maindeck", "mainboard"]:
            return self.main
        else:
            return self.get_board(default)

    def add_card(self, card, board):
        self.get_board(board).append(card)

    def add_cards(self, cards, board):
        self.get_board(board).extend(cards)


class DeckUpdate:
    """A DeckUpdate represents the last time a Deck was updated on a source."""

    # Because these are not stored anywhere, they don't need a db id.
    def __init__(self, deck, updated):
        self.deck: DeckDetails = deck
        self.updated: int = updated

    def __repr__(self):
        return f"<DeckUpdate deck={repr(self.deck)} updated={self.updated}>"

    def update(self):
        self.updated = utils.time_now()


class Card(database.StoredObject):
    def __init__(
        self,
        name,
        mtgo_id=None,
        is_dfc=False,
        collector_number=None,
        edition=None,
        db_id=None,
    ):
        super().__init__("cards", db_id)
        self.name: str = name
        self.mtgo_id: str = mtgo_id
        self.is_dfc: bool = is_dfc
        self.collector_number: str = collector_number
        self.edition: str = edition

    def __repr__(self):
        return (
            f"<Card name={self.name} mtgo_id={self.mtgo_id} "
            f"is_dfc={self.is_dfc} collector_number={self.collector_number} "
            f"edition={self.edition} id={self._id}>"
        )

    @staticmethod
    def from_record(tup):
        # database record format:
        # (id, name, mtgo_id, is_dfc, collector_number, set, is_reprint)
        _, name, mtgo_id, is_dfc, collector_number, edition, _ = tup
        return Card(
            name, mtgo_id and str(mtgo_id), is_dfc, collector_number, edition
        )
