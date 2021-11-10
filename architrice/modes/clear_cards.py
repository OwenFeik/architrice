import logging

from .. import database

from . import mode


class ClearCards(mode.Mode):
    def __init__(self):
        super().__init__("c", "clear-cards", "clear card info cache", [])

    def action(self, cache, args):
        database.execute("DELETE FROM cards;")
        logging.info("Successfully cleared card data.")
