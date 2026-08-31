#!/usr/bin/env python3
"""Write members/preview.html: chosen original vs site-used compressed avatar."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "members" / "originals"
DST_DIR = ROOT / "members" / "images"
OUT = ROOT / "members" / "preview.html"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def dim(path: Path) -> str:
    try:
        with Image.open(path) as img:
            return f"{img.width}×{img.height}"
    except OSError:
        return "?"


def kb(path: Path) -> float:
    return path.stat().st_size / 1024


def pick_source(files: list[Path]) -> Path:
    return max(files, key=lambda p: p.stat().st_size)


def rows() -> list[dict]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for src in SRC_DIR.iterdir():
        if src.is_file() and src.suffix.lower() in IMAGE_EXTS:
            groups[src.stem.lower()].append(src)

    items = []
    for stem, files in groups.items():
        src = files[0] if stem == "default" else pick_source(files)
        dest = DST_DIR / ("default.jpg" if stem == "default" else f"{stem}.jpg")
        extras = [p.name for p in files if p != src]
        src_kb = kb(src)
        dst_kb = kb(dest) if dest.is_file() else 0
        items.append(
            {
                "stem": stem,
                "src_name": src.name,
                "src": f"originals/{src.name}",
                "dst": f"images/{dest.name}" if dest.is_file() else "",
                "src_kb": src_kb,
                "dst_kb": dst_kb,
                "src_dim": dim(src),
                "dst_dim": dim(dest) if dest.is_file() else "—",
                "ratio": (100 * dst_kb / src_kb) if src_kb else 0,
                "saved": src_kb - dst_kb,
                "kept": dest.is_file() and dest.stat().st_size == src.stat().st_size,
                "extras": extras,
            }
        )
    items.sort(key=lambda r: r["saved"], reverse=True)
    return items


def main() -> None:
    data = rows()
    src_total = sum(r["src_kb"] for r in data)
    dst_total = sum(r["dst_kb"] for r in data)
    cards = []
    for r in data:
        tag = "kept original bytes" if r["kept"] else f"{r['ratio']:.0f}% of original"
        extra = (
            f'<p class="note">also in originals (unused): {", ".join(r["extras"])}</p>'
            if r["extras"]
            else ""
        )
        dst_img = (
            f'<img src="{r["dst"]}" alt="{r["stem"]} used" />' if r["dst"] else ""
        )
        cards.append(
            f"""
<article class="card" data-name="{r['stem']} {r['src_name'].lower()}">
  <h2>{r['stem']}</h2>
  <div class="pair">
    <figure>
      <img src="{r['src']}" alt="{r['src_name']} original" />
      <figcaption>original · {r['src_name']} · {r['src_dim']} · {r['src_kb']:.0f} KB</figcaption>
    </figure>
    <figure>
      {dst_img}
      <figcaption>used · {r['dst_dim']} · {r['dst_kb']:.0f} KB · {tag}</figcaption>
    </figure>
  </div>
  {extra}
</article>"""
        )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>头像压缩预览</title>
  <style>
    :root {{ font-family: "Hiragino Sans GB", "PT Serif", Georgia, serif; color: #222; }}
    body {{ margin: 0 auto; max-width: 1100px; padding: 24px 16px 80px; }}
    h1 {{ font-size: 1.6rem; margin-bottom: .3rem; }}
    .meta {{ color: #555; margin-bottom: 1rem; line-height: 1.5; }}
    .toolbar {{ display: flex; gap: .6rem; flex-wrap: wrap; align-items: center; margin: 1rem 0 1.5rem; }}
    input[type="search"] {{ flex: 1; min-width: 200px; padding: .45rem .7rem; border: 1px solid #ccc; border-radius: 999px; }}
    .card {{ border-top: 1px solid #eee; padding: 1.2rem 0; }}
    .card.is-hidden {{ display: none; }}
    h2 {{ font-size: 1rem; margin: 0 0 .6rem; font-weight: 600; }}
    .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    figure {{ margin: 0; }}
    img {{ width: 100%; max-height: 420px; object-fit: contain; background: #f4f4f4; border-radius: 8px; }}
    figcaption {{ font-size: .85rem; color: #555; margin-top: .35rem; }}
    .note {{ font-size: .85rem; color: #777; }}
    @media (max-width: 700px) {{ .pair {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>头像压缩预览</h1>
  <p class="meta">
    左：<code>members/originals/</code>（原图，脚本不会改）。
    右：<code>members/images/</code>（站点实际使用）。
    规则：最长边不超过 1200px，JPEG 质量 92、4:4:4；已经更小的 JPEG 原样拷贝；<code>default.jpg</code> 不重压。
    {len(data)} 张对照；原图合计 {src_total/1024:.1f} MB，使用图合计 {dst_total/1024:.1f} MB。
  </p>
  <div class="toolbar">
    <input type="search" id="q" placeholder="按文件名筛选…" />
    <span id="count"></span>
  </div>
  {''.join(cards)}
  <script>
    const cards = [...document.querySelectorAll('.card')];
    const box = document.getElementById('q');
    const count = document.getElementById('count');
    function apply() {{
      const q = box.value.toLowerCase().trim();
      let n = 0;
      cards.forEach((c) => {{
        const ok = !q || c.dataset.name.includes(q);
        c.classList.toggle('is-hidden', !ok);
        if (ok) n++;
      }});
      count.textContent = n + ' shown';
    }}
    box.addEventListener('input', apply);
    apply();
  </script>
</body>
</html>
"""
    OUT.write_text(html, "utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
