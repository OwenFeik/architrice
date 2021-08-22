import asyncio
import concurrent.futures
import logging
import os
import typing

from . import database
from . import sources
from . import targets
from . import utils


class Card(database.StoredObject):
    def __init__(
        self,
        name,
        mtgo_id=None,
        is_dfc=False,
        collector_number=None,
        edition=None,
        db_id=None,
    ):
        super().__init__("cards", db_id)
        self.name: str = name
        self.mtgo_id: str = mtgo_id
        self.is_dfc: bool = is_dfc
        self.collector_number: str = collector_number
        self.edition: str = edition

    def __repr__(self):
        return (
            f"<Card name={self.name} mtgo_id={self.mtgo_id} "
            f"is_dfc={self.is_dfc} collector_number={self.collector_number} "
            f"edition={self.edition} id={self.id}>"
        )

    @staticmethod
    def from_record(tup):
        # database record format:
        # (id, name, mtgo_id, is_dfc, collector_number, set, is_reprint)
        _, name, mtgo_id, is_dfc, collector_number, edition, _ = tup
        return Card(
            name, mtgo_id and str(mtgo_id), is_dfc, collector_number, edition
        )


class DeckDetails(database.StoredObject):
    """A DeckDetails object represents a deck in a source."""

    def __init__(self, deck_id, source, db_id=None):
        super().__init__("decks", db_id)
        self.deck_id: str = deck_id
        self.source: str = source

        if deck_id == source == None:
            import traceback

            traceback.print_stack()

    def __hash__(self):
        return hash((self.deck_id, self.source))

    def __repr__(self):
        return (
            f"<DeckDetails deck_id={self.deck_id} source={self.source} "
            f"id={self._id}>"
        )


class Deck(DeckDetails):
    """A Deck object represents a deck downloaded from a source."""

    # The cards held by the deck are (quantity, name) tuples rather than Card
    # objects. They are parsed into Cards before saving.
    def __init__(self, deck_id, source, name, description, **kwargs):
        super().__init__(deck_id, source, db_id=kwargs.get("id"))
        self.name: str = name
        self.description: str = description
        self.main: typing.List[typing.Tuple[int, str]] = kwargs.get("main", [])
        self.side: typing.List[typing.Tuple[int, str]] = kwargs.get("side", [])
        self.maybe: typing.List[typing.Tuple[int, str]] = kwargs.get(
            "maybe", []
        )
        self.commanders: typing.List[typing.Tuple[int, str]] = kwargs.get(
            "commanders", []
        )

    def __repr__(self):
        return super().__repr__().replace("<DeckDetails", "<Deck")

    def get_card_names(self, board):
        return [c[1] for c in self.get_board(board)]

    def get_all_card_names(self):
        return set(
            self.get_card_names("main")
            + self.get_card_names("side")
            + self.get_card_names("maybe")
            + self.get_card_names("commanders")
        )

    def get_main_deck(self, include_commanders=False):
        if include_commanders:
            return self.main + self.commanders
        return self.main

    def get_sideboard(self, include_commanders=True, include_maybe=True):
        sideboard = self.side
        if include_commanders:
            sideboard += self.commanders
        if include_maybe:
            sideboard += self.maybe
        return sideboard

    def get_board(self, board, default="main"):
        board = board.strip().lower()
        if board == "commanders":
            return self.commanders
        elif board in ["maybe", "maybeboard"]:
            return self.maybe
        elif board in ["side", "sideboard"]:
            return self.side
        elif board in ["main", "maindeck", "mainboard"]:
            return self.main
        else:
            return self.get_board(default)

    def add_card(self, card, board):
        self.get_board(board).append(card)

    def add_cards(self, cards, board):
        self.get_board(board).extend(cards)


class DeckUpdate:
    """A DeckUpdate represents the last time a Deck was updated on a source."""

    # Because these are not stored anywhere, they don't need a db id.
    def __init__(self, deck, updated):
        self.deck: DeckDetails = deck
        self.updated: int = updated

    def __repr__(self):
        return f"<DeckUpdate deck={repr(self.deck)} updated={self.updated}>"

    def update(self):
        self.updated = utils.time_now()


class DeckFile(database.StoredObject, DeckUpdate):
    """A DeckFile represents the last time a local Deck file was updated."""

    def __init__(self, deck, updated, file_name, output, db_id=None):
        database.StoredObject.__init__(self, "deck_files", db_id)
        DeckUpdate.__init__(self, deck, updated)
        self.file_name: str = file_name
        self.output: Output = output

    def __repr__(self):
        return (
            super().__repr__().replace("<DeckUpdate", "<DeckFile")[:-1]
            + f" file_name={self.file_name} output={self.output} id={self._id}>"
        )


