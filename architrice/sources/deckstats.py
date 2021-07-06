import re

import bs4
import requests

SOURCE_NAME = "Deckstats"
SOURCE_SHORT = "D"

URL_BASE = "https://deckstats.net/"


def card_json_to_tuple(card):
    return (card["amount"], card["name"], "//" in card["name"])


def deck_to_generic_format(deck):
    main = []
    side = []
    for section in deck.get("sections", []):
        for card in section.get("cards", []):
            if card.get("isCommander", False):
                side.append(card_json_to_tuple(card))
            else:
                main.append(card_json_to_tuple(card))

    for card in deck.get("sideboard", []) + deck.get("maybeboard", []):
        side.append(card_json_to_tuple(card))

    return {"name": deck["name"], "description": "", "main": main, "side": side}


# API Reference:
# https://deckstats.net/forum/index.php/topic,41323.msg112773.html#msg112773
#
# Note that deckstats IDs have the format "DECK_ID&owner_id=OWNER_ID" because
# this app assumes decks can be retrieved from a single ID, while deckstats
# requires owner ID as well.
def get_deck(deck_id):
    return deck_to_generic_format(
        requests.get(
            URL_BASE
            + "api.php/?action=get_deck&id_type=saved&response_type=json"
            f"&id={deck_id}"
        ).json()
    )


def get_user_id(username):
    html = requests.get(
        URL_BASE + f"members/search/?search_name={username}"
    ).content.decode()
    soup = bs4.BeautifulSoup(html, "html.parser")
    href = soup.select_one("a.member_name").get("href")
    return re.sub(r"^https://deckstats\.net/decks/(\d+).*$", r"\1", href)


def get_deck_list(username):
    user_id = get_user_id(username)

    decks = []
    i = 1
    while True:
        data = requests.get(
            URL_BASE + "api.php",
            params={
                "decks_page": i,
                "owner_id": user_id,
                "action": "user_folder_get",
                "result_type": "folder;decks;parent_tree;subfolders",
            },
        ).json()

        if folder := data.get("folder"):
            for deck in folder.get("decks", []):
                decks.append(
                    {
                        "id": str(deck["saved_id"]) + f"&owner_id={user_id}",
                        "updated": deck["updated"] or deck["added"],
                    }
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
