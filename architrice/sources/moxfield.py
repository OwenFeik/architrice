import logging
import threading
import time
import requests

from .. import utils

from . import source


class Moxfield(source.Source):
    NAME = "Moxfield"
    SHORT = NAME[0]
    DECK_LIST_PAGE_SIZE = 100
    REQUEST_OK = 200

    # Moxfield allows roughly one request per second and returns empty or
    # short bodies (rather than always a 503) when that limit is exceeded.
    # Requests are serialised and spaced by at least this many seconds.
    MIN_REQUEST_INTERVAL = 1.2

    # Retry a request that comes back empty or non-200 this many times
    # before giving up and letting the caller surface the error.
    MAX_REQUEST_RETRIES = 6

    # This URL points to an nginx proxy server which reroutes traffic through
    # to the Moxfield API while adding a user agent key provided by Moxfield to
    # allow access to their API.
    URL_BASE = "http://moxfield-proxy.feik.xyz/"

    def __init__(self):
        super().__init__(Moxfield.NAME, Moxfield.SHORT)

        self._logged_wait = False
        self._request_lock = threading.Lock()
        self._last_request = 0.0

    def _request(self, url, *, params=None):
        # Decks are downloaded concurrently, so serialise requests and space
        # them out to respect Moxfield's rate limit. Retry on empty/non-200
        # responses, which Moxfield returns (not always a 503) when the limit
        # is hit.
        resp = None
        for _ in range(Moxfield.MAX_REQUEST_RETRIES):
            with self._request_lock:
                wait = Moxfield.MIN_REQUEST_INTERVAL - (
                    time.monotonic() - self._last_request
                )
                if wait > 0:
                    time.sleep(wait)
                resp = requests.get(
                    url,
                    params=params,
                    headers={"User-Agent": utils.user_agent()},
                )
                self._last_request = time.monotonic()

            if resp.status_code == Moxfield.REQUEST_OK and resp.text:
                return resp

            if not self._logged_wait:
                logging.info(
                    "Received a rate-limited or empty response from Moxfield. "
                    + "Throttling to obey Moxfield's limit of ~1 request per "
                    + "second and retrying. Future waits will not be logged."
                )
                self._logged_wait = True
            time.sleep(Moxfield.MIN_REQUEST_INTERVAL)

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
                f"{Moxfield.URL_BASE}v2/decks/search",
                params={
                    "pageSize": Moxfield.DECK_LIST_PAGE_SIZE,
                    "pageNumber": i,
                    "authorUserNames": username,
                    "sortType": "updated",
                    "sortDirection": "descending",
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
