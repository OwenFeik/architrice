import logging
import time
import requests

from .. import utils

from . import source


class Moxfield(source.Source):
    NAME = "Moxfield"
    SHORT = NAME[0]
    DECK_LIST_PAGE_SIZE = 100
    REQUEST_OK = 200

    # This URL points to an nginx proxy server which reroutes traffic through
    # to the Moxfield API while adding a user agent key provided by Moxfield to
    # allow access to their API.
    URL_BASE = "http://moxfield-proxy.feik.xyz/"

    def __init__(self):
        super().__init__(Moxfield.NAME, Moxfield.SHORT)

        self._logged_wait = False

    def _request(self, url, *, params=None):
        resp = requests.get(
            url, params=params, headers={"User-Agent": utils.user_agent()}
        )

        if resp.status_code == 503:
            if not self._logged_wait:
                logging.info(
                    "Received 503 response due to hitting rate limit. Waiting "
                    + "10s to obey Moxfield rate limit of 1 request per "
                    + "second. Future waits will not be logged."
                )
                self._logged_wait = True
            time.sleep(10)
            return self._request(url, params)
        return resp

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
            self._request(f"{Moxfield.URL_BASE}v2/decks/all/{deck_id}").json(),
        )

    def deck_list_to_generic_format(self, decks):
        ret = []
        for deck in decks:
            ret.append(
                self.deck_update_from(
                    deck["publicId"],
                    utils.parse_iso_8601(deck["lastUpdatedAtUtc"]),
                )
            )
        return ret

    def _get_deck_list(self, username, allpages=True):
        decks = []
        i = 1
        while True:
            j = self._request(
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
        resp = self._request(f"{Moxfield.URL_BASE}v1/users/{username}")
        return resp.status_code == Moxfield.REQUEST_OK
