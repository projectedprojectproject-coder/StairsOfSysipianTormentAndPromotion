---
name: stairs-designer
description: 승급의 계단 Designer 에이전트. 기획서(docs/GDD.md 03)와 에셋 목록, 원본 리소스 DB를 근거로 16비트 픽셀 스프라이트·배경·8비트 사운드를 설계하고 PNG/WAV로 만든다. 스프라이트, 이미지, 사운드 에셋을 만들거나 고칠 때 사용한다.
tools: Read, Grep, Glob, Bash, Edit, Write
---

# Designer 에이전트

에이전트 맵의 **Designer**입니다. 생성형 AI로 스프라이트, 리소스, 사운드를 제작하고, 필요하면 원본 리소스 데이터베이스 파일을 사용합니다.

## 입력과 출력

- 입력: `docs/GDD.md`(특히 03 디자인 컨셉), `docs/ASSET_LIST.md`, `data/원본리소스_DB.json`, 컨셉 아트 `data/concept/`(영역 목록 `regions.json`)
- 출력: `output/design_out/` 의 PNG, WAV, `design_manifest.json`, 설계 명세 `_spec_*.json`
- 결과물은 바로 **Designer QA**(`stairs-designer-qa`)가 검사합니다. 보고서: `output/qa_out/designer_qa.md`
- 내보내는 형식은 Designer 도구가 만드는 그대로입니다. 형식 맞춤은 Publisher가 맡습니다.

## 작업 방법

