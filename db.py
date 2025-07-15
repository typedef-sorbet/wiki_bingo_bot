import sqlite3 as sql
from pathlib import Path
from json import loads, dumps

from enum import Enum

from sys import _getframe as frame

from typing import List, Dict, Tuple

import urllib

DB_FILE = "wiki.db"


class EntryType(Enum):
    CATEGORY = "category"
    ARTICLE = "article"


# Util functions here
def urlFormat(s):
    return urllib.parse.quote(s.encode("utf-8"))


def create_entry(entry_name: str, entry_type: EntryType) -> bool:
    funcname = frame().f_code.co_name

    try:
        conn = sql.connect(DB_FILE)
    except:
        print(f"{funcname}: Unable to open connection to database file {DB_FILE}")
        return False

    res = True

    with conn:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO PresetEntries(entry_name, entry_type) "
                "VALUES(?, ?)",
                (entry_name, entry_type),
            )
        except:
            print(f"{funcname}: Unable to insert into PresetEntries")
            res = False
        finally:
            conn.close()

    return res


def create_entries(
    entry_list: List[Dict[str, str]] | List[Tuple(str, str)],
) -> List[bool]:
    if len(entry_list) > 0:
        if isinstance(entry_list[0], dict):
            return [create_entry(d["entry_name"], d["entry_type"]) for d in entry_list]
        else:
            return [create_entry(*t) for t in entry_list]
    else:
        return []


def create_preset(preset_name: str, entries: List[str]) -> bool:
    funcname = frame().f_code.co_name

    if len(entries) == 0:
        print(f"{funcname}: empty entries list")
        return False

    if preset_exists(preset_name):
        print(f"{funcname}: preset {preset_name} already exists")
        return False

    conn = sql.connect(DB_FILE)

    with conn:
        all_valid_entries = set(conn.execute("SELECT entry_name FROM PresetEntries"))

    invalid_entries = [entry for entry in entries if entry not in all_valid_entries]

    if len(invalid_entries):
        print(
            f"{funcname}: The following entries were not found: {', '.join(invalid_entries)}"
        )
        return False

    entries_json = dumps(entries)

    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO Presets(preset_name, entries) VALUES(?, ?)",
            (preset_name, entries_json),
        )

    conn.close()

    return True


def update_preset(preset_name: str, entries: List[str]) -> bool:
    funcname = frame().f_code.co_name

    if len(entries) == 0:
        print(f"{funcname}: empty entries list")
        return False

    if not preset_exists(preset_name):
        print(f"{funcname}: preset {preset_name} doesn't exist")
        return False

    conn = sql.connect(DB_FILE)

    with conn:
        all_valid_entries = set(conn.execute("SELECT entry_name FROM PresetEntries"))

    invalid_entries = [entry for entry in entries if entry not in all_valid_entries]

    if len(invalid_entries):
        print(
            f"{funcname}: The following entries were not found: {', '.join(invalid_entries)}"
        )
        return False

    entries_json = dumps(entries)

    with conn:
        conn.execute(
            "UPDATE Presets SET entries = ? WHERE preset_name = ?",
            (entries_json, preset_name),
        )

    conn.close()


def append_to_preset(preset_name: str, entries: List[str]) -> bool:
    funcname = frame().f_code.co_name

    if len(entries) == 0:
        print(f"{funcname}: empty entries list")
        return False

    if not preset_exists(preset_name):
        print(f"{funcname}: preset {preset_name} doesn't exist")
        return False

    conn = sql.connect(DB_FILE)

    with conn:
        all_valid_entries = set(conn.execute("SELECT entry_name FROM PresetEntries")[0])

    invalid_entries = [entry for entry in entries if entry not in all_valid_entries]

    if len(invalid_entries):
        print(
            f"{funcname}: The following entries were not found: {', '.join(invalid_entries)}"
        )
        return False

    with conn:
        existing_entries = set(
            loads(
                conn.execute(
                    "SELECT entries FROM Presets WHERE preset_name = ?", (preset_name,)
                )[0]
            )
        )

    merged_entries = existing_entries.union(set(entries))

    entries_json = dumps(merged_entries)

    with conn:
        conn.execute(
            "UPDATE Presets SET entries = ? WHERE preset_name = ?",
            (entries_json, preset_name),
        )

    conn.close()

    return True


