# Architrice

Architrice is a tool to synchronise your online Archidekt deck collection
to your local machine to be used with Cockatrice. It downloads decks by user
or deck id, converts them to Cockatrice deck format and saves them in a location
of your choosing.
## Installation
Architrice is available on PyPi so you can install it with `python -m pip install -U architrice`
## Getting Started
To get started run `python -m architrice` for a simple wizard, or use the `-u`
and `-p` command line options to configure as in
```
python -m architrice -u archidekt_username -p /path/to/deck/directory
```
For detailed help, use `python -m architrice -h`.

Only your public decks on Archidekt can be seen and downloaded by Architrice.
