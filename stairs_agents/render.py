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


def _glow(img, d, e):
    """둥근 빛 번짐. 바깥에서 안쪽으로 옅은 타원을 겹쳐 그린다."""
    steps = max(1, e.get("steps", 6))
    for i in range(steps):  # 겹칠수록 밝아지도록 고리마다 따로 합성한다
        k = 1 - i / steps
        rx, ry = e["rx"] * k, e["ry"] * k
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse([e["x"] - rx, e["y"] - ry, e["x"] + rx, e["y"] + ry],
                                      fill=rgba(e["color"], round(255 * e.get("alpha", 0.3) / steps)))
        img.alpha_composite(layer)


def _tower(img, d, e):
    """가운데 우뚝 선 본사 타워. tiers(아래에서 위로)를 가운데 맞춰 쌓고, 맨 위 층 창만 crown_lit 색으로 켠다."""
    rnd = random.Random(e.get("seed", 1))
    cx, base = e["x"], e["y"]
    tiers = e["tiers"]
    y = base
    for ti, t in enumerate(tiers):
        w, h = t["w"], t["h"]
        x0, top = cx - w // 2, y - h
        d.rectangle([x0, top, x0 + w - 1, y - 1], fill=rgba(e["color"]))
        d.line([x0, top, x0, y - 1], fill=rgba(e.get("edge", e["color"])))           # 빛 받는 모서리
        d.line([x0 + w - 1, top, x0 + w - 1, y - 1], fill=rgba(e.get("shade", e["color"])))
        d.line([x0, top, x0 + w - 1, top], fill=rgba(e.get("edge", e["color"])))     # 층 구분 처마
        ww, wh, gx, gy = e.get("win", [2, 2, 1, 2])
        crown = ti == len(tiers) - 1
        if crown and e.get("crown_style", "band") == "band":
            # 맨 위 층: 통창 하나가 따뜻하게 켜져 있고, 세로 창틀만 어둡게 남는다
            d.rectangle([x0 + 2, top + 3, x0 + w - 3, y - 3], fill=rgba(e["crown_lit"]))
            for mx in range(x0 + 2, x0 + w - 2, e.get("mullion", 6)):
                d.line([mx, top + 3, mx, y - 3], fill=rgba(e["color"]))
        else:
            # 창 격자. crown_style "windows"면 맨 위 단의 창이 하나하나 따뜻하게 켜진다
            for wy in range(top + 3, y - wh - 1, wh + gy):
                for wx in range(x0 + 3, x0 + w - ww - 2, ww + gx):
                    if crown:
                        col = e["crown_lit"] if rnd.random() < e.get("crown_ratio", 0.9) else e["lit"]
                    else:
                        col = e["lit"] if rnd.random() < e.get("lit_ratio", 0) else e["window"]
                    d.rectangle([wx, wy, wx + ww - 1, wy + wh - 1], fill=rgba(col))
        if e.get("stripes"):
            for sx in range(x0 + 2, x0 + w - 1, e["stripes"]):
                d.line([sx, top + 1, sx, y - 1], fill=rgba(e.get("edge", e["color"])))
        y = top
    if e.get("spire"):
        d.line([cx, y - e["spire"], cx, y - 1], fill=rgba(e.get("edge", e["color"])))
        if e.get("beacon"):
            d.point([cx, y - e["spire"]], fill=rgba(e["beacon"]))


# 고개 숙인 사원 (9x14, 오른쪽을 봄): 굽은 등이 가장 높고, 머리는 어깨보다 앞쪽 아래로 떨어진다. b = 서류가방
FIGURE_BOWED = [
    ".###.....",
    "#####....",
    "######.##",
    "######.##",
    ".#####.#.",
    ".####....",
    ".####....",
    ".####....",
    "b####....",
    "bb###....",
    "bb#.#....",
    "..#.#....",
    "..#..#...",
    ".##..##..",
]
# 똑바로 선 사람 (9x14)
FIGURE_STANDING = [
    "...##....",
    "..####...",
    "..####...",
    "...##....",
    "..####...",
    ".######..",
    ".######..",
    ".######..",
    "b.####...",
    "bb####...",
    "bb#..#...",
    "..#..#...",
    "..#..#...",
    ".##..##..",
]


