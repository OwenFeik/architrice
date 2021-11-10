#!/bin/python3

import argparse
import logging

from . import modes
from . import sources
from . import targets
from . import utils

APP_NAME = utils.APP_NAME

DESCRIPTION = f"""
{APP_NAME} is a tool to download decks from online sources to local directories.
To set up, run {APP_NAME} with no arguments. This will run a wizard to set up a
link between an online source and a local directory. Future runs of {APP_NAME}
will then download all decklists that have been updated or created since the
last run to that directory. 

To add another download profile beyond this first one, run {APP_NAME} -a.

To delete an existing profile, run {APP_NAME} -d, which will launch a wizard to
do so.

To download only the most recently updated decklist for each profile, run
{APP_NAME} -l.

To set up a new profile or delete a profile without CLI, specify
non-interactivity with the -i or --non-interactive flag and use the flags for
source, user, target, path and name as in 
{APP_NAME} -i -s SOURCE -u USER -t TARGET -p PATH -n NAME -a
Replace -a with -d to delete instead of creating. 

To skip updating decklists while using other functionality, include the -k flag.

To add shortcuts to launch {APP_NAME}, run {APP_NAME} -r.
"""


def add_data_args(parser):
    # These arguments are prefixed with an underscore because they are
    # processed into non-underscored replacements with application objects.
    parser.add_argument(
        "-u", "--user", dest="user", help="set username to download decks of"
    )
    parser.add_argument(
        "-s", "--source", dest="source", help="set source website"
    )
    parser.add_argument(
        "-t", "--target", dest="target", help="set target program"
    )
    parser.add_argument(
        "-p", "--path", dest="path", help="set deck file output directory"
    )
    parser.add_argument(
        "-m",
        "--maybeboard",
        dest="include_maybe",
        help="include maybeboard in output sideboard",
        nargs="?",
        const=1,
    )
    # Any string is admissable for a profile name.
    parser.add_argument("-n", "--name", dest="name", help="set profile name")
    # various flags
    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        action="store_true",
        help="disable logging to stdout",
    )
    parser.add_argument(
        "-i",
        "--non-interactive",
        dest="interactive",
        action="store_false",
        help="disable interactivity (for scripts)",
    )


def process_args(args):
    args.source = sources.get(args.source)
    args.target = targets.get(args.target)
    args.user = args.user and args.user.strip()
    args.path = utils.expand_path(args.path)
    args.include_maybe = bool(args.include_maybe)

    return args


def main():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    add_data_args(parser)

    for mode in modes.flag_modes:
        parser.add_argument(
            mode.flag,
            mode.long,
            dest=mode.name,
            action="store_true",
            help=mode.help,
        )

    args = process_args(parser.parse_args())
    utils.set_up_logger(int(not args.quiet))

    selected_mode = None
    for mode in modes.flag_modes:
        if getattr(args, mode.name):
            if selected_mode is None:
                selected_mode = mode
            else:
                logging.info(
                    f"Action already selected: {selected_mode.name}."
                    f" Ignoring {mode.flag} flag."
                )

    # Default behaviour: sync decks
    if selected_mode is None:
        selected_mode = modes.Sync()

    selected_mode.main(args)


if __name__ == "__main__":
    main()
