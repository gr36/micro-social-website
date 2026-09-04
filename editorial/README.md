# Editorial: Micro Wrapped

The weekly edition Plus members see once at the top of the Timeline and can reopen from Plus Features, written as one Markdown file a week. Nothing here is hand-edited JSON: `feed.json` and the newsletter drafts are built from the issues by a GitHub Action whenever an issue changes on `main`.

## The desk (the easy way)

Double-click `editorial/Micro Wrapped Desk.command` in Finder. It installs the two Python packages it needs the first time, starts the desk and opens it in your browser. (Or `python3 editorial/desk.py` from Terminal.) The first double-click may need a right-click → Open, since macOS asks about scripts from outside the App Store.

It opens a page at localhost:8765. The left side is material: your Micro.blog bookmarks (save a link anywhere during the week and it shows up there) and the recent Discover posts for books, TV, movies, music and podcasts, with the books people are posting about counted up by ISBN. The right side is the edition: title, date, artwork, the note, and the lists. Tick a bookmark to make it a link, tap a post to add it as a pick, write the note. **Save & build** writes the issue file, resizes the artwork and builds and validates the feed. **Publish** commits and pushes to main. The first run asks for your Micro.blog app token (Account → App tokens); it stays on the Mac.

## Writing an edition by hand

Add `editorial/issues/YYYY-MM-DD.md`, dated the day it goes live (Saturdays). Write and commit it whenever you like: the app keeps it hidden until that date, and the built feed only promotes it to the top-level sections once the date has passed. Front matter carries the picks, the Markdown beneath it is your note.

```
---
title: Slow reads and a new challenge
date: 2026-08-31
artwork: 2026-08-31.jpg
summary: One line shown under the title.
books:
  - isbn: "9780593321201"
    title: Tomorrow, and Tomorrow, and Tomorrow
    authors: [Gabrielle Zevin]
    reason: Why it's here
people:
  - username: manton
    name: Manton Reece
    reason: Creator of Micro.blog   # shown in Find People, not in the edition
reads:
  - title: An article worth reading
    url: https://example.com/article
    source: Where it's from
    author: Who wrote it
    blurb: One or two lines on why it's worth their time.
watching:
  - title: Slow Horses
    subtitle: Apple TV+
playing:
  - title: Balatro
listening:
  - title: Core Intuition
    subtitle: Podcast
tip:
  label: Did you know?
  title: Micro.blog runs community challenges
  body: Photo and writing prompts from @challenges
  username: challenges
  glyph: trophy.fill
---
Your letter, in Markdown. Links like [this](https://micro.blog) are tappable in the app, and paragraphs are kept.

## Books

A line or two shown under the Books header, above the books. Use "## Links", "## Books", "## Watching", "## Playing", "## Listening" or "## Tip" to put text under any section; leave a heading out and that section has none.
```

Every section is optional. Artwork goes in `static/images/issues/` at 1200×675, imagery only with no text, since the app draws the date, title and summary over it. `artwork` is just its file name: the build turns it into the raw GitHub address, which is live the moment the commit lands on `main`. (A full `https://` address is used as given.) The app shows it on the Timeline card and as the cover of the edition. Without artwork the app uses its accent cover.

## What gets built

- `editorial/feed.json`: the file the app fetches. The newest issue whose date has arrived also fills the top-level people, books, tip and Activity titles, so every screen reads from the same week. The last eight issues are kept.
- `editorial/newsletter/YYYY-MM-DD.md`: the same issue as a Markdown post, ready to paste into Micro.blog with your newsletter category.

Check locally with:

```
python3 editorial/build.py && python3 editorial/validate.py editorial/feed.json
```
