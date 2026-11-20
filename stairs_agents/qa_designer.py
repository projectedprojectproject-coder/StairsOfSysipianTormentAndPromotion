"""Designer QA 에이전트.

역할: Designer 결과물(output/design_out)이 에셋 계약, 03 팔레트, 2배 밀도 규칙, 컨셉 아트(data/concept)와 맞는지 확인하고
      고칠 점을 Designer에게 돌려줄 수 있는 형태로 정리한다.
입력: output/design_out/ (PNG, WAV, design_manifest.json), docs/ASSET_LIST.md, docs/GDD.md 03 팔레트,
      data/concept/regions.json (concept.py로 참고 스프라이트를 뽑아 비교)
출력: output/qa_out/designer_qa.json, designer_qa.md, designer_contact.png (컨셉 참고 | 만든 프레임 대조표)
"""
from __future__ import annotations

import json
import time
import wave
from pathlib import Path

from PIL import Image, ImageDraw

from . import concept
from .contract import check_manifest, load_contract
from .qa import QAReport, ask_review, save
from .util import Paths, log

GDD_PALETTE = ["#5A5F66", "#8A9A5B", "#A13D3D", "#1E1F22", "#E8E6DF"]
PIXEL_SCALE = 2
LOGICAL = (320, 180)
CUTOUT_SHEETS = {"player", "rival", "projectiles", "warning", "props", "hud_icons"}
# 이미지와 비교할 컨셉 화면
IMAGE_CONCEPT = {"title_bg": "05-1_title", "bg_zone1": "05-3_play"}


def _frame(sheet: Image.Image, m: dict, anim: str, variant: str | None, i: int = 0) -> Image.Image:
    fw, fh = m["frame_w"], m["frame_h"]
    row = m["variants"].get(variant, 0) if variant else 0
    col = m["animations"][anim]["frames"][i]
    return sheet.crop((col * fw, row * fh, col * fw + fw, row * fh + fh))


def _alpha_share(im: Image.Image) -> float:
    a = im.getchannel("A")
    data = a.get_flattened_data() if hasattr(a, "get_flattened_data") else a.getdata()
    return sum(1 for v in data if v >= 128) / (im.width * im.height)


def _colors(im: Image.Image) -> int:
    c = im.convert("RGBA").getcolors(1 << 16)
    return len([x for x in c if x[1][3] >= 128]) if c else 99999


