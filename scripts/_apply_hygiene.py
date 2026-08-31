#!/usr/bin/env python3
"""One-shot HTML hygiene for the five main pages. Not part of the regular build."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NAV = """  <nav class="navbar navbar-expand-lg fixed-top navbar-light bg-light">
    <a class="d-flex align-items-center" href="index.html">
      <img alt="HX" class="rounded-circle mr-2" src="images/huixiong.jpg" style="height:50px;" />
      <span class="navbar-brand mb-0 h1">Hui Xiong</span>
    </a>
    <button aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation" class="navbar-toggler"
      data-nav-toggle type="button">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav ml-auto">
        <li class="nav-item"><a class="nav-link" data-value="about" href="index.html#about">Home</a></li>
        <li class="nav-item"><a class="nav-link" data-value="news" href="index.html#news">News</a></li>
        <li class="nav-item"><a class="nav-link{group}" href="group.html">Group</a></li>
        <li class="nav-item"><a class="nav-link{papers}" href="papers.html">Papers</a></li>
        <li class="nav-item"><a class="nav-link" data-value="teaching" href="index.html#teaching">Teaching</a></li>
        <li class="nav-item"><a class="nav-link" data-value="service" href="index.html#service">Service</a></li>
        <li class="nav-item"><a class="nav-link" data-value="media" href="index.html#media">Media</a></li>
        <li class="nav-item"><a class="nav-link{aca}" href="aca.html">Algorithm Association</a></li>
      </ul>
    </div>
  </nav>"""

SCRIPTS_TAIL = '  <script src="js/main.js"></script>\n'


def nav_for(page: str) -> str:
    flags = {"group": "", "papers": "", "aca": ""}
    if page in flags:
        flags[page] = " active"
    return NAV.format(**flags)


def strip_comments(html: str) -> str:
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


_WOW_ANIM = (
    r"fadeIn(?:Up|Down|Left|Right)?"
    r"|slideIn(?:Up|Down|Left|Right)"
    r"|zoomIn(?:Down|Left|Right)?"
    r"|bounceIn|flipInX"
)


def strip_wow(html: str) -> str:
    html = re.sub(rf"\s*\bwow\b(?:\s+(?:{_WOW_ANIM}))*", "", html)
    html = re.sub(r'\s*data-wow-delay="[^"]*"', "", html)
    return html


def strip_remote_fonts_and_wow_tags(html: str) -> str:
    html = re.sub(r'\s*<link[^>]+fonts\.(geekzu\.org|googleapis\.com)[^>]*>', "", html)
    html = re.sub(r'\s*<link[^>]+fonts\.gstatic\.com[^>]*>', "", html)
    html = re.sub(r"\s*<script[^>]*wow\.min\.js[^>]*></script>", "", html, flags=re.I)
    html = re.sub(r"\s*<script>\s*new WOW\(\)\.init\(\);\s*</script>", "", html, flags=re.I)
    html = re.sub(r'\s*<link[^>]+css/animate\.css[^>]*>', "", html)
    html = re.sub(
        r'\s*<meta http-equiv=[\'"](?:cache-control|expires|pragma)[\'"][^>]*>',
        "",
        html,
        flags=re.I,
    )
    html = re.sub(r"\s*<base[^>]*>", "", html)
    return html


def replace_first_nav(html: str, page: str) -> str:
    return re.sub(r"<nav\b.*?</nav>", nav_for(page), html, count=1, flags=re.S)


def replace_legacy_scripts(html: str) -> str:
    html = re.sub(
        r"\s*<script[^>]*(?:jquery|popper|bootstrap\.min\.js)[^>]*>\s*</script>",
        "",
        html,
        flags=re.I,
    )
    if "js/main.js" not in html:
        html = html.replace("</body>", SCRIPTS_TAIL + "</body>")
    return html


def mark_external_links(html: str) -> str:
    def repl(match: re.Match) -> str:
        tag = match.group(0)
        extra = []
        if "target=" not in tag:
            extra.append('target="_blank"')
        if "rel=" not in tag:
            extra.append('rel="noopener noreferrer"')
        if not extra:
            return tag
        return tag[:-1] + " " + " ".join(extra) + ">"

    return re.sub(
        r"<a\b[^>]*href=[\"']https?://[^\"']+[\"'][^>]*>",
        repl,
        html,
        flags=re.I,
    )


def upsert_meta(html: str, title: str, description: str) -> str:
    if 'name="description"' not in html:
        html = html.replace(
            "<head>",
            "<head>\n"
            f'  <meta name="description" content="{description}" />\n'
            f'  <meta property="og:title" content="{title}" />\n'
            f'  <meta property="og:description" content="{description}" />\n'
            '  <meta property="og:image" content="images/huixiong.jpg" />',
            1,
        )
    return html


def process_index() -> None:
    path = ROOT / "index.html"
    html = path.read_text("utf-8")
    html = strip_comments(html)
    html = strip_remote_fonts_and_wow_tags(html)
    html = strip_wow(html)
    html = replace_first_nav(html, "index")
    html = replace_legacy_scripts(html)
    html = mark_external_links(html)
    html = upsert_meta(
        html,
        "Home Page for Prof. Hui Xiong",
        "Hui Xiong is a Chair Professor at HKUST (Guangzhou). Research in AI, data mining, and mobile computing.",
    )
    # drop leftover empty script and wow stylesheet leftovers
    html = re.sub(r"\s*<script>\s*</script>", "", html)
    path.write_text(html, "utf-8")
    print("updated index.html")


def process_papers() -> None:
    path = ROOT / "papers.html"
    html = path.read_text("utf-8")
    html = strip_remote_fonts_and_wow_tags(html)
    html = strip_wow(html)
    html = replace_first_nav(html, "papers")
    html = replace_legacy_scripts(html)
    html = mark_external_links(html)
    html = upsert_meta(
        html,
        "Selected Publications – Hui Xiong",
        "Selected publications of Prof. Hui Xiong: books, journals, conference papers, and patents.",
    )
    if 'id="paper-query"' not in html:
        html = html.replace(
            '    <div class="pub-tabs">',
            '    <div class="paper-search-wrap">\n'
            '      <input type="text" id="paper-query" placeholder="Search papers..." aria-label="Search papers" />\n'
            '      <button type="button" id="paper-clear">Clear</button>\n'
            "    </div>\n"
            '    <div class="pub-tabs">',
            1,
        )
    if ".paper-search-wrap" not in html:
        html = html.replace(
            "    .pub-tabs {",
            "    .paper-search-wrap { display:flex; justify-content:center; gap:.5rem; margin: 12px 0 8px; }\n"
            "    .paper-search-wrap input { width: min(420px, 90%); border:1px solid #ced4da; border-radius:999px; padding:.4rem .8rem; }\n"
            "    .paper-search-wrap button { border:none; background:#f1f3f5; border-radius:999px; padding:.4rem .8rem; }\n"
            "    .pub-tabs {",
            1,
        )
    filter_js = """
    (function () {
      var input = document.getElementById('paper-query');
      var clear = document.getElementById('paper-clear');
      if (!input) return;
      function apply() {
        var q = (input.value || '').toLowerCase().trim();
        document.querySelectorAll('.paper').forEach(function (p) {
          var t = (p.textContent || '').toLowerCase();
          p.style.display = (!q || t.indexOf(q) !== -1) ? '' : 'none';
        });
      }
      input.addEventListener('input', apply);
      if (clear) clear.addEventListener('click', function () {
        input.value = '';
        apply();
        input.focus();
      });
    })();
