import logging
import time
import requests

from .. import utils
from ..modes import cli

from . import source


class Moxfield(source.Source):
    NAME = "Moxfield"
    SHORT = NAME[0]
    URL_BASE = "https://api.moxfield.com/"
    DECK_LIST_PAGE_SIZE = 100
    REQUEST_OK = 200
    USER_AGENT_KEY = "moxfield_user_agent"

    def __init__(self):
        super().__init__(Moxfield.NAME, Moxfield.SHORT)

        self._user_agent = ""
        self._last_request_time = 0
        self._logged_wait = False
        self._printed_user_agent_message = False

    def _request(self, url, *, params=None):
        delta = time.time() - self._last_request_time
        wait_time = round(1.0 - delta, 2)
        if wait_time > 0.0:
            if not self._logged_wait:
                logging.info(
                    "Waiting "
                    + str(wait_time)
                    + "s to obey Moxfield rate limit of 1 request per second."
                    + " Future waits will not be logged."
                )
                self._logged_wait = True
            time.sleep(wait_time)
        self._last_request_time = time.time()

        return requests.get(
            url, params=params, headers={"User-Agent": self._user_agent}
        )

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

    def ensure_setup(self, interactive, cache):
        if not self._user_agent:
            self._user_agent = cache.load_string_value(Moxfield.USER_AGENT_KEY)
        if not self._user_agent:
            if interactive:
                if not self._printed_user_agent_message:
                    print(USER_AGENT_MESSAGE)
                    self._printed_user_agent_message = True
                self._user_agent = cli.get_string("Moxfield user agent")
                resp = self._request(Moxfield.URL_BASE + "v1")
                if resp.status_code == 403:
                    prompt = (
                        "Failed to perform a request with user agent `"
                        + self._user_agent
                        + "`, try again?"
                    )
                    if cli.get_decision(prompt):
                        self.ensure_setup(True, cache)
                    else:
                        raise ValueError("Moxfield user agent not provided.")
                else:
                    cache.save_string_value(
                        Moxfield.USER_AGENT_KEY, self._user_agent
                    )
            else:
                raise ValueError(
                    "Missing Moxfield user agent and unable to retrieve it "
                    + "while non-interactive. Please run "
                    + utils.APP_NAME
                    + " interactively to provide your user agent."
                )


USER_AGENT_MESSAGE = """
The Moxfield API no longer allows arbritrary public access. As of version
0.1.0 architrice requires a user agent provided by Moxfield support to be able
to download decks from Moxfield. Such a user agent token can be obtained by
contacting Moxfield support by emailing support@moxfield.com with a request
similar to the below example:

Hi, I use a tool called Architrice (https://pypi.org/project/architrice/) to
sync my MTG decklists from Moxfield to my computer. This tool depends on the
Moxfield API and is blocked by Cloudflare. May I please have a user agent to
access the API so I can continue to use Moxfield in this way?

Once you have a user agent key (something like "architrice abcdef123456") you
can provide it for Architrice to use to download your decks.
"""