class OutputDir(database.StoredObject):
    # Keep a dict mapping path to OutputDir so that only one object exists for
    # each output directory.
    output_dirs: typing.Dict[str, "OutputDir"] = {}

    def __init__(self, path, db_id=None):
        super().__init__("output_dirs", db_id)
        self.path: str = path

        # maps hash(Output, DeckDetails) to DeckFile
        self.deck_files: typing.Dict[int, DeckFile] = {}

    def __repr__(self):
        return (
            f"<OutputDir path={self.path} n_deck_files={len(self.deck_files)} "
            f"id={self._id}>"
        )

    def key(self, output, deck):
        return hash((output, deck))

    def create_file_name(self, output, deck):
        """Create a file name for a deck. Will be unique in this dir."""

        file_name = suggested_file_name = output.target.create_file_name(
            deck.name
        )

        i = 1
        while any(d.file_name == file_name for d in self.deck_files.values()):
            file_name = suggested_file_name.replace(".", f"_{i}.")
            i += 1

        return file_name

    def add_deck_file(self, output, deck_file):
        self.deck_files[self.key(output, deck_file.deck)] = deck_file

    def get_deck_file(self, output, deck):
        key = self.key(output, deck)
        if key not in self.deck_files:
            self.deck_files[key] = DeckFile(
                deck, 0, self.create_file_name(output, deck), output
            )
        return self.deck_files[key]

    def has_deck_file(self, output, deck):
        return self.key(output, deck) in self.deck_files

    def deck_needs_updating(self, output, deck_update):
        if not deck_update:
            return False

        # Newly tracked deck file
        if not self.has_deck_file(output, deck_update.deck):
            return True

        deck_file = self.get_deck_file(output, deck_update.deck)

        # Deck file was deleted
        if not os.path.exists(os.path.join(self.path, deck_file.file_name)):
            return True

        # Deck has been updated at source
        if deck_update.updated > deck_file.updated:
            return True

        return False

    def store_deck_files(self):
        for deck_file in self.deck_files.values():
            deck_file.store()

    def remove_output(self, output):
        """Delete all DeckFiles associated with an Output."""

        to_delete = []

        for k, v in self.deck_files.items():
            if v.output is output:
                to_delete.append(k)

        for k in to_delete:
            del self.deck_files[k]

    @staticmethod
    def get_all():
        for tup in database.select("output_dirs"):
            db_id, path = tup
            if path not in OutputDir.output_dirs:
                OutputDir.output_dirs[path] = OutputDir(path, db_id)

        return list(OutputDir.output_dirs.values())

    @staticmethod
    def get(path):
        if not path:
            return None

        if path not in OutputDir.output_dirs:
            for output_dir in OutputDir.output_dirs.values():
                if os.path.samefile(path, output_dir.path):
                    return output_dir

            OutputDir.output_dirs[path] = OutputDir(
                path, database.select_one_column("output_dirs", "id", path=path)
            )
        return OutputDir.output_dirs[path]

    @staticmethod
    def load(db_id):
        if not db_id:
            return None

        path = (database.select_one_column("output_dirs", "path", id=db_id),)
        OutputDir.output_dirs[path] = OutputDir(path, db_id)
        return OutputDir.output_dirs[path]


class Output(database.StoredObject):
    def __init__(self, target, output_dir, profile=None, db_id=None):
        super().__init__("outputs", db_id)
        self.target: targets.target.Target = target
        self.output_dir: OutputDir = output_dir
        self.profile: Profile = profile  # Needed for FK in db

    def __hash__(self):
        # Only needs to be unique to a given output_dir.
        # As an output dir can have at most one output for each target, the
        # target is a perfect hash.
        return hash(self.target.short)

    def __repr__(self):
        return (
            f"<Output target={self.target.short} "
            f"output_dir={repr(self.output_dir)} id={self._id}>"
        )

    def equivalent(self, other):
        return other and (
            other.target is self.target and other.output_dir is self.output_dir
        )

    def set_profile(self, profile):
        self.profile = profile

    def get_updated_deck_file(self, deck):
        deck_file = self.output_dir.get_deck_file(self, deck)
        deck_file.update()

        return deck_file

    def save_deck(self, deck):
        self.target.save_deck(
            deck,
            os.path.join(
                self.output_dir.path, self.get_updated_deck_file(deck).file_name
            ),
        )

    def save_decks(self, decks):
        deck_tuples = []
        for deck in decks:
            deck_file = self.get_updated_deck_file(deck)
            deck_tuples.append(
                (deck, os.path.join(self.output_dir.path, deck_file.file_name))
            )

        self.target.save_decks(deck_tuples)

    def deck_needs_updating(self, deck_update):
        return self.output_dir.deck_needs_updating(self, deck_update)

    def decks_to_update(self, deck_updates):
        to_update = []
        for deck_update in deck_updates:
            if self.deck_needs_updating(deck_update):
                to_update.append(deck_update.deck.deck_id)
        return to_update

    def store(self):
        super().store()
        self.output_dir.store_deck_files()

    def delete_stored(self):
        super().delete_stored()
        self.output_dir.remove_output(self)

    def to_json(self):
        return {
            "target": self.target.name,
            "output_dir": self.output_dir.path,
        }

    @staticmethod
    def from_json(data):
        return Output(
            targets.get(data["target"], True), OutputDir.get(data["output_dir"])
        )


