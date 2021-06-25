import requests

import architrice.utils as utils

URL_BASE = "https://archidekt.com/api/decks/"

# Note that the api is sensitive to double slashes so /api/decks//id for
# instance will fail.

SIDEBOARD_CATEGORIES = {"Commander", "Maybeboard", "Sideboard"}


def deck_to_generic_format(deck):
    main = []
    side = []

    for card in deck["cards"]:
        card_tuple = (
            card["quantity"],
            card["card"]["oracleCard"]["name"],
            "dfc" in card["card"]["oracleCard"]["layout"],
        )
        if belongs_in_sideboard(card["categories"]):
            side.append(card_tuple)
        else:
            main.append(card_tuple)

    return {
        "name": deck["name"],
        "description": deck["description"],
        "main": main,
        "side": side,
    }


def get_deck(deck_id, small=True):
    return deck_to_generic_format(
        requests.get(
            URL_BASE + f"{deck_id}{'/small' if small else ''}/",
            params={"format": "json"},
        ).json()
    )


def deck_list_to_generic_format(decks):
    ret = []
    for deck in decks:
        ret.append(
            {
                "id": str(deck["id"]),
                "updated": utils.parse_iso_8601(deck["updatedAt"]),
            }
        )
    return ret


def get_deck_list(user_name):
    decks = []
    url = URL_BASE + f"cards/?owner={user_name}&ownerexact=true"
    while url:
        j = requests.get(url).json()
        decks.extend(j["results"])
        url = j["next"]

    return deck_list_to_generic_format(decks)


def belongs_in_sideboard(categories):
    return bool(SIDEBOARD_CATEGORIES.intersection(categories))
