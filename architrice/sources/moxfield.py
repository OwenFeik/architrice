import requests

from .. import caching
from .. import utils

from . import source


class Moxfield(source.Source):
    NAME = "Moxfield"
    SHORT = NAME[0]
    URL_BASE = "https://api.moxfield.com/"
    DECK_LIST_PAGE_SIZE = 100
    REQUEST_OK = 200

    def __init__(self):
        super().__init__(Moxfield.NAME, Moxfield.SHORT)

    def parse_to_cards(self, board):
        cards = []
        for k in board:
            cards.append(
                (
                    board[k]["quantity"],
                    k,
                )
            )

        return cards

    def deck_to_generic_format(self, deck_id, deck):
        d = self.create_deck(deck_id, deck["name"], deck["description"])

        for board in ["mainboard", "sideboard", "maybeboard", "commanders"]:
            d.add_cards(self.parse_to_cards(deck.get(board, {})), board)

        return d

    def _get_deck(self, deck_id):
        return self.deck_to_generic_format(
            deck_id,
            requests.get(f"{Moxfield.URL_BASE}v2/decks/all/{deck_id}").json(),
        )

    def deck_list_to_generic_format(self, decks):
        ret = []
        for deck in decks:
            ret.append(
                caching.DeckUpdate(
                    caching.DeckDetails(
                        deck["publicId"],
                        self.short,
                    ),
                    utils.parse_iso_8601(deck["lastUpdatedAtUtc"]),
                )
            )
        return ret

    def _get_deck_list(self, username, allpages=True):
        decks = []
        i = 1
        while True:
            j = requests.get(
                f"{Moxfield.URL_BASE}v2/users/{username}/decks",
                params={
                    "pageSize": Moxfield.DECK_LIST_PAGE_SIZE,
                    "pageNumber": i,
                },
            ).json()
            decks.extend(j["data"])
            i += 1
            if i > j["totalPages"] or not allpages:
                break

        return self.deck_list_to_generic_format(decks)

    def _verify_user(self, username):
        return (
            requests.get(f"{Moxfield.URL_BASE}v1/users/{username}").status_code
            == Moxfield.REQUEST_OK
        )
