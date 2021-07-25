import dataclasses
import enum
import logging
import os
import sqlite3

from . import utils

DATABASE_FILE = os.path.join(utils.DATA_DIR, "architrice.db")


class Database:
    USER_VERSION = 0

    def __init__(self, file, tables=None):
        self.file = file
        self.conn = self.cursor = None
        self.tables_to_init = tables
        self.tables = {}
        self.log = True

    def init(self, initial_setup=False):
        """Connect to and set up the database for user."""
        self.conn = sqlite3.connect(self.file, check_same_thread=False)
        self.cursor = self.conn.cursor()

        logging.debug("Connected to database.")

        if initial_setup:
            self.execute(f"PRAGMA user_version = {Database.USER_VERSION};")
        self.execute("PRAGMA foreign_keys = ON;")

        if self.tables_to_init is not None:
            for table in self.tables_to_init:
                self.add_table(table, initial_setup)

        self.tables_to_init = None

    def add_table(self, table, create=False):
        """Add a Table to the database, creating it if necessary."""
        table.set_db(self, create)
        self.tables[table.name] = table

    def insert(self, table, **kwargs):
        """Execute an INSERT into table using kwarg keys and values."""
        self.tables[table].insert(**kwargs)
        return self.cursor.lastrowid

    def upsert(self, table, **kwargs):
        """Execute an INSERT into table, updating on conflict."""
        kwargs["update"] = True
        self.tables[table].insert(**kwargs)
        return self.cursor.lastrowid

    def insert_many(self, table, **kwargs):
        """Execute many INSERTs into table, using kwarg keys and value lists."""
        self.tables[table].insert_many(**kwargs)

    def upsert_many(self, table, **kwargs):
        """Execute many upserts into table."""
        kwargs["update"] = True
        self.tables[table].insert_many(**kwargs)

    def select(self, table, columns="*", **kwargs):
        """SELECT columns FROM table WHERE kwargs keys = kwarg values."""
        if isinstance(columns, list):
            columns = ", ".join(columns)

        # Note: returns cursor; use list(db.select(...)) to get raw values.
        return self.tables[table].select(columns, **kwargs)

    def select_one(self, table, columns="*", **kwargs):
        """Return the first tuple resulting from this select."""
        result = list(self.select(table, columns, **kwargs))
        if result:
            return result[0]
        return None

    def select_one_column(self, table, column, **kwargs):
        """Return the first column of the first tuple from this select."""
        result = self.select_one(table, column, **kwargs)
        if result:
            return result[0]
        return None

    def select_ignore_none(self, table, columns="*", **kwargs):
        """Perform a SELECT, ignoring all kwargs which are None."""
        none_values = []
        for key in kwargs:
            if kwargs[key] is None:
                none_values.append(key)

        for key in none_values:
            del kwargs[key]

        return self.select(table, columns, **kwargs)

    def select_where_in(self, table, field, values, columns="*"):
        """SELECT columns FROM table WHERE field in values"""

    def delete(self, table, **kwargs):
        """DELETE FROM table WHERE kwarg keys = kwarg values"""
        self.tables[table].delete(**kwargs)

    def execute(self, command, tup=None):
        """Execute an SQL command, logging the command and data."""
        if tup:
            if self.log:
                logging.debug(
                    f"Executing database command: {command} with values {tup}."
                )
            return self.cursor.execute(command, tup)
        if self.log:
            logging.debug(f"Executing database command: {command}")
        return self.cursor.execute(command)

    def execute_many(self, command, tups):
        """Execute many SQL commands."""
        if self.log:
            logging.debug(f"Executing many with command: {command}")
        return self.conn.executemany(command, tups)

    def commit(self):
        """Commit database changes."""
        self.conn.commit()

    def close(self):
        """Close the database connection."""
        self.conn.close()

    def enable_logging(self):
        """Enable command logging."""
        self.log = True

    def disable_logging(self):
        """Disable command logging."""
        self.log = False


@dataclasses.dataclass
class Column:
    name: str  # note: update and columns are reserved names
    datatype: str
    primary_key: bool = False
    references: str = None  # Foreign key to this table. Cascade delete.
    not_null: bool = False
    unique: bool = False  # Is this column unique
    index_on: bool = False  # Create an index on this column?

    def __str__(self):
        column_def = f"{self.name} {self.datatype}"
        if self.not_null:
            column_def += " NOT NULL"
        if self.primary_key:
            column_def += " PRIMARY KEY"
        if self.unique:
            column_def += " UNIQUE"
        if self.references:
            column_def += f" REFERENCES {self.references} ON DELETE CASCADE"
        return column_def