def delete_preset(preset_name: str) -> bool:
    funcname = frame().f_code.co_name

    if len(entries) == 0:
        print(f"{funcname}: empty entries list")
        return False

    if not preset_exists(preset_name):
        print(f"{funcname}: preset {preset_name} doesn't exist")
        return False

    conn = sql.connect(DB_FILE)

    with conn:
        all_valid_entries = set(
            conn.execute(
                "DELETE FROM Presets WHERE preset_name = ? LIMIT 1", (preset_name,)
            )
        )

    conn.close()

    return True


def remove_from_preset(preset_name: str, entries: List[str]) -> bool:
    funcname = frame().f_code.co_name

    if len(entries) == 0:
        print(f"{funcname}: empty entries list")
        return False

    if not preset_exists(preset_name):
        print(f"{funcname}: preset {preset_name} doesn't exist")
        return False

    conn = sql.connect(DB_FILE)

    with conn:
        existing_entries = set(
            loads(
                conn.execute(
                    "SELECT entries FROM Presets WHERE preset_name = ?", (preset_name,)
                )[0]
            )
        )

    merged_entries = existing_entries.difference(set(entries))

    entries_json = dumps(merged_entries)

    with conn:
        conn.execute(
            "UPDATE Presets SET entries = ? WHERE preset_name = ?",
            (entries_json, preset_name),
        )

    conn.close()

    return True


def preset_contents(preset_name: str) -> List[Dict[str, str]]:
    conn = sql.connect(DB_FILE)

    entries_joined = []

    with conn:
        entries = loads(
            list(
                conn.execute(
                    "SELECT entries FROM Presets WHERE preset_name = ?", (preset_name,)
                )
            )[0][0]
        )

        for entry_name in entries:
            entry_type = list(
                conn.execute(
                    "SELECT entry_type FROM PresetEntries WHERE entry_name = ?",
                    (entry_name,),
                )
            )[0][0]
            entries_joined.append({"entry_name": entry_name, "entry_type": entry_type})

    conn.close()

    return entries_joined


def initialize_test_db():
    db_path = Path(DB_FILE)

    if not db_path.is_file():
        db_path.touch()

    del db_path

    conn = sql.connect(DB_FILE)

    with conn:
        # Create the Presets table if it doesn't exist already
        # `contents` is a list of keys into the PresetEntries table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS Presets("
            "preset_name TEXT PRIMARY KEY, "
            "entries JSON DEFAULT('[]'), "
            "description TEXT"
            ")"
        )

        # Create the PresetEntries table if it doesn't exist already
        conn.execute(
            "CREATE TABLE IF NOT EXISTS PresetEntries("
            "entry_name TEXT PRIMARY_KEY, "
            "entry_type TEXT CHECK( entry_type in ('category', 'article') )"
            ")"
        )

        # Load the PresetEntries table with some data
        preset_entries_data = [
            {"entry_name": "The Game Awards winners", "entry_type": "category"},
            {"entry_name": "Indie games", "entry_type": "category"},
            {
                "entry_name": "Digital deck-building card games",
                "entry_type": "category",
            },
            {"entry_name": "Bullet hell video games", "entry_type": "category"},
            {"entry_name": "Platform fighters", "entry_type": "category"},
        ]

        conn.executemany(
            "INSERT OR IGNORE INTO PresetEntries(entry_name, entry_type) "
            "VALUES(:entry_name, :entry_type)",
            preset_entries_data,
        )

        # Load the Presets table with subsets of the above entries
        presets_data = [
            {
                "preset_name": "GameAwardsWinners",
                "entries": dumps(["The Game Awards winners"]),
                "description": "Games that have won The Game Awards in the past.",
            },
            {
                "preset_name": "IndieDarlings",
                "entries": dumps(["Indie games"]),
                "description": "All indie games.",
            },
            {
                "preset_name": "Potpourri",
                "entries": dumps(
                    [
                        "Platform fighters",
                        "Bullet hell video games",
                        "Digital deck-building card games",
                        "The Game Awards winners",
                        "Indie games",
                    ]
                ),
                "description": "A little bit of everything.",
            },
        ]

        conn.executemany(
            "INSERT OR IGNORE INTO Presets(preset_name, entries, description) "
            "VALUES(:preset_name, :entries, :description)",
            presets_data,
        )

    conn.close()

    print("Database initialized with test data.")


def preset_exists(preset_name):
    conn = sql.connect(DB_FILE)

    with conn:
        rows = list(
            conn.execute("SELECT * FROM presets WHERE preset_name = ?", (preset_name,))
        )

    conn.close()

    return len(rows) > 0
