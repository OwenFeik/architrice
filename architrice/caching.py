import dataclasses
import logging
import os

from . import database
from . import profile
from . import sources
from . import targets
from . import utils


# TODO: This ignores targets. Need to mirror the database structure where
# deckfiles reference decks.
@dataclasses.dataclass
class DeckFile:
    deck_id: str
    source: str
    file_name: str = None
    updated: int = 0
    db_id: int = None

    def update(self):
        self.updated = utils.time_now()


class DirCache:
    def __init__(self, path, db_id=None):
        self.path = path
        self.tracked = {}  # {(source_short, deck_id): DeckFile}
        self.id = db_id

    def __repr__(self):
        return f"<DirCache path={self.path} id={self.id}>"

    def create_key(self, source_short, deck_id):
        return (source_short, deck_id)

    def tracked_key(self, update):
        return self.create_key(update.source, update.deck_id)

    def tracking(self, update):
        return self.tracked_key(update) in self.tracked

    def track(self, update):
        self.tracked[self.tracked_key(update)] = update

    def add_deck_update(self, update):
        # Works with both source.DeckUpdate and DeckFile objects

        if deck_file := self.tracked.get(self.tracked_key(update)):
            deck_file.updated = max(deck_file.updated, update.updated)
        else:
            if isinstance(update, DeckFile):
                self.track(update)
            else:
                self.track(
                    DeckFile(update.deck_id, update.source, update.updated)
                )

    def needs_update(self, update):
        return update and (
            not self.tracking(update)
            or not os.path.exists(
                os.path.join(
                    self.path, self.tracked[self.tracked_key(update)].file_name
                )
            )
            or update.updated > self.tracked[self.tracked_key(update)].updated
        )

    def decks_to_update(self, deck_updates):
        to_update = []
        for update in deck_updates:
            if self.needs_update(update):
                to_update.append(update.deck_id)
        return to_update

    def get_deck_file(self, source_short, deck_id):
        key = self.create_key(source_short, deck_id)
        if key not in self.tracked:
            self.tracked[key] = DeckFile(deck_id, source_short)
            logging.debug(f"Tracking new deck file for deck {deck_id}.")
        return self.tracked[key]


class Cache:
    def __init__(self, profiles=None, dir_caches=None):
        self.profiles = profiles if profiles is not None else []
        self.dir_caches = dir_caches if dir_caches is not None else []

    def add_profile(self, prof, new=True):
        for p in self.profiles:
            if p.equivalent(prof):
                logging.info(
                    f"A profile with identical details already exists, "
                    "skipping creation."
                )
                return

        self.profiles.append(prof)

        if new:
            logging.info(
                f"Added new profile: {prof.user} on {prof.source.name}."
            )

        return prof

    def remove_profile(self, prof):
        self.profiles.remove(prof)
        if prof.id:
            database.delete("profiles", id=prof.id)
        logging.info(f"Deleted profile for {str(prof)}.")

    def build_profile(self, source, user, name):
        return self.add_profile(
            profile.Profile(
                source,
                user,
                [],
                name,
            )
        )

    def build_profile_dir(self, prof, target, path):
        prof.add_dir(profile.ProfileDir(target, self.get_dir_cache(path)))

    def filter_profiles(self, source, user, name):
        ret = []
        for p in self.profiles:
            if source and p.source is not source:
                continue
            if user and p.user != user:
                continue
            if name and p.name != name:
                continue
            ret.append(p)
        return ret

    def get_dir_cache(self, path):
        if not path:
            return None

        for dir_cache in self.dir_caches:
            if os.path.samefile(path, dir_cache.path):
                break
        else:
            logging.debug(f"Adding new DirCache for {path}.")
            dir_cache = DirCache(path)
            self.dir_caches.append(dir_cache)
        return dir_cache

    @staticmethod
    def load(source=None, target=None, user=None, path=None, name=None):
        database.init()

        dir_caches = []
        for tup in database.select_ignore_none("dirs", path=path):
            db_id, path = tup
            dir_cache = DirCache(path, db_id)
            dir_caches.append(dir_cache)

            for tup in database.execute(
                "SELECT d.deck_id, d.source, df.id, df.file_name, df.updated "
                "FROM deck_files df LEFT JOIN decks d ON df.deck = d.id "
                "WHERE df.dir = ?;",
                (dir_cache.id,),
            ):
                df_deck_id, df_source, df_db_id, df_file_name, df_updated = tup
                dir_cache.add_deck_update(
                    DeckFile(
                        df_deck_id,
                        df_source,
                        df_file_name,
                        df_updated,
                        df_db_id,
                    )
                )

        profiles = []
        for tup in database.select_ignore_none(
            "profiles",
            source=getattr(source, "short", None),
            user=user,
            name=name,
        ):
            profile_db_id, profile_source, profile_user, profile_name = tup

            profile_dirs = []
            for tup in database.select_ignore_none(
                "profile_dirs",
                target=getattr(target, "short", None),
                profile=profile_db_id,
            ):
                profile_dir_db_id, profile_dir_target, dir_cache_id, _ = tup

                for dir_cache in dir_caches:
                    if dir_cache.id == dir_cache_id:
                        break
                else:
                    raise LookupError(
                        f"Failed to find dir with id {dir_cache_id}."
                    )

                profile_dirs.append(
                    profile.ProfileDir(
                        targets.get_target(profile_dir_target),
                        dir_cache,
                        profile_dir_db_id,
                    )
                )
            profiles.append(
                profile.Profile(
                    sources.get_source(profile_source),
                    profile_user,
                    profile_dirs,
                    profile_name,
                    profile_db_id,
                )
            )

        return Cache(profiles, dir_caches)

    def save(self):
        logging.debug("Saving cache.")
        database.disable_logging()

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
                    if profile_dir.dir.id is None:
                        profile_dir.dir.id = database.insert(
                            "dirs", path=profile_dir.dir.path
                        )
                    profile_dir.id = database.insert(
                        "profile_dirs",
                        target=profile_dir.target.short,
                        dir=profile_dir.dir.id,
                        profile=profile.id,
                    )

                if profile_dir.dir not in dir_caches:
                    dir_caches.append(profile_dir.dir)

        for dir_cache in dir_caches:
            for deck_file in dir_cache.tracked.values():
                deck = database.select_one_column(
                    "decks", "id", deck_id=deck_file.deck_id
                )
                if not deck:
                    deck = database.insert(
                        "decks",
                        deck_id=deck_file.deck_id,
                        source=deck_file.source,
                    )

                database.upsert(
                    "deck_files",
                    deck=deck,
                    file_name=deck_file.file_name,
                    dir=dir_cache.id,
                    updated=deck_file.updated,
                )

        database.enable_logging()
        database.commit()
        logging.debug("Successfully saved cache, closing database connection.")
        database.close()
