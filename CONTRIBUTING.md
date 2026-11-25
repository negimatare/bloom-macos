# Contributing

## Run from a checkout

Bloom uses [uv](https://docs.astral.sh/uv/) and a project-local `.venv`.
Nothing is installed system-wide.

```bash
uv sync
uv run bloom-gui      # the window
uv run pytest         # the tests
```

The tests use fakes for the keyboard and `hidutil`, so they need no keyboard.
A change to the keyboard, `hidutil` or the background helper also needs a
check on a real Razer BlackWidow Lite.

## Layout

- `src/bloom/`: the core. Lighting and HID (`device.py`, `lighting.py`,
  `protocol.py`), key mappings (`keymap.py`, `hid_usages.py`), profiles
  (`config.py`), the background helper (`watcher.py`), the app bundles
  (`bundle.py`, `launcher.py`) and the CLI (`cli.py`).
- `src/bloom/gui/`: the PySide6 window. `controller.py` holds the state and
  the actions; the other modules are screens and widgets.
- `scripts/`: the icon script and the release notes script.

## Branches

- `mochitsuki` is the integration branch. Branch off it with a
  `<type>/<slug>` branch, and open the pull request against it. GitHub
  proposes `main` as the base, so change the base to `mochitsuki`. Dependabot
  also opens its pull requests against `mochitsuki`.
- `main` holds only releases and hotfixes. Each commit on `main` is a
  release. Only a `release/0.x.y` branch or a hotfix branch targets `main`.
- Both branches take only squash merges. A squash does not put the commits of
  one branch into the history of the other, so `main` never merges
  `mochitsuki`. A release copies the files of `mochitsuki` to `main` instead,
  as [Release](#release) says.
- A hotfix goes to `main` first, and then to `mochitsuki` as a cherry-pick.
  Without the cherry-pick, the next release removes the fix from `main`.

A branch ruleset protects each branch. Each one requires a pull request with
a squash merge, signed commits, linear history, and the `Unit tests`
and `Analyze` checks. Each one also blocks force pushes and deletion. A tag
ruleset blocks a change to a `v*` tag, or its deletion.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

## Release

Versions follow [Semantic Versioning](https://semver.org/).

1. Create a `chore/release-0.x.y` branch from `mochitsuki`. On it:
   - Set the version in `pyproject.toml`, then run `uv lock`.
   - Replace "unreleased" in the `CHANGELOG.md` heading with the date, for
     example `## 0.x.y — YYYY-MM-DD`.

   Run `uv run python scripts/release_notes.py 0.x.y`. It shows the release
   notes, or the problem that stops them. Then open the pull request against
   `mochitsuki` and squash-merge it.
2. Copy the files of `mochitsuki` to a `release/0.x.y` branch from `main`:

   ```bash
   git fetch origin
   git switch -c release/0.x.y origin/main
   git restore --source=origin/mochitsuki --staged --worktree :/
   git commit -m "chore(release): 0.x.y"
   git push -u origin release/0.x.y
   ```

   `git restore` also removes the files that `mochitsuki` deleted, so the
   files of the branch are the same as the files of `mochitsuki`.
3. Open the pull request from `release/0.x.y` to `main`, with the title
   `chore(release): 0.x.y`. Its diff is the full release. When the diff
   removes a line of a hotfix, the cherry-pick of that hotfix is missing:
   stop and do it first. Squash-merge the pull request.
4. Sign a tag on the squashed commit on `main` and push it:

   ```bash
   git switch main && git pull
   git tag -s v0.x.y -m "Bloom 0.x.y"
   git tag -v v0.x.y   # reports a good signature from your key
   git push origin v0.x.y
   ```

   The tag uses the signing key that you use for your commits. The tag
   ruleset blocks a change to a tag after the push, so do the check before
   the push.

   The `Release` workflow then checks that the tag is on `main`, runs the
   tests and the notes script, and publishes the release with those notes.
   An immutable release keeps its tag, so the workflow stops before it
   publishes when something does not agree.

For a hotfix:

1. Create a `fix/<slug>` branch from `main`. In it, set the next patch
   version and add its `CHANGELOG.md` section, as step 1 says.
2. Run `uv run python scripts/release_notes.py 0.x.y`. Open the pull request
   against `main`, with the title `fix(<scope>): <subject>`, and
   squash-merge it.
3. Sign and push the tag, as step 4 says.
4. Cherry-pick the squashed commit to `mochitsuki`:

   ```bash
   git fetch origin
   git switch -c fix/<slug>-mochitsuki origin/mochitsuki
   git cherry-pick <squashed commit on main>   # resolve a conflict in CHANGELOG.md, then git cherry-pick --continue
   git push -u origin fix/<slug>-mochitsuki
   ```

   Open its pull request against `mochitsuki` and squash-merge it.
