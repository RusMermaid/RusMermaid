#!/usr/bin/env python3
"""Refresh the GitHub language card and apply RusMermaid's moonlight palette."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path


SOURCE_URL = (
    "https://github-stats-extended.vercel.app/api/top-langs/"
    "?username=RusMermaid&langs_count=7&count_private=true"
    "&exclude_repo=Ural_CS&theme=codeSTACKr"
    "&hide=nix,dockerfile,html,glsl,gdscript,javascript,css"
)
OUTPUT_PATH = Path("assets/github-languages-moonlight.svg")
MOONLIGHT_COLORS = (
    "#a88465",
    "#737b91",
    "#536fa8",
    "#688ac0",
    "#83a6d5",
    "#a8c8e8",
    "#d1e6fa",
)


def fetch_card() -> str:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "Accept": "image/svg+xml",
            "User-Agent": "RusMermaid-README-Card/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        svg = response.read().decode("utf-8")
    lowered = svg.lower()
    if "<svg" not in lowered or "</svg>" not in lowered:
        raise RuntimeError("Language-card provider did not return a complete SVG.")
    if any(marker in lowered for marker in ("something went wrong", "rate limit", "<html")):
        raise RuntimeError("Language-card provider returned an error document.")
    return svg


def set_testid_attr(svg: str, testid: str, attribute: str, value: str) -> str:
    pattern = re.compile(
        rf'(<rect\b(?=[^>]*data-testid="{re.escape(testid)}")[^>]*\b'
        rf'{re.escape(attribute)}=")[^"]*(")',
    )
    updated, count = pattern.subn(rf"\g<1>{value}\2", svg)
    if count < 1:
        raise RuntimeError(f'Could not theme "{testid}" {attribute}.')
    return updated


def apply_moonlight(svg: str) -> str:
    svg = svg.replace("#ff652f", "#d2ad86")
    svg = svg.replace("#ffffff", "#d9e7ff")
    svg = set_testid_attr(svg, "card-bg", "fill", "#171a29")
    svg = set_testid_attr(svg, "card-bg", "stroke", "#394360")
    svg = set_testid_attr(svg, "progress-background", "fill", "#30374d")

    progress_pattern = re.compile(
        r'(<rect\b(?=[^>]*class="lang-progress")[^>]*\bfill=")'
        r'#[0-9a-fA-F]{6}(")',
    )
    color_index = 0

    def replace_progress(match: re.Match[str]) -> str:
        nonlocal color_index
        color = MOONLIGHT_COLORS[min(color_index, len(MOONLIGHT_COLORS) - 1)]
        color_index += 1
        return f"{match.group(1)}{color}{match.group(2)}"

    svg = progress_pattern.sub(replace_progress, svg)
    if color_index < 1:
        raise RuntimeError("No language progress bars were found to theme.")
    return svg


def main() -> None:
    themed = apply_moonlight(fetch_card())
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(themed, encoding="utf-8")
    print(f"Updated {OUTPUT_PATH} with {len(MOONLIGHT_COLORS)} moonlight colors.")


if __name__ == "__main__":
    main()
