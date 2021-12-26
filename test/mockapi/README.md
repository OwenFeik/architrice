# API Mocking

This module provides a local test API for the various sources supported by
Architrice. It does this in a very limited fashion, by storing a collection
of sample documents based on the output of the various sources. Thus it is not
necessarily useful as a validation tool for the present state of the webpages as
it represents a snapshot of them. It is instead intended as a tool to test the
`Source -> Profile -> Target` pipeline of the app.

## Query String Hack

To properly mimic the various APIs used by Architrice, query strings need to be
supported. The way this is done here is by creating files from the query strings
by removing the question mark and substituting `&` for `_`. For example
`?owner=Test&ownerexact=true` becomes `owner=Test_ownerexact=true`. The
customised `SimpleHTTPRequestHandler` in `mockapi.py` handles this translation.

## Test Cases

Currently, for each source the following test case has been implemented:

* 1 user, named "Test", with user ID "1"
* 1 EDH deck, named "Test Deck", with deck ID "1", containing the cards
    * 1 Blex, Vexing Pest // Search for Blex (commander)
    * 1 Sol Ring
    * 1 Life // Death
    * 1 Bala Ged Recovery // Bala Ged Sanctuary

These cards where chosen to test the DFC handling of the app.

# Contents (`web/`)

## Archidekt

* `api/decks/`
    * `1/small/format=json` is the test decklist (`deck_id=1`).
    * `cards/owner=Test_ownerexact=true` is the list of decks for the test user.

## Deckstats

* `api.php/`
    * `members/search/search_name=Test` is the member search page for finding
        the member id.
    * `decks_page=1_owner_id=1_act...` is the test decklist.
    * `action=get_deck_id_type=sav...` is the list of decks.

## Moxfield

* `v1/Test` is the test user's information.
* `v2/`
    * `decks/all/1` is the test decklist.
    * `users/Test/decks` is the list of decks.

## TappedOut

* `users/Test/mtg-decks` is the list of decks.
* `mtg-decks/test-deck` is the test decklist.

## Scryfall

The card info gathering uses the Scryfall bulk data download, so this is mocked
as well. 

* `bulk-data/default-cards` contains the information about where to find card
    data.
* `file/scryfall-bulk/default-cards/default-cards.json` contains the data for
    the cards in the test deck.
