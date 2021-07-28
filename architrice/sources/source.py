import abc
import dataclasses
import logging

from .. import caching
from .. import database


class Source(database.KeyStoredObject, abc.ABC):
    # Abstract base class for deck sources, used to have common logging between
    # them.
    #
    # pylint: disable=assignment-from-no-return
    #
    # Private methods are not implemented in this base class, so there are some
    # methods with no returns. This is ok as this class is not directly
    # instantiated.

    def __init__(self, name, short):
        database.KeyStoredObject.__init__(self, short)

        self.name = name
        self.short = short

    def create_deck(self, deck_id, name, description):
        """Create a Deck with relevant information."""
        return caching.Deck(deck_id, self.short, name, description)

    def _get_deck(self, deck_id):
        pass

    def get_deck(self, deck_id):
        """Download as `Deck` the deck with id `deck_id` from this source."""
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
                f"has ID {latest.deck.deck_id}."
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
