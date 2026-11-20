"""컨셉 아트에서 스프라이트 뽑기 (Designer와 Designer QA가 함께 쓰는 도구, LLM 호출 없음).

컨셉 이미지(data/concept/*.png)의 한 영역을 잘라 배경을 지우고, 프레임 크기로 줄이고, 색을 줄여
Designer 명세와 같은 글자 격자(rows + palette)로 바꾼다. Designer는 이것을 참고 스프라이트로 받고,
Designer QA는 만든 스프라이트를 이것과 비교한다(색 거리, 실루엣 겹침).

  python -m stairs_agents.concept palette data/concept/05-3_play.png            # 주요 색
  python -m stairs_agents.concept extract data/concept/05-3_play.png --box 272,140,36,74 --size 32x48
  python -m stairs_agents.concept regions                                         # regions.json 전부 -> output/concept_refs/
  python -m stairs_agents.concept boxes data/concept/05-3_play.png                # 배경과 다른 덩어리 자동 찾기

영역 목록은 data/concept/regions.json 에 둔다 (id, image, box[x,y,w,h], size[w,h], colors, tol, clear, sheet, anim, variant).
배경이 덜 지워지면 tol(배경색 허용 거리)을 바꾸거나, 남는 조각을 clear([x,y,w,h], 자른 영역 기준)로 지운다.
"""
from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw

from .util import ROOT

SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#@$%&*+=?"
REGIONS = ROOT / "data" / "concept" / "regions.json"


# ---------------------------------------------------------------------- 색
def hexc(c) -> str:
    return "#%02X%02X%02X" % tuple(c[:3])


def rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def dist(a, b) -> float:
    """사람 눈에 가까운 가중 RGB 거리 (0~약 765)."""
    r = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return ((2 + r / 256) * dr * dr + 4 * dg * dg + (2 + (255 - r) / 256) * db * db) ** 0.5


def dominant(img: Image.Image, k: int = 12, box=None) -> list[dict]:
    """주요 색 k개와 비율. 투명 픽셀은 뺀다."""
    im = img.convert("RGBA")
    if box:
        x, y, w, h = box
        im = im.crop((x, y, x + w, y + h))
    px = [p[:3] for p in (im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()) if p[3] >= 128]
    if not px:
        return []
    flat = Image.new("RGB", (len(px), 1)); flat.putdata(px)
    q = flat.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: 3 * k]
    counts = sorted(q.getcolors(), reverse=True)
    total = len(px)
    return [{"hex": hexc(pal[3 * i: 3 * i + 3]), "share": round(n / total, 4)} for n, i in counts]


# ---------------------------------------------------------------------- 배경 지우기
def remove_bg(crop: Image.Image, tol: float = 70.0) -> Image.Image:
    """테두리 색과 비슷하고 테두리에서 이어진 픽셀을 투명하게 한다 (flood fill)."""
    im = crop.convert("RGBA")
    w, h = im.size
    px = im.load()
    border = [px[x, y][:3] for x in range(w) for y in (0, h - 1)] + [px[x, y][:3] for y in range(h) for x in (0, w - 1)]
    seeds = [c["hex"] for c in dominant(_strip(border), 4)]
    seeds = [rgb(s) for s in seeds]
    close = lambda c: min(dist(c, s) for s in seeds) <= tol  # noqa: E731
    seen = [[False] * h for _ in range(w)]
    q = deque((x, y) for x in range(w) for y in (0, h - 1))
    q.extend((x, y) for y in range(h) for x in (0, w - 1))
    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h or seen[x][y]:
            continue
        seen[x][y] = True
        if not close(px[x, y][:3]):
            continue
        r, g, b, _ = px[x, y]
        px[x, y] = (r, g, b, 0)
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return im


def _strip(colors) -> Image.Image:
    im = Image.new("RGB", (len(colors), 1)); im.putdata(colors)
    return im


