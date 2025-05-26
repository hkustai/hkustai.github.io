#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_members_en_links.py   • 2025-05-27
"""

from pathlib import Path
import textwrap, re
import pandas as pd
from bs4 import BeautifulSoup, NavigableString
from jinja2 import Template
from pypinyin import lazy_pinyin

# ───────── 基础路径 ─────────
ROOT = Path(__file__).parent
GROUP_HTML = ROOT / "group.html"
EXCEL_FILE = ROOT / "MembersAILab.xlsx"
OUT_DIR = ROOT / "members"
OUT_DIR.mkdir(exist_ok=True)

# 头像
IMAGES_DIR = OUT_DIR / "images"
IMG_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
PHOTO_SIZE = 120  # ------------ 统一头像尺寸 ------------

# ───────── 复姓表 ─────────
DOUBLE_SURNAMES = {
    "欧阳",
    "司马",
    "上官",
    "夏侯",
    "诸葛",
    "东方",
    "皇甫",
    "尉迟",
    "公羊",
    "赫连",
    "澹台",
    "公冶",
    "宗政",
    "濮阳",
    "淳于",
    "单于",
    "太叔",
    "申屠",
    "公孙",
    "仲孙",
    "轩辕",
    "令狐",
    "钟离",
    "宇文",
    "长孙",
    "慕容",
    "鲜于",
    "闾丘",
    "司徒",
    "司空",
    "亓官",
    "司寇",
    "子车",
    "颛孙",
    "司城",
    "南宫",
}

# ───────── 特殊主页 ─────────
SPECIAL_HOMEPAGES = {
    "郭伟钰": "https://weiyuguo.com",
    "管介超": "https://openreview.net/profile?id=%7EJiechao_Guan1",
    "徐亦捷": "https://yjx.me",
}

# ───────── 手动处理成员（英文名，无需头像和主页自动设置）─────────
MANUAL_MEMBERS = {"Ziyue Qiao", "Chao Wang"}


# ───────── 工具函数 ─────────
def slugify(cn: str) -> str:
    return "".join(lazy_pinyin(cn)).lower()


def en_name(cn: str) -> str:
    surname = cn[:2] if cn[:2] in DOUBLE_SURNAMES else cn[:1]
    given = cn[len(surname) :]
    return f"{''.join(lazy_pinyin(given)).capitalize()} {''.join(lazy_pinyin(surname)).capitalize()}"


def is_local(path: str) -> bool:
    return path and not path.startswith(
        ("http://", "https://", "//", "/", "data:", "#", "mailto:", "javascript:")
    )


def prefix_resources(html: str, prefix: str = "../") -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        for attr in ("src", "href", "data-src"):
            if tag.has_attr(attr):
                p = tag[attr].strip()
                if is_local(p) and not p.startswith(prefix):
                    tag[attr] = prefix + p
        if tag.has_attr("style"):
            tag["style"] = re.sub(
                r"url\([\"']?([^\"')]+)[\"']?\)",
                lambda m: f'url("{prefix + m.group(1)}")'
                if is_local(m.group(1)) and not m.group(1).startswith(prefix)
                else m.group(0),
                tag["style"],
            )
    return str(soup)


def pub_table_html(sub: pd.DataFrame) -> str:
    cols = ["Year", "Title", "Authors", "Venue", "Notes"]
    view = sub.rename(
        columns={
            "Year.1": "Year",
            "Publication Title": "Title",
            "Conferences/Journals": "Venue",
        }
    ).assign(Notes=sub.get("Notes", ""))[cols]

    def clean(y):
        if pd.isna(y) or y == "":
            return ""
        try:
            return str(int(float(y)))
        except ValueError:
            return str(y)

    view["Year"] = view["Year"].apply(clean)
    view = view.sort_values(
        "Year",
        key=lambda s: pd.to_numeric(s, errors="coerce").fillna(0),
        ascending=False,
    )

    thead = "".join(f"<th>{c}</th>" for c in cols)
    tbody = "".join(
        "<tr>"
        + "".join(f"<td>{r[c] if pd.notna(r[c]) else ''}</td>" for c in cols)
        + "</tr>"
        for _, r in view.iterrows()
    )
    return textwrap.dedent(f"""
    <div class="table-responsive">
      <table class="table table-striped table-bordered table-sm">
        <thead class="table-light"><tr>{thead}</tr></thead>
        <tbody>{tbody}</tbody>
      </table>
    </div>
    """)


# ───────── 解析 group.html ─────────
soup = BeautifulSoup(GROUP_HTML.read_text("utf-8"), "html.parser")
head_soup = BeautifulSoup(str(soup.head), "html.parser")
if not head_soup.find("base"):
    head_soup.head.insert(0, head_soup.new_tag("base", href="../"))
head_sub = prefix_resources(str(head_soup.head), "../")
nav_sub = prefix_resources(str(soup.nav), "../")
banner_sub = prefix_resources(str(soup.find("header")), "../")
footer_sub = prefix_resources(str(soup.footer), "../")

# ───────── 子页面模板 ─────────
PAGE = Template(
    textwrap.dedent("""\
