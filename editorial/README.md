# Editorial: Micro Wrapped

The weekly edition Plus members see once at the top of the Timeline and can reopen from Plus Features, written as one Markdown file a week. Nothing here is hand-edited JSON: `feed.json` and the newsletter drafts are built from the issues by a GitHub Action whenever an issue changes on `main`.

## Writing an edition

Add `editorial/issues/YYYY-MM-DD.md`, dated the day it goes live (Saturdays). Write and commit it whenever you like: the app keeps it hidden until that date, and the built feed only promotes it to the top-level sections once the date has passed. Front matter carries the picks, the Markdown beneath it is your note.

```
---
title: Slow reads and a new challenge
date: 2026-08-31
artwork: https://microsocial.app/images/issues/2026-08-31.jpg
summary: One line shown under the title.
books:
  - isbn: "9780593321201"
    title: Tomorrow, and Tomorrow, and Tomorrow
    authors: [Gabrielle Zevin]
    reason: Why it's here
people:
  - username: manton
    name: Manton Reece
    reason: Creator of Micro.blog
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
Your note for the week, in Markdown.
```

Every section is optional. Artwork goes in `static/images/issues/` at 1200×675 and `artwork` is just its file name: the build turns it into the raw GitHub address, which is live the moment the commit lands on `main`. (A full `https://` address is used as given.) The site at microsocial.app is not served from this repository, so never point artwork there. The app shows it on the Timeline card and as the cover of the edition. Without artwork the app uses its accent cover.

## What gets built

- `editorial/feed.json`: the file the app fetches. The newest issue whose date has arrived also fills the top-level people, books, tip and Activity titles, so every screen reads from the same week. The last eight issues are kept.
- `editorial/newsletter/YYYY-MM-DD.md`: the same issue as a Markdown post, ready to paste into Micro.blog with your newsletter category.

Check locally with:

```
python3 editorial/build.py && python3 editorial/validate.py editorial/feed.json
```
