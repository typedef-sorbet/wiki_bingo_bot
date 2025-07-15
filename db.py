import sqlite3 as sql
from pathlib import Path
from json import loads, dumps

from enum import Enum

from sys import _getframe as frame

DB_FILE = "wiki.db"


class EntryType(Enum):
    CATEGORY = "category"
    ARTICLE = "article"


class create_entry(entry_name: str, entry_type: EntryType) -> bool:
    try:
        conn = sql.connect(DB_FILE)
    except:
        print(f"{frame().f_code.co_name}: Unable to open connection to database file {DB_FILE}")
        return False

    res = True

    with conn:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO PresetEntries(entry_name, entry_type) "
                "VALUES(?, ?)",
                (entry_name, entry_type)
            )
        except:
            print(f"{frame().f_code.co_name}: Unable to insert into PresetEntries")
            res = False
        finally:
            conn.close()

    return res

class create_entries(entry_list: List[Dict[str, str]]) -> List[bool]:
    return [create_entry(d["entry_name"], d["entry_type"]) for d in entry_list]

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
            "entry_type TEXT CHECK( entry_type in ('category', 'article') ), "
        )

        # Load the PresetEntries table with some data
        preset_entries_data = {
            {"entry_name": "The Game Awards winners", "entry_type": "category"},
            {"entry_name": "Indie games", "entry_type": "category"},
            {
                "entry_name": "Digital deck-building card games",
                "entry_type": "category",
            },
            {"entry_name": "Bullet hell video games", "entry_type": "category"},
            {"entry_name": "Platform fighters", "entry_type": "category"},
        }

        conn.executemany(
            "INSERT OR IGNORE INTO PresetEntries(entry_name, entry_type) "
            "VALUES(:entry_name, :entry_type)",
            preset_entries_data,
        )

        # Load the Presets table with subsets of the above entries
        presets_data = {
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
        }

        conn.executemany(
            "INSERT OR IGNORE INTO Presets(preset_name, entries, description) "
            "VALUES(:preset_name, :entries, :description)",
            presets_data,
        )

    conn.close()

    print("Database initialized with test data.")
