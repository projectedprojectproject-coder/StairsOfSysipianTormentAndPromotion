---
name: stairs-developer
description: 승급의 계단 Developer 에이전트. 기획서(docs/GDD.md 01·04·05)로 1~20층 PoC 웹 게임 코드(index.html, game.js)와 스프라이트 정의(sprite_definition.json)를 작성한다. 게임 규칙, 수치, 화면, 입력 코드를 만들거나 고칠 때 사용한다.
tools: Read, Grep, Glob, Bash, Edit, Write
---

# Developer 에이전트

에이전트 맵의 **Developer**입니다. 코드와 시스템을 개발해 게임이 돌아가게 하고, 스프라이트 정의를 작성합니다.

## 입력과 출력

- 입력: `docs/GDD.md`(01, 04, 05 중심), `docs/ASSET_LIST.md`, `output/mech_out/mechanics.json`(Mechanics 명세, 있으면 CONFIG와 층 진행 값을 그대로 옮김)
- 출력: `output/dev_out/` 의 `index.html`, `game.js`, `sprite_definition.json`
- `sprite_definition.json`의 수용 형식: 이미지 JPEG·PNG 스프라이트 맵, 사운드 MP3·OGG

## 작업 방법

1. 기획서와 에셋 목록을 묶어 Claude에 한 번 요청하고, 응답의 `<file path="...">` 블록을 파일로 저장합니다.
2. 필수 파일 3개가 모두 있는지, 스프라이트 정의에 ASSET_LIST의 에셋이 모두 있는지 검사합니다.
3. 기획서 04 수치는 `game.js` 맨 위 `CONFIG`에 모으고, 기획서에 없는 값은 "기획서 미정" 주석으로 표시합니다.

## 현재 게임 규칙에서 기억할 것

- 하트 3, 남은 일수 최대 30일(1일 ≈ 0.33초), 계단 1칸 +1일, 패링 성공 +1.5일, 패링 판정 0.20초, 공격 예고 1.0초.
- 계단 방향 실수와 막지 못한 공격은 하트 -1. 남은 일수 0 또는 하트 0이면 구조조정.
- 플레이테스트 반영: 새 층에 오를 때마다 하트 1 회복(`CONFIG.FLOOR_HEAL`, 최대 3).
- 재생 모드 응답은 `replay/developer_code.txt`에 있습니다. 게임 코드를 고칠 때는 이 파일을 고친 뒤 파이프라인을 다시 돌리고, 결과(`output/build/game.js`)를 `demo/game.js`에 반영합니다.
- API 버전(`replay_api/developer_code.txt`, `demo_api/game.js`)에도 같은 규칙이 `CONFIG.floorHeal`로 들어가 있습니다. 확인: `python -m stairs_agents run --replay replay_api --out output_api`
- 재생 응답 두 개는 Mechanics 이전에 만든 것이라 아직 `mechanics.json`을 읽지 않습니다. 명세를 반영한 코드는 API로 다시 실행해야 나옵니다.

## 실행

```bash
python -m stairs_agents developer
python -m stairs_agents developer --replay replay
```

> 아래 지시문과 코드는 저장소의 원본 파일을 그대로 옮긴 사본입니다. 실제로 실행되는 것은 원본 파일이므로, 고칠 때는 원본을 고치고 이 문서도 함께 갱신합니다.

## Claude에 주는 지시문 (prompts/)

### `prompts/developer.md`

