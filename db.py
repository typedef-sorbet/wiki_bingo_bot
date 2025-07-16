import sqlite3 as sql
from pathlib import Path
from json import loads, dumps

from enum import Enum

from sys import _getframe as frame

from typing import List, Dict, Tuple

import urllib
import wiki

DB_FILE = "wiki.db"

conn = sql.connect(DB_FILE)


class EntryType(Enum):
    CATEGORY = "category"
    ARTICLE = "article"
    ERROR = "err"


# Util functions here
def urlFormat(s):
    return urllib.parse.quote(s.encode("utf-8"))


def create_entry(entry_name: str, entry_type: EntryType) -> bool:
    funcname = frame().f_code.co_name

    global conn
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

    return res


def create_entries_from_names(name_list: List[str]) -> Tuple[bool, str]:
    # Ensure that all names are either articles or categories.
    entry_list = [
        {"entry_name": name, "entry_type": wiki.entry_type(name)} for name in name_list
    ]

    invalid_names = [
        ent["entry_name"] for ent in entry_list if ent["entry_type"] == EntryType.ERROR
    ]

    if len(invalid_names) > 0:
        return (
            False,
            f"The following entries were not found as articles/categories: {', '.join(invalid_names)}",
        )

    create_entries(entry_list)

    return (True, "")


def create_entries(
    entry_list: List[Dict[str, str]] | List[Tuple[str, str]],
) -> List[bool]:
    if len(entry_list) > 0:
        if isinstance(entry_list[0], dict):
            return [create_entry(d["entry_name"], d["entry_type"]) for d in entry_list]
        else:
            return [create_entry(*t) for t in entry_list]
    else:
        return []


def create_preset(preset_name: str, entries: List[str]) -> Tuple[bool, str]:
    funcname = frame().f_code.co_name

    if len(entries) == 0:
        print(f"{funcname}: empty entries list")
        return (False, "Entry list was empty.")

    if preset_exists(preset_name):
        print(f"{funcname}: preset {preset_name} already exists")
        return (False, "A preset by the same name already exists.")

    global conn

    with conn:
        all_valid_entries = set(
            list(conn.execute("SELECT entry_name FROM PresetEntries"))[0]
        )

    not_found_entries = [entry for entry in entries if entry not in all_valid_entries]

    if len(not_found_entries) > 0:
        (success, reason) = create_entries_from_names(not_found_entries)
        if not success:
            return (success, reason)

    entries_json = dumps(entries)

    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO Presets(preset_name, entries) VALUES(?, ?)",
            (preset_name, entries_json),
        )

    return (True, "")


def update_preset(preset_name: str, entries: List[str]) -> Tuple[bool, str]:
    funcname = frame().f_code.co_name

    if len(entries) == 0:
        print(f"{funcname}: empty entries list")
        return (False, "Entry list was empty.")

    if not preset_exists(preset_name):
        print(f"{funcname}: preset {preset_name} doesn't exist")
        return (False, f'No preset found with the name "{preset_name}".')

    global conn

    with conn:
        all_valid_entries = set(
            list(conn.execute("SELECT entry_name FROM PresetEntries"))[0]
        )

    not_found_entries = [entry for entry in entries if entry not in all_valid_entries]

    if len(not_found_entries) > 0:
        (success, reason) = create_entries_from_names(not_found_entries)
        if not success:
            return (success, reason)

    entries_json = dumps(entries)

    with conn:
        conn.execute(
            "UPDATE Presets SET entries = ? WHERE preset_name = ?",
            (entries_json, preset_name),
        )

    return (True, "")


