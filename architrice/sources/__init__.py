from . import archidekt, moxfield, tappedout, deckstats

sourcelist = [archidekt, moxfield, tappedout, deckstats]

# Each source must implement:
#
#   SOURCE_NAME
#   SOURCE_SHORT
#   get_deck(deck_id)
#   get_deck_list(username)
#   verify_user(username)
