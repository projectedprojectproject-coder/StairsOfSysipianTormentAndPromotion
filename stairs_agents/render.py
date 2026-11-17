"""Designer가 만든 JSON 명세를 PNG로 그리는 픽셀 렌더러 (Pillow)."""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .util import hex_rgb

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]


def rgba(h: str, a: int = 255):
    r, g, b = hex_rgb(h)
    return (r, g, b, a)


# ---------------------------------------------------------------- sheets
def render_sheet(asset_id: str, spec: dict, palette: dict, out_dir: Path) -> dict:
    fw, fh = spec["frame_w"], spec["frame_h"]
    variants = spec.get("variants") or {"default": {}}
    anims = spec["animations"]

    # 애니메이션별 프레임 목록 (mirror 해석)
    resolved: dict[str, tuple[list, bool, float]] = {}
    for name, a in anims.items():
        if "mirror" in a:
            src = anims[a["mirror"]]
            resolved[name] = (src["frames"], True, a.get("fps", src.get("fps", 1)))
        else:
            resolved[name] = (a["frames"], False, a.get("fps", 1))

    columns, col = {}, 0
    for name, (frames, _, fps) in resolved.items():
        columns[name] = {"frames": list(range(col, col + len(frames))), "fps": fps}
        col += len(frames)

    sheet = Image.new("RGBA", (fw * col, fh * len(variants)), (0, 0, 0, 0))
    for row, (vname, override) in enumerate(variants.items()):
        pal = {**palette, **(override or {})}
        for name, (frames, mirror, _) in resolved.items():
            for i, frame in enumerate(frames):
                img = _draw_grid(frame, pal, fw, fh, asset_id, name)
                if mirror:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                sheet.paste(img, (columns[name]["frames"][i] * fw, row * fh))
    fname = f"{asset_id}.png"
    sheet.save(out_dir / fname)
    return {
        "file": fname, "frame_w": fw, "frame_h": fh,
        "variants": {v: i for i, v in enumerate(variants)},
        "animations": columns,
    }


def _draw_grid(rows: list[str], pal: dict, fw: int, fh: int, aid: str, anim: str) -> Image.Image:
    if len(rows) != fh:
        raise ValueError(f"{aid}/{anim}: 줄 수 {len(rows)} != frame_h {fh}")
    img = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    px = img.load()
    for y, line in enumerate(rows):
        if len(line) != fw:
            raise ValueError(f"{aid}/{anim} {y}행: 길이 {len(line)} != frame_w {fw}")
        for x, ch in enumerate(line):
            if ch == ".":
                continue
            if ch not in pal:
                raise ValueError(f"{aid}/{anim}: 팔레트에 없는 기호 '{ch}'")
            px[x, y] = rgba(pal[ch])
    return img


