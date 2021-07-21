import dataclasses
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

    def init(self):
        self.conn = sqlite3.connect(self.file)
        self.cursor = self.conn.cursor()
        self.execute(f"PRAGMA user_version = {Database.USER_VERSION};")
        self.execute("PRAGMA foreign_keys = ON;")

        if self.tables_to_init is not None:
            for table in self.tables_to_init:
                self.add_table(table)

        self.tables_to_init = None

        logging.debug("Connected to database.")

    def add_table(self, table):
        table.set_db(self)
        self.tables[table.name] = table

    def insert(self, table, **kwargs):
        self.tables[table].insert(**kwargs)
        return self.cursor.lastrowid

    def upsert(self, table, **kwargs):
        kwargs["replace"] = True
        self.tables[table].insert(**kwargs)
        return self.cursor.lastrowid

    def insert_many(self, table, **kwargs):
        self.tables[table].insert_many(**kwargs)

    def upsert_many(self, table, **kwargs):
        kwargs["replace"] = True
        self.tables[table].insert_many(**kwargs)

    def select(self, table, **kwargs):
        return self.tables[table].select(**kwargs)

    def execute(self, command, tup=None):
        if tup:
            logging.debug(
                f"Executing database command: {command} with values {tup}."
            )
            return self.cursor.execute(command, tup)
        logging.debug(f"Executing database command: {command}")
        return self.cursor.execute(command)

    def execute_many(self, command, tups):
        return self.conn.executemany(command, tups)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


@dataclasses.dataclass
class Column:
    name: str  # note: replace is a reserved name
    datatype: str
    primary_key: bool = False
    references: str = None  # This column is a foreign key to this table
    unique: bool = False  # Is this column unique
    index_on: bool = False  # Create an index on this column?

    def __str__(self):
        column_def = f"{self.name} {self.datatype}"
        if self.primary_key:
            column_def += " PRIMARY KEY"
        if self.unique:
            column_def += " UNIQUE"
        if self.references:
            column_def += f" REFERENCES {self.references}"
        return column_def


class Table:
    def __init__(self, name, columns, constraints=None, db=None):
        self.name = name
        self.columns = columns
        self.constraints = constraints or []
        self.set_db(db)

    def set_db(self, db):
        self.db = db
        if db:
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

    def insert_command(self, column_names, replace=False):
        return (
            "INSERT "
            + ("OR REPLACE " if replace else "")
            + f"INTO {self.name} ("
            + ", ".join(column_names)
            + ") VALUES ("
            + ("?, " * len(column_names))[:-2]
            + ");"
        )

    def column_names(self, **kwargs):
        return [c.name for c in self.columns if c.name in kwargs]

    def insert(self, **kwargs):
        column_names = self.column_names(**kwargs)
        self.db.execute(
            self.insert_command(column_names, kwargs.get("replace")),
            [kwargs[name] for name in column_names],
        )

    def insert_many(self, **kwargs):
        column_names = self.column_names(**kwargs)
        self.db.execute_many(
            self.insert_command(column_names, kwargs.get("replace")),
            zip(kwargs[name] for name in column_names),
        )

    def select(self, **kwargs):
        column_names = self.column_names(**kwargs)
        return list(
            self.db.execute(
                f"SELECT * FROM {self.name}"
                + (
                    (
                        " WHERE "
                        + " AND ".join([f"{name} = ?" for name in column_names])
                    )
                    if column_names
                    else ""
                )
                + ";",
                [kwargs[name] for name in column_names],
            )
        )


database = Database(
    DATABASE_FILE,
    [
        Table(
            "sources",
            [
                Column("short", "TEXT", primary_key=True),
                Column("name", "TEXT", unique=True),
            ],
        ),
        Table(
            "targets",
            [
                Column("short", "TEXT", primary_key=True),
                Column("name", "TEXT", unique=True),
            ],
        ),
        Table(
            "dirs",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("path", "TEXT", unique=True),
            ],
        ),
        Table(
            "profile_dirs",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("target", "TEXT", references="targets"),
                Column("dir", "INTEGER", references="dirs"),
                Column("profile", "INTEGER", references="profiles"),
            ],
        ),
        Table(
            "profiles",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("source", "TEXT", references="sources"),
                Column("user", "TEXT"),
                Column("name", "TEXT", unique=True),
            ],
        ),
        Table(
            "cards",
            [
                Column("name", "TEXT", unique=True, index_on=True),
                Column("mtgo_id", "INTEGER", unique=True),
                Column("is_dfc", "INTEGER"),
            ],
        ),
        Table(
            "decks",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("deck_id", "TEXT", unique=True, index_on=True),
                Column("source", "TEXT", references="sources"),
            ],
        ),
        Table(
            "deck_files",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("deck", "INTEGER", references="decks"),
                Column("file_name", "TEXT"),
                Column("dir", "INTEGER", references="dirs"),
                Column("updated", "INTEGER"),
            ],
            ["UNIQUE(file_name, dir)"],
        ),
    ],
)

insert = database.insert
insert_many = database.insert_many
upsert = database.upsert
upsert_many = database.upsert_many
select = database.select
commit = database.commit
close = database.close


def init():
    initial_setup = not os.path.exists(DATABASE_FILE)
    utils.ensure_data_dir()
    database.init()
    if initial_setup:
        logging.debug("Performing first-time database setup.")

        from . import sources

        for source in sources.sourcelist:
            insert("sources", short=source.SHORT, name=source.NAME)

        from . import targets

        for target in targets.targetlist:
            insert("targets", short=target.SHORT, name=target.NAME)
