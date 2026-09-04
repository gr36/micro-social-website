#!/usr/bin/env python3
"""Rebuilds community/feed.json from Micro.blog's Discover topics.

Runs every Monday from the workflow in this repository (and on demand from
the Actions tab). It refreshes the automatic parts: the people posting most,
the books linked most, and titles linked to film, game and music sites.
Anything hand-added on the desk that it did not find this week, and every
tip, is kept. Needs MICROBLOG_TOKEN in the environment.
"""
import html, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
FEED = HERE / "feed.json"
COLLECTIONS = ["books", "tv", "movies", "music", "podcasts"]
TAGS = re.compile(r"<[^>]+>")
LINK = re.compile(r'<a\s[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
BOOK_LINK = re.compile(r'<a\s[^>]*?href="[^"]*micro\.blog/books/(\d{10,13})"[^>]*>(.*?)</a>', re.S | re.I)
SKIP_HOSTS = ("micro.blog", "twitter.com", "x.com", "instagram.com", "facebook.com", "threads.net")
WATCH_HOSTS = ("letterboxd.com", "themoviedb.org", "imdb.com", "trakt.tv", "tv.apple.com", "netflix.com", "justwatch.com")
PLAY_HOSTS = ("store.steampowered.com", "backloggd.com", "rawg.io", "nintendo.com", "playstation.com", "xbox.com", "gog.com")
LISTEN_HOSTS = ("music.apple.com", "open.spotify.com", "bandcamp.com", "overcast.fm", "podcasts.apple.com", "pocketcasts.com", "song.link", "album.link")
LIMIT = 8


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
            by = ((item.get("author") or {}).get("_microblog") or {}).get("username") or (item.get("author") or {}).get("name")
            if by:
                entry = people.setdefault(by, {"username": by, "count": 0, "topics": set()})
                entry["count"] += 1
                entry["topics"].add(collection)
            for isbn, inner in BOOK_LINK.findall(body):
                entry = books.setdefault(isbn, {"isbn": isbn, "title": strip_html(inner) or ("ISBN " + isbn), "count": 0, "by": set()})
                entry["count"] += 1
                if by:
                    entry["by"].add(by)
            for url, inner in LINK.findall(body):
                url = html.unescape(url)
                host = host_of(url)
                if not host or matches(host, SKIP_HOSTS):
                    continue
                text = strip_html(inner)
                if not text or text.startswith("http"):
                    continue
                key = "watching" if matches(host, WATCH_HOSTS) else "playing" if matches(host, PLAY_HOSTS) else "listening" if matches(host, LISTEN_HOSTS) else None
                if key:
                    entry = titles[key].setdefault(text, {"title": text, "subtitle": host.split(".")[0].title(), "count": 0})
                    entry["count"] += 1

    def top(items):
        return sorted(items, key=lambda x: -x["count"])[:LIMIT]

    existing = {}
    if FEED.exists():
        try:
            existing = json.loads(FEED.read_text())
        except json.JSONDecodeError:
            existing = {}

    def keep(old, new, key):
        """New automatic rows first, then rows from the current file that
        the pull did not find (hand-added on the desk), up to the limit."""
        seen = {x[key] for x in new}
        kept = [x for x in old or [] if x.get(key) not in seen]
        return (new + kept)[:LIMIT]

    fresh_people = [{"username": p["username"], "name": p["username"], "reason": "Posting about " + ", ".join(sorted(p["topics"])) + " this week"} for p in top(people.values())]
    fresh_books = [{"isbn": b["isbn"], "title": b["title"], "cover": f"https://micro.blog/books/{b['isbn']}/cover.jpg", "reason": f"Mentioned by {len(b['by'])} {'person' if len(b['by']) == 1 else 'people'} this week"} for b in top(books.values())]
    old_activity = existing.get("activity") or {}
    feed = {
        "version": 1,
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "people": keep(existing.get("people"), fresh_people, "username"),
        "books": keep(existing.get("books"), fresh_books, "isbn"),
        "events": existing.get("events") or [],
        "activity": {
            key: keep(old_activity.get(key), [{"title": t["title"], "subtitle": t["subtitle"]} for t in top(titles[key].values())], "title")
            for key in ("watching", "playing", "listening")
        },
    }
    FEED.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
    print(f"feed.json: {len(feed['people'])} people, {len(feed['books'])} books, " + ", ".join(f"{k} {len(v)}" for k, v in feed["activity"].items()))


if __name__ == "__main__":
    main()