<!doctype html>
<html lang="en">
{{ head }}
<body>
{{ nav }}
{{ banner }}
<main class="container my-5">
  <h1 class="text-center mb-4 wow fadeIn">{{ name_en }}</h1>
  <section class="my-4"><h3>Research Interest</h3><p><!-- Fill in later --></p></section>
  <section class="my-4"><h3>Education</h3><ul><li><strong>Bachelor&nbsp;School:</strong></li><li><strong>Master&nbsp;School:</strong></li></ul></section>
  <section class="my-4"><h3>Publications</h3>{{ pub_table|safe }}</section>
</main>
{{ footer }}
</body>
</html>""")
)

# ───────── 生成成员页 ─────────
df = pd.read_excel(EXCEL_FILE, sheet_name=0)
slug_map, en_map = {}, {}
for cn, sub in df.groupby("姓名"):
    en_map[cn] = en = en_name(cn)
    if cn in SPECIAL_HOMEPAGES or cn in MANUAL_MEMBERS:
        print(f"✓ skip {cn}")
        continue
    slug_map[cn] = slug = slugify(cn)
    (OUT_DIR / f"{slug}.html").write_text(
        PAGE.render(
            head=head_sub,
            nav=nav_sub,
            banner=banner_sub,
            footer=footer_sub,
            name_en=en,
            pub_table=pub_table_html(sub),
        ),
        "utf-8",
    )
    print(f"✓ wrote members/{slug}.html")
print("Member pages generated.\n")

# ───────── 反向映射 ─────────
en2cn = {v: k for k, v in en_map.items()}

# ───────── 注入统一 CSS ─────────
STYLE_ID = "member-avatar-style"
if tag := soup.find("style", id=STYLE_ID):
    tag.decompose()
soup.head.append(
    BeautifulSoup(
        f"""
<style id="{STYLE_ID}">
.member-avatar{{width:{PHOTO_SIZE}px;height:{PHOTO_SIZE}px;margin:0 auto 8px;
               display:flex;justify-content:center;align-items:center}}
.member-avatar img{{width:100%;height:100%;object-fit:cover;border-radius:50%}}
.member-avatar i{{font-size:{PHOTO_SIZE * 0.8}px;line-height:{PHOTO_SIZE}px;color:#6c757d}}
</style>
""",
        "html.parser",
    )
)

# ───────── 处理首页卡片 ─────────
for card in soup.select(".member-card"):
    # —— 名字处理 ——
    p_tag = card.find("p")
    if not p_tag:
        continue
    raw = p_tag.text.strip()
    cn = en2cn.get(raw, raw)
    en = en_map.get(cn, raw)
    if p_tag.text.strip() != en:
        p_tag.string.replace_with(en)

    # —— 链接 ——
    if cn in MANUAL_MEMBERS:
        href = None
    elif cn in SPECIAL_HOMEPAGES:
        href, tgt = SPECIAL_HOMEPAGES[cn], "_blank"
    elif cn in slug_map:
        href, tgt = f"members/{slug_map[cn]}.html", "_self"
    else:
        href = None
    if href:
        anchor = card.parent if card.parent.name == "a" else soup.new_tag("a")
        if anchor.parent is None:
            card.wrap(anchor)
        anchor["href"], anchor["target"] = href, tgt

    # —— 头像 / 占位符 ——
    if cn in MANUAL_MEMBERS:
        continue  # 不改头像
    slug = slug_map.get(cn)
    img_src = None
    if slug:
        for ext in IMG_EXTS:
            p = IMAGES_DIR / f"{slug}{ext}"
            if p.exists():
                img_src = p.relative_to(ROOT).as_posix()
                break

    # 删除旧 <i> 或 <img>；重建 avatar
    for tag in card.find_all(["i", "img"], recursive=False):
        tag.decompose()
    avatar = card.find("div", class_="member-avatar")
    if avatar:
        avatar.clear()
    else:
        avatar = soup.new_tag("div", **{"class": "member-avatar"})
    if img_src:
        avatar.append(soup.new_tag("img", src=img_src))
    else:
        avatar.append(
            soup.new_tag("i", **{"class": "fas fa-user-circle", "aria-hidden": "true"})
        )
    card.insert(0, avatar)

# ───────── 保存 ─────────
GROUP_HTML.write_text(str(soup), "utf-8")
print(f"✓ wrote {GROUP_HTML.relative_to(ROOT)}\nAll done!")