# ---------------------------------------------------------------- scenes
def render_scene(spec: dict) -> Image.Image:
    img = Image.new("RGBA", (spec["w"], spec["h"]), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    for el in spec["elements"]:
        fn = SCENE_KINDS.get(el["kind"])
        if fn is None:
            raise ValueError(f"알 수 없는 scene 요소: {el['kind']}")
        fn(img, d, el)
    return img


def _rect(img, d, e):
    d.rectangle([e["x"], e["y"], e["x"] + e["w"] - 1, e["y"] + e["h"] - 1], fill=rgba(e["color"]))


def _gradient(img, d, e):
    c0, c1 = hex_rgb(e["c0"]), hex_rgb(e["c1"])
    steps = max(1, e.get("steps", 6))
    span = e["y1"] - e["y0"]
    for i in range(steps):
        t = i / max(1, steps - 1)
        c = tuple(round(a + (b - a) * t) for a, b in zip(c0, c1)) + (255,)
        y0 = e["y0"] + span * i // steps
        y1 = e["y0"] + span * (i + 1) // steps - 1
        d.rectangle([0, y0, img.width - 1, y1], fill=c)


def _line(img, d, e):
    d.line([e["x0"], e["y0"], e["x1"], e["y1"]], fill=rgba(e["color"]))


def _window_grid(img, d, e):
    rnd = random.Random(e.get("seed", 1))
    for r in range(e["rows"]):
        for c in range(e["cols"]):
            x = e["x"] + c * (e["cell_w"] + e["gap"])
            y = e["y"] + r * (e["cell_h"] + e["gap"])
            col = e["lit"] if rnd.random() < e.get("lit_ratio", 0) else e["color"]
            d.rectangle([x, y, x + e["cell_w"] - 1, y + e["cell_h"] - 1], fill=rgba(col))


def _building(img, d, e, rnd=None):
    rnd = rnd or random.Random(e.get("seed", 1))
    x, base, w, h = e["x"], e["y"], e["w"], e["h"]
    top = base - h
    d.rectangle([x, top, x + w - 1, base - 1], fill=rgba(e["color"]))
    if e.get("window"):
        for wy in range(top + 3, base - 3, 4):
            for wx in range(x + 2, x + w - 2, 3):
                lit = rnd.random() < e.get("lit_ratio", 0)
                col = e.get("lit") if lit and e.get("lit") else e["window"]
                d.point([wx, wy], fill=rgba(col))
    if e.get("top_lit"):
        for wx in range(x + 2, x + w - 2, 3):
            d.rectangle([wx, top + 2, wx + 1, top + 4], fill=rgba(e["top_lit"]))


def _skyline(img, d, e):
    rnd = random.Random(e.get("seed", 1))
    x = -rnd.randint(0, 10)
    for _ in range(e["count"]):
        w = rnd.randint(e["min_w"], e["max_w"])
        h = rnd.randint(e["min_h"], e["max_h"])
        _building(img, d, {"x": x, "y": e["y"], "w": w, "h": h, "color": e["color"],
                           "window": e.get("window"), "lit": e.get("lit", e.get("window")),
                           "lit_ratio": e.get("window_ratio", 0)}, rnd)
        x += w + rnd.randint(0, 3)
        if x > img.width:
            break


def _partition(img, d, e):
    x, y, w, h = e["x"], e["y"], e["w"], e["h"]
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=rgba(e["color"]))
    d.line([x, y, x + w - 1, y], fill=rgba(e["edge"]))
    for px in range(x + 3, x + w - 1, 4):
        d.line([px, y + 2, px, y + h - 2], fill=rgba(e["edge"]))


def _desk(img, d, e):
    x, y, w = e["x"], e["y"], e["w"]
    d.rectangle([x, y, x + w - 1, y + 1], fill=rgba(e["color"]))
    d.rectangle([x + 1, y + 2, x + 1, y + 9], fill=rgba(e["leg"]))
    d.rectangle([x + w - 2, y + 2, x + w - 2, y + 9], fill=rgba(e["leg"]))


def _monitor(img, d, e):
    x, y = e["x"], e["y"]
    d.rectangle([x, y, x + 9, y + 6], fill=rgba(e["color"]))
    d.rectangle([x + 1, y + 1, x + 8, y + 5], fill=rgba(e["screen"]))
    d.rectangle([x + 4, y + 7, x + 5, y + 8], fill=rgba(e["color"]))


def _chair(img, d, e):
    x, y = e["x"], e["y"]
    d.rectangle([x, y, x + 1, y + 7], fill=rgba(e["color"]))
    d.rectangle([x, y + 6, x + 5, y + 7], fill=rgba(e["color"]))
    d.rectangle([x + 2, y + 8, x + 2, y + 10], fill=rgba(e["color"]))


def _plant(img, d, e):
    x, y = e["x"], e["y"]
    d.rectangle([x, y + 6, x + 4, y + 10], fill=rgba(e["pot"]))
    for dx, dy in [(2, 0), (1, 1), (3, 1), (0, 2), (2, 2), (4, 2), (1, 3), (3, 3), (2, 4), (0, 4), (4, 4), (2, 5)]:
        d.point([x + dx, y + dy], fill=rgba(e["leaf"]))


def _table(img, d, e):
    x, y, w = e["x"], e["y"], e["w"]
    d.rectangle([x, y, x + w - 1, y + 2], fill=rgba(e["color"]))
    for lx in (x + 3, x + w - 4):
        d.rectangle([lx, y + 3, lx, y + 10], fill=rgba(e["color"]))


