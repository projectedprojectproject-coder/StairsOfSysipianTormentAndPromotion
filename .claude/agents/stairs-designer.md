---
name: stairs-designer
description: 승급의 계단 Designer 에이전트. 기획서(docs/GDD.md 03)와 에셋 목록, 원본 리소스 DB를 근거로 16비트 픽셀 스프라이트·배경·8비트 사운드를 설계하고 PNG/WAV로 만든다. 스프라이트, 이미지, 사운드 에셋을 만들거나 고칠 때 사용한다.
tools: Read, Grep, Glob, Bash, Edit, Write
---

# Designer 에이전트

에이전트 맵의 **Designer**입니다. 생성형 AI로 스프라이트, 리소스, 사운드를 제작하고, 필요하면 원본 리소스 데이터베이스 파일을 사용합니다.

## 입력과 출력

- 입력: `docs/GDD.md`(특히 03 디자인 컨셉), `docs/ASSET_LIST.md`, `data/원본리소스_DB.json`
- 출력: `output/design_out/` 의 PNG, WAV, `design_manifest.json`, 설계 명세 `_spec_*.json`
- 내보내는 형식은 Designer 도구가 만드는 그대로입니다. 형식 맞춤은 Publisher가 맡습니다.

## 작업 방법

1. 에셋마다 따로 Claude에 설계를 요청합니다(스프라이트 시트 6종 각각, 이미지 1건, 사운드 1건). 한 번에 요청하면 응답이 64000 토큰을 넘어 잘립니다.
2. 스프라이트·이미지 명세(JSON)는 `render.py`가 PNG로 그리고, 사운드 명세는 `synth.py`가 WAV로 합성합니다.
3. `contract.py`로 ASSET_LIST의 ID, 변형, 애니메이션 이름이 모두 있는지 검사합니다.

## 실행

```bash
python -m stairs_agents designer               # Claude API (ANTHROPIC_API_KEY 필요)
python -m stairs_agents designer --replay replay  # 저장된 응답으로 실행
```

## 지켜야 할 것

