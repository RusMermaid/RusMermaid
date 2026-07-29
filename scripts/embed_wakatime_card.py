#!/usr/bin/env python3
"""Embed the real WakaTime card without touching the generated chess regions."""

from pathlib import Path


README_PATH = Path("README.md")
LANGUAGE_CARD = "![My GitHub Language Stats](./assets/github-languages-moonlight.svg)"
TIME_CARD_PATH = "./assets/wakatime-all-time.svg"
TWO_COLUMN_BLOCK = """<p>
  <img width="48%" align="center" src="./assets/github-languages-moonlight.svg" alt="My GitHub Language Stats" />
  <img width="48%" align="center" src="./assets/wakatime-all-time.svg" alt="My All-Time Coding Stats" />
</p>
"""


def main() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    if TIME_CARD_PATH in readme:
        print("WakaTime card is already embedded.")
        return

    chess_heading = "# Lets play Chess!"
    chess_index = readme.find(chess_heading)
    if chess_index < 0:
        raise RuntimeError("Chess heading is missing; refusing to edit README.")
    chess_tail = readme[chess_index:]

    if readme.count(LANGUAGE_CARD) != 1:
        raise RuntimeError("Expected exactly one moonlight GitHub language card.")
    updated = readme.replace(LANGUAGE_CARD, TWO_COLUMN_BLOCK, 1)

    updated_chess_index = updated.find(chess_heading)
    if updated_chess_index < 0 or updated[updated_chess_index:] != chess_tail:
        raise RuntimeError("Chess content changed; refusing to write README.")
    if "</p>\n\n" not in updated:
        raise RuntimeError("Required blank line after the card HTML block is missing.")

    README_PATH.write_text(updated, encoding="utf-8")
    print("Embedded the real WakaTime card beside the GitHub language card.")


if __name__ == "__main__":
    main()
