"""Print the CHANGELOG.md section of a release, for its GitHub release notes.

    uv run python scripts/release_notes.py 0.x.y

Stops with the problem when pyproject.toml has another version, or when the
section is missing or has no release date.
"""

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def notes(version: str, changelog: str, project_version: str) -> str:
    if version != project_version:
        raise SystemExit(f"pyproject.toml has version {project_version}, not {version}.")
    section = re.search(rf"^## {re.escape(version)} — (\S+)\n(.*?)(?=^## |\Z)", changelog, re.M | re.S)
    if section is None:
        raise SystemExit(f"CHANGELOG.md has no section for {version}.")
    date, body = section.groups()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise SystemExit(f"The {version} section of CHANGELOG.md has no release date.")
    return body.strip() + "\n"


def main() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    print(notes(sys.argv[1], (ROOT / "CHANGELOG.md").read_text(), project), end="")


if __name__ == "__main__":
    main()
