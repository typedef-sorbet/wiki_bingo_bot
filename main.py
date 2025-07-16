import discord
import config
import urllib
import requests
import logging

import sqlite3 as sql

from discord.ext import commands, tasks
from bs4 import BeautifulSoup as Soup
from datetime import datetime

from bs4 import BeautifulSoup

from enum import Enum

from json import dumps

from typing import List, Dict, Tuple

import db
import wiki
import random


class WikiError(Enum):
    NO_ERROR = 0
    PRESET_NOT_EXISTS_ERROR = 1


logging.basicConfig(level=logging.INFO)
bot = commands.Bot(command_prefix="!", intents=discord.Intents(34305))

# Trick the site into thinking we're a browser
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 \
    (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
}

DB_NAME = "wiki.db"


# Yes, this pattern fucking sucks, I know
def renderMessage(data):
    # Render the data struct as a text message depending on the contents of the data.
    res = "\n"
    match data:
        case {"type": "list_presets", "presets": list(presets)}:
            for preset_name, description in presets:
                res += f"**{preset_name}** - {description}\n"

        case {
            "type": "list_preset_contents",
            "preset_name": str(preset_name),
            "contents": list(contents),
        }:
            if len(contents) == 0:
                res = f"A preset with the name '{preset_name}' either doesn't exist, or doesn't have any categories/articles listed."
            else:
                res = "\n".join(
                    f'{entry["entry_name"]} _({entry["entry_type"]})_'
                    for entry in contents
                )

        case {"type": "start_game", "room_code": room_code}:
            res += f"BingoSync game created: https://bingosync.com{room_code}"

        # General purpose confirmation
        case True:
            res = "Done."

        case (True, ""):
            res = "Done."

        # General purpose error message
        case (False, reason):
            res = reason

        case WikiError.PRESET_NOT_EXISTS_ERROR:
            res = "Given preset does not exist. Use `!wiki presets` to see a list of registered presets."

        case str(msg):
            res = msg

        case _:
            print(f"Unknown data type: categories {data['Categories']}")
            print(data)
            res = "Unknown data struct, check logs."

    return res


async def sendMessageFromData(ctx, data):
    # Render the data contained in the data struct, and send it
    try:
        await ctx.send(renderMessage(data))

    except discord.HTTPException as httpErr:
        print(f"Failed to send message: {httpErr}")
        return None
    except discord.Forbidden as forbiddenErr:
        print(f"Improper permissions to send message: {forbiddenErr}")
        return None
    except discord.InvalidArgument as invalidErr:
        print(f"Invalid message argument: {invalidErr}")
        return None


# Bot commands go here...
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("-----")


@bot.command(name="wiki")
async def _wiki(ctx, *args):
    match args:
        # Preset Management
        case ["preset"] | ["presets"]:
            await list_presets(ctx)

        case ["preset", "create", preset_name, *entries]:
            await create_preset(ctx, preset_name, entries)

        case ["preset", "delete", preset_name]:
            await delete_preset(ctx, preset_name)

        case ["preset", "update", preset_name, *entries]:
            await update_preset(ctx, preset_name, entries)

        case ["preset", "append", preset_name, *entries]:
            await append_to_preset(ctx, preset_name, entries)

        case ["preset", "remove", preset_name, *entries]:
            await remove_from_preset(ctx, preset_name, entries)

        case ["preset", preset_name]:
            await list_preset_contents(ctx, preset_name)

        # Game Management
        case ["start", game_type, preset_name]:
            await start_game(ctx, game_type, preset_name)

        case ["start", preset_name]:
            await start_game(ctx, "TODO", preset_name)

        # General
        case ["help"]:
            await sendMessageFromData(
                ctx,
                "\n".join([
                    "**Preset Management**",
                    "",
                    "`!wiki presets` - List all preset pools of articles/categories.",
                    "`!wiki preset PRESET_NAME` - List all articles/categories in the named preset pool.",
                    "`!wiki preset create PRESET_NAME (CATEGORY|ARTICLE)...` - Create a new preset pool with the listed categories/articles. Category/article names containing spaces should be wrapped in double-quotes _(e.g. \"Médecins Sans Frontières\")._",
                    "`!wiki preset append PRESET_NAME (CATEGORY|ARTICLE)...` - Append the listed categories/articles to the named preset.",
                    "`!wiki preset update PRESET_NAME (CATEGORY|ARTICLE)...` - Replace the category/article list of the named preset with the given list.",
                    "`!wiki preset remove PRESET_NAME (CATEGORY|ARTICLE)...` - Remove the listed categories/articles from the named preset.",
                    "`!wiki preset delete PRESET_NAME` - Delete the named preset.",
                    "",
                    "**Game Management**",
                    "",
                    "`!wiki start PRESET_NAME` - Start a new bingo board using the named preset. Defaults to Lockout Bingo.",
                    "",
                    "**General**",
                    "",
                    "`!wiki help` - Show this help message.",
                    "`!wiki github` - Returns a link to this bot's GitHub repo."
                ])
            )

        case ["github"]:
            await sendMessageFromData(ctx, "https://github.com/typedef-sorbet/wiki_bingo_bot")

        case _:
            await sendMessageFromData(ctx, "Unknown command. Type `!wiki help` for a list of commands.")


