# Community feed

One JSON file the app fetches at most once a day. It carries suggested people, book picks, an occasional event card for the Timeline and popular titles for the Activity screen. Nothing goes the other way: the app never sends anything about the person using it.

## Where it lives

The file is `static/community/feed.json` in this repository. Hugo publishes everything under `static/` as-is, so once deployed it is at `https://microsocial.app/community/feed.json`. The app reads the raw file straight from GitHub (`main` branch), so a merged edit is live for the app without waiting for a site deploy. The URL the app reads is the `feedURL` constant in the app's `Services/CommunityFeedService.swift`.

## Editing

Every section is optional. Leave one out and the app carries on without it.

- `version`: always `1`.
- `updated`: when you last changed the file, ISO 8601.
- `people`: `username` (required), `name`, `reason`. Shown in Find People instead of the built-in list. Anyone already followed is hidden.
- `books`: `title` (required), `isbn`, `authors`, `cover` (URL), `reason`. Shown as Picks under the book recommendations. Without a `cover` the app fetches one by ISBN.
- `events`: `id` (required, unique, never reuse one), `title` (required), `body`, `url`, `glyph` (an SF Symbol name), `starts`, `ends`. One card shows at the top of the Timeline while the event is live. Closing it hides that `id` for good on that phone.
- `activity`: `watching`, `playing`, `listening`, each a list of `title` (required), `subtitle`, `image` (URL). Shown as a Popular Now strip on the Activity screen before a search; tapping one runs that search.

Check a change with:

```
python3 community/validate.py static/community/feed.json
```
