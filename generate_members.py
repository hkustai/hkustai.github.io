#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_members_en_links.py   • 2025-05-24

✓ /members/<slug>.html 继承 CSS/JS/图片 (全局补前缀)
✓ 首页中文名 → “名 姓”，卡片可点击
✓ Publications → Bootstrap 表格 (含 Notes，年份无 .0)
✓ 支持部分成员跳转外部个人主页（如郭伟钰 → weiyuguo.com）
"""

from pathlib import Path
import textwrap, re
import pandas as pd
from bs4 import BeautifulSoup, NavigableString, Comment
from jinja2 import Template
from pypinyin import lazy_pinyin

# ───────── 基础路径 ─────────
ROOT        = Path(__file__).parent
GROUP_HTML  = ROOT / "group.html"
EXCEL_FILE  = ROOT / "MembersAILab.xlsx"
OUT_DIR     = ROOT / "members"
OUT_DIR.mkdir(exist_ok=True)

# ───────── 复姓表 ─────────
DOUBLE_SURNAMES = {
    "欧阳","司马","上官","夏侯","诸葛","东方","皇甫","尉迟","公羊","赫连","澹台",
    "公冶","宗政","濮阳","淳于","单于","太叔","申屠","公孙","仲孙","轩辕","令狐",
    "钟离","宇文","长孙","慕容","鲜于","闾丘","司徒","司空","亓官","司寇",
    "子车","颛孙","司城","南宫"
}

# ───────── 特殊主页映射 ─────────
SPECIAL_HOMEPAGES = {
    "郭伟钰": "https://weiyuguo.com",
    "管介超": "https://openreview.net/profile?id=%7EJiechao_Guan1",
    "徐亦捷": "https://yjx.me"
}

# ───────── 工具函数 ─────────
def slugify(cn_name: str) -> str:
    return "".join(lazy_pinyin(cn_name)).lower()

def en_name(cn_name: str) -> str:
    """中文姓名 → 'GivenName Surname'"""
    surname = cn_name[:2] if cn_name[:2] in DOUBLE_SURNAMES else cn_name[:1]
    given   = cn_name[len(surname):]
    sur_en  = "".join(lazy_pinyin(surname)).capitalize()
    giv_en  = "".join(lazy_pinyin(given)).capitalize()
    return f"{giv_en} {sur_en}"

def is_local(path: str) -> bool:
    return path and not path.startswith((
        "http://", "https://", "//", "/", "data:", "#", "mailto:", "javascript:"
    ))

def prefix_resources(html: str, prefix: str = "../") -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        for attr in ("src", "href", "data-src"):
            if tag.has_attr(attr):
                path = tag[attr].strip()
                if is_local(path) and not path.startswith(prefix):
                    tag[attr] = prefix + path
        if tag.has_attr("style"):
            style = tag["style"]
            new_style = re.sub(
                r'url\([\'"]?([^\'")]+)[\'"]?\)',
                lambda m: f'url("{prefix + m.group(1)}")'
                if is_local(m.group(1)) and not m.group(1).startswith(prefix)
                else m.group(0),
                style
            )
            tag["style"] = new_style
    return str(soup)

def pub_table_html(sub_df: pd.DataFrame) -> str:
    cols = ["Year", "Title", "Authors", "Venue", "Notes"]
    view = (
        sub_df.rename(columns={
            "Year.1": "Year",
            "Publication Title": "Title",
            "Conferences/Journals": "Venue"
        })
        .assign(Notes=sub_df.get("Notes", ""))
        .loc[:, cols]
    )

    def clean_year(y):
        if pd.isna(y) or y == "":
            return ""
        try:
            return str(int(float(y)))
        except ValueError:
            return str(y)
    view["Year"] = view["Year"].apply(clean_year)

    view = view.sort_values(
        "Year",
        key=lambda s: pd.to_numeric(s, errors="coerce").fillna(0),
        ascending=False
    )

    head_row = "".join(f"<th>{c}</th>" for c in cols)
    body_rows = [
        "<tr>" + "".join(f"<td>{r[c] if pd.notna(r[c]) else ''}</td>" for c in cols) + "</tr>"
        for _, r in view.iterrows()
    ]

    return textwrap.dedent(f"""
    <div class="table-responsive">
      <table class="table table-striped table-bordered table-sm">
        <thead class="table-light"><tr>{head_row}</tr></thead>
        <tbody>{"".join(body_rows)}</tbody>
      </table>
    </div>
    """)

# ───────── 解析 group.html，提取片段并统一前缀 ─────────
master_soup = BeautifulSoup(GROUP_HTML.read_text(encoding="utf-8"), "html.parser")

head_soup = BeautifulSoup(str(master_soup.head), "html.parser")
if not head_soup.find("base"):
    head_soup.head.insert(0, head_soup.new_tag("base", href="../"))
head_sub_html = prefix_resources(str(head_soup.head), "../")

nav_html    = prefix_resources(str(master_soup.nav), "../")
banner_html = prefix_resources(str(master_soup.find("header")), "../")
footer_html = prefix_resources(str(master_soup.footer), "../")

# ───────── 子页面模板 ─────────
PAGE_TMPL = Template(textwrap.dedent("""
<!doctype html>
<html lang="en">
{{ head }}
<body>
{{ nav }}
{{ banner }}
<main class="container my-5">
  <h1 class="text-center mb-4 wow fadeIn">{{ name_en }}</h1>

  <section class="my-4">
    <h3>Research Interest</h3>
    <p><!-- Fill in later --></p>
  </section>

  <section class="my-4">
    <h3>Education</h3>
    <ul>
      <li><strong>Bachelor&nbsp;School:</strong> <!-- Fill in later --></li>
      <li><strong>Master&nbsp;School:</strong> <!-- Fill in later --></li>
    </ul>
  </section>

  <section class="my-4">
    <h3>Publications</h3>
    {{ pub_table|safe }}
  </section>
</main>
{{ footer }}
</body>
</html>
"""))

# ───────── 读取 Excel，生成子页面 ─────────
df = pd.read_excel(EXCEL_FILE, sheet_name=0)
slug_map, en_map = {}, {}

for cn_name, sub in df.groupby("姓名"):
    eng = en_name(cn_name)
    en_map[cn_name] = eng

    if cn_name in SPECIAL_HOMEPAGES:
        print(f"✓ skipped {cn_name} (external homepage)")
        continue

    slug = slugify(cn_name)
    slug_map[cn_name] = slug

    html = PAGE_TMPL.render(
        head=head_sub_html,
        nav=nav_html,
        banner=banner_html,
        footer=footer_html,
        name_en=eng,
        pub_table=pub_table_html(sub)
    )
    (OUT_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
    print(f"✓ wrote members/{slug}.html")

print("Member pages generated.\n")

# ───────── 更新首页：英文名 & 可点击 ─────────
for card in master_soup.select(".member-card"):
    p_tag = card.find("p")
    if not p_tag:
        continue
    cn = p_tag.text.strip()
    p_tag.string.replace_with(en_map.get(cn, cn))

    if cn in SPECIAL_HOMEPAGES:
        href = SPECIAL_HOMEPAGES[cn]
    elif cn in slug_map:
        href = f"members/{slug_map[cn]}.html"
    else:
        continue

    if card.parent.name != "a":
        card.wrap(master_soup.new_tag("a", href=href, target="_self"))

# ───────── 输出新首页 ─────────
new_home = ROOT / "group.html"
new_home.write_text(str(master_soup), encoding="utf-8")
print(f"✓ wrote {new_home.relative_to(ROOT)}")

print("\nAll done!")