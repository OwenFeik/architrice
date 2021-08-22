import re

import bs4
import requests

from .. import caching
from .. import utils

from . import source


class Deckstats(source.Source):
    NAME = "Deckstats"
    SHORT = NAME[0]
    URL_BASE = "https://deckstats.net/"

    def __init__(self):
        super().__init__(Deckstats.NAME, Deckstats.SHORT)

    def format_deck_id(self, deck_id, owner_id):
        return deck_id + f"?owner_id={owner_id}"

    def card_json_to_card(self, card):
        return (card["amount"], card["name"])

    def deck_to_generic_format(self, deck_id, deck):
        d = self.create_deck(deck_id, deck["name"], "")

        for section in deck.get("sections", []):
            for card in section.get("cards", []):
                if card.get("isCommander", False):
                    d.commanders.append(self.card_json_to_card(card))
                else:
                    d.main.append(self.card_json_to_card(card))

        for board in ["sideboard", "maybeboard"]:
            for card in deck.get(board, []):
                d.add_card(self.card_json_to_card(card), board)

        return d

    # API Reference:
    # https://deckstats.net/forum/index.php/topic,41323.msg112773.html#msg112773
    #
    # Note that deckstats IDs have the format "DECK_ID&owner_id=OWNER_ID"
    # because this app assumes decks can be retrieved from a single ID, while
    # deckstats requires owner ID as well.
    #
    # It is for this reason that params is not used in requests.get, as it would
    # escape ampersands in the id.
    def _get_deck(self, deck_id):
        return self.deck_to_generic_format(
            deck_id,
            requests.get(
                Deckstats.URL_BASE
                + "api.php/?action=get_deck&id_type=saved&response_type=json"
                f"&id={deck_id}",
            ).json(),
        )

    def get_user_id(self, username):
        html = requests.get(
            f"{Deckstats.URL_BASE}members/search/?search_name={username}"
        ).content.decode()
        soup = bs4.BeautifulSoup(html, "html.parser")
        try:
            href = soup.select_one("a.member_name").get("href")
            return re.sub(
                r"^https://deckstats\.net/decks/(\d+).*$", r"\1", href
            )
        except AttributeError:
            return None

    def _get_deck_list(self, username):
        user_id = self.get_user_id(username)

        decks = []
        i = 1
        while True:
            data = requests.get(
                Deckstats.URL_BASE + "api.php",
                params={
                    "decks_page": i,
                    "owner_id": user_id,
                    "action": "user_folder_get",
                    "result_type": "folder;decks;parent_tree;subfolders",
                },
            ).json()

            folder = data.get("folder")
            if folder:
                for deck in folder.get("decks", []):
                    decks.append(
                        caching.DeckUpdate(
                            caching.DeckDetails(
                                self.format_deck_id(deck["saved_id"], user_id),
                                self.short,
                            ),
                            utils.timestamp_to_utc(deck["updated"]),
                        )
                    )

                if (
                    folder["decks_current_page"] * folder["decks_per_page"]
                    < folder["decks_total"]
                ):
                    i += 1
                else:
                    return decks
            else:
                return []

    def verify_user(self, username):
        return bool(self.get_user_id(username))
