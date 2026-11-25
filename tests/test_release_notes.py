import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "release_notes.py"
_spec = importlib.util.spec_from_file_location("release_notes", _SCRIPT)
release_notes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release_notes)

CHANGELOG = """# Changelog

Intro.

## 0.2.0 — unreleased

- **Next.** Work in progress.

## 0.1.0 — 2026-11-30

- **First.** The first release.
"""


def test_the_notes_are_the_section_of_the_release():
    assert release_notes.notes("0.1.0", CHANGELOG, "0.1.0") == "- **First.** The first release.\n"


def test_a_section_without_a_date_is_refused():
    with pytest.raises(SystemExit, match="no release date"):
        release_notes.notes("0.2.0", CHANGELOG, "0.2.0")


def test_a_tag_that_differs_from_the_project_version_is_refused():
    with pytest.raises(SystemExit, match="pyproject.toml"):
        release_notes.notes("0.1.0", CHANGELOG, "0.2.0")