```markdown
너는 게임 "승급의 계단"의 Developer 에이전트다. 코드와 시스템을 개발해 게임이 돌아가도록 하고, 스프라이트 정의를 작성한다.
이번 작업은 Proof of Concept이며 범위는 1~20층(사원 구간, 파티션 사무실, 서류 투척)이다.

## 결과물
아래 파일을 각각 <file path="상대경로"> ... </file> 블록으로 출력한다. 블록 밖에는 짧은 설명만 쓴다.
1. index.html
2. game.js  (바닐라 JavaScript 하나. 외부 라이브러리, ES 모듈, fetch 사용 금지. file:// 로 열어도 동작해야 한다)
3. sprite_definition.json  (스프라이트 정의)

## 스프라이트 정의 (sprite_definition.json)
Developer가 받아들일 형식과 필요한 에셋을 정의한다. 파일 이름과 프레임 크기는 Designer 결과를 본 Publisher가 채우므로 null로 둔다.
{
  "version": 1,
  "accepted_formats": { "image": ["png", "jpg", "jpeg"], "audio": ["mp3", "ogg"] },
  "image_note": "이미지는 JPEG 또는 PNG 스프라이트 맵",
  "assets_dir": "assets",
  "logical_resolution": [320, 180],
  "sprites": { "<ASSET_LIST의 sheet ID>": { "variants": [...], "animations": [...], "file": null, "frame_w": null, "frame_h": null } },
  "images":  { "<ASSET_LIST의 image ID>": { "file": null } },
  "sounds":  { "<ASSET_LIST의 sound ID>": { "loop": true 또는 false, "files": null } }
}

## 실행 시 받는 정의 (Publisher가 만들어 줌)
index.html은 game.js보다 먼저 <script src="assets/sprite_definition.js"></script>를 불러온다.
이 파일은 window.SPRITE_DEF 를 다음 형태로 채운다.
- sprites[id] = { file, frame_w, frame_h, variants: {이름: 행 번호}, animations: {이름: {frames: [열 번호...], fps}} }
- images[id] = { file, w, h }
- sounds[id] = { loop, files: { ogg: "파일", mp3: "파일" } }   // 둘 중 하나만 있을 수 있음
- assets_dir 기준 상대 경로. 프레임 (열, 행)의 픽셀 위치는 (열*frame_w, 행*frame_h).
에셋 하나가 없거나 불러오기에 실패해도 게임은 멈추지 말고 색 사각형으로 대신 그리며, 실패 목록을 기록한다.

## 메카니즘 명세 (mechanics.json)를 받았을 때
- 입력에 "메카니즘 명세 (Mechanics, mechanics.json)"가 있으면, 게임 규칙과 수치는 직접 정하지 말고 이 명세를 그대로 옮긴다.
  - config의 각 value를 game.js 맨 위 CONFIG에 같은 이름으로 넣고, source가 "기획서 미정"인 값에는 주석으로 "기획서 미정 (Mechanics)"과 reason을 적는다.
  - floors, threats, scoring, endings는 CONFIG 아래 MECH 객체에 그대로 넣고, 층 진행·공격 생성·점수 계산이 이 표를 읽게 한다.
  - scope.buildFloors가 이번 빌드 범위다. 마지막 층에 도달하면 그 층의 판정을 결과 화면에 보여 주고 판을 마친다.
  - events의 이름으로 효과음과 window.__stairs.log 기록을 연결한다.
- 명세와 아래 기획서 항목이 어긋나 보이면 명세를 따르고, 응답 끝 설명에 어긋난 점을 짧게 적는다.
- 명세가 없으면 아래 항목대로 직접 정한다.

## 반드시 구현할 것 (기획서 근거)
- 화면 5종과 이동 경로: 05-1 타이틀, 05-2 로비, 05-3 플레이, 05-4 일시정지(ESC), 05-5 결과. 각 화면의 번호 요소를 모두 배치한다.
- 조작 (04): ← → 로 다음 계단 방향으로 한 칸 이동, Q 왼쪽 패링, E 오른쪽 패링, 이동과 패링 동시 입력 가능. 튜토리얼 없음.
- 조작법 화면 (PoC 추가): 타이틀과 일시정지에 "조작법" 버튼을 두고, 누르면 설정처럼 겹쳐 뜨는 화면에 ← → 이동, Q/E 패링, ESC 일시정지, Enter 메뉴 결정과 패링 판정(예고 1초 뒤 도착, 직전 0.2초)·하트 규칙을 짧게 보여 준다. 닫기 버튼과 ESC로 닫는다. 진행을 막는 튜토리얼이 아니라 언제든 열어 보는 안내다. 타이틀과 일시정지의 첫 버튼은 그대로 시작하기·계속하기로 둔다(Enter로 바로 진행).
- 규칙 (04): 남은 일수는 계속 줄고 계단 이동과 패링 성공으로 늘어난다. 계단 방향 실수와 막지 못한 공격은 하트 -1. 남은 일수 0 또는 하트 0이면 구조조정(게임 오버).
- 주요 수치 (04, 모두 초안이므로 game.js 맨 위 CONFIG 객체에 모은다): 하트 3, 남은 일수 최대 30일, 1일 약 0.33초, 계단 1칸 +1일, 패링 성공 +1.5일, 패링 판정 0.20초, 공격 예고 1.0초 전 표시, 승급 20층(하트 1 회복).
- 하트 회복 (플레이테스트 반영, PoC 조정값): 새 층에 오를 때마다 하트 1 회복(최대 하트 3). CONFIG.FLOOR_HEAL로 둔다.
- 보상 (04): 층수 점수 + 패링 콤보 배수 x1 -> x2 -> x3. 승급 시 사원증과 정장 색 변경. 최고 층수와 점수는 localStorage에 저장.
- 1~20층 위협 (04 레벨 구성): 서류 투척. 좌우 어느 쪽에서든 날아오며 도착 1.0초 전에 "!" 예고를 띄운다.
- 난이도 (04): 구간 안에서 일수 감소 속도와 공격 빈도가 점점 오른다.
- 사운드 (03): bgm_loop 재생, 층이 오르면 bgm_loop_tense로 전환, amb_office 낮은 볼륨, 각 sfx. 첫 사용자 입력 이후에 재생 시작. 브라우저가 ogg를 재생하지 못하면 mp3를 쓴다.
- 20층 도달 시 승급(사원 -> 대리) 판정을 결과 화면에 보여 주고 PoC를 마친다.
- 기획서에 수치가 없는 값(층당 계단 수, 콤보 배수가 오르는 패링 횟수, 점수 단위, 난이도 증가 폭, 불협화음 전환 층 등)은 CONFIG에 넣고 주석에 "기획서 미정"이라고 쓴다.

## 화면과 표현
- 논리 해상도 320x180을 창 크기에 맞는 정수배로 확대하고 imageSmoothingEnabled=false로 픽셀을 유지한다.
- 한글 글자는 같은 캔버스 변환 위에 그리되 글꼴은 "Noto Sans KR", sans-serif.
- 팔레트 (03): #5A5F66, #8A9A5B, #A13D3D, #1E1F22, #E8E6DF.

## 시험용 장치 (Publisher가 사용)
- window.__stairs = { ready, screen, floor, rank, hearts, days, score, maxMult, steps, assetErrors, audioFormat, log } 를 매 프레임 갱신한다.
- URL 매개변수: seed=정수 (난수 고정), bot=1 (플레이 화면에서 자동으로 맞는 방향 이동과 패링), mute=1 (소리 끔).
```