def append_to_preset(preset_name: str, entries: List[str]) -> Tuple[bool, str]:
    funcname = frame().f_code.co_name

    if len(entries) == 0:
        print(f"{funcname}: empty entries list")
        return (False, "Entry list was empty.")

    if not preset_exists(preset_name):
        print(f"{funcname}: preset {preset_name} doesn't exist")
        return (False, f'No preset found with the name "{preset_name}".')

    global conn

    with conn:
        all_valid_entries = set(
            list(conn.execute("SELECT entry_name FROM PresetEntries"))[0]
        )

    not_found_entries = [entry for entry in entries if entry not in all_valid_entries]

    if len(not_found_entries) > 0:
        (success, reason) = create_entries_from_names(not_found_entries)
        if not success:
            return (success, reason)

    with conn:
        existing_entries = set(
            loads(
                list(
                    conn.execute(
                        "SELECT entries FROM Presets WHERE preset_name = ?",
                        (preset_name,),
                    )
                )[0][0]
            )
        )

    merged_entries = existing_entries.union(set(entries))

    entries_json = dumps(list(merged_entries))

    with conn:
        conn.execute(
            "UPDATE Presets SET entries = ? WHERE preset_name = ?",
            (entries_json, preset_name),
        )

    return (True, "")


def delete_preset(preset_name: str) -> Tuple[bool, str]:
    funcname = frame().f_code.co_name

    if not preset_exists(preset_name):
        print(f"{funcname}: preset {preset_name} doesn't exist")
        return (False, f'No preset found with the name "{preset_name}".')

    global conn

    with conn:
        conn.execute(
            "DELETE FROM Presets WHERE preset_name = ? LIMIT 1", (preset_name,)
        )

    return (True, "")


def remove_from_preset(preset_name: str, entries: List[str]) -> bool:
    funcname = frame().f_code.co_name

    if len(entries) == 0:
        print(f"{funcname}: empty entries list")
        return (False, "Entry list was empty.")

    if not preset_exists(preset_name):
        print(f"{funcname}: preset {preset_name} doesn't exist")
        return (False, f'No preset found with the name "{preset_name}".')

    global conn

    with conn:
        existing_entries = set(
            loads(
                list(
                    conn.execute(
                        "SELECT entries FROM Presets WHERE preset_name = ?",
                        (preset_name,),
                    )
                )[0][0]
            )
        )

    merged_entries = existing_entries.difference(set(entries))

    entries_json = dumps(list(merged_entries))

    with conn:
        conn.execute(
            "UPDATE Presets SET entries = ? WHERE preset_name = ?",
            (entries_json, preset_name),
        )

    return (True, "")


def preset_contents(preset_name: str) -> List[Dict[str, str]]:
    global conn

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

    return entries_joined


def presets() -> List[Tuple[str, str]]:
    global conn

    with conn:
        return list(conn.execute("SELECT preset_name, description FROM Presets"))


def initialize_test_db():
    db_path = Path(DB_FILE)

    if not db_path.is_file():
        db_path.touch()

    del db_path

    global conn

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

        # Create CategoryCache table if not exists
        conn.execute(
            "CREATE TABLE IF NOT EXISTS CategoryCache("
            "category_name TEXT PRIMARY KEY, "
            "pages JSON DEFAULT('[]')"
            ")"
        )

    print("Database initialized with test data.")


def category_cache_exists(category_name: str) -> bool:
    global conn

    with conn:
        cache_row = list(
            conn.execute(
                "SELECT category_name FROM CategoryCache WHERE category_name = ?",
                (category_name,),
            )
        )

    return len(cache_row) > 0


def category_cache(category_name: str) -> List[str]:
    global conn

    with conn:
        cache_string = list(
            conn.execute(
                "SELECT pages FROM CategoryCache WHERE category_name = ?",
                (category_name,),
            )
        )[0][0]

        # print(f"Cached string: {cache_string}")

        cache_row = loads(cache_string)

    return cache_row


def cache_category(category_name: str, pages: List[str]) -> bool:
    global conn

    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO CategoryCache(category_name, pages) " "VALUES(?, ?)",
            (category_name, dumps(pages)),
        )

    return True


def preset_exists(preset_name):
    global conn

    with conn:
        rows = list(
            conn.execute("SELECT * FROM presets WHERE preset_name = ?", (preset_name,))
        )

    return len(rows) > 0
