#!/usr/bin/env python3
"""Update the five public visitors shown in the profile README."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


BEGIN_MARKER = "<!-- BEGIN RECENT VISITORS -->"
END_MARKER = "<!-- END RECENT VISITORS -->"
LOGIN_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
MAX_VISITORS = 5
VISITOR_CELL_WIDTH = "14%"


def valid(login: str) -> str:
    login = login.strip().lstrip("@")
    if not LOGIN_PATTERN.fullmatch(login):
        raise ValueError(f"Invalid GitHub login: {login!r}")
    return login


def load(path: Path) -> list[str]:
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
        login = valid(item)
        folded = login.casefold()
        if folded not in seen:
            seen.add(folded)
            visitors.append(login)
    return visitors


def save(path: Path, visitors: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(visitors, indent=2) + "\n", encoding="utf-8")


def add(visitors: list[str], login: str, owner: str) -> list[str]:
    login = valid(login)
    owner = valid(owner)
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


def cell(login: str) -> str:
    display_login = login.replace("-", "&#8209;")
    return f'      <td align="center" valign="top" width="{VISITOR_CELL_WIDTH}"><a href="https://github.com/{login}"><img src="https://github.com/{login}.png?size=64" alt="@{login}" width="52" height="52"><br><strong>@{display_login}</strong></a></td>'


def cells(visitors: list[str]) -> str:
    rows = [cell(login) for login in visitors[:MAX_VISITORS]]
    rows.extend(
        f'      <td align="center" valign="top" width="{VISITOR_CELL_WIDTH}">'
        '<sub>Waiting for a visitor</sub></td>'
        for _ in range(MAX_VISITORS - len(rows))
    )
    return "\n".join(rows)


def inject(readme: str, visitors: list[str]) -> str:
    if readme.count(BEGIN_MARKER) != 1 or readme.count(END_MARKER) != 1:
        raise ValueError("README must contain exactly one recent-visitors marker pair")

    start = readme.index(BEGIN_MARKER) + len(BEGIN_MARKER)
    end = readme.index(END_MARKER)
    if start >= end:
        raise ValueError("Recent-visitors markers are out of order")

    return readme[:start] + "\n" + cells(visitors) + "\n      " + readme[end:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("login", help="GitHub login checking in")
    parser.add_argument("--owner", default="RusMermaid")
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument(
        "--data", type=Path, default=Path("data/recent_visitors.json")
    )
    args = parser.parse_args()

    visitors = add(load(args.data), args.login, args.owner)
    readme = inject(args.readme.read_text(encoding="utf-8"), visitors)

    save(args.data, visitors)
    args.readme.write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
