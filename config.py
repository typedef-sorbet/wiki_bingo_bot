import json

_CONFIG_PATH = "/home/sanctity/personal/wiki_bingo/config.json"

def as_dict():
    with open(_CONFIG_PATH, "r") as infile:
        return json.loads(infile.read())

def notify_channel():
    return int(as_dict()["notify_channel"])

def token():
    return as_dict()["client_token"]

def permissions():
    return int(as_dict()["permissions"])