def _figure(d, x, y, c, pose, face, accent=None):
    """사원 한 명. x는 왼쪽, y는 발 위치, face는 1(오른쪽) 또는 -1(왼쪽, 좌우 반전)."""
    rows = FIGURE_BOWED if pose == "bowed" else FIGURE_STANDING
    h, w = len(rows), len(rows[0])
    for ry, line in enumerate(rows):
        for rx, ch in enumerate(line if face > 0 else line[::-1]):
            if ch == "#":
                d.point([x + rx, y - h + ry], fill=c)
            elif ch == "b" and accent:
                d.point([x + rx, y - h + ry], fill=accent)
    return w


# 2배 해상도용 고개 숙인 직장인 (16x30, 오른쪽으로 걷는다). k = 머리카락·신발, s = 정장, x = 셔츠, w = 피부, b = 가방
WALKER_2X = [
    "................",
    "......kkkk......",
    ".....kkkkkk.....",
    ".....kkkkkkk....",
    "......wwwkkk....",
    ".......wwwkk....",
    ".....sss.ww.....",
    "....sssssx......",
    "...ssssssxs.....",
    "...sssssssss....",
    "...sssssssss....",
    "...ssssssss.....",
    "...ssssssss.....",
    "..sss.sssss.....",
    "..ss..sssss.....",
    "..ss..sssss.....",
    "..ww..sssss.....",
    ".bbbb.sssss.....",
    ".bbbb.sssss.....",
    ".bbbb.ssss......",
    "......ssss......",
    ".....ss..ss.....",
    ".....ss..ss.....",
    "....ss....ss....",
    "....ss....ss....",
    "....ss.....ss...",
    "...ss......ss...",
    "...ss.......ss..",
    "..kkk.......kkk.",
    "..kkk.......kkk.",
]


WALKER_2X_L = [
    "....................",
    "........kkkk........",
    ".......kkkkkk.......",
    "......kkkkkkkk......",
    "......kkkkkkkkk.....",
    ".......wwwwkkkk.....",
    "........wwwwkkk.....",
    ".........wwwkk......",
    ".......ssxxww.......",
    "......sssxxss.......",
    ".....ssssxtsss......",
    "....sssssxtssss.....",
    "....sssssxtssss.....",
    "....ssssssxssss.....",
    "....ssssssssss......",
    "....ssssssssss......",
    "...sss.sssssss......",
    "...sss.sssssss......",
    "...ss..sssssss......",
    "...ss..sssssss......",
    "...ww..sssssss......",
    "..bbbb.sssssss......",
    "..bbbb.dddddd.......",
    "..bbbb.dddddd.......",
    "..bbbb.dddddd.......",
    ".......ddd.ddd......",
    ".......ddd..ddd.....",
    "......ddd....dd.....",
    "......ddd....ddd....",
    "......dd......dd....",
    ".....ddd......ddd...",
    ".....dd........dd...",
    ".....dd........dd...",
    "....ddd........ddd..",
    "....dd..........dd..",
    "....dd..........dd..",
    "...kkk..........kkk.",
    "...kkkk.........kkkk",
    "....................",
    "....................",
]


def _draw_template(d, rows, x, y, colors, face=1):
    """문자 그림 rows를 (x, y=발 위치)에 그린다. colors는 문자 → 색."""
    h = len(rows)
    for ry, line in enumerate(rows):
        for rx, ch in enumerate(line if face > 0 else line[::-1]):
            if ch in colors and colors[ch] is not None:
                d.point([x + rx, y - h + ry], fill=colors[ch])


