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

* Cockatrice (.cod)
* Generic (.txt)
* MTGO (.dek)
* XMage (.dck)

## Installation
Architrice is available on PyPi so you can install it with
`python -m pip install -U architrice` . Architrice requires version Python 3.7
or better.
## Getting Started
To get started run `python -m architrice` for a simple wizard, or use the `-s`,
`-u`, `-t`, `-p` and `-n` command line options to configure as in
```
python -m architrice -a -s website_name -u website_username -t target_program \
    -p /path/to/deck/directory -n profile_name
```
To remove a configured profile use `python -m architrice -d` for a wizard, or
specify a unique subset of source, user, target, path and name as above. To add
another profile use `-a` . For detailed help, use `python -m architrice -h` .

Only your public decks can be seen and downloaded by Architrice.

Flags to filter or provide details of profiles:

* `-u` (`--user`) : set the username to download decks of.
* `-s` (`--source`) : set the website to download decks from.
* `-t` (`--target`) : set the output file format.
* `-p` (`--path`) : set deck file output directory.
* `-n` (`--name`) : set profile name.

Providing these will cause Architrice to filter which profiles it loads. In 
addition they will be used to fill in details for adding new profiles or
outputs. Whenever you need to specify a source or target, you can just use the
first letter. For example `G` instead of `Generic` when specifying a target.

Flags to modify behaviour:

* `-a` (`--add`) : add a new profile.
* `-d` (`--delete`) : delete an existing profile.
* `-o` (`--output`) : add an output to an existing profile.
* `-e` (`--edit`) : edit an existing profile as JSON.
* `-l` (`--latest`) : download only the most recently updated deck for each
    profile.
* `-v` (`--verbose`) : show more information.
* `-q` (`--quiet`) : disable output to terminal.
* `-i` (`--non-interactive`) : prevent input prompts, for scripting.
* `-k` (`--skip-update`) : don't update decks on this run.
* `-r` (`--relink`) : set up shortcuts to start architrice with other 
    applications.
