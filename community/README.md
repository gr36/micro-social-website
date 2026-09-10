# Community Suggestions

`feed.json` is what the app reads: the popular titles for Activity's Popular Now strip, each
with up to three of the people behind it. `update.py` rebuilds it from Micro.blog's Discover
topics every Monday (the workflow in `.github/workflows/update-community.yml`, which needs a
`MICROBLOG_TOKEN` secret; an optional `COMMUNITY_EXCLUDE` secret lists accounts, comma-separated,
that are never shown), or on demand from the Actions tab.
