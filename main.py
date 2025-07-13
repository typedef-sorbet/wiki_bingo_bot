import discord
import config
import urllib
import requests
import logging

from discord.ext import commands, tasks
from bs4 import BeautifulSoup as Soup
from datetime import datetime

logging.basicConfig(level=logging.INFO)
bot = commands.Bot(
    command_prefix="!", 
    intents = discord.Intents(34305)
)

# Trick the site into thinking we're a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 \
    (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
}

# Util functions here
def urlFormat(s):
    return urllib.parse.quote(s.encode("utf-8"))

def renderMessage(data):
    # Render the data struct as a text message depending on the contents of the data.
    match data:
        case _:
            print(f"Unknown data type: categories {data['Categories']}")
            print(data)

async def sendMessageFromData(ctx, data):
    # Render the data contained in the data struct, and send it
    try:
        await ctx.send(renderMessage(data))

        if "Images" in data:
            for idx, img in enumerate(data["Images"]):
                if "Locations" in data and idx >= len(data["Locations"]):
                    break
                else:
                    embed = discord.Embed(description=data["Locations"][idx])
                    embed.set_image(url=img)
                    await ctx.send(embed=embed)
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

        case ["preset", "create", preset_name, *categories]:
            await create_preset(ctx, preset_name, categories)

        case ["preset", "delete", preset_name]:
            await delete_preset(ctx, preset_name)

        case ["preset", "update", preset_name, *categories]:
            await update_preset(ctx, preset_name, categories)

        case ["preset", "append", preset_name, *categories]:
            await append_to_preset(ctx, preset_name, categories)

        case ["preset", "remove", preset_name, *categories]:
            await remove_from_preset(ctx, preset_name, categories)

        case ["preset", preset_name]:
            await list_preset_contents(ctx, preset_name)

        # Game Management
        case ["start", game_type, preset_name]:
            await start_game(ctx, game_type, preset_name)


async def list_presets(ctx):
    print("list_presets")

async def list_preset_contents(ctx, preset_name):
    print(f"list_preset_contents for {preset_name}")

async def create_preset(ctx, preset_name, categories):
    print(f"create_preset with name {preset_name} and categories {categories}")

async def delete_preset(ctx, preset_name):
    print(f"delete_preset with name {preset_name}")

async def update_preset(ctx, preset_name, categories):
    print(f"update_preset with name {preset_name} and categories {categories}")

async def append_to_preset(ctx, preset_name, categories):
    print(f"append_to_preset with name {preset_name} and categories {categories}")

async def remove_from_preset(ctx, preset_name, categories):
    print(f"remove_from_preset with name {preset_name} and categories {categories}")

async def start_game(ctx, game_type, preset_name):
    print(f"start_game with game type {game_type} and preset name {preset_name}")

if __name__ == "__main__":
    bot.run(config.token())