def _walkers(img, d, e):
    """2배 해상도 거리의 직장인들. xs 위치마다 한 명, 고개를 숙이고 걷는다."""
    rnd = random.Random(e.get("seed", 1))
    cols = {"k": rgba(e["hair"]), "s": rgba(e["suit"]), "x": rgba(e["shirt"]), "w": rgba(e["skin"]),
            "b": rgba(e["bag"]), "d": rgba(e.get("pants", e["suit"])), "t": rgba(e.get("tie", e["suit"]))}
    rows = WALKER_2X_L if e.get("size", "large") == "large" else WALKER_2X
    for x in e["xs"]:
        face = 1 if rnd.random() < 0.5 else -1
        c = dict(cols)
        if rnd.random() > e.get("bag_ratio", 0.5):
            c["b"] = None
        _draw_template(d, rows, x, e["y"], c, face)


def _clouds(img, d, e):
    """밤구름 띠. 무작위 타원 덩어리를 겹치고, 위쪽 가장자리를 밝게 칠한다."""
    rnd = random.Random(e.get("seed", 1))
    body, rim, shade = rgba(e["color"]), rgba(e["rim"]), rgba(e.get("shade", e["color"]))
    blobs = []
    for _ in range(e["count"]):
        cx = rnd.randint(e.get("x0", 0), e.get("x1", img.width))
        cy = rnd.randint(e["y0"], e["y1"])
        rx = rnd.randint(e["min_r"], e["max_r"])
        blobs.append((cx, cy, rx, max(3, rx // e.get("flat", 3))))
    for cx, cy, rx, ry in blobs:          # 그림자(아래쪽)
        d.ellipse([cx - rx, cy - ry + 2, cx + rx, cy + ry + 2], fill=shade)
    for cx, cy, rx, ry in blobs:          # 밝은 윗가장자리
        d.ellipse([cx - rx, cy - ry - 1, cx + rx, cy + ry - 1], fill=rim)
    for cx, cy, rx, ry in blobs:          # 몸통
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=body)


def _city(img, d, e):
    """세밀한 빌딩 숲 (2배 해상도). 건물마다 층별 창 격자, 일부는 따뜻하게·일부는 흐리게 켜져 있고, 옥상 계단·안테나가 있다."""
    rnd = random.Random(e.get("seed", 1))
    x = e.get("x0", 0) - rnd.randint(0, 12)
    ww, wh, gx, gy = e.get("win", [2, 3, 2, 3])
    while x < e.get("x1", img.width):
        w = rnd.randint(e["min_w"], e["max_w"])
        h = rnd.randint(e["min_h"], e["max_h"])
        if e.get("skip_x0") is not None and e["skip_x0"] < x + w and x < e["skip_x1"]:
            x += w + rnd.randint(e.get("min_gap", 0), e.get("max_gap", 4))
            continue
        base, top = e["y"], e["y"] - h
        body = rgba(e["color"])
        d.rectangle([x, top, x + w - 1, base - 1], fill=body)
        d.line([x + w - 1, top, x + w - 1, base - 1], fill=rgba(e.get("shade", e["color"])))
        d.line([x, top, x, base - 1], fill=rgba(e.get("edge", e["color"])))
        if rnd.random() < e.get("setback_ratio", 0.3) and w > 14:   # 옥상 한 단
            sw = w // 2
            d.rectangle([x + (w - sw) // 2, top - 6, x + (w + sw) // 2, top - 1], fill=body)
        if rnd.random() < e.get("antenna_ratio", 0.25):
            ax = x + rnd.randint(3, max(3, w - 3))
            d.line([ax, top - rnd.randint(8, 16), ax, top - 1], fill=rgba(e.get("edge", e["color"])))
        if rnd.random() < e.get("stripe_ratio", 0):
            # 세로 기둥 줄무늬 외벽: 밝은 기둥선 사이로 좁은 창 띠
            step = e.get("stripe_gap", 4)
            for sx in range(x + 2, x + w - 2, step):
                d.line([sx, top + 2, sx, base - 1], fill=rgba(e.get("edge", e["color"])))
            for wy in range(top + 6, base - 4, e.get("stripe_floor", 9)):
                for sx in range(x + 3, x + w - 3, step):
                    r = rnd.random()
                    col = e["warm"] if r < e.get("warm_ratio", 0.15) * 0.3 else (e["lit"] if r < e.get("lit_ratio", 0.1) else e["window"])
                    d.rectangle([sx, wy, sx + step - 2, wy + 3], fill=rgba(col))
            x += w + rnd.randint(e.get("min_gap", 0), e.get("max_gap", 4))
            continue
        warm_floor = rnd.random() < e.get("warm_ratio", 0.15)
        for wy in range(top + 4, base - wh - 2, wh + gy):
            for wx in range(x + 3, x + w - ww - 2, ww + gx):
                r = rnd.random()
                if warm_floor and r < 0.7:
                    col = e["warm"]
                elif r < e.get("lit_ratio", 0.1):
                    col = e["lit"]
                else:
                    col = e["window"]
                d.rectangle([wx, wy, wx + ww - 1, wy + wh - 1], fill=rgba(col))
        x += w + rnd.randint(e.get("min_gap", 0), e.get("max_gap", 4))


def _crowd(img, d, e):
    """출근길 사원 무리. x0~x1 사이에 간격을 섞어 세우고, 방향과 가방을 무작위로 정한다."""
    rnd = random.Random(e.get("seed", 1))
    c = rgba(e["color"])
    acc = rgba(e["accent"]) if e.get("accent") else None
    x = e["x0"]
    while x < e["x1"]:
        face = 1 if rnd.random() < 0.5 else -1
        _figure(d, x, e["y"] - rnd.randint(0, e.get("jitter", 0)), c, e.get("pose", "bowed"), face,
                acc if rnd.random() < e.get("accent_ratio", 0.5) else None)
        x += rnd.randint(e.get("min_gap", 8), e.get("max_gap", 16))


def _silhouette(img, d, e):
    """창가에 서서 아래를 내려다보는 한 사람 (최상층 CEO 등)."""
    _figure(d, e["x"], e["y"], rgba(e["color"]), "bowed", e.get("face", 1))


def _lamps(img, d, e):
    """가로등 여러 개. 기둥, 팔, 등, 아래로 퍼지는 불빛."""
    for x in e["xs"]:
        top = e["y"] - e["h"]
        d.line([x, top, x, e["y"] - 1], fill=rgba(e["color"]))
        d.line([x, top, x + 4, top], fill=rgba(e["color"]))
        d.rectangle([x + 4, top, x + 5, top + 1], fill=rgba(e["light"]))
        _light_cone(img, d, {"x": x + 5, "y": top + 2, "w": e.get("spread", 22), "h": e["h"] - 2,
                             "color": e["light"], "alpha": e.get("alpha", 0.12)})


SCENE_KINDS = {
    "rect": _rect, "gradient": _gradient, "line": _line, "window_grid": _window_grid,
    "skyline": _skyline, "building": _building, "partition": _partition, "desk": _desk,
    "monitor": _monitor, "chair": _chair, "plant": _plant, "table": _table, "door": _door,
    "frame": _frame, "light_cone": _light_cone, "workers": _workers,
    "glow": _glow, "tower": _tower, "crowd": _crowd, "silhouette": _silhouette, "lamps": _lamps,
    "clouds": _clouds, "city": _city, "walkers": _walkers,
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
    pad, gap = spec.get("pad", 5), spec.get("gap", 2)
    w = title.width + pad * 2 + 1
    h = title.height + pad * 2 + 1 + (sub.height + 2 if sub else 0)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], fill=rgba(spec["plate"]), outline=rgba(spec["border"]))
    d.rectangle([gap, gap, w - 1 - gap, h - 1 - gap], outline=rgba(spec["border"]))   # 이중 테두리
    if gap > 2:
        d.rectangle([1, 1, w - 2, h - 2], outline=rgba(spec["border"]))
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
