import requests
from json import loads, dumps

from typing import List

import urllib


def urlFormat(s):
    return urllib.parse.quote(s.encode("utf-8"))


def category_contents(category_name: str, n: int = 10) -> List[str]:
    import db

    if db.category_cache_exists(category_name):
        return db.category_cache(category_name)

    request_params = {
        "action": "query",
        "list": "categorymembers",
        "format": "json",
        "cmtitle": f"Category:{category_name}",
        "cmlimit": min(n, 100),
        "cmprop": "title|type",
    }

    pages = []

    while len(pages) < n:
        resp = requests.get("https://en.wikipedia.org/w/api.php", params=request_params)
        js = resp.json()

        if "query" not in js:
            print(f"Got unexpected response from wiki API: {resp.content}")
            return []
        else:
            # print(js)
            pass

        pages.extend(js["query"]["categorymembers"])

        if "continue" in js:
            request_params["cmcontinue"] = js["continue"]["cmcontinue"]
            request_params["cmlimit"] -= 100
        else:
            # we're out of entries, break out
            break

    page_titles = [page["title"] for page in pages if page["type"] == "page"]

    db.cache_category(category_name, page_titles)

    return page_titles


def entry_type(entry_name: str) -> str:
    # category check:
    # https://en.wikipedia.org/w/api.php?action=query&format=json&prop=info&list=allcategories&formatversion=2&acprefix=The%20Game%20Awards%20winners

    # check if it's a category
    category_check_params = {
        "action": "query",
        "format": "json",
        "prop": "info",
        "list": "allcategories",
        "formatversion": "2",
        "acprefix": entry_name,
    }

    category_check_resp = requests.get(
        "https://en.wikipedia.org/w/api.php", params=category_check_params
    )
    category_check_json = category_check_resp.json()

    if (
        "query" in category_check_json
        and len(category_check_json["query"]["allcategories"]) > 0
    ):
        return "category"

    # Okay, it's not a category. It may still be an article.
    article_check_params = {
        "action": "query",
        "format": "json",
        "prop": "categories",
        "titles": entry_name,
        "formatversion": "2",
    }

    article_check_resp = requests.get(
        "https://en.wikipedia.org/w/api.php", params=article_check_params
    )
    article_check_json = article_check_resp.json()

    if "query" in article_check_json and (
        "missing" not in article_check_json["query"]["pages"][0]
    ):
        return "article"

    return "err"
