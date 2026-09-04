# Micro Wrapped

One Markdown file per edition in `issues/`, named for the Saturday it goes live
(`2026-09-12.md`), with its cover in `static/images/issues/` (`2026-09-12-cover.jpg`,
1200×675, no text). Copy `TEMPLATE.md` to start, or paste the outline the
[desk](https://github.com/gr36/micro-wrapped-desk) puts on your clipboard.

Push the file, or upload it on github.com. The **Build Micro Wrapped feed** Action then
rebuilds `feed.json`, the file the app reads, and commits it. If the header block has a
mistake the Action goes red with a message saying which line. Nothing reaches the app
until it passes. The app shows an edition from its date, so files can go in early.

The header block, between the `---` lines, holds the picks: `reads` (interesting links),
`books`, `watching`, `playing`, `listening` and one `tip`. Your letter goes below it. A
`## Books` style heading in the letter puts that text under the matching section in the
app. All of it is optional.