def _door(img, d, e):
    x, y, w, h = e["x"], e["y"], e["w"], e["h"]
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=rgba(e["color"]))
    d.point([x + w - 3, y + h // 2], fill=rgba(e["knob"]))


def _frame(img, d, e):
    x, y, w, h = e["x"], e["y"], e["w"], e["h"]
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=rgba(e["color"]))
    d.rectangle([x + 1, y + 1, x + w - 2, y + h - 2], fill=rgba(e["inner"]))


def _light_cone(img, d, e):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    a = round(255 * e.get("alpha", 0.3))
    x, y, w, h = e["x"], e["y"], e["w"], e["h"]
    ld.polygon([(x - 2, y), (x + 2, y), (x + w // 2, y + h), (x - w // 2, y + h)], fill=rgba(e["color"], a))
    img.alpha_composite(layer)


def _workers(img, d, e):
    c = rgba(e["color"])
    for i in range(e["count"]):
        x = e["x"] + i * e["spacing"]
        y = e["y"]
        if e.get("pose") == "bowed":
            d.rectangle([x, y - 7, x + 2, y - 1], fill=c)       # 다리와 몸
            d.rectangle([x + 1, y - 11, x + 4, y - 7], fill=c)  # 숙인 상체
            d.rectangle([x + 4, y - 10, x + 5, y - 8], fill=c)  # 숙인 머리
        else:
            d.rectangle([x, y - 9, x + 2, y - 1], fill=c)
            d.rectangle([x, y - 12, x + 2, y - 10], fill=c)


SCENE_KINDS = {
    "rect": _rect, "gradient": _gradient, "line": _line, "window_grid": _window_grid,
    "skyline": _skyline, "building": _building, "partition": _partition, "desk": _desk,
    "monitor": _monitor, "chair": _chair, "plant": _plant, "table": _table, "door": _door,
    "frame": _frame, "light_cone": _light_cone, "workers": _workers,
}


# ---------------------------------------------------------------- logo
def _font(px: int):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, px)
    raise FileNotFoundError("한글 글꼴을 찾지 못했습니다. render.FONT_CANDIDATES에 경로를 추가하세요.")


def _pixel_text(text: str, px: int, color) -> Image.Image:
    """작은 크기로 그린 뒤 이진화해 픽셀 글자처럼 만든다."""
    f = _font(px)
    l, t, r, b = f.getbbox(text)
    img = Image.new("L", (r - l + 2, b - t + 2), 0)
    ImageDraw.Draw(img).text((1 - l, 1 - t), text, font=f, fill=255)
    mask = img.point(lambda v: 255 if v > 110 else 0)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(Image.new("RGBA", img.size, color), mask=mask)
    return out


def render_logo(spec: dict) -> Image.Image:
    title = _pixel_text(spec["text"], spec["font_px"], rgba(spec["fg"]))
    shadow = _pixel_text(spec["text"], spec["font_px"], rgba(spec["shadow"]))
    sub = _pixel_text(spec["subtitle"], max(8, spec["font_px"] // 3), rgba(spec["border"])) if spec.get("subtitle") else None
    pad = 5
    w = title.width + pad * 2 + 1
    h = title.height + pad * 2 + 1 + (sub.height + 2 if sub else 0)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], fill=rgba(spec["plate"]), outline=rgba(spec["border"]))
    d.rectangle([2, 2, w - 3, h - 3], outline=rgba(spec["border"]))
    img.alpha_composite(shadow, (pad + 1, pad + 1))
    img.alpha_composite(title, (pad, pad))
    if sub:
        img.alpha_composite(sub, ((w - sub.width) // 2, pad + title.height + 1))
    return img


def render_image(asset_id: str, spec: dict, out_dir: Path) -> dict:
    if spec["type"] == "scene":
        img = render_scene(spec)
    elif spec["type"] == "text":
        img = render_logo(spec)
    else:
        raise ValueError(f"{asset_id}: 알 수 없는 image type {spec['type']}")
    fname = f"{asset_id}.png"
    img.save(out_dir / fname)
    return {"file": fname, "w": img.width, "h": img.height}
