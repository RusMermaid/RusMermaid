#!/usr/bin/env python3
"""Generate a codeSTACKr-style all-time WakaTime language card."""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Any


API_ROOT = "https://api.wakatime.com/api/v1"
MIN_SECONDS = 60 * 60
MAX_LANGUAGES = 7
PINNED_LANGUAGES = ("C#", "F#", "Python")
MOONLIGHT_COLORS = (
    "#a88465",
    "#737b91",
    "#536fa8",
    "#688ac0",
    "#83a6d5",
    "#a8c8e8",
    "#d1e6fa",
)
SPIRE_PROJECT = os.environ.get("SPIRE_PROJECT", "SpireModH3")
OUTPUT_PATH = Path(
    os.environ.get("OUTPUT_PATH", "assets/wakatime-all-time.svg"),
)

FALLBACK_COLORS = {
    "C#": "#178600",
    "F#": "#b845fc",
    "Python": "#3572A5",
    "C++": "#f34b7d",
}


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class WakaTimeClient:
    def __init__(self, api_key: str) -> None:
        token = base64.b64encode(api_key.encode()).decode()
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {token}",
            "User-Agent": "RusMermaid-WakaTime-Card/1.0",
        }

    def get(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        request = urllib.request.Request(
            f"{API_ROOT}{path}{query}",
            headers=self.headers,
        )
        for attempt in range(6):
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    return response.status, json.load(response)
            except urllib.error.HTTPError as error:
                retryable = error.code in {429, 500, 502, 503, 504}
                if retryable and attempt < 5:
                    retry_after = error.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else min(2 ** attempt, 30)
                    time.sleep(delay)
                    continue
                detail = error.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"WakaTime API request failed ({error.code}): {detail}",
                ) from error
            except urllib.error.URLError as error:
                if attempt < 5:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                raise RuntimeError(
                    f"WakaTime API request failed: {error.reason}",
                ) from error
        raise RuntimeError("WakaTime API request exhausted all retries.")


def fetch_all_time_languages(
    client: WakaTimeClient,
) -> list[dict[str, Any]]:
    for attempt in range(6):
        status, payload = client.get("/users/current/stats/all_time")
        data = payload.get("data", {})
        if status == 200 and data.get("is_up_to_date", True):
            return data.get("languages", [])
        if attempt < 5:
            time.sleep(15)
    raise RuntimeError(
        "WakaTime all-time statistics are still being calculated. "
        "Run the workflow again in a few minutes.",
    )


def find_project_start(client: WakaTimeClient, project_name: str) -> date | None:
    _, payload = client.get(
        "/users/current/projects",
        {"q": project_name},
    )
    projects = payload.get("data", [])
    project = next(
        (item for item in projects if item.get("name") == project_name),
        None,
    )
    if project is None:
        print(
            f'WakaTime project "{project_name}" is not present yet; '
            "no Spire JSON time needs remapping.",
        )
        return None

    first_activity = (
        parse_datetime(project.get("first_heartbeat_at"))
        or parse_datetime(project.get("created_at"))
    )
    if first_activity:
        return first_activity.date()

    _, user_payload = client.get("/users/current")
    account_created = parse_datetime(
        user_payload.get("data", {}).get("created_at"),
    )
    return account_created.date() if account_created else date(2015, 1, 1)


def fetch_project_languages(
    client: WakaTimeClient,
    project_name: str,
) -> list[dict[str, Any]]:
    current = find_project_start(client, project_name)
    if current is None:
        return []
    today = datetime.now(timezone.utc).date()
    totals: dict[str, float] = defaultdict(float)
    colors: dict[str, str] = {}

    while current <= today:
        end = min(current + timedelta(days=13), today)
        _, payload = client.get(
            "/users/current/summaries",
            {
                "start": current.isoformat(),
                "end": end.isoformat(),
                "project": project_name,
            },
        )
        for summary in payload.get("data", []):
            for language in summary.get("languages", []):
                name = str(language.get("name", "Other"))
                totals[name] += float(language.get("total_seconds", 0))
                if language.get("color"):
                    colors[name] = str(language["color"])
        current = end + timedelta(days=1)
        time.sleep(0.25)

    return [
        {"name": name, "total_seconds": seconds, "color": colors.get(name)}
        for name, seconds in totals.items()
    ]


