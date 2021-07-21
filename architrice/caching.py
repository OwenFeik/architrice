import dataclasses
import datetime
import json
import logging
import os

from . import database
from . import profile
from . import utils


@dataclasses.dataclass
class DeckFile:
    deck_id: str
    file_name: str = None
    updated: float = 0
    db_id = None

    def update(self):
        self.updated = datetime.datetime.utcnow().timestamp()

    def to_json(self):
        return {
            "deck_id": self.deck_id,
            "file_name": self.file_name,
            "updated": self.updated,
        }

    @staticmethod
    def from_json(data):
        return DeckFile(data["deck_id"], data["file_name"], data["updated"])


class DirCache:
    def __init__(self, path, db_id=None):
        self.path = path
        self.tracked = {}  # {deck_id: DeckFile} ... for each deck
        self.id = db_id

    def add_deck_update(self, update):
        # Works with both source.DeckUpdate and DeckFile objects

        if update.deck_id in self.tracked:
            deck_file = self.tracked[update.deck_id]
            deck_file.updated = max(deck_file.updated, update.updated)
        else:
            if isinstance(update, DeckFile):
                self.tracked[update.deck_id] = update
            else:
                self.tracked[update.deck_id] = DeckFile(
                    update.deck_id, None, update.updated
                )

    def needs_update(self, update):
        return (
            update
            and update.deck_id not in self.tracked
            or update.updated > self.tracked[update.deck_id].updated
        )

    def decks_to_update(self, deck_updates):
        to_update = []
        for update in deck_updates:
            if self.needs_update(update):
                to_update.append(update.deck_id)
        return to_update

    def get_deck_file(self, deck_id):
        if deck_id not in self.tracked:
            self.tracked[deck_id] = DeckFile(deck_id)
            logging.debug(f"Tracking new deck file for deck {deck_id}.")
        return self.tracked[deck_id]

    def to_json(self):
        return {
            "path": self.path,
            "deck_files": [d.to_json() for d in self.tracked.values()],
        }

    @staticmethod
    def from_json(data):
        dir_cache = DirCache(data["path"])
        for deck_file in data["deck_files"]:
            dir_cache.add_deck_update(DeckFile.from_json(deck_file))
        return dir_cache


class Cache:
    CACHE_FILE = os.path.join(utils.DATA_DIR, "cache.json")

    def __init__(self, profiles=None, dir_caches=None):
        self.profiles = profiles if profiles is not None else []
        self.dir_caches = dir_caches if dir_caches is not None else []

    def add_profile(self, profile, new=True):
        for p in self.profiles:
            if p.equivalent(profile):
                logging.info(
                    f"A profile with identical details already exists, "
                    "skipping creation."
                )
                return

        self.profiles.append(profile)

        if new:
            logging.info(
                f"Added new profile: {profile.user} on "
                f"{profile.source.name} outputting in {profile.target.name} "
                f"format to {profile.path}"
            )

    def remove_profile(self, profile):
        self.profiles.remove(profile)
        logging.info(f"Deleted profile for {str(profile)}.")

    def build_profile(self, source, target, user, path):
        self.add_profile(
            profile.Profile(
                source, target, user, path, self.get_dir_cache(path)
            )
        )

    def filter_profiles(self, source, target, user, path):
        ret = []
        for p in self.profiles:
            if source and p.source is not source:
                continue
            if target and p.target is not target:
                continue
            if user and p.user != user:
                continue
            if path and not os.path.samefile(p.path, path):
                continue
            ret.append(p)
        return ret

    def get_dir_cache(self, path):
        for dir_cache in self.dir_caches:
            if os.path.samefile(path, dir_cache.path):
                break
        else:
            logging.debug(f"Adding new DirCache for {path}.")
            dir_cache = DirCache(path)
            self.dir_caches.append(dir_cache)
        return dir_cache

    def to_json(self):
        return {
            "profiles": [p.to_json() for p in self.profiles],
            "dirs": [d.to_json() for d in self.dir_caches],
        }

    def save(self):
        utils.ensure_data_dir()
        with open(Cache.CACHE_FILE, "w") as f:
            json.dump(self.to_json(), f, indent=4)

    def save_to_db(self):
        dir_caches = []
        for profile in self.profiles:
            if profile.id is None:
                profile.id = database.insert(
                    "profiles",
                    source=profile.source.short,
                    user=profile.user,
                    name=profile.name,
                )
            for profile_dir in profile.dirs:
                if profile_dir.id is None:
                    if profile.dir_cache.id is None:
                        profile.dir_cache.id = database.insert(
                            "dirs", path=profile.dir_cache.path
                        )
                    profile_dir.id = database.insert(
                        "profile_dirs",
                        target=profile_dir.target.short,
                        dir=profile_dir.dir_cache.id,
                        profile=profile.id,
                    )

                if profile_dir.dir_cache not in dir_caches:
                    dir_caches.append(profile_dir.dir_cache)

        # TODO finish database saving

    @staticmethod
    def from_json(data):
        c = Cache(dir_caches=[DirCache.from_json(d) for d in data["dirs"]])
        for p in data["profiles"]:
            c.add_profile(profile.Profile.from_json(p, c), False)
        return c

    @staticmethod
    def load():
        try:
            if os.path.isfile(Cache.CACHE_FILE):
                with open(Cache.CACHE_FILE, "r") as f:
                    return Cache.from_json(json.load(f))
        except:  # corrupted files / old formats / etc
            pass
        return Cache()
