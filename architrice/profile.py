import asyncio
import concurrent.futures
import logging
import os

from . import utils

THREAD_POOL_MAX_WORKERS = 12


class ProfileDir:
    def __init__(self, target, dir_cache, db_id=None):
        self.target = target
        self.dir = dir_cache
        self.id = db_id

    def update_deck_file(self, deck):
        deck_file = self.dir.get_deck_file(deck.source, deck.deck_id)
        if deck_file.file_name is None:
            deck_file.file_name = self.target.create_file_name(deck.name)
        deck_file.update()
        return deck_file

    def save_deck(self, deck):
        self.target.save_deck(
            os.path.join(self.dir.path, self.update_deck_file(deck).file_name)
        )

    def save_decks(self, decks):
        deck_tuples = []
        for deck in decks:
            deck_file = self.update_deck_file(deck)
            deck_tuples.append(
                (deck, os.path.join(self.dir.path, deck_file.file_name))
            )

        self.target.save_decks(deck_tuples)


class Profile:
    def __init__(self, source, user, profile_dirs, name=None, db_id=None):
        self.source = source
        self.user = user
        self.dirs = profile_dirs
        self.name = name
        self.id = db_id

    def __repr__(self):
        return f"<Profile source={self.source.name} user={self.user}>"

    def __str__(self):
        return self.user_string

    @property
    def user_string(self):
        return f"{self.user} on {self.source.name}"

    def equivalent(self, other):
        return (
            other.source == self.source
            and other.user == self.user
            and len(set(other.dirs + self.dirs)) == len(self.dirs)
        )

    def add_dir(self, profile_dir):
        self.dirs.append(profile_dir)

    def save_deck(self, deck):
        for profile_dir in self.dirs:
            profile_dir.save_deck(deck)

    def save_decks(self, decks):
        for profile_dir in self.dirs:
            profile_dir.save_decks(decks)

    def download_deck(self, deck_id):
        logging.debug(f"Downloading {self.source.name} deck {deck_id}.")

        return self.source.get_deck(deck_id)

    # This is asynchronous so that it can use a ThreadPoolExecutor to speed up
    # perfoming many deck requests.
    async def download_decks_pool(self, loop, deck_ids, outputs):
        logging.info(
            f"Downloading {len(deck_ids)} decks for {self.user_string}."
        )

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=THREAD_POOL_MAX_WORKERS
        ) as executor:
            futures = [
                loop.run_in_executor(executor, self.download_deck, deck_id)
                for deck_id in deck_ids
            ]
            decks = await asyncio.gather(*futures)

        # Gather all decks and then save synchonously so that we can update the
        # card database first if necessary.
        self.save_decks(decks)

    def download_all(self, outputs):
        logging.info(f"Updating all decks for {self.user_string}.")

        decks_to_update = set()
        deck_list = self.source.get_deck_list(self.user)
        for profile_dir in outputs:
            decks_to_update.update(profile_dir.dir.decks_to_update(deck_list))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            self.download_decks_pool(loop, decks_to_update, outputs)
        )

        logging.info(f"Successfully updated all decks for {self.user_string}.")

    def download_latest(self, outputs):
        latest = self.source.get_latest_deck(self.user)
        if any(profile_dir.dir.needs_update(latest) for profile_dir in outputs):
            logging.info(f"Updating latest deck for {self.user_string}.")
            self.save_deck(self.download_deck(latest.deck_id))
        else:
            logging.info(
                f"{self.source.name} user {self.user}"
                "'s latest deck is up to date."
            )

    def update(self, latest=False, filter_targets=None, filter_dirs=None):
        outputs = []
        for profile_dir in self.dirs:
            if filter_targets and profile_dir.target != filter_targets:
                continue
            if filter_dirs and not os.path.samefile(
                filter_dirs, profile_dir.dir.path
            ):
                continue
            if not utils.check_dir(profile_dir.dir.path):
                logging.error(
                    f"Output directory {profile_dir.dir.path} already "
                    "exists and is a file. Skipping files in this directory."
                )
                continue
            outputs.append(profile_dir)

        if not outputs:
            logging.info("No outputs match filters. Nothing to update.")
            return

        if latest:
            self.download_latest(outputs)
        else:
            self.download_all(outputs)