class Table:
    def __init__(self, name, columns, constraints=None, db=None):
        self.name = name
        self.columns = columns
        self.constraints = constraints or []
        self.set_db(db)

    def set_db(self, db, create=True):
        self.db = db
        if db and create:
            self.create()

    def create(self):
        self.db.execute(
            f"CREATE TABLE IF NOT EXISTS {self.name} ("
            + ", ".join(str(c) for c in self.columns + self.constraints)
            + ");"
        )

        for c in self.columns:
            if c.index_on:
                self.db.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{self.name}_{c.name} "
                    f"ON {self.name} ({c.name});"
                )

    def insert_command(self, column_names, update=False):
        return (
            "INSERT "
            + f"INTO {self.name} ("
            + ", ".join(column_names)
            + ") VALUES ("
            + ("?, " * len(column_names))[:-2]
            + ")"
            + (
                (
                    " ON CONFLICT DO UPDATE SET ("
                    + ", ".join(column_names)
                    + ") = ("
                    + ("?, " * len(column_names))[:-2]
                    + ")"
                )
                if update
                else ""
            )
            + ";"
        )

    def column_names(self, **kwargs):
        return [c.name for c in self.columns if c.name in kwargs]

    def create_insert_args(self, **kwargs):
        column_names = self.column_names(**kwargs)
        arguments = [kwargs[name] for name in column_names]
        if kwargs.get("update"):
            arguments *= 2
        return (column_names, arguments)

    def insert(self, **kwargs):
        column_names, arguments = self.create_insert_args(**kwargs)
        self.db.execute(
            self.insert_command(column_names, kwargs.get("update")),
            arguments,
        )

    def insert_many(self, **kwargs):
        column_names, arguments = self.create_insert_args(**kwargs)
        arguments = zip(*arguments)
        self.db.execute_many(
            self.insert_command(column_names, kwargs.get("update")),
            arguments,
        )

    def where_string(self, column_names):
        return (
            (" WHERE " + " AND ".join([f"{name} = ?" for name in column_names]))
            if column_names
            else ""
        )

    def select(self, column_string, **kwargs):
        column_names = self.column_names(**kwargs)
        return self.db.execute(
            f"SELECT {column_string} FROM {self.name}"
            + self.where_string(column_names)
            + ";",
            [kwargs[name] for name in column_names],
        )

    def select_where_in(self, field, values, column_string):
        return self.db.execute(
            f"SELECT {column_string} FROM {self.name} WHERE {field} IN ("
            + ("?, " * len(values))[:-2]
            + ");",
            values,
        )

    def delete(self, **kwargs):
        column_names = self.column_names(**kwargs)
        self.db.execute(
            f"DELETE FROM {self.name}" + self.where_string(column_names) + ";",
            [kwargs[name] for name in column_names],
        )


class DatabaseEvents(enum.Enum):
    CARD_LIST_UPDATE = 1


database = Database(
    DATABASE_FILE,
    [
        Table(
            "sources",
            [
                Column("short", "TEXT", primary_key=True),
                Column("name", "TEXT", not_null=True, unique=True),
            ],
        ),
        Table(
            "targets",
            [
                Column("short", "TEXT", primary_key=True),
                Column("name", "TEXT", not_null=True, unique=True),
            ],
        ),
        Table(
            "dirs",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("path", "TEXT", not_null=True, unique=True),
            ],
        ),
        Table(
            "profile_dirs",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("target", "TEXT", references="targets", not_null=True),
                Column("dir", "INTEGER", references="dirs", not_null=True),
                Column(
                    "profile", "INTEGER", references="profiles", not_null=True
                ),
            ],
        ),
        Table(
            "profiles",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("source", "TEXT", references="sources", not_null=True),
                Column("user", "TEXT", not_null=True),
                Column("name", "TEXT", unique=True),
            ],
        ),
        Table(
            "cards",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("name", "TEXT", unique=True, index_on=True),
                Column("mtgo_id", "INTEGER", unique=True),
                Column("is_dfc", "INTEGER", not_null=True),
                Column("collector_number", "TEXT", not_null=True),
                Column("edition", "TEXT", not_null=True),
            ],
        ),
        Table(
            "decks",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("deck_id", "TEXT", not_null=True, index_on=True),
                Column("source", "TEXT", not_null=True, references="sources"),
            ],
            ["UNIQUE(deck_id, source)"],
        ),
        Table(
            "deck_files",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("deck", "INTEGER", references="decks", not_null=True),
                Column("file_name", "TEXT", not_null=True),
                Column("dir", "INTEGER", references="dirs", not_null=True),
                Column("updated", "INTEGER"),
            ],
            ["UNIQUE(file_name, dir)"],
        ),
        Table(
            "database_events",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("time", "INTEGER", not_null=True),
            ],
        ),
    ],
)

insert = database.insert
insert_many = database.insert_many
upsert = database.upsert
upsert_many = database.upsert_many
select = database.select
select_one = database.select_one
select_one_column = database.select_one_column
select_ignore_none = database.select_ignore_none
delete = database.delete
execute = database.execute
commit = database.commit
close = database.close
enable_logging = database.enable_logging
disable_logging = database.disable_logging


def init():
    """Connect to the database, setting it up if necessary."""

    initial_setup = not os.path.exists(DATABASE_FILE)
    utils.ensure_data_dir()
    database.init(initial_setup)
    if initial_setup:
        logging.debug("Performing first-time database setup.")

        from . import sources

        for source in sources.sourcelist:
            insert("sources", short=source.SHORT, name=source.NAME)

        from . import targets

        for target in targets.targetlist:
            insert("targets", short=target.SHORT, name=target.NAME)
