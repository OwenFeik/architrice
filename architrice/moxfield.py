import requests

import architrice.utils as utils

URL_BASE = "https://api.moxfield.com/v2/"
DECK_LIST_PAGE_SIZE = 100
SIDEBOARD_CATEGORIES = ["sideboard", "maybeboard", "commanders"]


def is_dfc(layout):
    return layout in ["transform", "modal_dfc"]


def parse_to_tuples(board):
    card_tuples = []
    for k in board:
        card_tuples.append(
            (board[k]["quantity"], k, is_dfc(board[k]["card"]["layout"]))
        )

    return card_tuples


def deck_to_generic_format(deck):
    main = parse_to_tuples(deck["mainboard"])
    side = []
    for c in SIDEBOARD_CATEGORIES:
        if deck.get(c):
            side.extend(parse_to_tuples(deck[c]))

    return {
        "name": deck["name"],
        "description": deck["description"],
        "main": main,
        "side": side,
    }


def get_deck(deck_id):
    return deck_to_generic_format(
        requests.get(URL_BASE + f"decks/all/{deck_id}").json()
    )


def deck_list_to_generic_format(decks):
    ret = []
    for deck in decks:
        ret.append(
            {
                "id": deck["publicId"],
                "updated": utils.parse_iso_8601(deck["lastUpdatedAtUtc"]),
            }
        )
    return ret


def get_deck_list(user_name):
    decks = []
    i = 1
    while True:
        j = requests.get(
            URL_BASE
            + f"users/{user_name}/decks"
            + f"?pageSize={DECK_LIST_PAGE_SIZE}&pageNumber={i}"
        ).json()
        decks.extend(j["data"])
        i += 1
        if i > j["totalPages"]:
            break

    return deck_list_to_generic_format(decks)
