import requests

from .. import utils

from . import source


class Archidekt(source.Source):
    NAME = "Archidekt"
    SHORT = NAME[0]
    URL_BASE = "https://archidekt.com/"

    def __init__(self):
        super().__init__(Archidekt.NAME, Archidekt.SHORT)

    def format_api_request(self, path):
        return Archidekt.URL_BASE + "api/decks/" + path

    def deck_to_generic_format(self, deck_id, deck):
        d = self.create_deck(deck_id, deck["name"], deck["description"])

        for card in deck["cards"]:
            c = (card["quantity"], card["card"]["oracleCard"]["name"])

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
            deck_id,
            requests.get(
                self.format_api_request(
                    deck_id + "/" + "small/" if small else "/"
                ),
                params={"format": "json"},
            ).json(),
        )

    def deck_list_to_generic_format(self, decks):
        ret = []
        for deck in decks:
            ret.append(
                self.deck_update_from(
                    str(deck["id"]), utils.parse_iso_8601(deck["updatedAt"])
                )
            )
        return ret

    def _get_deck_list(self, username, allpages=True):
        decks = []
        url = self.format_api_request(
            f"cards/?owner={username}&ownerexact=true"
        )
        while url:
            j = requests.get(url).json()
            decks.extend(j["results"])

            if not allpages:
                break

            url = j["next"]

        return self.deck_list_to_generic_format(decks)

    def _get_latest_deck(self, username):
        try:
            # By passing allpages=False, we avoid grabbing unnecessary pages of
            # results, as Archidekt returns results presorted by updated time.
            return max(
                self._get_deck_list(username, False), key=lambda d: d.updated
            )
        except ValueError:
            return None

    def _verify_user(self, username):
        return bool(len(self._get_deck_list(username, False)))