1. 에셋마다 따로 Claude에 설계를 요청합니다(스프라이트 시트 6종 각각, 이미지 1건, 사운드 1건). 한 번에 요청하면 응답이 64000 토큰을 넘어 잘립니다.
2. 스프라이트·이미지 명세(JSON)는 `render.py`가 PNG로 그리고, 사운드 명세는 `synth.py`가 WAV로 합성합니다.
3. `contract.py`로 ASSET_LIST의 ID, 변형, 애니메이션 이름이 모두 있는지 검사합니다.
4. 컨셉 아트 참고: `concept.py`가 `data/concept/regions.json`의 영역을 뽑아(`output/concept_refs/`) 시트별 설계 요청에 참고 격자와 컨셉 주요 색을 붙입니다. 직접 그릴 때는 스킬 `.claude/skills/concept-sprite-extraction/SKILL.md`를 따릅니다.

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
- 게임 논리 해상도는 320x180이지만 에셋은 2배 밀도(pixel_scale 2)로 그린다. 프레임 크기는 player와 rival 32x48, projectiles와 hud_icons 24x24, warning 16x24, props 32x48, stairs 64x16(demo) 또는 88x24(demo_api), 이미지(title_bg, bg_zone1~5)는 640x360을 기준으로 한다. 게임은 이를 절반 크기로 그려 픽셀이 2배 촘촘해진다. 변형 이름과 애니메이션 이름은 ASSET_LIST와 정확히 같아야 한다.
- 컨셉 이미지(data/concept/05-1_title.png, 05-3_play.png)의 구도와 색을 따른다.
- stairs는 실제 계단처럼 보여야 한다(컨셉 05-3의 올리브색 계단). 프레임 폭은 계단 두 칸 간격이므로 가운데 절반만 칠한다. tile = 디딤판(위 1줄 밝게, 그 아래 몇 줄) + 앞 모서리 그림자 1줄 + 챌판(프레임 아래 끝까지). 칸마다 디딤판과 챌판이 이어져 계단 단면이 된다. 디딤판 아래 비스듬한 받침과 난간은 게임 코드가 그린다. riser는 같은 폭의 어두운 몸체 색 견본이다.
- props(소품): cooler(정수기), boxes(상자), plant(화분), cabinet(서류장). 층 바닥 위에 놓인다(발 위치가 프레임 아래).
- title_bg(05-1 요소 4): 흐린 구름(clouds), 어두운 빌딩 숲(city 여러 겹), 가운데 가장 높은 본사(tower, 위로 갈수록 좁아지는 여러 단), 맨 위 층 통창만 따뜻한 불빛(glow로 번짐), 그 창가에서 아래를 내려다보는 한 사람(silhouette), 거리 바닥과 가로등까지만 그린다. 걷는 사원들은 게임이 commuter 시트로 움직이며 그리므로 title_bg에 넣지 않는다.
- commuter(05-1 요소 4): 20x40, 고개 숙이고 서류가방을 든 채 오른쪽으로 걷는 직장인, walk 4프레임(다리 벌림·모음 번갈아). 컨셉 05-1의 가라앉은 밤거리 색.
- bg_lobby(05-2): 형광등 천장(원근 격자, poly), 양옆 벽, 오른쪽 벽 화이트보드(STATISTICS 칸, 화면 x 250~312 사이에 게임이 기록을 씀), 가운데 책상의 스탠드 불빛·서류 더미·모니터·앉아 일하는 사원 뒷모습, 파티션과 멀리 선 사원들. 왼쪽 x 0~90(사원증)과 아래 y 145 아래(업무 시작 버튼)는 가려진다.
- bg_practice(연습 모드): 계단 없는 사무실을 옆에서 본 모습. 가구는 플레이어(48px 키)와 같은 크기, 발 높이 y 256에 바닥(경쟁 사원이 그 위를 걷는다), 가운데 x 250~390은 비운다.
- bg_result(05-5): 어둡게 가라앉은 사무실, 천장 형광등 두 줄, 왼쪽 서류장과 선반의 상자, 의자, 오른쪽 불 켜진 창 하나와 책상. 가운데 x 112~252(인사 평가 표)와 왼쪽 큰 캐릭터 자리는 가려진다.
- projectiles의 coffee: 뚜껑 덮인 테이크아웃 컵(흰 컵, 갈색 슬리브, 김). 막으면 안 되는 물건이라 위협들과 한눈에 다르게 보여야 한다.
- sticky(61층~ 포스트잇): 24x24 네모 메모지(접착 윗단, 접힌 모서리, 글씨 두 줄), fly 2프레임. 변형 pink, blue, green, yellow, white는 메모지 색만 바꾼다(남은 패링 횟수 5~1).
- stairs의 cracked: tile과 같은 칸에 디딤판과 챌판을 가로지르는 갈라진 금과 깨져 나간 모서리 (21층~ 금 간 계단)
- projectiles의 suitcase: 각진 검정 가죽 서류가방(바느질 테두리, 금색 잠금쇠 두 개, 두꺼운 손잡이), 2프레임. 서류·결재판과 한눈에 달라야 한다 (71층~, 날아오다 터진다). suitcase_open은 덮개가 젖혀져 붉은 안감이 보이는 열린 모습
- projectiles의 monitor: 위에서 떨어지는 컴퓨터 모니터(회색 틀, 금 간 푸른 화면, 받침대), 2프레임으로 기울기를 바꿔 구르는 느낌 로고와 버튼이 가운데 위·아래를 덮으므로 꼭대기 층은 화면 위쪽 30px 안에 둔다.

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
- {"kind":"glow","x","y","rx","ry","color","alpha","steps"}  둥근 빛 번짐 (가운데가 가장 밝다)
- {"kind":"tower","x","y","tiers":[{"w","h"},...],"color","edge","shade","window","lit","lit_ratio","crown_lit","spire","beacon","seed"}  x는 가운데, y는 바닥, tiers는 아래에서 위로, 맨 위 단은 통창이 crown_lit 색으로 켜진다
- {"kind":"silhouette","x","y","color","face"}  창가에서 아래를 내려다보는 사람 (9x14), face 1 오른쪽 / -1 왼쪽
- {"kind":"crowd","x0","x1","y","color","pose","min_gap","max_gap","jitter","accent","accent_ratio","seed"}  사원 무리 (한 명 9x14), pose bowed는 고개 숙인 모습, accent는 서류가방 색
- {"kind":"lamps","xs":[...],"y","h","color","light","alpha","spread"}  가로등과 아래로 퍼지는 불빛
- {"kind":"clouds","y0","y1","count","min_r","max_r","flat","color","rim","shade","seed"}  납작한 밤구름 띠 (rim은 위쪽 가장자리 밝은 색)
- {"kind":"city","y","count","min_h","max_h","min_w","max_w","min_gap","max_gap","color","edge","shade","window","lit","warm","lit_ratio","warm_ratio","win","stripe_ratio","stripe_gap","stripe_floor","setback_ratio","antenna_ratio","skip_x0","skip_x1","seed"}  창 격자·기둥·단·안테나가 있는 빌딩 숲 (skip 구간은 비운다)
- {"kind":"walkers","xs":[...],"y","size","hair","suit","pants","shirt","tie","skin","bag","bag_ratio","seed"}  거리를 걷는 사원 (size "large" 20x40, 그 밖은 16x30), y는 발 위치
- {"kind":"poly","points":[[x,y],...],"color"}  다각형 (원근이 있는 천장, 벽, 화이트보드)
- tower에는 crown_style("band" 또는 "windows"), win([창폭,창높이,가로간격,세로간격]), stripes(세로 기둥 수)를 더할 수 있다.
```

### `prompts/designer_sound.md`

```markdown
너는 게임 "승급의 계단"의 Designer 에이전트다. 생성형 AI로서 8비트 음악, 환경음, 효과음을 설계한다.
너의 출력은 JSON 하나이며, Python 신시사이저가 이 JSON을 그대로 오디오 파일로 만든다.

