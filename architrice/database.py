import dataclasses
import enum
import logging
import os
import sqlite3
import traceback
import typing

from . import utils

DATABASE_FILE = "architrice.db"


class Database:
    USER_VERSION = 0

    def __init__(self, tables=None):
        self.conn = None
        self.file: str = None
        self.tables_to_init = tables
        self.tables = {}
        self.log = True

    def init(self, database_file, initial_setup=False):
        """Connect to and set up the database for user."""
        self.file = database_file
        self.conn = sqlite3.connect(self.file)

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
        return self.tables[table].insert(**kwargs)

    def upsert(self, table, **kwargs):
        """Execute an INSERT into table, updating on conflict."""
        kwargs["conflict"] = "update"
        return self.insert(table, **kwargs)

    def insert_many(self, table, **kwargs):
        """Execute many INSERTs into table, using kwarg keys and value lists."""
        self.tables[table].insert_many(**kwargs)

    def insert_many_tuples(self, table, columns, tuples, conflict=None):
        """Execute many INSERT INTO INTO table (columns) VALUES(tuples)"""
        self.execute_many(
            self.tables[table].insert_command(columns, columns, conflict),
            tuples,
        )

    def upsert_many(self, table, **kwargs):
        """Execute many upserts into table."""
        kwargs["conflict"] = "update"
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

    def execute_ret(self, is_insert, cursor, result):
        if is_insert:
            if cursor.rowcount:
                return cursor.lastrowid
            else:
                return None
        else:
            return result

    def execute(self, command, tup=None):
        """Execute an SQL command, logging the command and data."""

        cursor = self.conn.cursor()
        is_insert = command.startswith("INSERT")

        if tup:
            try:
                if self.log:
                    logging.debug(
                        f"Executing database command: {command} with values "
                        f"{tup}."
                    )

                return self.execute_ret(
                    is_insert, cursor, cursor.execute(command, tup)
                )
            except sqlite3.Error as e:
                logging.debug(
                    f"Database errored on command {command} with values {tup}"
                )
                logging.error(f"Database error: {str(e)}")
                if utils.DEBUG:
                    traceback.print_stack()
                    exit()
                return None if is_insert else []

        if self.log:
            logging.debug(f"Executing database command: {command}")
        try:
            return self.execute_ret(is_insert, cursor, cursor.execute(command))
        except sqlite3.Error as e:
            logging.debug(f"Database errored on command {command}")
            logging.error(f"Database error: {str(e)}.")
            if utils.DEBUG:
                traceback.print_stack()
                exit()
            return None if is_insert else []

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
    name: str  # note: conflict and columns are reserved names
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
        self.name: str = name
        self.columns: typing.List[Column] = columns
        self.constraints: typing.List[str] = constraints or []
        self.set_db(db)

    def set_db(self, db, create=True):
        self.db = db
        if db and create:
            self.create()

    def primary_key(self):
        for c in self.columns:
            if c.primary_key:
                return c

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

    def column_string(self, columns):
        return "(" + ", ".join(columns) + ")"

    def substitution_string(self, iterable):
        return "(" + ("?, " * len(iterable))[:-2] + ")"

    def on_conflict_update_string(self, conflict_columns, update_columns):
        if len(update_columns) == 0:
            update_string = " DO NOTHING"
        else:
            update_string = (
                " DO UPDATE SET "
                + self.column_string(update_columns)
                + " = "
                + self.substitution_string(update_columns)
            )

        return (
            " ON CONFLICT"
            + self.column_string(conflict_columns)
            + update_string
        )

    def update_columns(self, conflict_columns, column_names, arguments):
        # Note: this mutates the argument list to add additional arguments
        # for the new updates.

        update_columns = [
            c for c in column_names if c not in conflict_columns and c != "id"
        ]
        for c in update_columns:
            arguments.append(arguments[column_names.index(c)])
        return update_columns

    def create_upsert_string(self, column_names, arguments):
        conflict_string = ""

        for c in self.constraints:
            if "UNIQUE" in c:
                conflict_columns = (
                    c.replace("UNIQUE(", "").replace(")", "").split(", ")
                )

                # Only handle conflicts in columns which could actually occur
                if any(c in column_names for c in conflict_columns):
                    conflict_string += self.on_conflict_update_string(
                        conflict_columns,
                        self.update_columns(
                            conflict_columns, column_names, arguments
                        ),
                    )

        for c in self.columns:
            if (c.unique or c.primary_key) and c.name in column_names:
                conflict_string += self.on_conflict_update_string(
                    [c.name],
                    self.update_columns([c.name], column_names, arguments),
                )

        return conflict_string

    def insert_command(self, column_names, arguments, conflict=None):
        substitution_string = self.substitution_string(arguments)

        if conflict == "update":
            upsert_string = self.create_upsert_string(column_names, arguments)
        else:
            upsert_string = ""

        return (
            "INSERT "
            + ("OR IGNORE " if conflict == "ignore" else "")
            + f"INTO {self.name} {self.column_string(column_names)} VALUES "
            + substitution_string
            + upsert_string
            + ";"
        )

    def column_names(self, **kwargs):
        return [c.name for c in self.columns if c.name in kwargs]

    def create_insert_args(self, **kwargs):
        column_names = self.column_names(**kwargs)
        arguments = [kwargs[name] for name in column_names]
        return (column_names, arguments)

    def insert(self, **kwargs):
        column_names, arguments = self.create_insert_args(**kwargs)
        return self.db.execute(
            self.insert_command(
                column_names, arguments, kwargs.get("conflict")
            ),
            arguments,
        )

    def insert_many(self, **kwargs):
        column_names, arguments = self.create_insert_args(**kwargs)
        self.db.execute_many(
            self.insert_command(
                column_names, arguments, kwargs.get("conflict")
            ),
            zip(*arguments),
        )

    def is_null_check(self, arg):
        if isinstance(arg, str) and "NULL" in arg:
            return True
        return False

    def equality_string(self, name, arg):
        if self.is_null_check(arg):
            return f"{name} IS {arg}"
        return f"{name} = ?"

    def create_where_string(self, column_names, arguments):
        where_string = (
            (
                " WHERE "
                + " AND ".join(
                    [
                        self.equality_string(name, arg)
                        for name, arg in zip(column_names, arguments)
                    ]
                )
            )
            if column_names
            else ""
        )
        arguments = [arg for arg in arguments if not self.is_null_check(arg)]
        return where_string, arguments

    def common_where_handling(self, **kwargs):
        return self.create_where_string(*self.create_insert_args(**kwargs))

    def select(self, column_string, **kwargs):
        where_string, arguments = self.common_where_handling(**kwargs)
        return self.db.execute(
            f"SELECT {column_string} FROM {self.name}{where_string};",
            arguments,
        )

    def select_where_in(self, field, values, column_string):
        return self.db.execute(
            f"SELECT {column_string} FROM {self.name} WHERE {field} IN ("
            + ("?, " * len(values))[:-2]
            + ");",
            values,
        )

    def delete(self, **kwargs):
        where_string, arguments = self.common_where_handling(**kwargs)
        self.db.execute(
            f"DELETE FROM {self.name}{where_string};",
            arguments,
        )


