#!/usr/bin/env python3
"""Update the three opt-in public visitors shown in the profile README."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


BEGIN_MARKER = "<!-- BEGIN RECENT VISITORS -->"
END_MARKER = "<!-- END RECENT VISITORS -->"
LOGIN_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
MAX_VISITORS = 3


def validate_login(login: str) -> str:
    login = login.strip().lstrip("@")
    if not LOGIN_PATTERN.fullmatch(login):
        raise ValueError(f"Invalid GitHub login: {login!r}")
    return login


def load_visitors(path: Path) -> list[str]:
    if not path.exists():
        return []

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Recent visitors data must be a JSON list")

    visitors: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            raise ValueError("Every recent visitor must be a GitHub login string")
        login = validate_login(item)
        folded = login.casefold()
        if folded not in seen:
            seen.add(folded)
            visitors.append(login)
    return visitors


def update_visitors(visitors: list[str], login: str, owner: str) -> list[str]:
    login = validate_login(login)
    owner = validate_login(owner)
    visitors = [
        visitor
        for visitor in visitors
        if visitor.casefold() != owner.casefold()
    ]
    if login.casefold() == owner.casefold():
        return visitors[:MAX_VISITORS]

    return [login] + [
        visitor
        for visitor in visitors
        if visitor.casefold() not in {login.casefold(), owner.casefold()}
    ][: MAX_VISITORS - 1]


def visitor_cell(login: str) -> str:
    return (
        f'      <td align="center" width="18%"><a href="https://github.com/{login}">'
        f'<img src="https://github.com/{login}.png?size=64" alt="@{login}" width="56">'
        f'<br><strong>@{login}</strong></a></td>'
    )


def render_cells(visitors: list[str]) -> str:
    cells = [visitor_cell(login) for login in visitors[:MAX_VISITORS]]
    cells.extend(
        '      <td align="center" width="18%"><sub>Waiting for a visitor</sub></td>'
        for _ in range(MAX_VISITORS - len(cells))
    )
    return "\n".join(cells)


def update_readme(readme: str, visitors: list[str]) -> str:
    if readme.count(BEGIN_MARKER) != 1 or readme.count(END_MARKER) != 1:
        raise ValueError("README must contain exactly one recent-visitors marker pair")

    start = readme.index(BEGIN_MARKER) + len(BEGIN_MARKER)
    end = readme.index(END_MARKER)
    if start >= end:
        raise ValueError("Recent-visitors markers are out of order")

    return readme[:start] + "\n" + render_cells(visitors) + "\n      " + readme[end:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("login", help="GitHub login checking in")
    parser.add_argument("--owner", default="RusMermaid")
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument(
        "--data", type=Path, default=Path("data/recent_visitors.json")
    )
    args = parser.parse_args()

    visitors = update_visitors(load_visitors(args.data), args.login, args.owner)
    readme = update_readme(args.readme.read_text(encoding="utf-8"), visitors)

    args.data.parent.mkdir(parents=True, exist_ok=True)
    args.data.write_text(json.dumps(visitors, indent=2) + "\n", encoding="utf-8")
    args.readme.write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
