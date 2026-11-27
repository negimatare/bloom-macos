# Bloom

A macOS app, in Python with PySide6, for the backlight and the key mappings
of a Razer BlackWidow Lite. `CONTRIBUTING.md` has the layout, the branches
and the release steps.

## Verification

Run from the repository root before you call a change done:

```bash
uv run pytest
```

## Project-specific rules

- Integration branch: `mochitsuki`. The mochi skills read this line: they
  branch off `mochitsuki` and open each pull request against it. `main`
  gets only releases and hotfixes.
- Use the project-local `.venv` through `uv` only. Install nothing
  system-wide, and no tool such as Karabiner.
- Text in the app is in UK English.
- The repository is public: no personal data in code, commits or docs.
- A pull request body fills the mochi `pr-body.md` asset, not
  `.github/pull_request_template.md`. Write each paragraph on one line:
  GitHub shows each newline as a line break.
- A `CHANGELOG.md` release: a short intro, `### Update` only when users must
  do a step, then `### Bloom`. Each item starts with a bold lead.
- Write a version in a docs example as `0.x.y`, and its tag as `v0.x.y`.
