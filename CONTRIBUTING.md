# Contributing to Dalang AI

Thanks for helping kids see their own stories as wayang kulit. Bahasa Indonesia, Basa Jawa and English are
all welcome in issues and pull requests.

## Run it and check it (no keys, no cost)

```bash
make install      # Python venv + dev tools, web packages
make demo         # app on the built-in fake Meta API, http://localhost:3000
make check        # ruff, mypy, pytest, eslint, tsc, next build
make e2e          # full stack smoke test (do not run two at once: same ports and data dir)
```

Without `META_API_KEY` every Meta call is answered by `api/fake_meta.py`, so tests never spend money.

## Ground rules

* All Meta calls go through `api/meta_client.py`. Only use model ids and endpoints from Meta's docs (see
  `docs/META_MODELS.md`); don't guess new ones.
* Prompts live in `api/prompts.py`. Run `python scripts/gen_prompts_doc.py` after changing them.
* Numbers in the docs come from `scripts/facts.py`, so don't type test counts or video lengths by hand.
* Docs and comments should read like a person wrote them. `python scripts/voice_check.py` lists every
  AI-sounding word, dash or note-to-a-tool it finds (with line numbers) and `tests/test_voice_check.py` fails on any.
* Kids' safety comes first. Keep the story safety screen, the per-film budget and the abuse limits on. The app
  collects no names, schools or faces, and it should stay that way.
* Check wayang characters, terms and Javanese text against `docs/CULTURAL_REVIEW.md`. Corrections from dalang,
  sanggar or Javanese speakers are very welcome.
* Placeholder art, sample films, the synthetic sample recording and placeholder testimonials stay labelled as such
  in the UI and docs.
* Add or update a test in `tests/` for any change in `api/`, and keep `make check` green.

## Pull requests

Keep PRs small and focused, with a short note on what changed and how you checked it. By contributing you agree
that your code is released under the MIT licence (see `LICENSE`) and that you follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
