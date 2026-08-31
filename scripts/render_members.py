#!/usr/bin/env python3
"""Render group.html roster sections from data/members.json."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GROUP = ROOT / "group.html"
DATA = ROOT / "data" / "members.json"
IMG_DIR = ROOT / "members" / "images"
DEFAULT_PHOTO = "default.jpg"
START = "<!-- roster:start -->"
END = "<!-- roster:end -->"


def photo_src(photo: str | None) -> str:
    name = photo or DEFAULT_PHOTO
    if not (IMG_DIR / name).is_file():
        name = DEFAULT_PHOTO
    return f"members/images/{name}"


def card(member: dict) -> str:
    name = escape(member["name"])
    aff = escape(member.get("affiliation") or "hkust")
    href = member.get("href")
    notes = member.get("notes") or []
    badge = ""
    if aff == "ustc":
        badge = '            <span class="member-badge badge-ustc">USTC</span>\n'
    note_html = "".join(
        f'            <span class="member-year">{escape(n)}</span>\n' for n in notes
    )
    inner = (
        f"          <div class=\"member-card\">\n"
        f"{badge}"
        f"            <div class=\"member-avatar\">"
        f"<img loading=\"lazy\" width=\"120\" height=\"120\" "
        f"src=\"{escape(photo_src(member.get('photo')))}\" alt=\"{name}\" "
        f"onerror=\"this.onerror=null;this.src='members/images/default.jpg'\" /></div>\n"
        f"            <p>{name}"
        + (
            ' <i class="fa fa-external-link member-home" aria-hidden="true"></i>'
            if href
            else ""
        )
        + "</p>\n"
        f"{note_html}"
        f"          </div>\n"
    )
    if href:
        return (
            f'        <a class="member-item" href="{escape(href, quote=True)}" '
            f'target="_blank" rel="noopener noreferrer" data-affiliation="{aff}">\n'
            f"{inner}"
            f"        </a>"
        )
    return (
        f'        <div class="member-item" data-affiliation="{aff}">\n'
        f"{inner}"
        f"        </div>"
    )


def grid(members: list[dict]) -> str:
    cards = "\n".join(card(m) for m in members)
    return f'      <div class="member-grid">\n{cards}\n      </div>'


def yearly_section(title: str, section_id: str, years: dict[str, list]) -> str:
    chunks = [
        f'    <section class="member-category my-5" id="{section_id}">',
        f'      <h2 class="text-center mb-4">{title}</h2>',
    ]
    for year, members in years.items():
        chunks.append(f'      <h3 class="year-subtitle">{escape(year)}</h3>')
        chunks.append(grid(members))
    chunks.append("    </section>")
    return "\n".join(chunks)


def visiting_table(rows: list[dict]) -> str:
    body = []
    for row in rows:
        body.append(
            "            <tr class=\"member-item\" data-affiliation=\"\">\n"
            f"              <td>{escape(row['name'])}</td>\n"
            f"              <td>{escape(row['year'])}</td>\n"
            f"              <td>{escape(row['position'])}</td>\n"
            "            </tr>"
        )
    return "\n".join(
        [
            '    <section class="member-category my-5" id="visiting">',
            '      <h2 class="text-center mb-4">Visiting Students &amp; Scholars</h2>',
            '      <div class="visiting-table-container">',
            '        <table class="table table-visiting">',
            "          <thead>",
            "            <tr>",
            "              <th>Name</th>",
            "              <th>Year</th>",
            "              <th>Position</th>",
            "            </tr>",
            "          </thead>",
            "          <tbody>",
            *body,
            "          </tbody>",
            "        </table>",
            "      </div>",
            "    </section>",
        ]
    )


def render(data: dict) -> str:
    parts = [
        '    <section class="member-category my-5" id="postdocs">',
        '      <h2 class="text-center mb-4">Postdoctoral Researchers</h2>',
        grid(data["postdocs"]),
        "    </section>",
        "",
        yearly_section("Ph.D. Students", "phd", data["phd"]),
        "",
        yearly_section("Master's Students", "masters", data["masters"]),
        "",
        yearly_section("Postdoc &amp; Ph.D. Placements", "placements-phd", data["placementsPhd"]),
        "",
        yearly_section("Master Placements", "placements-master", data["placementsMaster"]),
        "",
        visiting_table(data["visiting"]),
    ]
    return "\n".join(parts)


def main() -> None:
    data = json.loads(DATA.read_text("utf-8"))
    roster = render(data)
    text = GROUP.read_text("utf-8")
    if START not in text or END not in text:
        raise SystemExit(f"{GROUP} is missing {START} / {END} markers")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    GROUP.write_text(f"{before}{START}\n{roster}\n    {END}{after}", "utf-8")
    print(f"rendered roster into {GROUP.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