class DesignerQAAgent:
    name = "qa_designer"

    def __init__(self, llm, paths: Paths):
        self.llm = llm
        self.paths = paths

    def run(self) -> dict:
        t0 = time.time()
        p = self.paths
        out = p.design_out
        rep = QAReport("designer")
        man_path = out / "design_manifest.json"
        if not rep.check("매니페스트", man_path.exists(),
                         "design_manifest.json " + ("있음" if man_path.exists() else "없음"), "high",
                         fix="Designer를 먼저 실행한다"):
            return save(p, rep, "Designer QA 보고서", t0)
        man = json.loads(man_path.read_text(encoding="utf-8"))
        contract = load_contract(p.docs / "ASSET_LIST.md")
        probs = check_manifest(contract, man)
        rep.check("에셋 계약", not probs, "; ".join(probs) or "ASSET_LIST의 ID·변형·애니메이션 모두 있음", "high",
                  fix="빠진 변형·애니메이션을 같은 이름으로 추가한다")

        sheets = {aid: Image.open(out / m["file"]).convert("RGBA") for aid, m in man["sprites"].items()}
        # ---- 스프라이트 시트
        for aid, m in man["sprites"].items():
            sh, fw, fh = sheets[aid], m["frame_w"], m["frame_h"]
            rep.check(f"{aid} 2배 밀도", fw % PIXEL_SCALE == 0 and fh % PIXEL_SCALE == 0,
                      f"프레임 {fw}x{fh}", "mid", aid, f"프레임 크기를 {PIXEL_SCALE}의 배수로 한다")
            empty = []
            for v, row in m["variants"].items():
                for anim, a in m["animations"].items():
                    for k, col in enumerate(a["frames"]):
                        if _alpha_share(sh.crop((col * fw, row * fh, col * fw + fw, row * fh + fh))) == 0:
                            empty.append(f"{v}/{anim}#{k}")
            rep.check(f"{aid} 빈 프레임", not empty, ", ".join(empty[:8]) or "없음", "high", aid,
                      "빈 프레임에 그림을 채운다")
            if aid in CUTOUT_SHEETS:
                share = max(_alpha_share(_frame(sh, m, an, None)) for an in m["animations"])
                rep.check(f"{aid} 배경 투명", share < 0.92, f"가장 꽉 찬 프레임 불투명 {share:.0%}", "mid", aid,
                          "캐릭터·소품 주위를 '.'(투명)으로 비운다")
            n = _colors(sh)
            rep.check(f"{aid} 색 수", n <= 48, f"{n}색", "low", aid, "명암 단계를 줄여 16비트 느낌을 지킨다")

        # ---- 이미지
        sizes = {}
        for aid, m in man["images"].items():
            im = Image.open(out / m["file"]).convert("RGB")
            sizes[aid] = im.size
            if aid != "logo":
                ok = im.size == (LOGICAL[0] * PIXEL_SCALE, LOGICAL[1] * PIXEL_SCALE)
                rep.check(f"{aid} 크기", ok, f"{im.size[0]}x{im.size[1]}", "mid", aid,
                          f"{LOGICAL[0] * PIXEL_SCALE}x{LOGICAL[1] * PIXEL_SCALE}로 그린다")
            lo, hi = im.convert("L").getextrema()
            rep.check(f"{aid} 내용", hi - lo > 20, f"밝기 범위 {lo}~{hi}", "high", aid, "비어 있는 이미지를 다시 그린다")

        # ---- 03 팔레트 근접도 (명암 중간색을 허용해 거리 110 안이면 근접으로 본다)
        gdd = [concept.rgb(h) for h in GDD_PALETTE]
        near = []
        for aid, sh in sheets.items():
            cols = sh.getcolors(1 << 16) or []
            tot = sum(n for n, c in cols if c[3] >= 128) or 1
            ok = sum(n for n, c in cols if c[3] >= 128 and min(concept.dist(c, g) for g in gdd) <= 110)
            near.append((aid, ok / tot))
        rep.metrics["03 팔레트 근접도"] = ", ".join(f"{a} {v:.0%}" for a, v in near)
        low = [a for a, v in near if v < 0.5]
        rep.check("03 팔레트 근접", not low, "근접도 50% 미만: " + (", ".join(low) or "없음"), "low",
                  ", ".join(low), "03 팔레트 색과 그 명암 단계 위주로 다시 칠한다")

        # ---- 컨셉 대조
        refs = concept.extract_regions(p.out / "concept_refs")
        pairs = []
        if not refs:
            rep.check("컨셉 참고", True, "data/concept/regions.json 없음 (컨셉 대조 생략)", "low")
        for rid, r in (refs.get("regions") or {}).items():
            aid, anim = r.get("sheet"), r.get("anim")
            if not aid or aid not in man["sprites"] or anim not in man["sprites"][aid]["animations"]:
                continue
            ours = _frame(sheets[aid], man["sprites"][aid], anim, r.get("variant"))
            ref = Image.open(p.out / "concept_refs" / r["file"]).convert("RGBA")
            pd = concept.palette_distance([c["hex"] for c in concept.dominant(ref, 6)],
                                          [c["hex"] for c in concept.dominant(ours, 6)])
            iou = concept.silhouette_iou(ref, ours)
            rep.metrics[f"컨셉 {rid}"] = f"색 거리 {pd}, 실루엣 겹침 {iou}"
            rep.check(f"컨셉 색 {rid}", pd <= 90, f"{aid}/{anim} 색 거리 {pd} (90 이하 목표)", "mid", aid,
                      f"컨셉 {r.get('note')}의 색(참고: output/concept_refs/{r['file']})에 맞춘다")
            rep.check(f"컨셉 실루엣 {rid}", iou >= 0.4, f"{aid}/{anim} 겹침 {iou} (0.4 이상 목표)", "low", aid,
                      "컨셉 참고 격자의 비율과 자세를 따른다")
            pairs.append((rid, ref, ours))
        for aid, cname in IMAGE_CONCEPT.items():
            if aid not in man["images"] or cname not in (refs.get("images") or {}):
                continue
            ours = Image.open(out / man["images"][aid]["file"]).convert("RGB")
            cimg = refs["images"][cname]
            pd = concept.palette_distance([c["hex"] for c in cimg["palette"][:8]],
                                          [c["hex"] for c in concept.dominant(ours, 8)])
            dl = round(abs(concept.luminance(ours) - cimg["luminance"]), 1)
            rep.metrics[f"컨셉 {aid}"] = f"색 거리 {pd}, 평균 밝기 차 {dl}"
            rep.check(f"컨셉 화면 {aid}", pd <= 80 and dl <= 30, f"{cname}와 색 거리 {pd}, 밝기 차 {dl}", "mid", aid,
                      f"컨셉 {cname}의 주요 색과 밝기에 맞춘다")

        # ---- 사운드
        for aid, m in man["sounds"].items():
            try:
                with wave.open(str(out / m["file"])) as w:
                    dur = w.getnframes() / w.getframerate()
                    raw = w.readframes(w.getnframes())
                    width = w.getsampwidth()
            except (wave.Error, FileNotFoundError) as e:
                rep.check(f"{aid} 소리", False, f"읽지 못함: {e}", "high", aid); continue
            ok = dur >= (2.0 if contract["sounds"].get(aid) else 0.02)
            peak = 0
            if width == 2:
                import array
                arr = array.array("h", raw)
                peak = max((abs(v) for v in arr), default=0) / 32767
            rep.check(f"{aid} 소리", ok and peak < 0.999, f"{dur:.2f}초, 최대 {peak:.0%}", "low", aid,
                      "반복 음악은 2초 이상, 효과음은 0.02초 이상, 소리가 잘리지 않게 음량을 낮춘다")

        contact = self._contact(pairs, sheets, man, out)
        rep.metrics["대조표"] = str(contact.relative_to(p.root)) if contact.is_relative_to(p.root) else str(contact)
        imgs = [contact] + [p.data / "concept" / v for v in (concept.load_regions().get("images") or {}).values()]
        user = ("# Designer 규칙 검사 결과\n" + json.dumps(rep.to_dict(), ensure_ascii=False, indent=1) +
                "\n\n첫 이미지는 대조표(왼쪽 컨셉에서 뽑은 참고, 오른쪽 Designer 프레임)와 시트 미리보기다. "
                "나머지는 컨셉 원본이다. 위 출력 형식으로 검토하라.")
        ask_review(self.llm, p, rep, self.name, user, images=[str(i) for i in imgs if Path(i).exists()])
        return save(p, rep, "Designer QA 보고서", t0)

    def _contact(self, pairs, sheets, man, out) -> Path:
        """컨셉 참고와 만든 프레임을 나란히 놓은 대조표 + 각 시트 첫 줄 미리보기."""
        Z, pad = 4, 8
        rows = []
        for rid, ref, ours in pairs:
            a = ref.resize((ref.width * Z, ref.height * Z), Image.Resampling.NEAREST)
            b = ours.resize((ours.width * Z, ours.height * Z), Image.Resampling.NEAREST)
            rows.append((rid, a, b))
        strips = []
        for aid, m in man["sprites"].items():
            s = sheets[aid].crop((0, 0, sheets[aid].width, m["frame_h"]))
            z = 2 if s.width * 2 <= 1400 else 1
            strips.append((aid, s.resize((s.width * z, s.height * z), Image.Resampling.NEAREST)))
        W = max([pad * 3 + a.width + b.width + 120 for _, a, b in rows] + [s.width + pad * 2 + 120 for _, s in strips] + [400])
        H = sum(max(a.height, b.height) + pad for _, a, b in rows) + sum(s.height + pad for _, s in strips) + pad * 2
        sheet = Image.new("RGBA", (W, H), (46, 48, 54, 255))
        d = ImageDraw.Draw(sheet)
        y = pad
        for rid, a, b in rows:
            d.text((pad, y), rid, fill=(232, 230, 223))
            sheet.alpha_composite(a, (pad + 110, y)); sheet.alpha_composite(b, (pad * 2 + 110 + a.width, y))
            y += max(a.height, b.height) + pad
        for aid, s in strips:
            d.text((pad, y), aid, fill=(232, 230, 223))
            sheet.alpha_composite(s, (pad + 110, y)); y += s.height + pad
        path = self.paths.out / "qa_out" / "designer_contact.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(path)
        log.info("[Designer QA] 대조표: %s", path)
        return path
