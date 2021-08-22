from . import card_info
from . import target


class XMage(target.Target):
    NAME = "XMage"
    SHORT = NAME[0]
    FILE_EXTENSION = ".dck"
    MAIN_DECK_FORMAT = "{} [{}:{}] {}\n"
    SIDEBOARD_FORMAT = f"SB: {MAIN_DECK_FORMAT}"
    SHORTCUT_NAME = "XMage.lnk"
    EXECUTABLE_NAME = "mage-client"
    SUPPORTS_RELNK = True

    def __init__(self):
        super().__init__(XMage.NAME, XMage.SHORT, XMage.FILE_EXTENSION)

    def xmage_name(self, name):
        return name.partition("//")[0].strip()

    def format_card_list(self, card_info_map, card_list, sideboard=False):
        format_string = (
            XMage.SIDEBOARD_FORMAT if sideboard else XMage.MAIN_DECK_FORMAT
        )

        card_list_string = ""
        for quantity, name in card_list:
            info = card_info_map.get(name)
            if info is None:  # Skip cards we don't have data for
                continue

            card_list_string += format_string.format(
                quantity,
                info.edition.upper(),
                info.collector_number,
                self.xmage_name(name),
            )

        return card_list_string

    def save_deck(self, deck, path, card_info_map=None):
        # XMage decks have the following format:
        #
        # QTY [SET:COLLECTOR_NUMBER] CARD_NAME
        #   ... for each main deck card
        # SB: QTY [SET:COLLECTOR_NUMBER] CARD_NAME
        #   ... for each sideboard card
        # LAYOUT MAIN:(ROWS, COLS)(NONE,false,50)|([SET:COLLECTOR_NUMBER],)
        #   where each | seperated tuple contains the cards in that cell
        # LAYOUT SIDEBOARD:(ROW< COLS)(NONE,false,50)|([SET:COLLECTOR_NUMBER],)
        #   as with the main deck. These layout specifications are optional and
        #   so Architrice omits them.

        if card_info_map is None:
            card_info_map = card_info.map_from_deck(
                deck, mtgo_id_required=False
            )

        deck_string = self.format_card_list(
            card_info_map, deck.get_main_deck()
        ) + self.format_card_list(card_info_map, deck.get_sideboard(), True)

        with open(path, "w") as f:
            f.write(deck_string)