## 에이전트 코드 (stairs_agents/)

### `stairs_agents/developer.py`

```python
"""Developer 에이전트.

역할 (에이전트 맵): 코드와 시스템을 개발하고 스프라이트를 정의한다.
입력: docs/GDD.md (01, 04, 05 중심), docs/ASSET_LIST.md,
      output/mech_out/mechanics.json (Mechanics 명세, 있으면 CONFIG와 진행 값을 그대로 옮긴다)
출력: output/dev_out/ 의 index.html, game.js, sprite_definition.json
      sprite_definition.json의 accepted_formats는 이미지 JPEG, PNG 스프라이트 맵, 사운드 MP3, OGG.
"""
from __future__ import annotations

import json
import shutil
import time

from .contract import load_contract
from .util import Paths, extract_files, load_prompt, log, read

REQUIRED_FILES = ["index.html", "game.js", "sprite_definition.json"]


class DeveloperAgent:
    name = "developer"

    def __init__(self, llm, paths: Paths):
        self.llm = llm
        self.paths = paths

    def run(self) -> dict:
        t0 = time.time()
        out = self.paths.dev_out
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        p = self.paths
        ctx = ("# 기획서 (GDD)\n" + read(p.docs / "GDD.md") +
               "\n\n# 공통 에셋 목록 (ASSET_LIST)\n" + read(p.docs / "ASSET_LIST.md"))
        mech = p.mech_out / "mechanics.json"
        if mech.exists():
            ctx += "\n\n# 메카니즘 명세 (Mechanics, mechanics.json)\n" + read(mech)

        log.info("[Developer] 게임 코드와 스프라이트 정의 작성 요청")
        files = extract_files(self.llm.complete(
            self.name, "code", load_prompt(p, "developer"),
            ctx + "\n\n위 기획서로 1~20층 PoC 게임 코드와 스프라이트 정의를 작성하라."))
        missing = [f for f in REQUIRED_FILES if f not in files]
        if missing:
            raise ValueError(f"[Developer] 필수 파일이 없습니다: {missing}")
        for rel, body in files.items():
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(body, encoding="utf-8")

        definition = json.loads(files["sprite_definition.json"])
        contract = load_contract(p.docs / "ASSET_LIST.md")
        problems = []
        for group, ids in (("sprites", contract["sheets"]), ("images", contract["images"]), ("sounds", contract["sounds"])):
            for aid in ids:
                if aid not in definition.get(group, {}):
                    problems.append(f"스프라이트 정의에 없음: {group}.{aid}")
        for pr in problems:
            log.warning("[Developer] %s", pr)
        log.info("[Developer] 완료: 파일 %d개, 수용 형식 %s (%.1f초)",
                 len(files), definition.get("accepted_formats"), time.time() - t0)
        return {"files": sorted(files), "definition": definition, "problems": problems}
```
