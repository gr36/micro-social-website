#!/usr/bin/env python3
"""Builds editorial/feed.json from the Micro Wrapped editions in editorial/issues/.

Each edition is one Markdown file named YYYY-MM-DD.md, dated the day it goes
live: YAML front matter for the picks, Markdown below it for the note. An
edition can be written and committed early; the app hides it until its date.
The newest edition whose date has arrived also fills the top-level people,
books, events and activity sections, so every screen reads from the same one.
A ready-to-paste newsletter post is written to editorial/newsletter/.

Run: python3 editorial/build.py
"""
import json, re, sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
ISSUES = ROOT / "issues"
FEED = ROOT / "feed.json"
NEWSLETTER = ROOT / "newsletter"

FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)


def fail(message):
    print(f"build: {message}")
    sys.exit(1)


def read_issue(path):
    text = path.read_text()
    match = FRONT.match(text)
    if not match:
        fail(f"{path.name}: needs YAML front matter between --- lines")
    meta = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()
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

    def people():
        return [{"username": p["username"], "name": p.get("name"), "reason": p.get("reason")}
                for p in meta.get("people") or []]

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
        "artwork": meta.get("artwork"),
        "body": body,
        "books": books(),
        "people": people(),
        "activity": {"watching": picks("watching"), "playing": picks("playing"), "listening": picks("listening")},
        "tip": event,
    }, issue_date


def strip_none(value):
    if isinstance(value, dict):
        return {k: strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_none(v) for v in value]
    return value


def newsletter(issue):
    lines = [f"# {issue['title']}", ""]
    if issue.get("summary"):
        lines += [issue["summary"], ""]
    if issue.get("body"):
        lines += [issue["body"], ""]
    if issue["books"]:
        lines += ["## Books", ""]
        for b in issue["books"]:
            authors = ", ".join(b["authors"]) if b["authors"] else ""
            link = f"https://micro.blog/books/{b['isbn']}" if b.get("isbn") else None
            name = f"[{b['title']}]({link})" if link else b["title"]
            line = f"- {name}" + (f" by {authors}" if authors else "") + (f". {b['reason']}" if b.get("reason") else "")
            lines.append(line)
        lines.append("")
    if issue["people"]:
        lines += ["## Worth a follow", ""]
        for p in issue["people"]:
            name = p.get("name") or p["username"]
            line = f"- [{name}](https://micro.blog/{p['username']}) (@{p['username']})" + (f". {p['reason']}" if p.get("reason") else "")
            lines.append(line)
        lines.append("")
    for key, label in (("watching", "Watching"), ("playing", "Playing"), ("listening", "Listening")):
        picks = issue["activity"].get(key) or []
        if picks:
            lines.append(f"**{label}:** " + ", ".join(p["title"] for p in picks))
            lines.append("")
    if issue.get("tip"):
        t = issue["tip"]
        target = f"https://micro.blog/{t['username']}" if t.get("username") else t.get("url")
        line = f"**{t['title']}**" + (f" — {t['body']}" if t.get("body") else "")
        if target:
            line += f" [{target}]({target})"
        lines += [line, ""]
    return "\n".join(lines).rstrip() + "\n"


def main():
    files = sorted(ISSUES.glob("*.md"))
    if not files:
        fail("no issues found in editorial/issues/")
    issues = []
    for path in files:
        issue, issue_date = read_issue(path)
        issues.append((issue_date, issue))
    issues.sort(key=lambda pair: pair[0], reverse=True)

    today = datetime.now(timezone.utc).date()
    current = next((issue for d, issue in issues if d <= today), issues[-1][1])

    feed = {
        "version": 1,
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "people": current["people"],
        "books": current["books"],
        "events": [current["tip"]] if current.get("tip") else [],
        "activity": current["activity"],
        "issues": [issue for _, issue in issues[:8]],
    }
    FEED.write_text(json.dumps(strip_none(feed), indent=2, ensure_ascii=False) + "\n")

    NEWSLETTER.mkdir(exist_ok=True)
    for _, issue in issues:
        (NEWSLETTER / f"{issue['id']}.md").write_text(newsletter(issue))

    print(f"feed.json: {len(issues)} issue(s), current is {current['id']}")


if __name__ == "__main__":
    main()
