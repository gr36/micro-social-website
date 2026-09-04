# Editorial

The weekly issue the app shows Plus members at the top of the Timeline, written as one Markdown file a week. Nothing here is hand-edited JSON: `feed.json` and the newsletter drafts are built from the issues by a GitHub Action whenever an issue changes on `main`.

## Writing a week

Add `editorial/issues/YYYY-MM-DD.md`, dated the Monday it goes live. Front matter carries the picks, the Markdown beneath it is your note.

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

Every section is optional. Artwork goes in `static/images/issues/` at 1200×675 and is published by the site; the app shows it on the Timeline card and at the top of the issue. Without artwork the app uses its accent card.

## What gets built

- `editorial/feed.json`: the file the app fetches. The newest issue whose date has arrived also fills the top-level people, books, tip and Activity titles, so every screen reads from the same week. The last eight issues are kept.
- `editorial/newsletter/YYYY-MM-DD.md`: the same issue as a Markdown post, ready to paste into Micro.blog with your newsletter category.

Check locally with:

```
python3 editorial/build.py && python3 editorial/validate.py editorial/feed.json
```
