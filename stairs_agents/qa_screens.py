"""화면 대조 QA (Developer QA 2단계, Publisher 뒤에 돈다).

역할: Publisher가 실제 게임에서 찍은 화면(output/dist/screens)을 컨셉 화면(data/concept)과 나란히 놓고
      구도, 강조색(빨강) 위치, 색, 밝기를 재고, 컨셉의 번호 요소 목록과 함께 Claude 시각 검토를 받는다.
      화면 배치와 UI는 Developer, 그림은 Designer의 몫이므로 문제마다 어느 쪽이 고칠지 적는다.
입력: output/dist/screens/*.png, data/concept/regions.json 의 "screens" (화면 -> 컨셉 이미지, 번호 요소)
출력: output/qa_out/screens_qa.md, screens_qa.json, screens_contact.png
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from PIL import Image, ImageDraw

from . import concept
from .qa import QAReport, ask_review, save
from .util import Paths, log

ACCENT = concept.rgb("#A13D3D")
GRID = (64, 36)


def _gray(im: Image.Image) -> list[float]:
    g = im.convert("L").resize(GRID, Image.Resampling.BOX)
    return list(g.get_flattened_data() if hasattr(g, "get_flattened_data") else g.getdata())


def layout_corr(a: Image.Image, b: Image.Image) -> float:
    """두 화면의 밝고 어두운 배치 상관계수 (-1~1, 1이면 구도가 같다)."""
    x, y = _gray(a), _gray(b)
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sum((p - mx) * (q - my) for p, q in zip(x, y))
    sx = sum((p - mx) ** 2 for p in x) ** 0.5
    sy = sum((q - my) ** 2 for q in y) ** 0.5
    return round(sxy / (sx * sy), 3) if sx and sy else 0.0


def accent_mask(im: Image.Image) -> list[bool]:
    small = im.convert("RGB").resize(GRID, Image.Resampling.BOX)
    px = small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata()
    return [concept.dist(c, ACCENT) < 95 and c[0] > c[1] + 35 for c in px]


def accent_iou(a: Image.Image, b: Image.Image) -> tuple[float, float]:
    """강조색(빨강) 영역의 겹침과, 컨셉에서 강조색이 차지하는 비율."""
    ma, mb = accent_mask(a), accent_mask(b)
    inter = sum(p and q for p, q in zip(ma, mb)); union = sum(p or q for p, q in zip(ma, mb))
    return (round(inter / union, 3) if union else 1.0), round(sum(mb) / len(mb), 3)


def run_screen_qa(llm, paths: Paths, round_no: int = 1) -> dict:
    t0 = time.time()
    rep = QAReport("screens")
    spec = concept.load_regions()
    screens = spec.get("screens") or {}
    shots = paths.dist / "screens"
    base = concept.REGIONS.parent
    pairs = []
    if not rep.check("화면 캡처", shots.exists(), "output/dist/screens " + ("있음" if shots.exists() else "없음 (Publisher를 먼저 실행)"), "high"):
        return save(paths, rep, "화면 대조 QA 보고서 (Developer QA 2단계)", t0)
    for name, s in screens.items():
        shot = shots / f"{name}.png"
        cfile = base / spec["images"][s["concept"]]
        if not shot.exists() or not cfile.exists():
            rep.check(f"{name} 파일", False, f"없음: {shot.name if not shot.exists() else cfile.name}", "mid", name)
            continue
        a, b = Image.open(shot).convert("RGB"), Image.open(cfile).convert("RGB")
        corr = layout_corr(a, b)
        iou, share = accent_iou(a, b)
        pd = concept.palette_distance([c["hex"] for c in concept.dominant(b, 8)], [c["hex"] for c in concept.dominant(a, 8)])
        dl = round(abs(concept.luminance(a) - concept.luminance(b)), 1)
        rep.metrics[name] = f"컨셉 {s['concept']}: 구도 상관 {corr}, 강조색 겹침 {iou} (컨셉 강조색 {share:.0%}), 색 거리 {pd}, 밝기 차 {dl}"
        who = s.get("owner", "Developer")
        rep.check(f"{name} 구도", corr >= 0.3, f"밝고 어두운 배치 상관 {corr} (0.3 이상 목표)", "mid", name,
                  f"{who}: 컨셉 {s['concept']}의 요소 배치를 따른다 — " + "; ".join(s["elements"][:3]))
        if share >= 0.01:
            rep.check(f"{name} 강조색 위치", iou >= 0.25, f"빨간 요소 겹침 {iou} (0.25 이상 목표)", "mid", name,
                      f"{who}: 컨셉에서 빨간 요소(버튼·판정 판·D-일수)가 있는 자리에 같은 강조색 요소를 둔다")
        rep.check(f"{name} 색·밝기", pd <= 80 and dl <= 35, f"색 거리 {pd}, 밝기 차 {dl}", "low", name,
                  "Designer: 배경 이미지의 색과 밝기를 컨셉에 맞춘다")
        pairs.append((name, s, a, b))
    contact = _contact(pairs, paths)
    rep.metrics["대조표"] = str(contact)
    user = ("# 화면 대조 규칙 검사 결과\n" + json.dumps(rep.to_dict(), ensure_ascii=False, indent=1) +
            "\n\n# 화면별 컨셉 번호 요소\n" + "\n".join(
                f"## {n} (컨셉 {s['concept']})\n" + "\n".join("- " + e for e in s["elements"]) for n, s, _, _ in pairs) +
            "\n\n대조표 이미지는 줄마다 왼쪽이 컨셉, 오른쪽이 실제 게임 화면이다. 요소마다 있는지, 자리와 모양이 맞는지 보고, "
            "issues의 asset에는 '화면/요소 번호', fix 앞에는 고칠 쪽(Developer 또는 Designer)을 적어라.")
    ask_review(llm, paths, rep, "qa_screens", user, images=[str(contact)], round_no=round_no)
    return save(paths, rep, "화면 대조 QA 보고서 (Developer QA 2단계)", t0)


def _contact(pairs, paths: Paths) -> Path:
    W, H, pad = 640, 360, 10
    sheet = Image.new("RGB", (W * 2 + pad * 3, (H + pad + 14) * max(1, len(pairs)) + pad), (40, 42, 47))
    d = ImageDraw.Draw(sheet)
    y = pad
    for name, s, shot, con in pairs:
        d.text((pad, y), f"concept {s['concept']}", fill=(232, 230, 223))
        d.text((W + pad * 2, y), f"game {name}", fill=(232, 230, 223))
        sheet.paste(con.resize((W, H)), (pad, y + 14)); sheet.paste(shot.resize((W, H)), (W + pad * 2, y + 14))
        y += H + pad + 14
    out = paths.out / "qa_out" / "screens_contact.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    log.info("[화면 QA] 대조표: %s", out)
    return out
