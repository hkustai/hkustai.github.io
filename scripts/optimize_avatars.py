#!/usr/bin/env python3
"""Build site avatars in members/images/ from untouched originals in members/originals/.

Quality-first: downscale only past 1200px, JPEG q=92, 4:4:4 chroma.
If a JPEG original is already smaller than the encode, keep the original bytes.
Never writes back into members/originals/. default.jpg is copied as-is.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "members" / "originals"
DST_DIR = ROOT / "members" / "images"
DATA = ROOT / "data" / "members.json"
MAX_EDGE = 1200
JPEG_QUALITY = 92
SKIP_STEMS = {"default"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def groups() -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = defaultdict(list)
    for path in SRC_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            out[path.stem.lower()].append(path)
    return out


def pick_source(files: list[Path]) -> Path:
    return max(files, key=lambda p: p.stat().st_size)


def load_rgb(path: Path) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(path))
    if img.mode in {"RGBA", "LA", "P"}:
        bg = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return img.convert("RGB")


def encode_jpeg(img: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(
        dest,
        "JPEG",
        quality=JPEG_QUALITY,
        optimize=True,
        progressive=True,
        subsampling=0,
    )


def optimize_stem(stem: str, files: list[Path]) -> tuple[str, Path]:
    dest = DST_DIR / f"{stem}.jpg"
    if stem in SKIP_STEMS:
        src = next((p for p in files if p.name.lower() == "default.jpg"), files[0])
        dest.write_bytes(src.read_bytes())
        return src.name, dest

    src = pick_source(files)
    img = load_rgb(src)
    if max(img.size) > MAX_EDGE:
        img.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
    encode_jpeg(img, dest)

    already_jpeg = src.suffix.lower() in {".jpg", ".jpeg"}
    if already_jpeg and dest.stat().st_size >= src.stat().st_size:
        dest.write_bytes(src.read_bytes())
    return src.name, dest


def rewrite_photo(name: str | None, renamed: dict[str, str]) -> str | None:
    if not name:
        return None
    if name in renamed:
        return renamed[name]
    stem = Path(name).stem.lower()
    if stem in SKIP_STEMS:
        return name
    return f"{stem}.jpg"


def walk_members(data: dict, renamed: dict[str, str]) -> None:
    def fix_list(items: list) -> None:
        for item in items:
            item["photo"] = rewrite_photo(item.get("photo"), renamed)

    fix_list(data["postdocs"])
    for key in ("phd", "masters", "placementsPhd", "placementsMaster"):
        for items in data[key].values():
            fix_list(items)


def main() -> None:
    if not SRC_DIR.is_dir():
        raise SystemExit(f"missing originals directory: {SRC_DIR}")
    DST_DIR.mkdir(parents=True, exist_ok=True)
    renamed: dict[str, str] = {}
    kept_stems = set()
    for stem, files in sorted(groups().items()):
        src_name, dest = optimize_stem(stem, files)
        kept_stems.add(dest.name)
        if Path(src_name).name != dest.name:
            renamed[src_name] = dest.name
            if Path(src_name).suffix.lower() != dest.suffix.lower():
                renamed[Path(src_name).name] = dest.name
        for extra in files:
            if extra.name != dest.name:
                renamed[extra.name] = dest.name
    for leftover in DST_DIR.iterdir():
        if leftover.is_file() and leftover.suffix.lower() in IMAGE_EXTS:
            if leftover.name not in kept_stems and leftover.stem.lower() not in SKIP_STEMS:
                leftover.unlink()
    if DATA.exists():
        data = json.loads(DATA.read_text("utf-8"))
        walk_members(data, renamed)
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"wrote {len(kept_stems)} file(s) to {DST_DIR.relative_to(ROOT)} from {SRC_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
