import datetime
import re

import bs4
import requests

from .. import utils

SOURCE_NAME = "Tapped Out"
SOURCE_SHORT = "T"

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


def age_string_to_timestamp(string):
    now = datetime.datetime.utcnow().timestamp()
    if string == "Updated a few seconds ago.":
        return now
    elif m := re.match(
        r"Updated (?P<n>\d+) (?P<unit>minute|hour|day|month|year)s? ago\.",
        string,
    ):
        n = int(m.group("n"))
        unit = {
            "minute": 60,
            "hour": 60 * 60,
            "day": 60 * 60 * 24,
            "month": 60 * 60 * 24 * 28,
            "year": 60 * 60 * 24 * 365,
        }[m.group("unit")]
        return now - n * unit
    return now


def get_deck_list(username, allpages=True):
    decks = []

    url_base = URL_BASE + f"users/{username}/mtg-decks/"

    html = requests.get(url_base).content.decode()
    soup = bs4.BeautifulSoup(html, "html.parser")

    if not allpages:
        pages = 1
    else:
        try:
            pages = int(
                soup.select_one("ul.pagination")
                .find_all("li")[-1]
                .select_one("a.page-btn")
                .text
            )
        except AttributeError:
            # If we hit a None on one of the selects, no pagination ul exists
            # as there is only a single page.
            pages = 1

    i = 1

    HREF_TO_ID_REGEX = re.compile(r"^.*/(.*)/$")

    while i <= pages:
        # First page is grabbed outside the loop so that the number of pages
        # can be determined in advance. For other pages we need to download
        # the page now.
        if i > 1:
            html = requests.get(url_base + f"?page={i}").content.decode()
            soup = bs4.BeautifulSoup(html, "html.parser")

        for chunk in utils.group_iterable(soup.select("div.contents"), 3):
            # Each set of three divs is a single deck entry. The first div is
            # the colour breakdown graph, which is not relevant.

            _, name_div, details_div = chunk

            deck_id = re.sub(
                HREF_TO_ID_REGEX,
                r"\1",
                name_div.select_one("h3.name > a").get("href"),
            )

            for h5 in details_div.select("h5"):
                if "Updated" in h5.text:
                    updated = age_string_to_timestamp(h5.text.strip())
                    break

            decks.append({"id": deck_id, "updated": updated})

        i += 1

    return decks


def verify_user(username):
    return bool(len(get_deck_list(username, False)))
