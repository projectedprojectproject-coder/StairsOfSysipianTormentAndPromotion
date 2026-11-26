---
name: stairs-designer-qa
description: 승급의 계단 Designer QA 에이전트. Designer 결과물(스프라이트·이미지·사운드)이 에셋 계약, 03 팔레트, 2배 밀도, 컨셉 아트(data/concept)와 맞는지 규칙 검사와 Claude 시각 검토로 확인하고 고칠 점을 보고한다. 스프라이트나 배경을 만든 뒤 품질을 확인하거나 컨셉과 비교할 때 사용한다.
tools: Read, Grep, Glob, Bash
---

# Designer QA 에이전트

Designer 바로 뒤에 도는 품질 확인 에이전트입니다. 결과물을 고치지 않고, Designer가 고칠 수 있는 지시를 보고합니다.

## 입력과 출력

- 입력: `output/design_out/`(PNG, WAV, `design_manifest.json`), `docs/ASSET_LIST.md`, 03 팔레트, `data/concept/`
- 출력: `output/qa_out/designer_qa.md`·`designer_qa.json`(판정, 문제와 고칠 점), `designer_contact.png`(왼쪽 컨셉에서 뽑은 참고, 오른쪽 만든 프레임)

## 확인 방법

1. 규칙 검사(LLM 없음): 에셋 계약, 빈 프레임, 캐릭터·소품 배경 투명, 2배 밀도(프레임 크기 짝수, 이미지 640x360), 시트별 색 수(48 이하), 03 팔레트 근접도, 컨셉 대조(색 거리 90 이하, 실루엣 겹침 0.4 이상, title_bg·bg_zone1과 컨셉 화면의 색·밝기), 사운드 길이·클리핑.
2. Claude 검토: 규칙 결과와 대조표·컨셉 원본 이미지를 보내 실루엣, 읽힘, 팔레트, 애니메이션을 검토받습니다(`prompts/qa_designer.md`). 재생 모드에 `qa_designer_review.txt`가 없으면 건너뛰고 보고서에 적습니다.
3. 판정: 규칙 high → fail, mid 또는 Claude revise → revise, 그 밖 pass. `--strict-qa`면 fail일 때 Publisher 전에 멈춥니다.
4. 고침 반복: pass가 아니면 고칠 점(`qa.feedback_text`)을 Designer에게 돌려줘 다시 만들고 다시 확인하기를 최대 11번(`--qa-rounds`) 되풀이합니다. 나아지지 않으면 일찍 멈추고, 재생 모드는 1번만 확인합니다. 차례별 판정: `output/qa_out/designer_loop.json`

직접 검토할 때는 대조표를 Read로 보고, 컨셉 영역을 더 뽑아야 하면 스킬 `.claude/skills/concept-sprite-extraction/SKILL.md`를 따릅니다.

## 실행

```bash
python -m stairs_agents qa-designer --replay replay
python -m stairs_agents qa-designer --replay replay_api --out output_api
```

> 아래 지시문과 코드는 저장소의 원본 파일을 그대로 옮긴 사본입니다. 실제로 실행되는 것은 원본 파일이므로, 고칠 때는 원본을 고치고 이 문서도 함께 갱신합니다.

## Claude에 주는 지시문 (prompts/)

### `prompts/qa_designer.md`

