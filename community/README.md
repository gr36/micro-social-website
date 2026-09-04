# Community Suggestions

`feed.json` is what the app reads: featured people, book picks, popular titles for Activity,
and tips. `update.py` rebuilds it from Micro.blog's Discover topics every Monday (the
workflow in `.github/workflows/update-community.yml`, which needs a `MICROBLOG_TOKEN` secret),
or on demand from the Actions tab. Tips and anything added by hand on the desk are kept.
Editorial (Micro Wrapped) is separate, in `editorial/`.
