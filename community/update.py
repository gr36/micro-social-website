#!/usr/bin/env python3
"""Rebuilds community/feed.json from Micro.blog's Discover topics.

Runs every Monday from the workflow in this repository (and on demand from
the Actions tab): the titles linked to film, game and music sites this
week, with up to three of the people behind each, rebuilt from scratch.
Needs MICROBLOG_TOKEN.
"""
import html, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
FEED = HERE / "feed.json"
COLLECTIONS = ["books", "tv", "movies", "music", "podcasts", "videogames"]
TOPIC_LABELS = {"tv": "TV", "videogames": "games"}
TAGS = re.compile(r"<[^>]+>")
LINK = re.compile(r'<a\s[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
BOOK_LINK = re.compile(r'<a\s[^>]*?href="[^"]*micro\.blog/books/(\d{10,13})"[^>]*>(.*?)</a>', re.S | re.I)
SKIP_HOSTS = ("micro.blog", "twitter.com", "x.com", "instagram.com", "facebook.com", "threads.net")
WATCH_HOSTS = ("letterboxd.com", "themoviedb.org", "imdb.com", "trakt.tv", "tv.apple.com", "netflix.com", "justwatch.com")
PLAY_HOSTS = ("store.steampowered.com", "backloggd.com", "rawg.io", "nintendo.com", "playstation.com", "xbox.com", "gog.com")
LISTEN_HOSTS = ("music.apple.com", "open.spotify.com", "bandcamp.com", "overcast.fm", "podcasts.apple.com", "pocketcasts.com", "song.link", "album.link")
LIMIT = 8
# Link text that is just the site's own name, not a title
SITE_NAMES = {"the movie database", "tmdb", "letterboxd", "imdb", "trakt", "justwatch", "netflix", "apple tv", "apple tv+",
              "steam", "backloggd", "rawg", "nintendo", "playstation", "xbox", "gog", "gog.com",
              "apple music", "spotify", "bandcamp", "overcast", "apple podcasts", "pocket casts", "song.link", "album.link"}
# Trailing year, season and episode markers: "Vigil [2021] S3E2" -> "Vigil"
TITLE_NOISE = re.compile(r"\s*(\[\d{4}\]|\(\d{4}\)|S\d{1,2}E\d{1,3}|Season \d+|Episode \d+|,? \d{4})\s*", re.I)


def clean_title(text, host):
    """The title as a person would say it, or None if the link text is not
    a title at all."""
    title = TITLE_NOISE.sub(" ", text).strip(" -:–|")
    title = re.sub(r"\s{2,}", " ", title)
    low = title.lower()
    if not title or low in SITE_NAMES or low.replace(" ", "") == host.split(".")[0]:
        return None
    return title
# Accounts never featured and whose posts are never counted: the
# COMMUNITY_EXCLUDE secret, comma-separated usernames, lower case.
EXCLUDE = {name.strip().lower() for name in os.environ.get("COMMUNITY_EXCLUDE", "").split(",") if name.strip()}


def api(path):
    token = os.environ.get("MICROBLOG_TOKEN")
    if not token:
        sys.exit("MICROBLOG_TOKEN is not set")
    request = Request("https://micro.blog" + path, headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def strip_html(text):
    return html.unescape(TAGS.sub("", text or "")).strip()


def host_of(url):
    match = re.match(r"https?://([^/]+)", url or "")
    return match.group(1).lower().replace("www.", "") if match else ""


def matches(host, hosts):
    return any(host == h or host.endswith("." + h) for h in hosts)


def main():
    people, books, titles = {}, {}, {"watching": {}, "playing": {}, "listening": {}}
    for collection in COLLECTIONS:
        try:
            items = api(f"/posts/discover/{collection}").get("items", [])
        except Exception as error:
            print(f"discover/{collection}: {error}")
            continue
        for item in items:
            body = item.get("content_html") or ""
            author = item.get("author") or {}
            by = (author.get("_microblog") or {}).get("username") or author.get("name")
            if by and by.lower() in EXCLUDE:
                continue
            if by:
                entry = people.setdefault(by, {"username": by, "name": author.get("name") or by, "avatar": author.get("avatar"), "count": 0, "topics": set()})
                entry["count"] += 1
                entry["topics"].add(collection)
            poster = {"username": by, "name": author.get("name") or by, "avatar": author.get("avatar")} if by else None
            for isbn, inner in BOOK_LINK.findall(body):
                entry = books.setdefault(isbn, {"isbn": isbn, "title": strip_html(inner) or ("ISBN " + isbn), "count": 0, "by": {}})
                entry["count"] += 1
                if poster:
                    entry["by"].setdefault(by, poster)
            for url, inner in LINK.findall(body):
                url = html.unescape(url)
                host = host_of(url)
                if not host or matches(host, SKIP_HOSTS):
                    continue
                text = strip_html(inner)
                if not text or text.startswith("http"):
                    continue
                key = "watching" if matches(host, WATCH_HOSTS) else "playing" if matches(host, PLAY_HOSTS) else "listening" if matches(host, LISTEN_HOSTS) else None
                title = clean_title(text, host) if key else None
                if key and title:
                    entry = titles[key].setdefault(title.lower(), {"title": title, "subtitle": host.split(".")[0].title(), "count": 0, "by": {}})
                    entry["count"] += 1
                    if poster:
                        entry["by"].setdefault(by, poster)

    def top(items):
        return sorted(items, key=lambda x: -x["count"])[:LIMIT]

    book_titles = {b["title"].lower() for b in books.values()}

    def faces(entry):
        """Up to three people behind a row, with avatar when known."""
        out = []
        for person in list(entry["by"].values())[:3]:
            row = {"username": person["username"], "name": person["name"]}
            if person.get("avatar"):
                row["avatar"] = person["avatar"]
            out.append(row)
        return out
    feed = {
        "version": 1,
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "activity": {
            key: [{"title": t["title"], "subtitle": t["subtitle"], "by": faces(t)} for t in top(v for v in titles[key].values() if v["title"].lower() not in book_titles)]
            for key in ("watching", "playing", "listening")
        },
    }
    FEED.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
    print("feed.json: " + ", ".join(f"{k} {len(v)}" for k, v in feed["activity"].items()))


if __name__ == "__main__":
    main()