```markdown
너는 게임 "승급의 계단"의 Designer QA 에이전트다. Designer가 만든 16비트 픽셀 스프라이트·배경·사운드가 기획서, 공통 에셋 목록, 컨셉 아트와 맞는지 검토하고, Designer가 바로 고칠 수 있는 지시를 돌려준다.

## 받는 것
- 규칙 검사 결과 JSON (코드로 잰 항목: 에셋 계약, 빈 프레임, 투명 배경, 2배 밀도, 색 수, 03 팔레트 근접도, 컨셉과의 색 거리·실루엣 겹침, 사운드 길이)
- 대조표 이미지: 각 줄 왼쪽은 컨셉 아트에서 뽑은 참고 스프라이트(concept.py), 오른쪽은 Designer가 만든 같은 동작의 프레임. 아래쪽은 시트마다 첫 변형 줄 미리보기
- 컨셉 원본 이미지 (05-1 타이틀, 05-3 플레이)

## 볼 것
1. 컨셉과 같은 게임으로 보이는가: 실루엣, 등신(4~5등신), 자세, 색 배치(정장 색, 넥타이, 올리브 계단), 명암 방향.
2. 읽히는가: 320x180 화면에서 절반 크기로 그렸을 때 위협 3종(서류, 결재판, 전화기)과 경쟁 사원이 서로, 그리고 배경과 구분되는가. 예고 "!"가 눈에 띄는가.
3. 03 팔레트(#5A5F66, #8A9A5B, #A13D3D, #1E1F22, #E8E6DF)와 그 명암 중간색 위주인가.
4. 애니메이션: 프레임끼리 자세가 바뀌고 떨림이나 위치 튐이 없는가. 표정은 그리지 않고 자세로 상태를 보여 주는가.
5. 규칙 검사에서 문제로 나온 항목이 실제로 문제인지(예: 일부러 꽉 채운 타일) 판단해 설명한다.

## 하지 말 것
- 기획서와 컨셉에 없는 새 에셋이나 기능을 요구하지 않는다.
- 취향만으로 high를 주지 않는다. high는 게임에서 잘못 읽히거나 계약이 깨지는 경우에만 쓴다.

## 출력 형식
<json> 와 </json> 사이에 아래 JSON만 넣는다.
{
  "verdict": "pass" 또는 "revise",
  "summary": "두세 문장 총평",
  "issues": [
    { "asset": "에셋 ID (예: player/idle)", "severity": "high" | "mid" | "low",
      "problem": "무엇이 어떻게 다른가", "fix": "Designer 명세에서 바꿀 것 (색 기호, 줄, 프레임 단위로 구체적으로)" }
  ]
}
```

## 에이전트 코드 (stairs_agents/)

### `stairs_agents/qa_designer.py`

```python
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

    def run(self, round_no: int = 1) -> dict:
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
            n = _colors(sh); lim = 48 if man.get("pixel_scale", PIXEL_SCALE) <= 2 else 1024   # 32비트(4배 밀도) 판은 부드러운 명암 단계가 많다
            rep.check(f"{aid} 색 수", n <= lim, f"{n}색", "low", aid, "명암 단계를 줄여 16비트 느낌을 지킨다" if lim == 48 else "명암 단계를 줄인다")

        # ---- 이미지
        sizes = {}
        ps = man.get("pixel_scale", PIXEL_SCALE)   # 밀도: 매니페스트에 적힌 값 (32비트 판은 4)
        for aid, m in man["images"].items():
            im = Image.open(out / m["file"]).convert("RGB")
            sizes[aid] = im.size
            if aid != "logo" and not m.get("density"):   # 컷신 배경(density 적힘)은 크기가 장면마다 다르다
                ok = im.size == (LOGICAL[0] * ps, LOGICAL[1] * ps)
                rep.check(f"{aid} 크기", ok, f"{im.size[0]}x{im.size[1]}", "mid", aid,
                          f"{LOGICAL[0] * ps}x{LOGICAL[1] * ps}로 그린다")
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
        ask_review(self.llm, p, rep, self.name, user, images=[str(i) for i in imgs if Path(i).exists()], round_no=round_no)
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
```

### `stairs_agents/qa.py`

