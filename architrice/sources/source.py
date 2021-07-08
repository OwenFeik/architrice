import abc
import dataclasses
import logging


class Source(abc.ABC):
    # Abstract base class for deck sources, used to have common logging between
    # them.
    #
    # pylint: disable=assignment-from-no-return
    #
    # Private methods are not implemented in this base class, so there are some
    # methods with no returns. This is ok as this class is not directly
    # instantiated.

    def __init__(self, name, short):
        self.name = name
        self.short = short

    def format_deck_id(self, deck_id):
        """Return an id gauranteed to be unique across sources for this deck."""

        # Because multiple sources use numeric ids, we might have collisions.
        # By prepending the short form of the source name, collisions are
        # prevented.
        return f"{self.short}_{str(deck_id)}"

    def unformat_deck_id(self, internal_deck_id):
        """Convert a formatted deck id back to the source format."""

        # Just need to slice off the source identifier character
        return internal_deck_id[2:]

    def _get_deck(self, deck_id):
        pass

    def get_deck(self, internal_deck_id):
        """Download as `Deck` the deck with id `deck_id` from this source."""
        deck_id = self.unformat_deck_id(internal_deck_id)
        deck = self._get_deck(deck_id)
        logging.info(f"Downloaded {self.name} deck {deck.name} (id: {deck_id})")
        return deck

    def _get_deck_list(self, username):
        pass

    def get_deck_list(self, username):
        """Get a list of `DeckUpdate` for all public decks of `username`."""
        deck_list = self._get_deck_list(username)
        logging.info(
            f"Found {len(deck_list)} decks for {self.name} user {username}."
        )
        return deck_list

    def _get_latest_deck(self, username):
        try:
            return max(self.get_deck_list(username), key=lambda d: d.updated)
        except ValueError:  # max on empty list produces ValueError
            return None

    def get_latest_deck(self, username):
        """Get a `DeckUpdate` for `username`'s most recently updated deck."""
        latest = self._get_latest_deck(username)
        if latest:
            logging.info(
                f"Latest deck for {self.name} user {username} "
                f"has ID {latest.deck_id}."
            )
        else:
            logging.info(
                f"Didn't find any decks for {username} on {self.name}."
            )
        return latest

    def _verify_user(self, username):
        pass

    def verify_user(self, username):
        """Verify that user `username` has an account with this source."""
        logging.info(f"Verifying {self.name} user {username}.")
        result = self._verify_user(username)
        if result:
            logging.info("Verification succesful.")
        else:
            logging.error("Verfification failed.")
        return result


@dataclasses.dataclass
class Card:
    quantity: int
    name: str
    is_dfc: bool


class Deck:
    def __init__(self, name, description, **kwargs):
        self.name = name
        self.description = description
        self.main = kwargs.get("main", [])
        self.side = kwargs.get("side", [])
        self.maybe = kwargs.get("maybe", [])
        self.commanders = kwargs.get("commanders", [])

    def get_main_deck(self, include_commanders=False):
        if include_commanders:
            return self.main + self.commanders
        return self.main

    def get_sideboard(self, include_commanders=True, include_maybe=True):
        sideboard = self.side
        if include_commanders:
            sideboard += self.commanders
        if include_maybe:
            sideboard += self.maybe
        return sideboard

    def get_board(self, board, default="main"):
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


@dataclasses.dataclass
class DeckUpdate:
    deck_id: str  # ID of the deck within the relevant web service
    updated: float  # UTC decimal timestamp of last updated time
