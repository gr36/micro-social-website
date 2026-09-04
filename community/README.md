# Community feed

One JSON file the app fetches at most once a day. It carries suggested people, book picks, an occasional event card for the Timeline and popular titles for the Activity screen. Nothing goes the other way: the app never sends anything about the person using it.

## Where it lives

The file is `community/feed.json` in this repository, outside `static/` so Hugo leaves it out of the site. The app reads it raw from GitHub on `main`, so a merged edit is live for the app straight away. The URL the app reads is the `feedURL` constant in the app's `Services/CommunityFeedService.swift`.

## Editing

Every section is optional. Leave one out and the app carries on without it.

- `version`: always `1`.
- `updated`: when you last changed the file, ISO 8601.
- `people`: `username` (required), `name`, `reason`. Shown in Find People instead of the built-in list. Anyone already followed is hidden.
- `books`: `title` (required), `isbn`, `authors`, `cover` (URL), `reason`. Shown as Picks under the book recommendations. Without a `cover` the app fetches one by ISBN.
- `events`: `id` (required, unique, never reuse one), `title` (required), `label` (the small line above the title, "Did you know?" when left out), `body`, `username` (a Micro.blog account to open in the app), `url` (opened when there is no `username`), `glyph` (an SF Symbol name), `starts`, `ends`. One small row shows at the top of the Timeline while the event is live. Closing it hides that `id` for good on that phone.
- `activity`: `watching`, `playing`, `listening`, each a list of `title` (required), `subtitle`, `image` (URL). Shown as a Popular Now strip on the Activity screen before a search; tapping one runs that search.

Check a change with:

```
python3 community/validate.py community/feed.json
```
