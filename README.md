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

Only your public decks can be seen and downloaded by Architrice.
Architrice can output for the following MtG clients

* Cockatrice (.cod)
* Generic (.txt)
* MTGO (.dek)
* XMage (.dck)

## Installation
Architrice is available on PyPi so you can install it with
`python -m pip install -U architrice` . Architrice requires Python version 3.7
or better.
## Getting Started
To get started run `python -m architrice` for a simple wizard, or use the `-s`,
`-u`, `-t`, `-p` and `-n` command line options to configure as in
```
python -m architrice -a -s website_name -u website_username -t target_program \
    -p /path/to/deck/directory -n profile_name
```
To remove a configured profile use `python -m architrice -d` for a wizard, or
specify a unique combination of source, user, target, path and name as above.
To add another profile use `-a` . For detailed help, use
`python -m architrice -h` .
## Details

Flags to filter or provide details of profiles, used with a string to provide it
as an argument (e.g. `architrice -u Username`):

* `-u` (`--user`) : set the username to download decks of.
* `-s` (`--source`) : set the website to download decks from.
* `-t` (`--target`) : set the output file format.
* `-p` (`--path`) : set deck file output directory.
* `-n` (`--name`) : set profile name.

In addition there is a which by it's specification or not determines whether the
"maybeboards" of downloaded decks should be included. No argument needs to be
supplied, calling `architrice -m` specifies that maybeboards should be included.

* `-m` (`--include-maybe`)

Providing any of these will cause Architrice to filter which profiles it loads.
In  addition they will be used to fill in details for adding new profiles or
outputs. Whenever you need to specify a source or target, you can just use the
first letter. For example `G` instead of `Generic` when specifying a target.

Flags to modify behaviour:

* `-q` (`--quiet`) : disable output to terminal.
* `-i` (`--non-interactive`) : prevent input prompts, for scripting. If
    insufficient arguments are supplied this may cause some modes to fail.
* `-a` (`--add-profile`) : add a new profile.
* `-d` (`--delete`) : delete an existing profile and exit.
* `-e` (`--edit`) : edit an existing profile as JSON, using `$EDITOR`.
* `-j` (`--export-json`) : echo a JSON description of filtered profiles.
* `-J` (`--import-json`) : imports the JSON profile file specified using `-p`.
* `-l` (`--latest`) : download only the most recently updated deck for each
    profile.
* `-o` (`--add-output`) : add an output to an existing profile.
* `-r` (`--relink`) : set up shortcuts to start architrice with other 
    applications. Note: this feature is in beta and isn't available for all
    clients.
* `-v` (`--version`) : print Architrice version and exit.
* `-c` (`--clear-cards`) : clear local card info cache.
