import bs4
import re

import requests

URL_BASE = "https://tappedout.net/"


def parse_to_tuples(card_list_string):
    card_tuples = []
    REGEX = re.compile(r"^(?P<qty>\d+) (?P<name>.*) \(.*\)( \d+)?$")
    for line in card_list_string.split("\n"):
        m = REGEX.match(line)
        if m:
            # Note that tappedout gives card names in the same format as
            # Cockatrice, so DFCs already have the back face name stripped
            # and no further processing needs doing, hence is_dfc can be False
            card_tuples.append((m.group("qty"), m.group("name"), False))
    return card_tuples


def deck_to_generic_format(mtga_deck, name, description, commanders):
    SIDEBOARD_SEPERATOR = "\n\n"
    if SIDEBOARD_SEPERATOR in mtga_deck:
        main_string, side_string = mtga_deck.split(SIDEBOARD_SEPERATOR)
        main = parse_to_tuples(main_string)
        side = parse_to_tuples(side_string)
    else:
        main = parse_to_tuples(mtga_deck)
        side = []

    # Move commanders to the sideboard
    to_move = []
    for card in main:
        if card[1] in commanders:
            to_move.append(card)

    for card in to_move:
        main.remove(card)
        side.append(card)

    return {
        "name": name,
        "description": description,
        "main": main,
        "side": side,
    }


def get_deck(deck_id):
    # TappedOut offers a few export formats, but none of them include deck
    # name, deck description, or specify which cards are commanders. Therefore
    # we scrape the HTML with bs4 instead.

    html = requests.get(URL_BASE + f"mtg-decks/{deck_id}/").content.decode()
    soup = bs4.BeautifulSoup(html, "html.parser")

    mtga_deck = soup.find(attrs={"id": "mtga-textarea"}).text

    commanders = []
    for tag in soup.select("div.board-col > h3"):
        if "Commander" in tag.text:
            for card in tag.find_next_sibling("ul").select("span.card > a"):
                commanders.append(card.get("data-name"))

    PAGE_TITLE_PREFIX = "MTG DECK: "
    name = (
        soup.find("meta", attrs={"property": "og:title"})
        .get("content")
        .replace(PAGE_TITLE_PREFIX, "")
    )

    description = soup.find("meta", attrs={"property": "og:description"}).get(
        "content"
    )

    return deck_to_generic_format(mtga_deck, name, description, commanders)


def get_deck_list(username, allpages=True):
    decks = []
    while True:
        requests.get(URL_BASE + f"users/{username}/mtg-decks/")