"""
    if 'id="paper-query"' in html and "p.style.display" not in html:
        html = html.replace(
            "</body>",
            f"  <script>{filter_js}\n  </script>\n</body>",
            1,
        )
    path.write_text(html, "utf-8")
    print("updated papers.html")


def process_simple(name: str, title: str, description: str, page_key: str) -> None:
    path = ROOT / name
    html = path.read_text("utf-8")
    html = strip_remote_fonts_and_wow_tags(html)
    html = strip_wow(html)
    html = replace_first_nav(html, page_key)
    html = replace_legacy_scripts(html)
    html = mark_external_links(html)
    html = upsert_meta(html, title, description)
    html = re.sub(r"\s*<script>\s*</script>", "", html)
    path.write_text(html, "utf-8")
    print(f"updated {name}")


def process_group() -> None:
    path = ROOT / "group.html"
    html = path.read_text("utf-8")
    html = replace_first_nav(html, "group")
    if "js/main.js" not in html:
        html = html.replace("</body>", SCRIPTS_TAIL + "</body>")
    path.write_text(html, "utf-8")
    print("updated group.html")


def main() -> None:
    process_index()
    process_papers()
    process_group()
    process_simple(
        "aca.html",
        "Algorithmic Contest Association | Prof. Hui Xiong",
        "ICPC / CCPC training and contest results of the Algorithmic Contest Association at HKUST (Guangzhou).",
        "aca",
    )
    process_simple(
        "prospective.html",
        "For Prospective Students – Hui Xiong",
        "PhD, MPhil, and visiting opportunities in Prof. Hui Xiong's research group at HKUST (Guangzhou).",
        "group",
    )


if __name__ == "__main__":
    main()
