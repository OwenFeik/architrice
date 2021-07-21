import asyncio
import concurrent.futures
import datetime
import logging
import os

from . import sources
from . import targets

THREAD_POOL_MAX_WORKERS = 12


class ProfileDir:
    def __init__(self, target, dir_cache, db_id=None):
        self.target = target
        self.dir = dir_cache
        self.id = db_id


class Profile:
    def __init__(self, source, user, profile_dirs, name=None, db_id=True):
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
            and other.dir_cache == self.dir_cache
        )

    def download_deck(self, deck_id):
        logging.debug(f"Downloading {self.source.name} deck {deck_id}.")

        deck_file = self.dir_cache.get_deck_file(deck_id)
        deck = self.source.get_deck(deck_id)

        if deck_file.file_name is None:
            deck_file.file_name = self.target.create_file_name(deck.name)

        self.target.save_deck(
            deck, os.path.join(self.path, deck_file.file_name)
        )
        deck_file.update()

    # This is asynchronous so that it can use a ThreadPoolExecutor to speed up
    # perfoming many deck requests.
    async def download_decks_pool(self, loop, decks):
        logging.info(f"Downloading {len(decks)} decks for {self.user_string}.")
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=THREAD_POOL_MAX_WORKERS
        ) as executor:
            futures = [
                loop.run_in_executor(executor, self.download_deck, deck_id)
                for deck_id in decks
            ]
            return await asyncio.gather(*futures)

    def download_all(self):
        logging.info(f"Updating all decks for {self.user_string}.")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            self.download_decks_pool(
                loop,
                self.dir_cache.decks_to_update(
                    self.source.get_deck_list(self.user)
                ),
            )
        )

        logging.info(f"Successfully updated all decks for {self.user_string}.")

    def download_latest(self):
        if self.dir_cache.needs_update(
            (latest := self.source.get_latest_deck(self.user))
        ):
            logging.info(f"Updating latest deck for {self.user_string}.")
            self.download_deck(latest.deck_id)
        else:
            logging.info(
                f"{self.source.name} user {self.user}"
                "'s latest deck is up to date."
            )

    def update(self, latest=False):
        if latest:
            self.download_latest()
        else:
            self.download_all()

    def to_json(self):
        return {
            "source": self.source.name,
            "target": self.target.name,
            "user": self.user,
            "dir": self.path,
        }

    @staticmethod
    def from_json(data, cache):
        return Profile(
            sources.get_source(data["source"]),
            targets.get_target(data["target"]),
            data["user"],
            data["dir"],
            cache.get_dir_cache(data["dir"]),
        )