## 반드시 지킬 것
- 기획서 03 사운드 음악을 근거로 한다: 타자기, 도장, 형광등 소리 환경음 + 단조로운 8비트 루프, 층수가 오를수록 불협화음을 섞어 긴장감 고조.
- ASSET_LIST의 모든 사운드 ID를 빠짐없이 만든다.
- bgm_loop_tense는 bgm_loop와 같은 길이, 같은 bpm으로 만들어 게임이 두 곡을 자연스럽게 바꿀 수 있게 한다.
- 패링 타이밍 소리는 ASSET_LIST에 적힌 "박"의 시작 시각을 정확히 지킨다(게임이 박이 판정 창 한가운데 오도록 그만큼 앞에서 튼다): sfx_cue_clipboard 나무판 "딱… 딱!" 두 번째 딱 0.30초, sfx_cue_rival 짧은 "헤이!" 모음 0.045초(앞은 'ㅎ' 잡음), sfx_phone_ring 벨 두 번 중 두 번째 벨 0.40초, sfx_cue_paper 바스락 뒤 "착" 접는 소리 0.25초. 박 앞의 쉼은 volume 0 구간으로 만든다. sfx_monitor_shatter는 높은 잡음이 터지고 짧은 유리 조각 소리가 흩어지는 0.4초 안팎의 소리다.

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
입력: docs/GDD.md (특히 03 디자인 컨셉), docs/ASSET_LIST.md, data/원본리소스_DB.json,
      data/concept/ 컨셉 아트 (concept.py로 주요 색과 참고 스프라이트 격자를 뽑아 요청에 붙인다)
출력: output/design_out/ 의 디자인 파일(PNG, WAV)과 design_manifest.json
      내보내는 형식은 Designer의 도구가 만드는 그대로이며, 형식 맞춤은 Publisher가 맡는다.
"""
from __future__ import annotations

import shutil
import time
from concurrent.futures import ThreadPoolExecutor

from . import concept, render, synth
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

    def run(self, feedback: str | None = None, round_no: int = 1) -> dict:
        """feedback: Designer QA가 돌려준 고칠 점 (2번째 차례부터). 요청마다 덧붙이고, 응답 단계 이름에 _r<차례>를 붙인다."""
        sfx = f"_r{round_no}" if round_no > 1 else ""
        fb = ("\n\n" + feedback) if feedback else ""
        t0 = time.time()
        out = self.paths.design_out
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        ctx = self._context()
        contract = load_contract(self.paths.docs / "ASSET_LIST.md")

        system_sprites = load_prompt(self.paths, "designer_sprites")
        system_sound = load_prompt(self.paths, "designer_sound")
        refs = concept.extract_regions(self.paths.out / "concept_refs")
        if refs:
            log.info("[Designer] 컨셉 참고 스프라이트 %d개를 요청에 붙임", len(refs["regions"]))

        def ask_sheet(aid):
            c = contract["sheets"][aid]
            req = (f"이번 요청에서는 sheet '{aid}' 하나만 설계하라. 변형: {', '.join(c['variants'])}. "
                   f"애니메이션: {', '.join(c['animations'])}. 출력 JSON에는 palette와 sheets.{aid}만 넣는다.")
            ref = concept.ref_text(refs, aid)
            if ref:
                req = ref + "\n\n" + req
            return aid, extract_json(self.llm.complete(self.name, f"sprite_{aid}{sfx}", system_sprites, ctx + "\n\n" + req + fb))

        def ask_images():
            req = ("이번 요청에서는 images만 설계하라: " + ", ".join(contract["images"]) +
                   ". 출력 JSON에는 images만 넣는다.")
            ref = concept.ref_text(refs, "__images__")
            if ref:
                req = ref + "\n\n" + req
            return extract_json(self.llm.complete(self.name, "images" + sfx, system_sprites, ctx + "\n\n" + req + fb))

        def ask_sound():
            return extract_json(self.llm.complete(self.name, "sound" + sfx, system_sound,
                                                  ctx + "\n\nASSET_LIST의 모든 사운드를 위 출력 형식으로 설계하라." + fb))

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


def _poly(img, d, e):
    """다각형 (원근이 있는 천장, 벽, 화이트보드 등). points는 [[x, y], ...]."""
    d.polygon([tuple(pt) for pt in e["points"]], fill=rgba(e["color"]))


SCENE_KINDS = {
    "rect": _rect, "gradient": _gradient, "line": _line, "window_grid": _window_grid,
    "skyline": _skyline, "building": _building, "partition": _partition, "desk": _desk,
    "monitor": _monitor, "chair": _chair, "plant": _plant, "table": _table, "door": _door,
    "frame": _frame, "light_cone": _light_cone, "workers": _workers,
    "glow": _glow, "tower": _tower, "crowd": _crowd, "silhouette": _silhouette, "lamps": _lamps,
    "clouds": _clouds, "city": _city, "walkers": _walkers, "poly": _poly,
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