async def list_presets(ctx):
    data = {"type": "list_presets", "presets": db.presets()}

    await sendMessageFromData(ctx, data)


async def list_preset_contents(ctx, preset_name):
    data = {
        "type": "list_preset_contents",
        "preset_name": preset_name,
        "contents": db.preset_contents(preset_name),
    }

    await sendMessageFromData(ctx, data)


async def create_preset(ctx, preset_name, entries):
    await sendMessageFromData(ctx, db.create_preset(preset_name, entries))


async def delete_preset(ctx, preset_name):
    await sendMessageFromData(ctx, db.delete_preset(preset_name))


async def update_preset(ctx, preset_name, entries):
    await sendMessageFromData(ctx, db.update_preset(preset_name, entries))


async def append_to_preset(ctx, preset_name, entries):
    await sendMessageFromData(ctx, db.append_to_preset(preset_name, entries))


async def remove_from_preset(ctx, preset_name, entries):
    await sendMessageFromData(ctx, db.remove_from_preset(preset_name, entries))


async def start_game(ctx, game_type, preset_name):
    # Here's where the rubber meets the road.
    # Start a session, then issue a GET request to the main bingosync site
    # to get the CSRF token.

    session = requests.Session()

    resp = session.get("https://bingosync.com/")

    if resp.status_code != 200:
        await sendMessageFromData(
            ctx,
            (
                False,
                f"GET request to bingosync.com gave status code {resp.status_code}",
            ),
        )
        return

    # The csrf middleware token is embedded in the response HTML, grab it.
    soup = BeautifulSoup(resp.content, "html.parser")
    csrf_token = soup.find("input", {"name": "csrfmiddlewaretoken"}).get("value", "")

    if len(csrf_token) == 0:
        await sendMessageFromData(
            ctx, (False, "Unable to find CSRF middleware token in response HTML.")
        )
        return

    print(f"Found csrfmiddlewaretoken {csrf_token}")

    preset_json = dumps(generate_board_for_preset(preset_name))
    print(f'Generated board: "{preset_json}"')

    post_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Connection": "keepalive",
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.5",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    }

    post_params = {
        "room_name": "discord bot test",
        "passphrase": "youllneverguess",
        "nickname": "wikibot",
        "game_type": "18",  # custom
        "variant_type": "172",  # randomized
        "custom_json": preset_json,
        "lockout_mode": "2",  # TODO: make this configurable
        "seed": "",  # TODO: make this configurable
        "hide_card": "on",
        "csrfmiddlewaretoken": csrf_token,
    }

    resp = session.post(
        "https://bingosync.com/",
        data=post_params,
        headers=post_headers,
        allow_redirects=False,
    )

    if "Location" not in resp.headers:  # File Found
        await sendMessageFromData(
            ctx,
            (
                False,
                f"Got unexpected status code from POST request {resp.status_code} with no Location header",
            ),
        )
        print(f"POST request status code: {resp.status_code}")
        print(f"POST request headers: {resp.headers}")
        # print(f"POST request content: {resp.content}")
        soup = BeautifulSoup(resp.content, "html.parser")
        alert = soup.find("div", {"class": "alert"}).get_text()
        print(f"Alert block text: {alert}")
        return

    room_code = resp.headers["Location"]

    await sendMessageFromData(ctx, {"type": "start_game", "room_code": room_code})


def generate_board_for_preset(
    preset_name: str, cat_depth: int = 500
) -> List[Dict[str, str]]:
    pages = []

    preset_entries = db.preset_contents(preset_name)

    for entry in preset_entries:
        if entry["entry_type"] == db.EntryType.ARTICLE:
            pages.append(entry["entry_name"])
        else:
            pages.extend(wiki.category_contents(entry["entry_name"]))

    # Pages fully loaded, randomly select 25 of them.
    return [{"name": page_name} for page_name in random.sample(pages, 25)]


# Database utility functions


def preset_as_json_string(preset_name):
    conn = sql.connect(DB_NAME)

    with conn:
        contents = str(
            list(
                conn.execute(
                    "SELECT contents FROM presets WHERE preset_name = ?", (preset_name,)
                )
            )[0][0]
        )

    return dumps(
        [{"name": article} for article in contents.split(",")], separators=(",", ":")
    )


if __name__ == "__main__":
    bot.run(config.token())
