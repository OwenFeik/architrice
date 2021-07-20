# Architrice

Architrice is a tool to synchronise your online deck collection
to your local machine to be used with MtG clients. It downloads decks by user, 
converts them to the right deck format and saves them in a location
of your choosing.

Architrice currently supports the following deckbuilding websites

* Archidekt
* Deckstats
* Moxfield
* Tapped Out

and the following MtG clients

* Cockatrice
* MTGO

## Installation
Architrice is available on PyPi so you can install it with
`python -m pip install -U architrice` . Architrice requires version Python 3.8
or better.
## Getting Started
To get started run `python -m architrice` for a simple wizard, or use the `-s`,
`-u` and `-p` command line options to configure as in
```
python -m architrice -n -s website_name -u website_username -p \
    /path/to/deck/directory
```
To remove a configured profile use `python -m architrice -d` for a wizard, or
specify source, user and path as above. To add another profile use `-n` . For
detailed help, use `python -m architrice -h` .

Only your public decks can be seen and downloaded by Architrice.
