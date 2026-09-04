#!/usr/bin/env python3
"""Builds editorial/feed.json, the file the app reads, from editorial/issues/*.md.

Each edition is one Markdown file named YYYY-MM-DD.md, dated the Saturday it
goes live: a header block between --- lines for the picks, your letter in
Markdown below it. Drop a file in any time; the app hides it until its date.
A GitHub Action runs this on every push that touches editorial/issues/ and
commits the result. To run it by hand from the repository root:

    python3 editorial/build.py && python3 editorial/validate.py editorial/feed.json
"""
import json, re, sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

WEBSITE = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
ROOT = WEBSITE / "editorial"
ISSUES = ROOT / "issues"
FEED = ROOT / "feed.json"

FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)

# Artwork lives in static/images/issues/ and is served raw from GitHub.
# A short name like "issues/2026-09-05.jpg" or "2026-09-05.jpg" becomes
# the full address; a full https:// address is left alone.
RAW_IMAGES = "https://raw.githubusercontent.com/gr36/micro-social-website/main/static/images/"


def artwork_url(value):
    if not value:
        return None
    value = str(value).strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    value = value.lstrip("/")
    if value.startswith("static/images/"):
        value = value[len("static/images/"):]
    elif value.startswith("images/"):
        value = value[len("images/"):]
    elif "/" not in value:
        value = "issues/" + value
    return RAW_IMAGES + value


def fail(message):
    print(f"build: {message}")
    sys.exit(1)


# A "## Heading" in the note starts text for that section, shown under its
# header in the app. Everything before the first heading is the letter.
SECTION_HEADINGS = {
    "links": "links", "interesting links": "links", "reading": "links", "worth reading": "links",
    "books": "books",
    "people": "people", "follow": "people", "worth a follow": "people", "who to follow": "people",
    "watching": "watching", "playing": "playing", "listening": "listening",
    "tip": "tip", "did you know": "tip",
    "games": "playing",
}


def split_body(text):
    letter, notes, current = [], {}, None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            key = SECTION_HEADINGS.get(heading.group(1).strip().lower().rstrip("?"))
            if key is None:
                fail(f"unknown section heading '## {heading.group(1)}' (use Links, Books, People, Watching, Playing, Listening or Tip)")
            current = key
            notes.setdefault(current, [])
            continue
        (notes[current] if current else letter).append(line)
    cleaned = {k: "\n".join(v).strip() for k, v in notes.items()}
    return "\n".join(letter).strip(), {k: v for k, v in cleaned.items() if v}


def read_issue(path):
    text = path.read_text()
    match = FRONT.match(text)
    if not match:
        fail(f"{path.name}: needs YAML front matter between --- lines")
    meta = yaml.safe_load(match.group(1)) or {}
    body, notes = split_body(match.group(2).strip())
    issue_date = meta.get("date")
    if isinstance(issue_date, datetime):
        issue_date = issue_date.date()
    if not isinstance(issue_date, date):
        fail(f"{path.name}: 'date' must be a date like 2026-09-08")
    if not meta.get("title"):
        fail(f"{path.name}: 'title' is required")

    def picks(key):
        items = meta.get(key) or []
        return [{"title": p["title"], "subtitle": p.get("subtitle"), "image": p.get("image")} for p in items]

    def books():
        out = []
        for b in meta.get("books") or []:
            out.append({
                "isbn": str(b["isbn"]) if b.get("isbn") is not None else None,
                "title": b["title"],
                "authors": b.get("authors") or [],
                "cover": b.get("cover"),
                "reason": b.get("reason"),
            })
        return out

    def reads():
        out = []
        for r in meta.get("reads") or []:
            out.append({
                "title": r["title"],
                "url": r["url"],
                "source": r.get("source"),
                "author": r.get("author"),
                "blurb": r.get("blurb"),
            })
        return out

    tip = meta.get("tip")
    event = None
    if tip:
        event = {
            "id": f"tip-{issue_date.isoformat()}",
            "label": tip.get("label"),
            "title": tip["title"],
            "body": tip.get("body"),
            "username": tip.get("username"),
            "url": tip.get("url"),
            "glyph": tip.get("glyph"),
            "starts": f"{issue_date.isoformat()}T00:00:00Z",
        }

    return {
        "id": issue_date.isoformat(),
        "date": f"{issue_date.isoformat()}T00:00:00Z",
        "title": meta["title"],
        "summary": meta.get("summary"),
        "artwork": artwork_url(meta.get("artwork")),
        "body": body,
        "notes": notes,
        "reads": reads(),
        "books": books(),
        "activity": {"watching": picks("watching"), "playing": picks("playing"), "listening": picks("listening")},
        "tip": event,
    }, issue_date


def strip_none(value):
    if isinstance(value, dict):
        return {k: strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_none(v) for v in value]
    return value


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_editorial():
    files = sorted(ISSUES.glob("*.md"))
    if not files:
        print("editorial: no editions, feed left alone")
        return
    issues = []
    for path in files:
        issue, issue_date = read_issue(path)
        issues.append((issue_date, issue))
    issues.sort(key=lambda pair: pair[0], reverse=True)
    feed = {"version": 1, "updated": now_iso(), "issues": [issue for _, issue in issues[:8]]}
    FEED.write_text(json.dumps(strip_none(feed), indent=2, ensure_ascii=False) + "\n")
    print(f"editorial/feed.json: {len(issues)} edition(s), newest {issues[0][1]['id']}")


def main():
    build_editorial()


if __name__ == "__main__":
    main()