class User(database.StoredObject):
    # Keep a dict mapping (name, source) to User so that only one instance
    # exists for each user.
    users: typing.Dict[typing.Tuple[str, str], "User"] = {}

    def __init__(self, name, source, source_id=None, db_id=None):
        super().__init__("users", db_id)
        self.name: str = name
        self.source: str = source
        self.source_id: str = source_id

    def __hash__(self):
        return hash((self.name, self.source))

    def __str__(self):
        return self.name

    def __repr__(self):
        return (
            f"<User name={self.name} source={self.source} "
            f"source_id={self.source_id}>"
        )

    @staticmethod
    def get_all():
        for tup in database.select("users"):
            db_id, name, short, source_id = tup
            key = (name, short)
            if key not in User.users:
                User.users[key] = User(name, short, source_id, db_id)

        return User.users.values()

    @staticmethod
    def get(name, source: sources.source.Source):
        if not name:
            return None

        key = (name, source.short)
        if key not in User.users:
            User.users[key] = User(
                name,
                source.short,
                None,
                database.select_one_column(
                    "users", "id", name=name, source=source.short
                ),
            )

        return User.users[key]

    @staticmethod
    def load(db_id):
        if not db_id:
            return None

        name, short, source_id = database.select_one(
            "users", ["name", "source", "source_id"], id=db_id
        )
        user = User(name, short, source_id, db_id)
        User.users[(name, short)] = user
        return user


class Profile(database.StoredObject):
    THREAD_POOL_MAX_WORKERS = 12

    def __init__(self, user, name, outputs=None, db_id=None):
        super().__init__("profiles", db_id)
        self.source: sources.source.Source = sources.get(user.source)
        self.user: User = user
        self.name: str = name or None  # Ignore empty string
        self.outputs: typing.List[Output] = []

        if outputs:
            for output in outputs:
                self.add_output(output)

    def __repr__(self):
        return (
            f"<Profile source={self.source.short} user={self.user} "
            f"name={self.name} outputs={self.outputs} id={self._id}>"
        )

    def __str__(self):
        return self.user_string

    @property
    def user_string(self):
        return f"{self.user} on {self.source.name}"

    def equivalent(self, other):
        return (
            other.user == self.user  # same user
            and other.source is self.source  # on same website
            and all(
                any(output.path == o.path for o in self.outputs)
                for output in other.outputs
            )  # with a subset of the outputs
        )

    def add_output(self, output):
        output.set_profile(self)
        if not any(o.equivalent(output) for o in self.outputs):
            self.outputs.append(output)
        else:
            logging.info(
                "Skipping output addition as new output is equivalent to an"
                " existing output."
            )

    def save_deck(self, deck):
        for output in self.outputs:
            output.save_deck(deck)

    def save_decks(self, decks):
        for output in self.outputs:
            output.save_decks(decks)

    def download_deck(self, deck_id):
        logging.debug(f"Downloading {self.source.name} deck {deck_id}.")

        return self.source.get_deck(deck_id)

    # This is asynchronous so that it can use a ThreadPoolExecutor to speed up
    # perfoming many deck requests.
    async def download_decks_pool(self, loop, deck_ids):
        logging.info(
            f"Downloading {len(deck_ids)} decks for {self.user_string}."
        )

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=Profile.THREAD_POOL_MAX_WORKERS
        ) as executor:
            futures = [
                loop.run_in_executor(executor, self.download_deck, deck_id)
                for deck_id in deck_ids
            ]
            decks = await asyncio.gather(*futures)

        # Gather all decks and then save synchonously so that we can update the
        # card database first if necessary.
        self.save_decks(decks)

    def download_all(self):
        logging.info(f"Updating all decks for {self.user_string}.")

        decks_to_update = set()
        deck_list = self.source.get_deck_list(self.user.name)
        for output in self.outputs:
            decks_to_update.update(output.decks_to_update(deck_list))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.download_decks_pool(loop, decks_to_update))

        logging.info(f"Successfully updated all decks for {self.user_string}.")

    def download_latest(self):
        latest = self.source.get_latest_deck(self.user.name)
        if any(output.deck_needs_updating(latest) for output in self.outputs):
            logging.info(f"Updating latest deck for {self.user_string}.")
            self.save_deck(self.download_deck(latest.deck.deck_id))
        else:
            logging.info(
                f"{self.source.name} user {self.user}"
                "'s latest deck is up to date."
            )

    def update(self, latest):
        if not self.outputs:
            logging.info(
                f"No outputs match filters for {self.user_string}. Skipping."
            )

        if latest:
            self.download_latest()
        else:
            self.download_all()

    def store(self):
        self.user.store()
        super().store()
        for output in self.outputs:
            output.store()

    def delete_stored(self):
        for output in self.outputs:
            output.delete_stored()
        super().delete_stored()

    def to_json(self):
        return {
            "source": self.source.name,
            "user": self.user.name,
            "name": self.name,
            "outputs": [output.to_json() for output in self.outputs],
        }

    @staticmethod
    def from_json(data):
        return Profile(
            User.get(data["user"], sources.get(data["source"], True)),
            data["name"],
            [Output.from_json(output) for output in data["outputs"]],
        )