```python
"""품질 확인(QA) 에이전트 공통 부분: 문제 기록, Claude 검토 요청, 보고서 쓰기.

QA 에이전트는 두 단계로 확인한다.
1. 규칙 검사: 코드로 재는 항목 (LLM 없이 항상 돈다)
2. Claude 검토: 규칙 검사 결과와 결과물(이미지 또는 코드)을 Claude에 보내 기획서·컨셉과 맞는지 묻는다.
   재생 모드에서 응답 파일(replay/qa_<대상>_review.txt)이 없으면 이 단계는 건너뛰고 그 사실을 보고서에 적는다.

판정: 규칙 검사에 high 문제가 하나라도 있으면 fail, high는 없고 mid가 있거나 Claude가 revise라고 하면 revise, 아니면 pass.

고침 반복 (qa_loop): 판정이 pass가 아니면 QA의 고칠 점을 만든 에이전트에게 돌려줘 다시 만들게 하고 다시 확인한다.
최대 MAX_ROUNDS(11)번까지 돌고, 통과하거나, 문제 목록이 앞 차례와 같아 나아지지 않거나,
재생 모드처럼 다시 만들어도 같은 응답이 나오는 경우에는 일찍 멈춘다. 차례마다의 판정은 qa_out/<대상>_loop.json에 남는다.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .llm import LLMError
from .util import Paths, extract_json, load_prompt, log, write_json

SEVERITIES = ("high", "mid", "low")
MAX_ROUNDS = 11


@dataclass
class QAReport:
    target: str                          # "designer" 또는 "developer"
    checks: list = field(default_factory=list)   # {"id","ok","detail"}
    issues: list = field(default_factory=list)   # {"source","asset","severity","problem","fix"}
    metrics: dict = field(default_factory=dict)
    review: dict | None = None
    review_note: str = ""

    def check(self, cid: str, ok: bool, detail: str = "", severity: str = "mid", asset: str = "", fix: str = ""):
        self.checks.append({"id": cid, "ok": bool(ok), "detail": detail})
        if not ok:
            self.issues.append({"source": "규칙", "asset": asset or cid, "severity": severity,
                                "problem": detail or cid, "fix": fix})
        return ok

    @property
    def verdict(self) -> str:
        rule = [i for i in self.issues if i["source"] == "규칙"]
        if any(i["severity"] == "high" for i in rule):
            return "fail"
        if any(i["severity"] == "high" for i in self.issues if i["source"] == "Claude"):
            return "revise"
        if any(i["severity"] == "mid" for i in self.issues) or (self.review or {}).get("verdict") == "revise":
            return "revise"
        return "pass"

    def to_dict(self) -> dict:
        return {"target": self.target, "verdict": self.verdict, "checks": self.checks, "issues": self.issues,
                "metrics": self.metrics, "review": self.review, "review_note": self.review_note}

    def markdown(self, title: str) -> str:
        ok = sum(c["ok"] for c in self.checks)
        lines = [f"# {title}", "", f"판정: **{self.verdict}** · 규칙 검사 {ok}/{len(self.checks)} 통과", ""]
        if self.review_note:
            lines += [f"Claude 검토: {self.review_note}", ""]
        elif self.review:
            lines += ["Claude 검토 요약: " + str(self.review.get("summary", "")), ""]
        lines += ["## 문제와 고칠 점", ""]
        if not self.issues:
            lines.append("없음")
        else:
            lines += ["| 심각도 | 출처 | 대상 | 문제 | 고칠 점 |", "|---|---|---|---|---|"]
            order = {s: i for i, s in enumerate(SEVERITIES)}
            for i in sorted(self.issues, key=lambda x: order.get(x["severity"], 9)):
                cells = [i["severity"], i["source"], i["asset"], i["problem"], i.get("fix", "")]
                lines.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in cells) + " |")
        lines += ["", "## 규칙 검사", "", "| 항목 | 결과 | 내용 |", "|---|---|---|"]
        for c in self.checks:
            lines.append(f"| {c['id']} | {'통과' if c['ok'] else '문제'} | {c['detail']} |")
        if self.metrics:
            lines += ["", "## 수치", ""]
            for k, v in self.metrics.items():
                lines.append(f"- {k}: {v}")
        return "\n".join(lines) + "\n"


def ask_review(llm, paths: Paths, report: QAReport, agent: str, user: str, images=None, round_no: int = 1) -> None:
    """Claude에 검토를 요청하고 응답의 issues를 report에 더한다. 응답이 없으면 건너뛴 이유를 적는다."""
    if llm is None:
        report.review_note = "건너뜀 (LLM 없이 실행)"
        return
    try:
        text = llm.complete(agent, "review" + (f"_r{round_no}" if round_no > 1 else ""), load_prompt(paths, agent), user, images=images)
    except LLMError as e:
        report.review_note = f"건너뜀 ({e})"
        log.info("[%s] Claude 검토 건너뜀: %s", agent, e)
        return
    try:
        rv = extract_json(text)
    except ValueError as e:
        report.review_note = f"응답을 읽지 못함 ({e})"
        return
    report.review = rv
    for i in rv.get("issues", []):
        sev = i.get("severity", "low")
        report.issues.append({"source": "Claude", "asset": i.get("asset", ""),
                              "severity": sev if sev in SEVERITIES else "low",
                              "problem": i.get("problem", ""), "fix": i.get("fix", "")})


def save(paths: Paths, report: QAReport, title: str, t0: float) -> dict:
    out = paths.out / "qa_out"
    out.mkdir(parents=True, exist_ok=True)
    d = report.to_dict()
    write_json(out / f"{report.target}_qa.json", d)
    (out / f"{report.target}_qa.md").write_text(report.markdown(title), encoding="utf-8")
    high = sum(i["severity"] == "high" for i in report.issues)
    log.info("[%s QA] 판정 %s: 문제 %d개 (high %d), 규칙 %d/%d 통과 (%.1f초)", report.target.capitalize(), report.verdict,
             len(report.issues), high, sum(c["ok"] for c in report.checks), len(report.checks), time.time() - t0)
    return d


def feedback_text(report: dict, round_no: int) -> str:
    """QA 보고를 만든 에이전트에게 돌려줄 고칠 점 문구."""
    order = {s: i for i, s in enumerate(SEVERITIES)}
    issues = sorted(report.get("issues", []), key=lambda i: order.get(i["severity"], 9))
    lines = [f"# {report['target']} QA가 돌려준 고칠 점 ({round_no}번째 만들기, 앞 차례 판정 {report['verdict']})",
             "아래 문제를 고쳐 같은 출력 형식으로 다시 내라. 문제가 없는 부분은 그대로 둔다."]
    lines += [f"- [{i['severity']}] {i['asset']}: {i['problem']}" + (f" -> {i['fix']}" if i.get("fix") else "") for i in issues]
    return "\n".join(lines)


def _signature(report: dict) -> tuple:
    return tuple(sorted((i["severity"], i["asset"], i["problem"]) for i in report.get("issues", [])))


def qa_loop(paths: Paths, target: str, produce, check, rounds: int = MAX_ROUNDS, can_retry: bool = True):
    """produce(feedback, round_no)로 만들고 check(round_no)로 확인하기를 판정이 pass가 될 때까지 최대 rounds(<=11)번 되풀이한다.
    (첫 차례의 produce는 feedback=None으로 부른다.) 마지막 결과와 QA 보고를 돌려준다."""
    rounds = max(1, min(MAX_ROUNDS, rounds))
    result = produce(None, 1)
    rep = check(1)
    history, stop = [{"round": 1, "verdict": rep["verdict"], "issues": len(rep["issues"])}], "최대 차례"
    for n in range(2, rounds + 1):
        if rep["verdict"] == "pass":
            stop = "통과"; break
        if not can_retry:
            stop = "다시 만들 수 없음 (재생 모드는 같은 응답을 돌려준다)"; break
        prev = _signature(rep)
        log.info("[%s QA] %d번째 고침: 문제 %d개를 돌려준다", target.capitalize(), n, len(rep["issues"]))
        result = produce(feedback_text(rep, n), n)
        rep = check(n)
        history.append({"round": n, "verdict": rep["verdict"], "issues": len(rep["issues"])})
        if _signature(rep) == prev and rep["verdict"] != "pass":
            stop = "나아지지 않음 (앞 차례와 같은 문제)"; break
    else:
        if rep["verdict"] == "pass":
            stop = "통과"
    rep["loop"] = {"rounds": len(history), "max": rounds, "stop": stop, "history": history}
    write_json(paths.out / "qa_out" / f"{target}_loop.json", rep["loop"])
    log.info("[%s QA] 고침 반복 %d/%d번에서 멈춤: %s (판정 %s)", target.capitalize(), len(history), rounds, stop, rep["verdict"])
    return result, rep
```

### `stairs_agents/concept.py`

```python
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
```