# ---------------------------------------------------------------------- 줄이기와 색 줄이기
def fit(im: Image.Image, w: int, h: int, anchor: str = "bottom") -> Image.Image:
    """불투명 부분만 남겨 w x h 안에 비율을 지켜 줄이고, 가운데 아래(발 위치)에 놓는다."""
    bbox = im.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
    if not bbox:
        return Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im = im.crop(bbox)
    s = min(w / im.width, h / im.height)
    nw, nh = max(1, round(im.width * s)), max(1, round(im.height * s))
    # 색은 상자 평균, 투명도는 반 이상이면 불투명 (픽셀아트 가장자리를 또렷하게)
    small = im.resize((nw, nh), Image.Resampling.BOX)
    a = small.getchannel("A").point(lambda v: 255 if v >= 110 else 0)
    small.putalpha(a)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = h - nh if anchor == "bottom" else (h - nh) // 2
    out.paste(small, ((w - nw) // 2, y))
    return out


def quantize(im: Image.Image, colors: int = 10, palette: list[str] | None = None) -> Image.Image:
    """불투명 픽셀의 색을 palette(주어지면) 또는 median cut colors개로 맞춘다."""
    im = im.convert("RGBA")
    px = im.load()
    opaque = [px[x, y][:3] for y in range(im.height) for x in range(im.width) if px[x, y][3]]
    if not opaque:
        return im
    pal = [rgb(p) for p in palette] if palette else [rgb(c["hex"]) for c in dominant(_strip(opaque), colors)]
    cache: dict = {}
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if not a:
                continue
            c = cache.get((r, g, b))
            if c is None:
                c = cache[(r, g, b)] = min(pal, key=lambda p: dist(p, (r, g, b)))
            px[x, y] = (*c, 255)
    return im


def to_grid(im: Image.Image) -> tuple[list[str], dict[str, str]]:
    """RGBA 이미지를 Designer 명세의 글자 격자와 팔레트로 바꾼다 ('.'은 투명)."""
    px = im.load()
    sym: dict[str, str] = {}
    rows = []
    for y in range(im.height):
        row = []
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if not a:
                row.append("."); continue
            hx = hexc((r, g, b))
            if hx not in sym:
                if len(sym) >= len(SYMBOLS):
                    raise ValueError("색이 너무 많습니다. colors를 줄이세요.")
                sym[hx] = SYMBOLS[len(sym)]
            row.append(sym[hx])
        rows.append("".join(row))
    return rows, {s: hx for hx, s in sym.items()}


def extract(image_path: Path, box, size, colors: int = 10, palette=None, tol: float = 70.0,
            keep_bg: bool = False, clear=None) -> dict:
    """컨셉 이미지의 box 영역을 size 프레임의 스프라이트 격자로 뽑는다. clear는 지울 [x, y, w, h] 목록(자른 영역 기준)."""
    src = Image.open(image_path).convert("RGBA")
    x, y, w, h = box
    crop = src.crop((x, y, x + w, y + h))
    cut = crop.copy() if keep_bg else remove_bg(crop, tol)
    for cx, cy, cw, ch in clear or []:
        cut.paste((0, 0, 0, 0), (cx, cy, cx + cw, cy + ch))
    small = quantize(fit(cut, *size), colors, palette)
    rows, pal = to_grid(small)
    return {"rows": rows, "palette": pal, "image": small, "crop": cut}


# ---------------------------------------------------------------------- 비교 (QA용)
def palette_distance(a: list[str], b: list[str]) -> float:
    """두 팔레트의 평균 최근접 색 거리 (양방향 평균, 낮을수록 비슷)."""
    if not a or not b:
        return 999.0
    A, B = [rgb(x) for x in a], [rgb(x) for x in b]
    ab = sum(min(dist(p, q) for q in B) for p in A) / len(A)
    ba = sum(min(dist(p, q) for q in A) for p in B) / len(B)
    return round((ab + ba) / 2, 1)


def silhouette_iou(a: Image.Image, b: Image.Image) -> float:
    """두 스프라이트의 불투명 영역 겹침 (각자 불투명 부분을 같은 크기로 맞춘 뒤 IoU)."""
    def mask(im):
        im = im.convert("RGBA")
        bb = im.getchannel("A").getbbox()
        if not bb:
            return None
        return im.crop(bb).getchannel("A").resize((24, 36), Image.Resampling.NEAREST)
    ma, mb = mask(a), mask(b)
    if ma is None or mb is None:
        return 0.0
    pa, pb = list(ma.get_flattened_data() if hasattr(ma, "get_flattened_data") else ma.getdata()), list(mb.get_flattened_data() if hasattr(mb, "get_flattened_data") else mb.getdata())
    inter = sum(1 for p, q in zip(pa, pb) if p >= 128 and q >= 128)
    union = sum(1 for p, q in zip(pa, pb) if p >= 128 or q >= 128)
    return round(inter / union, 3) if union else 0.0


def luminance(img: Image.Image) -> float:
    g = img.convert("L")
    return round(sum(g.get_flattened_data() if hasattr(g, "get_flattened_data") else g.getdata()) / (g.width * g.height), 1)


# ---------------------------------------------------------------------- 덩어리 자동 찾기
def boxes(image_path: Path, tol: float = 60.0, min_area: int = 120) -> list[list[int]]:
    """이미지 전체의 주요 배경색과 다른 픽셀 덩어리의 경계 상자 목록 (영역을 고를 때 참고)."""
    im = Image.open(image_path).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = [rgb(c["hex"]) for c in dominant(im, 6)[:3]]
    fg = [[min(dist(px[x, y], b) for b in bg) > tol for y in range(h)] for x in range(w)]
    seen = [[False] * h for _ in range(w)]
    out = []
    for sx in range(w):
        for sy in range(h):
            if not fg[sx][sy] or seen[sx][sy]:
                continue
            q, n = deque([(sx, sy)]), 0
            x0 = x1 = sx; y0 = y1 = sy
            seen[sx][sy] = True
            while q:
                x, y = q.popleft(); n += 1
                x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and fg[nx][ny] and not seen[nx][ny]:
                        seen[nx][ny] = True; q.append((nx, ny))
            if n >= min_area:
                out.append([x0, y0, x1 - x0 + 1, y1 - y0 + 1])
    return sorted(out, key=lambda b: -b[2] * b[3])


# ---------------------------------------------------------------------- regions.json 전체
def load_regions(path: Path = REGIONS) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}


def extract_regions(out_dir: Path, path: Path = REGIONS) -> dict:
    """regions.json의 모든 영역을 뽑아 out_dir에 refs.json, 미리보기 PNG, 영역 표시 이미지를 쓴다."""
    spec = load_regions(path)
    if not spec:
        return {}
    out_dir.mkdir(parents=True, exist_ok=True)
    base = Path(path).parent
    refs = {"images": {}, "regions": {}}
    marked = {}
    for name, rel in spec.get("images", {}).items():
        img = Image.open(base / rel).convert("RGB")
        refs["images"][name] = {"file": rel, "size": list(img.size), "palette": dominant(img, 12),
                                "luminance": luminance(img)}
        marked[name] = img.copy()
    for r in spec.get("regions", []):
        res = extract(base / spec["images"][r["image"]], r["box"], r["size"], r.get("colors", 10),
                      r.get("palette"), r.get("tol", 70.0), r.get("keep_bg", False), r.get("clear"))
        res["image"].save(out_dir / f"{r['id']}.png")
        res["image"].resize((r["size"][0] * 4, r["size"][1] * 4), Image.Resampling.NEAREST).save(out_dir / f"{r['id']}_x4.png")
        refs["regions"][r["id"]] = {k: r.get(k) for k in ("image", "box", "size", "sheet", "anim", "variant", "note")}
        refs["regions"][r["id"]].update(rows=res["rows"], palette=res["palette"], file=f"{r['id']}.png")
        d = ImageDraw.Draw(marked[r["image"]])
        x, y, w, h = r["box"]
        d.rectangle((x, y, x + w - 1, y + h - 1), outline=(255, 64, 160))
        d.text((x + 1, y + 1), r["id"], fill=(255, 64, 160))
    for name, img in marked.items():
        img.save(out_dir / f"_regions_{name}.png")
    (out_dir / "refs.json").write_text(json.dumps(refs, ensure_ascii=False, indent=1), encoding="utf-8")
    return refs


def ref_text(refs: dict, sheet: str | None = None) -> str:
    """Designer에게 줄 참고 문구. sheet를 주면 그 시트의 참고 격자만 넣는다 ("__images__"는 시트 없는 배경 참고)."""
    if not refs:
        return ""
    lines = ["# 컨셉 아트 참고 (concept.py가 data/concept/ 이미지에서 뽑음)"]
    for name, im in refs["images"].items():
        lines.append(f"- {name} 주요 색: " + ", ".join(f"{c['hex']}({c['share']:.0%})" for c in im["palette"][:10]))
    for rid, r in refs["regions"].items():
        if sheet and r.get("sheet") != (None if sheet == "__images__" else sheet):  # __images__: 시트 없는 배경 참고
            continue
        lines.append(f"\n## 참고 스프라이트 {rid} ({r.get('note') or ''}, {r['size'][0]}x{r['size'][1]}, "
                     f"시트 {r.get('sheet')}/{r.get('anim')})")
        lines.append("팔레트: " + json.dumps(r["palette"], ensure_ascii=False))
        lines.append("\n".join(r["rows"]))
    lines.append("\n참고 격자는 실루엣, 비율, 색 배치를 맞추는 데 쓴다. 그대로 베끼지 말고 03 팔레트와 프레임 크기에 맞게 다듬는다.")
    return "\n".join(lines)


# ---------------------------------------------------------------------- 명령줄
def _box(s: str) -> list[int]:
    return [int(v) for v in s.split(",")]


def _size(s: str) -> list[int]:
    return [int(v) for v in s.lower().split("x")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="stairs_agents.concept", description="컨셉 아트에서 스프라이트 뽑기")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("palette"); p.add_argument("image"); p.add_argument("-k", type=int, default=12)
    p.add_argument("--box", type=_box)
    e = sub.add_parser("extract"); e.add_argument("image"); e.add_argument("--box", type=_box, required=True)
    e.add_argument("--size", type=_size, required=True); e.add_argument("--colors", type=int, default=10)
    e.add_argument("--tol", type=float, default=70.0); e.add_argument("--keep-bg", action="store_true")
    e.add_argument("--out", help="미리보기 PNG 경로 (4배)")
    b = sub.add_parser("boxes"); b.add_argument("image"); b.add_argument("--tol", type=float, default=60.0)
    b.add_argument("--min-area", type=int, default=120)
    r = sub.add_parser("regions"); r.add_argument("--out", default=str(ROOT / "output" / "concept_refs"))
    r.add_argument("--file", default=str(REGIONS))
    a = ap.parse_args(argv)

    if a.cmd == "palette":
        for c in dominant(Image.open(a.image), a.k, a.box):
            print(f"{c['hex']}  {c['share']:.1%}")
    elif a.cmd == "extract":
        res = extract(Path(a.image), a.box, a.size, a.colors, None, a.tol, a.keep_bg)
        print(json.dumps({"palette": res["palette"]}, ensure_ascii=False))
        print("\n".join(res["rows"]))
        if a.out:
            res["image"].resize((a.size[0] * 4, a.size[1] * 4), Image.Resampling.NEAREST).save(a.out)
    elif a.cmd == "boxes":
        for bx in boxes(Path(a.image), a.tol, a.min_area)[:40]:
            print(",".join(map(str, bx)))
    else:
        refs = extract_regions(Path(a.out), Path(a.file))
        print(f"영역 {len(refs.get('regions', {}))}개 -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