class Cache:
    def __init__(self, profiles=None, output_dirs=None):
        self.profiles: typing.List[Profile] = profiles or []

    def add_profile(self, profile):
        for p in self.profiles:
            if p.equivalent(profile):
                logging.info(
                    f"A profile with identical details already exists, "
                    "skipping creation."
                )
                return p

        self.profiles.append(profile)
        return profile

    def remove_profile(self, profile):
        self.profiles.remove(profile)
        profile.delete_stored()
        logging.info(f"Deleted profile for {profile.user_string}.")

    def build_profile(self, source, user, name):
        return self.add_profile(Profile(User.get(user, source), name, []))

    def build_output(self, profile, target, path):
        profile.add_output(Output(target, OutputDir.get(path)))

    def save(self):
        logging.debug("Saving cache to database.")

        if not utils.DEBUG:
            database.disable_logging()

        for profile in self.profiles:
            profile.store()

        database.enable_logging()
        database.commit()
        logging.debug("Successfullly saved cache, closing connection.")
        database.close()

    @staticmethod
    def load(source=None, target=None, user=None, path=None, name=None):
        """Load all relevant data into memory from the database."""
        database.init()

        output_dirs = []
        for tup in database.select_ignore_none("output_dirs", path=path):
            db_id, path = tup
            output_dirs.append(OutputDir(path, db_id))

        profiles = []

        query = (
            "SELECT p.id, p.user, p.name "
            "FROM profiles p LEFT JOIN users u ON p.user = u.id"
        )
        arguments = []
        conditions = []
        if user:
            conditions.append("UPPER(u.name) = UPPER(?)")
            arguments.append(user)
        if source:
            conditions.append("u.source = ?")
            arguments.append(source.short)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        for tup in database.execute(query + ";", arguments):
            profile_db_id, profile_user, profile_name = tup

            outputs = []
            for tup in database.select_ignore_none(
                "outputs",
                target=getattr(target, "short", None),
                profile=profile_db_id,
            ):
                output_db_id, output_target, output_dir_id, _ = tup

                for output_dir in output_dirs:
                    if output_dir.id == output_dir_id:
                        break
                else:
                    raise LookupError(
                        f"Failed to find dir with id {output_dir_id}."
                    )

                output = Output(
                    targets.get(output_target),
                    output_dir,
                    db_id=output_db_id,
                )
                outputs.append(output)

                for tup in database.execute(
                    "SELECT "
                    "d.id, d.deck_id, d.source, df.id, df.file_name, df.updated"
                    " FROM deck_files df LEFT JOIN decks d ON df.deck = d.id "
                    "WHERE df.output = ?;",
                    (output.id,),
                ):
                    (
                        d_db_id,
                        d_deck_id,
                        d_source,
                        df_db_id,
                        df_file_name,
                        df_updated,
                    ) = tup
                    output.output_dir.add_deck_file(
                        output,
                        DeckFile(
                            DeckDetails(d_deck_id, d_source, d_db_id),
                            df_updated,
                            df_file_name,
                            output,
                            df_db_id,
                        ),
                    )

            profiles.append(
                Profile(
                    User.load(profile_user),
                    profile_name,
                    outputs,
                    profile_db_id,
                )
            )

        return Cache(profiles, output_dirs)