class KeyStoredObject:
    # Singletons like Sources or Targets which are referred in the database
    # by keys.

    def __init__(self, key):
        self.key: str = key


class StoredObject:
    # Objects which are stored in the database may subclass from this class.
    # If they do, they should have attributes for each of the relevant fields
    # in the database. id is provided by default and so only tables with an
    # id column are applicable.

    def __init__(self, table, db_id=None):
        self.table: str = table
        self._id: int = db_id

    @property
    def id(self):
        """Database ID of the StoredObject. Will store() to generate one."""

        if not self._id:
            self.store()
        return self._id

    def get_value(self, name):
        if name == "id":
            return self._id
        value = getattr(self, name, None)
        if isinstance(value, StoredObject):
            value = value.id
        elif isinstance(value, KeyStoredObject):
            value = value.key
        return value

    def store(self):
        """Store this object in the database."""
        kwargs = {}
        for column in database.tables[self.table].columns:
            kwargs[column.name] = self.get_value(column.name)
        insert_id = upsert(self.table, **kwargs)
        if insert_id:
            self._id = insert_id
        elif not self._id:
            self._id = select_one_column(
                self.table,
                "id",
                **{
                    column.name: self.get_value(column.name)
                    for column in database.tables[self.table].columns
                    if column.name != "id"
                },
            )

    def delete_stored(self):
        """If this object has been stored in the db, delete the record."""
        if self._id:
            delete(self.table, id=self._id)


class DatabaseEvents(enum.Enum):
    CARD_LIST_UPDATE = 1


database = Database(
    [
        Table(
            "sources",
            [
                Column("short", "TEXT", primary_key=True),
                Column("name", "TEXT", not_null=True, unique=True),
            ],
        ),
        Table(
            "users",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("name", "TEXT", not_null=True),
                Column("source", "TEXT", references="sources", not_null=True),
                Column("source_id", "TEXT"),
            ],
            ["UNIQUE(source, name)"],
        ),
        Table(
            "targets",
            [
                Column("short", "TEXT", primary_key=True),
                Column("name", "TEXT", not_null=True, unique=True),
            ],
        ),
        Table(
            "output_dirs",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("path", "TEXT", not_null=True, unique=True),
            ],
        ),
        Table(
            "outputs",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("target", "TEXT", references="targets", not_null=True),
                Column(
                    "output_dir",
                    "INTEGER",
                    references="output_dirs",
                    not_null=True,
                ),
                Column(
                    "profile", "INTEGER", references="profiles", not_null=True
                ),
            ],
            ["UNIQUE(target, output_dir, profile)"],
        ),
        Table(
            "profiles",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("user", "INTEGER", references="users", not_null=True),
                Column("name", "TEXT", unique=True),
            ],
        ),
        Table(
            "cards",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("name", "TEXT", index_on=True),
                Column("mtgo_id", "INTEGER", unique=True),
                Column("is_dfc", "INTEGER", not_null=True),
                Column("collector_number", "TEXT", not_null=True),
                Column("edition", "TEXT", not_null=True),
                Column("reprint", "INTEGER", not_null=True),
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
                Column(
                    "output",
                    "INTEGER",
                    references="outputs",
                    not_null=True,
                ),
                Column("updated", "INTEGER"),
            ],
            ["UNIQUE(file_name, output)"],
        ),
        Table(
            "database_events",
            [
                Column("id", "INTEGER", primary_key=True),
                Column("time", "INTEGER", not_null=True),
                Column("data", "TEXT"),
            ],
        ),
    ],
)

insert = database.insert
insert_many = database.insert_many
insert_many_tuples = database.insert_many_tuples
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

    database_file = os.path.join(utils.DATA_DIR, DATABASE_FILE)
    initial_setup = not os.path.exists(database_file)
    utils.ensure_data_dir()
    database.init(database_file, initial_setup)

    from . import sources

    for source in sources.sourcelist:
        insert(
            "sources", conflict="ignore", short=source.SHORT, name=source.NAME
        )

    from . import targets

    for target in targets.targetlist:
        insert(
            "targets", conflict="ignore", short=target.SHORT, name=target.NAME
        )

    commit()