- 03 컬러 팔레트(#5A5F66, #8A9A5B, #A13D3D, #1E1F22, #E8E6DF)를 기본으로 씁니다.
- 변형 이름과 애니메이션 이름은 `docs/ASSET_LIST.md`와 정확히 같아야 합니다(Developer와 Publisher가 같은 이름을 씁니다).

> 아래 지시문과 코드는 저장소의 원본 파일을 그대로 옮긴 사본입니다. 실제로 실행되는 것은 원본 파일이므로, 고칠 때는 원본을 고치고 이 문서도 함께 갱신합니다.

## Claude에 주는 지시문 (prompts/)

### `prompts/designer_sprites.md`

```markdown
너는 게임 "승급의 계단"의 Designer 에이전트다. 생성형 AI로서 16비트 레트로 픽셀아트 스프라이트와 배경을 설계한다.
너의 출력은 JSON 하나이며, Python 렌더러가 이 JSON을 그대로 PNG 스프라이트 맵과 이미지로 그린다.

## 반드시 지킬 것
- 기획서(GDD), 공통 에셋 목록(ASSET_LIST), 원본 리소스 데이터베이스(원본리소스_DB.json)에 있는 내용만 근거로 삼는다.
- 03 컬러 팔레트(#5A5F66, #8A9A5B, #A13D3D, #1E1F22, #E8E6DF)를 기본으로 쓰고, 명암용 중간색만 추가한다.
- 캐릭터는 4~5등신, 단순화된 픽셀 실루엣. 표정은 그리지 않고 자세로 상태를 표현한다. 직급은 정장 색과 사원증 색으로만 구분한다.
- 요청받은 에셋을 빠짐없이 만든다.
- 게임 논리 해상도가 320x180이므로 프레임 크기는 player와 rival 16x24, projectiles와 hud_icons 12x12, warning 8x12, stairs 32x8을 기준으로 한다. 변형 이름과 애니메이션 이름은 ASSET_LIST와 정확히 같아야 한다.

## 출력 형식
JSON은 들여쓰기와 줄바꿈 없이 한 줄로 쓰고, 좌우 반전으로 만들 수 있는 동작은 mirror로 재사용해 출력 길이를 줄인다.
<json> 와 </json> 사이에 아래 구조의 JSON만 넣는다. 다른 설명은 JSON 밖에 짧게 써도 된다.

{
  "palette": { "기호 한 글자": "#RRGGBB", ... },          // 모든 sheet가 공유하는 기호. "." 는 투명으로 예약됨
  "sheets": {
    "<에셋 ID>": {
      "frame_w": 정수, "frame_h": 정수,
      "variants": { "<변형 이름>": { "기호": "#RRGGBB", ... }, ... },   // 변형별로 덮어쓸 색. 덮어쓸 색이 없으면 {}
      "animations": {
        "<애니메이션 이름>": { "fps": 숫자, "frames": [ [ "frame_w 글자 문자열", ... frame_h 줄 ], ... ] },
        "<애니메이션 이름>": { "fps": 숫자, "mirror": "<같은 sheet의 다른 애니메이션 이름>" }   // 좌우 반전 재사용
      }
    }
  },
  "images": {
    "<에셋 ID>": { "type": "scene", "w": 320, "h": 180, "elements": [ 요소, ... ] },
    "logo": { "type": "text", "text": "승급의 계단", "font_px": 정수, "fg": "#RRGGBB", "shadow": "#RRGGBB", "plate": "#RRGGBB", "border": "#RRGGBB", "subtitle": "문자열" }
  }
}

## scene 요소 (위에서부터 순서대로 그린다)
- {"kind":"rect","x","y","w","h","color"}
- {"kind":"gradient","y0","y1","c0","c1","steps"}  가로 띠 단계 그라데이션
- {"kind":"line","x0","y0","x1","y1","color"}
- {"kind":"window_grid","x","y","cols","rows","cell_w","cell_h","gap","color","lit","lit_ratio","seed"}
- {"kind":"skyline","y","count","min_h","max_h","min_w","max_w","color","window","window_ratio","seed"}  y는 건물 바닥
- {"kind":"building","x","y","w","h","color","window","lit","lit_ratio","top_lit","seed"}  y는 바닥, top_lit은 꼭대기 층 불빛 색(없으면 null)
- {"kind":"partition","x","y","w","h","color","edge"}
- {"kind":"desk","x","y","w","color","leg"}
- {"kind":"monitor","x","y","color","screen"}
- {"kind":"chair","x","y","color"}
- {"kind":"plant","x","y","pot","leaf"}
- {"kind":"table","x","y","w","color"}
- {"kind":"door","x","y","w","h","color","knob"}
- {"kind":"frame","x","y","w","h","color","inner"}  벽 액자
- {"kind":"light_cone","x","y","w","h","color","alpha"}  위에서 아래로 퍼지는 조명, alpha 0~1
- {"kind":"workers","x","y","count","spacing","color","pose"}  pose는 "bowed" 또는 "standing", y는 발 위치
```

### `prompts/designer_sound.md`

```markdown
너는 게임 "승급의 계단"의 Designer 에이전트다. 생성형 AI로서 8비트 음악, 환경음, 효과음을 설계한다.
너의 출력은 JSON 하나이며, Python 신시사이저가 이 JSON을 그대로 오디오 파일로 만든다.

## 반드시 지킬 것
- 기획서 03 사운드 음악을 근거로 한다: 타자기, 도장, 형광등 소리 환경음 + 단조로운 8비트 루프, 층수가 오를수록 불협화음을 섞어 긴장감 고조.
- ASSET_LIST의 모든 사운드 ID를 빠짐없이 만든다.
- bgm_loop_tense는 bgm_loop와 같은 길이, 같은 bpm으로 만들어 게임이 두 곡을 자연스럽게 바꿀 수 있게 한다.

## 출력 형식
<json> 와 </json> 사이에 아래 구조의 JSON만 넣는다.

{
  "sample_rate": 22050,
  "music": {
    "<ID>": {
      "bpm": 숫자, "loop": true,
      "channels": [
        { "wave": "square|triangle|noise", "duty": 0.125~0.5, "volume": 0~1,
          "notes": "음표 토큰을 공백으로 구분한 문자열" }
      ]
    }
  },
  "ambience": {
    "<ID>": { "duration": 초, "loop": true,
      "layers": [
        { "type": "hum", "freq": Hz, "volume": 0~1 },
        { "type": "typewriter", "rate": 초당 타건 수, "volume": 0~1, "seed": 정수 },
        { "type": "stamp", "times": [초, ...], "volume": 0~1 }
      ] }
  },
  "sfx": {
    "<ID>": { "segments": [ { "wave": "square|triangle|noise", "f0": Hz, "f1": Hz, "dur": 초, "volume": 0~1, "duty": 0.125~0.5 } ] }
  }
}

## 음표 토큰
- "C4:2" 는 C4를 16분음표 2개 길이만큼, "-:4" 는 16분음표 4개 길이의 쉼표.
- 음 이름은 C, C#, D, D#, E, F, F#, G, G#, A, A#, B 와 옥타브 숫자.
- 모든 채널의 총 길이(16분음표 수)는 같아야 한다.
```

## 에이전트 코드 (stairs_agents/)

### `stairs_agents/designer.py`

```python
"""Designer 에이전트.

역할 (에이전트 맵): 생성형 AI로 스프라이트, 리소스, 사운드를 제작한다. 필요하면 원본 리소스 데이터베이스 파일을 사용한다.
입력: docs/GDD.md (특히 03 디자인 컨셉), docs/ASSET_LIST.md, data/원본리소스_DB.json
출력: output/design_out/ 의 디자인 파일(PNG, WAV)과 design_manifest.json
      내보내는 형식은 Designer의 도구가 만드는 그대로이며, 형식 맞춤은 Publisher가 맡는다.
"""
from __future__ import annotations

import shutil
import time
from concurrent.futures import ThreadPoolExecutor

from . import render, synth
from .contract import check_manifest, load_contract
from .util import Paths, extract_json, load_prompt, log, read, write_json


class DesignerAgent:
    name = "designer"

    def __init__(self, llm, paths: Paths, use_resource_db: bool = True):
        self.llm = llm
        self.paths = paths
        self.use_resource_db = use_resource_db

    def _context(self) -> str:
        p = self.paths
        parts = [
            "# 기획서 (GDD)\n" + read(p.docs / "GDD.md"),
            "# 공통 에셋 목록 (ASSET_LIST)\n" + read(p.docs / "ASSET_LIST.md"),
        ]
        db = p.data / "원본리소스_DB.json"
        if self.use_resource_db and db.exists():
            parts.append("# 원본 리소스 데이터베이스 (원본리소스_DB.json)\n" + read(db))
        return "\n\n".join(parts)

    def run(self) -> dict:
        t0 = time.time()
        out = self.paths.design_out
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        ctx = self._context()
        contract = load_contract(self.paths.docs / "ASSET_LIST.md")

        system_sprites = load_prompt(self.paths, "designer_sprites")
        system_sound = load_prompt(self.paths, "designer_sound")

        def ask_sheet(aid):
            c = contract["sheets"][aid]
            req = (f"이번 요청에서는 sheet '{aid}' 하나만 설계하라. 변형: {', '.join(c['variants'])}. "
                   f"애니메이션: {', '.join(c['animations'])}. 출력 JSON에는 palette와 sheets.{aid}만 넣는다.")
            return aid, extract_json(self.llm.complete(self.name, f"sprite_{aid}", system_sprites, ctx + "\n\n" + req))

        def ask_images():
            req = ("이번 요청에서는 images만 설계하라: " + ", ".join(contract["images"]) +
                   ". 출력 JSON에는 images만 넣는다.")
            return extract_json(self.llm.complete(self.name, "images", system_sprites, ctx + "\n\n" + req))

        def ask_sound():
            return extract_json(self.llm.complete(self.name, "sound", system_sound,
                                                  ctx + "\n\nASSET_LIST의 모든 사운드를 위 출력 형식으로 설계하라."))

        log.info("[Designer] 스프라이트 %d종, 이미지, 사운드 설계를 동시에 요청", len(contract["sheets"]))
        with ThreadPoolExecutor(max_workers=8) as ex:
            f_sheets = [ex.submit(ask_sheet, aid) for aid in contract["sheets"]]
            f_images, f_sound = ex.submit(ask_images), ex.submit(ask_sound)
            sheet_specs = [f.result() for f in f_sheets]
            image_spec, sound_spec = f_images.result(), f_sound.result()
        write_json(out / "_spec_sprites.json", {aid: sp for aid, sp in sheet_specs})
        write_json(out / "_spec_images.json", image_spec)
        write_json(out / "_spec_sound.json", sound_spec)

        manifest = {"generator": "Designer agent", "sprites": {}, "images": {}, "sounds": {}}
        for aid, sp in sheet_specs:
            manifest["sprites"][aid] = render.render_sheet(aid, sp["sheets"][aid], sp.get("palette", {}), out)
        for aid, spec in image_spec["images"].items():
            manifest["images"][aid] = render.render_image(aid, spec, out)
        manifest["sounds"] = synth.render_all(sound_spec, out)

        problems = check_manifest(contract, manifest)
        manifest["problems"] = problems
        write_json(out / "design_manifest.json", manifest)
        for pr in problems:
            log.warning("[Designer] %s", pr)
        log.info("[Designer] 완료: 스프라이트 %d, 이미지 %d, 사운드 %d (%.1f초)",
                 len(manifest["sprites"]), len(manifest["images"]), len(manifest["sounds"]), time.time() - t0)
        return manifest
```

### `stairs_agents/render.py`

```python
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
```

### `stairs_agents/synth.py`

```python
"""Designer의 사운드 JSON 명세를 WAV로 합성하는 8비트 신시사이저 (numpy)."""
from __future__ import annotations

import re
import wave
from pathlib import Path

import numpy as np

NOTE_IDX = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
TOKEN = re.compile(r"^(-|[A-G]#?\d):(\d+)$")


def note_freq(name: str) -> float:
    pitch, octave = name[:-1], int(name[-1])
    midi = 12 * (octave + 1) + NOTE_IDX[pitch]
    return 440.0 * 2 ** ((midi - 69) / 12)


def osc(wave_type: str, freq: np.ndarray | float, n: int, sr: int, duty: float = 0.5, rng=None) -> np.ndarray:
    if wave_type == "noise":
        rng = rng or np.random.default_rng(0)
        # 8비트풍 노이즈: 주파수에 따라 샘플을 유지
        f = float(np.mean(freq)) if np.ndim(freq) else float(freq)
        hold = max(1, int(sr / max(f, 1)))
        vals = rng.uniform(-1, 1, n // hold + 1)
        return np.repeat(vals, hold)[:n]
    phase = np.cumsum(np.broadcast_to(freq, (n,)) / sr) % 1.0
    if wave_type == "square":
        return np.where(phase < duty, 1.0, -1.0)
    if wave_type == "triangle":
        return 4 * np.abs(phase - 0.5) - 1
    raise ValueError(f"알 수 없는 파형: {wave_type}")


def envelope(n: int, sr: int, attack=0.005, release=0.03) -> np.ndarray:
    env = np.ones(n)
    a, r = min(n, int(attack * sr)), min(n, int(release * sr))
    if a:
        env[:a] = np.linspace(0, 1, a)
    if r:
        env[-r:] *= np.linspace(1, 0, r)
    return env


def render_music(spec: dict, sr: int) -> np.ndarray:
    step = 60.0 / spec["bpm"] / 4  # 16분음표 길이(초)
    tracks, lengths = [], []
    for ch in spec["channels"]:
        parts = []
        for tok in ch["notes"].split():
            m = TOKEN.match(tok)
            if not m:
                raise ValueError(f"음표 토큰 형식 오류: {tok}")
            name, units = m.group(1), int(m.group(2))
            n = int(round(units * step * sr))
            if name == "-":
                parts.append(np.zeros(n))
            else:
                sig = osc(ch["wave"], note_freq(name), n, sr, ch.get("duty", 0.5))
                parts.append(sig * envelope(n, sr))
        tr = np.concatenate(parts) * ch.get("volume", 0.3)
        tracks.append(tr)
        lengths.append(len(tr))
    n = max(lengths)
    mix = np.zeros(n)
    for tr in tracks:
        mix[: len(tr)] += tr
    return mix


def render_ambience(spec: dict, sr: int) -> np.ndarray:
    n = int(spec["duration"] * sr)
    t = np.arange(n) / sr
    mix = np.zeros(n)
    for layer in spec["layers"]:
        kind, vol = layer["type"], layer.get("volume", 0.2)
        if kind == "hum":
            f = layer["freq"]
            mix += vol * (0.7 * np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t))
        elif kind == "typewriter":
            rng = np.random.default_rng(layer.get("seed", 1))
            count = int(spec["duration"] * layer["rate"])
            for s in rng.uniform(0, spec["duration"] - 0.05, count):
                i, k = int(s * sr), int(0.012 * sr)
                click = rng.uniform(-1, 1, k) * np.linspace(1, 0, k) ** 2
                mix[i:i + k] += vol * click
        elif kind == "stamp":
            k = int(0.12 * sr)
            tt = np.arange(k) / sr
            thud = np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 35)
            thud += 0.4 * np.random.default_rng(3).uniform(-1, 1, k) * np.exp(-tt * 60)
            for s in layer["times"]:
                i = int(s * sr)
                mix[i:i + k] += vol * thud[: max(0, min(k, n - i))]
        else:
            raise ValueError(f"알 수 없는 환경음 층: {kind}")
    return mix


def render_sfx(spec: dict, sr: int) -> np.ndarray:
    parts = []
    for seg in spec["segments"]:
        n = int(seg["dur"] * sr)
        freq = np.linspace(seg["f0"], seg["f1"], n)
        sig = osc(seg["wave"], freq, n, sr, seg.get("duty", 0.5))
        parts.append(sig * envelope(n, sr, 0.002, min(0.02, seg["dur"] / 3)) * seg.get("volume", 0.4))
    return np.concatenate(parts)


def write_wav(path: Path, sig: np.ndarray, sr: int) -> float:
    peak = np.max(np.abs(sig)) if len(sig) else 0
    if peak > 0.98:
        sig = sig / peak * 0.98
    data = (sig * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())
    return len(data) / sr


def render_all(spec: dict, out_dir: Path) -> dict:
    sr = spec.get("sample_rate", 22050)
    manifest = {}
    groups = [("music", render_music), ("ambience", render_ambience), ("sfx", render_sfx)]
    for group, fn in groups:
        for sid, s in spec.get(group, {}).items():
            fname = f"{sid}.wav"
            dur = write_wav(out_dir / fname, fn(s, sr), sr)
            manifest[sid] = {"file": fname, "loop": bool(s.get("loop", False)), "duration": round(dur, 3)}
    return manifest
```
