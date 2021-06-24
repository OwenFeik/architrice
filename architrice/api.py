import requests

URL_BASE = "https://archidekt.com/api/decks/"

# Note that the api is sensitive to double slashes so /api/decks//id for
# instance will fail.


def get_deck(deck_id, small=True):
    return requests.get(
        URL_BASE + f"{deck_id}{'/small' if small else ''}/",
        params={"format": "json"},
    ).json()


def get_decks(user_name):
    decks = []
    url = URL_BASE + f"cards/?owner={user_name}&ownerexact=true"
    while url:
        j = requests.get(url).json()
        decks.extend(j["results"])
        url = j["next"]

    return decks