def remap_and_sort(
    global_languages: list[dict[str, Any]],
    spire_languages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seconds: dict[str, float] = defaultdict(float)
    colors: dict[str, str] = {}

    for language in global_languages:
        name = str(language.get("name", "Other"))
        seconds[name] += float(language.get("total_seconds", 0))
        if language.get("color"):
            colors[name] = str(language["color"])

    spire_json_seconds = sum(
        float(language.get("total_seconds", 0))
        for language in spire_languages
        if str(language.get("name", "")).casefold() == "json"
    )
    available_json_seconds = seconds.get("JSON", 0.0)
    moved_json_seconds = min(spire_json_seconds, available_json_seconds)
    seconds["JSON"] = max(0.0, available_json_seconds - moved_json_seconds)
    seconds["C++"] += moved_json_seconds
    colors["C++"] = FALLBACK_COLORS["C++"]

    visible = [
        {
            "name": name,
            "total_seconds": total,
            "color": colors.get(name) or FALLBACK_COLORS.get(name, "#858585"),
        }
        for name, total in seconds.items()
        if total > MIN_SECONDS and name != "Other"
    ]

    pinned = [
        next((item for item in visible if item["name"] == name), None)
        for name in PINNED_LANGUAGES
    ]
    pinned = [item for item in pinned if item is not None]
    rest = sorted(
        (
            item
            for item in visible
            if item["name"] not in PINNED_LANGUAGES
        ),
        key=lambda item: item["total_seconds"],
        reverse=True,
    )
    ordered = (pinned + rest)[:MAX_LANGUAGES]
    for index, item in enumerate(ordered):
        item["color"] = MOONLIGHT_COLORS[index]
    return ordered


def format_hours(seconds: float) -> str:
    hours = seconds / 3600
    if hours >= 100:
        return f"{hours:,.0f} h"
    return f"{hours:,.1f} h"


def render_svg(languages: list[dict[str, Any]]) -> str:
    width = 500
    row_height = 70
    height = 94 + row_height * max(len(languages), 1) + 24
    maximum = max(
        (float(item["total_seconds"]) for item in languages),
        default=1.0,
    )

    rows: list[str] = []
    if not languages:
        rows.append(
            '<text x="30" y="116" class="empty">'
            "No all-time languages over one hour yet."
            "</text>",
        )
    else:
        for index, item in enumerate(languages):
            y = 110 + index * row_height
            bar_width = max(
                8.0,
                345 * float(item["total_seconds"]) / maximum,
            )
            rows.extend(
                [
                    (
                        f'<text x="30" y="{y}" class="language">'
                        f'{escape(str(item["name"]))}</text>'
                    ),
                    (
                        f'<rect x="30" y="{y + 18}" width="345" height="12" '
                        'rx="6" fill="#30374d"/>'
                    ),
                    (
                        f'<rect x="30" y="{y + 18}" width="{bar_width:.1f}" '
                        f'height="12" rx="6" fill="{escape(str(item["color"]))}"/>'
                    ),
                    (
                        f'<text x="470" y="{y + 30}" class="hours" '
                        f'text-anchor="end">{format_hours(float(item["total_seconds"]))}</text>'
                    ),
                ],
            )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-labelledby="title desc">
  <title id="title">All-Time Coding</title>
  <desc id="desc">All-time WakaTime language totals over one hour, with SpireModH3 classified as C++.</desc>
  <style>
    .title {{ fill: #d2ad86; font: 700 25px "Segoe UI", Ubuntu, sans-serif; }}
    .language {{ fill: #d9e7ff; font: 400 17px "Segoe UI", Ubuntu, sans-serif; }}
    .hours {{ fill: #d9e7ff; font: 400 16px "Segoe UI", Ubuntu, sans-serif; }}
    .empty {{ fill: #a8b9d8; font: 400 15px "Segoe UI", Ubuntu, sans-serif; }}
  </style>
  <rect x="0.5" y="0.5" width="499" height="{height - 1}" rx="5" fill="#171a29" stroke="#394360"/>
  <text x="30" y="54" class="title">All-Time Coding</text>
  {''.join(rows)}
</svg>
"""


def load_fixture(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["global_languages"], payload["spire_languages"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()

    if args.fixture:
        global_languages, spire_languages = load_fixture(args.fixture)
    else:
        api_key = os.environ.get("WAKATIME_API_KEY")
        if not api_key:
            raise RuntimeError(
                "WAKATIME_API_KEY is required. Store it as a GitHub Actions secret.",
            )
        client = WakaTimeClient(api_key)
        global_languages = fetch_all_time_languages(client)
        if not global_languages:
            print("WakaTime has no recorded language time yet; card remains unpublished.")
            return
        spire_languages = fetch_project_languages(client, SPIRE_PROJECT)

    languages = remap_and_sort(global_languages, spire_languages)
    if not languages:
        print("No WakaTime languages are over one hour yet; card remains unpublished.")
        return
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_svg(languages), encoding="utf-8")
    print(f"Generated {OUTPUT_PATH} with {len(languages)} languages.")


if __name__ == "__main__":
    main()
