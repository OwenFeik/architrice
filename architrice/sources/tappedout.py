import re

import bs4
import requests

from .. import caching
from .. import utils

from . import source


class TappedOut(source.Source):
    NAME = "Tapped Out"
    SHORT = NAME[0]
    URL_BASE = "https://tappedout.net/"
    MTGA_CARD_REGEX = re.compile(r"^(?P<qty>\d+) (?P<name>.*) \(.*\)( \d+)?$")
    DECK_HREF_TO_ID_REGEX = re.compile(r"^.*/(.*)/$")

    def __init__(self):
        super().__init__(TappedOut.NAME, TappedOut.SHORT)

    def parse_to_cards(self, mtga_string):
        cards = []
        for line in mtga_string.split("\n"):
            m = TappedOut.MTGA_CARD_REGEX.match(line)
            if m:
                cards.append((m.group("qty"), m.group("name")))
        return cards

    def deck_to_generic_format(
        self, deck_id, mtga_deck, name, description, commanders
    ):
        d = self.create_deck(deck_id, name, description)

        SIDEBOARD_SEPERATOR = "\n\n"
        if SIDEBOARD_SEPERATOR in mtga_deck:
            main_string, side_string = mtga_deck.split(SIDEBOARD_SEPERATOR)
            d.main.extend(self.parse_to_cards(main_string))
            d.side.extend(self.parse_to_cards(side_string))
        else:
            d.main.extend(self.parse_to_cards(mtga_deck))

        # Move commanders to correct list
        to_move = []
        for tup in d.main:
            _, card = tup
            if card in commanders:
                to_move.append(tup)

        for card in to_move:
            d.main.remove(card)
            d.commanders.append(card)

        return d

    def _get_deck(self, deck_id):
        # TappedOut offers a few export formats, but none of them include deck
        # name, deck description, or specify which cards are commanders.
        # Therefore we scrape the HTML with bs4 instead.

        html = requests.get(
            f"{TappedOut.URL_BASE}mtg-decks/{deck_id}/"
        ).content.decode()

        with open(utils.DATA_DIR + "/tmp.html", "w") as f:
            f.write(html)
        soup = bs4.BeautifulSoup(html, "html.parser")

        mtga_deck = soup.find(attrs={"id": "mtga-textarea"}).text

        commanders = []
        for tag in soup.select("div.board-col > h3"):
            if "Commander" in tag.text:
                for card in tag.find_next_sibling("ul").select("span > a"):
                    commanders.append(card.get("data-name"))

        PAGE_TITLE_PREFIX = "MTG Deck: "
        name = (
            soup.find("meta", attrs={"property": "og:title"})
            .get("content")
            .replace(PAGE_TITLE_PREFIX, "")
        )

        description = soup.find(
            "meta", attrs={"property": "og:description"}
        ).get("content")

        return self.deck_to_generic_format(
            deck_id, mtga_deck, name, description, commanders
        )

    def age_string_to_timestamp(self, string):
        # No timestamp, so parse the string for an approximation
        now = utils.time_now()
        if string == "Updated a few seconds ago.":
            return now

        m = re.match(
            r"Updated (?P<n>\d+) (?P<unit>minute|hour|day|month|year)s? ago\.",
            string,
        )
        if m:
            return now - int(m.group("n")) * {
                "minute": 60,
                "hour": 60 * 60,
                "day": 60 * 60 * 24,
                "month": 60 * 60 * 24 * 28,
                "year": 60 * 60 * 24 * 365,
            }[m.group("unit")]
        return now

    def get_page_count(self, soup):
        try:
            return int(
                soup.select_one("ul.pagination")
                .find_all("li")[-1]
                .select_one("a.page-btn")
                .text
            )
        except AttributeError:
            # If we hit a None on one of the selects, no pagination ul exists
            # as there is only a single page.
            return 1

    def _get_deck_list(self, username, allpages=True):
        decks = []

        url_base = f"{TappedOut.URL_BASE}users/{username}/mtg-decks/"

        html = requests.get(url_base).content.decode()
        soup = bs4.BeautifulSoup(html, "html.parser")

        pages = 1 if not allpages else self.get_page_count(soup)
        i = 1
        while i <= pages:
            # First page is grabbed outside the loop so that the number of pages
            # can be determined in advance. For other pages we need to download
            # the page now.
            if i > 1:
                html = requests.get(url_base + f"?page={i}").content.decode()
                soup = bs4.BeautifulSoup(html, "html.parser")

            for chunk in utils.group_iterable(soup.select("div.contents"), 3):
                # Each set of three divs is a single deck entry. The first div
                # is the colour breakdown graph, which is not relevant.

                _, name_div, details_div = chunk

                deck_id = re.sub(
                    TappedOut.DECK_HREF_TO_ID_REGEX,
                    r"\1",
                    name_div.select_one("h3.name > a").get("href"),
                )

                for h5 in details_div.select("h5"):
                    if "Updated" in h5.text:
                        updated = self.age_string_to_timestamp(h5.text.strip())
                        break

                decks.append(
                    caching.DeckUpdate(
                        caching.DeckDetails(deck_id, self.short), updated
                    )
                )

            i += 1

        return decks

    def _verify_user(self, username):
        return bool(len(self._get_deck_list(username, False)))
