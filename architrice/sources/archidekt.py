import requests

from .. import utils

from . import source


class Archidekt(source.Source):
    NAME = "Archidekt"
    SHORT = NAME[0]
    URL_BASE = "https://archidekt.com/api/decks/"

    def __init__(self):
        super().__init__(Archidekt.NAME, Archidekt.SHORT)

    def deck_to_generic_format(self, deck):
        d = source.Deck(deck["name"], deck["description"])

        for card in deck["cards"]:
            c = source.Card(
                card["quantity"],
                card["card"]["oracleCard"]["name"],
                "dfc" in card["card"]["oracleCard"]["layout"],
            )

            if "Commander" in card["categories"]:
                d.commanders.append(c)
            elif "Maybeboard" in card["categories"]:
                d.maybe.append(c)
            elif "Sideboard" in card["categories"]:
                d.side.append(c)
            else:
                d.main.append(c)

        return d

    def _get_deck(self, deck_id, small=True):
        return self.deck_to_generic_format(
            requests.get(
                Archidekt.URL_BASE + deck_id + "/" + "small/" if small else "/",
                params={"format": "json"},
            ).json()
        )

    def deck_list_to_generic_format(self, decks):
        ret = []
        for deck in decks:
            ret.append(
                source.DeckUpdate(
                    self.format_deck_id(str(deck["id"])),
                    utils.parse_iso_8601(deck["updatedAt"]),
                )
            )
        return ret

    def _get_deck_list(self, username, allpages=True):
        decks = []
        url = f"{Archidekt.URL_BASE}cards/?owner={username}&ownerexact=true"
        while url:
            j = requests.get(url).json()
            decks.extend(j["results"])

            if not allpages:
                break

            url = j["next"]

        return self.deck_list_to_generic_format(decks)

    def _verify_user(self, username):
        return bool(len(self._get_deck_list(username, False)))
