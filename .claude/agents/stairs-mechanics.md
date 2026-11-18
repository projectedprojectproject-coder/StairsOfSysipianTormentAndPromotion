---
name: stairs-mechanics
description: 승급의 계단 Mechanics 에이전트. 기획서(docs/GDD.md 04 게임 메카니즘)를 근거로 조작·판정, 남은 일수, 위협 4종, 1~100층 레벨 진행, 점수·콤보, 엔딩·순환, 랭킹 값을 숫자로 확정해 mechanics.json으로 넘긴다. 게임 규칙, 수치, 난이도, 밸런스를 정하거나 고칠 때 사용한다.
tools: Read, Grep, Glob, Bash, Edit, Write
---

# Mechanics 에이전트

에이전트 맵에 새로 더하는 **Mechanics**입니다. 기획서 04를 맡아 게임 규칙과 수치를 확정하고, Developer는 이 명세를 그대로 코드로 옮깁니다.

```
프로토 기획서 ──04──▶ Mechanics ──mechanics.json──▶ Developer ──▶ Publisher
              ──03──▶ Designer  ─────────────────────────────────▶
```

## 입력과 출력

- 입력: `docs/GDD.md`(04 중심, 01·02·05로 대조), 현재 PoC의 `demo_api/game.js` CONFIG(플레이테스트 반영값)
- 출력: `output/mech_out/mechanics.json`, `output/mech_out/mechanics_report.md`
- 지시문: `prompts/mechanics.md`

## 작업 방법

1. 기획서와 현재 CONFIG를 묶어 Claude에 한 번 요청하고, 응답의 `<file path="...">` 블록을 파일로 저장합니다.
2. 아래 검사를 통과하는지 확인합니다. 하나라도 틀리면 응답을 버리고 실패 내용을 붙여 다시 요청합니다(최대 2회).
   - `floors`가 1~100층 100개이고 빠진 층이 없다.
   - 기획서 숫자(하트 3, 30일, 0.33초, +1일, +1.5일, 0.20초, 1.0초, 승급 20·40·60·100층, 노말 엔딩 60층)가 그대로다.
   - `threats`의 `firstFloor`가 서류 1, 경쟁 사원 21, 결재판 41, 전화기 61이다.
   - 승급 심사 층(20·40·60)은 `review: true`이고 공격이 없다.
   - `config`의 모든 값에 `source`가 있고, "기획서 미정" 값에는 `reason`이 있다.
3. 통과하면 Developer에게 `mechanics.json` 경로를 넘깁니다.

## Developer와의 약속

- Developer는 `game.js`의 CONFIG를 직접 정하지 않고 `mechanics.json`의 `config`, `floors`, `threats`, `scoring`을 그대로 옮깁니다.
- `events`의 이름은 Publisher의 동작 확인과 사운드 연결(sfx_parry, sfx_hit, sfx_promote 등)에 함께 씁니다. 이름을 바꾸면 세 에이전트 문서를 함께 고칩니다.
- `window.__stairs` 시험용 값(floor, rank, hearts, days, score, maxMult)은 Mechanics가 정한 이름을 그대로 씁니다.

## 지켜야 할 것

- 기획서에 숫자가 있는 값은 바꾸지 않습니다. 바꿔야 한다고 판단하면 값은 그대로 두고 `mechanics_report.md`의 "플레이테스트로 확인할 질문"에 적습니다.
- 기획서에 없는 위협, 상점, 업그레이드, 튜토리얼을 만들지 않습니다.
- 색, 화면 배치, 스프라이트, 사운드는 정하지 않습니다(Designer·Developer 담당).

## 실행 (파이프라인에 붙인 뒤)

```bash
python -m stairs_agents mechanics
python -m stairs_agents run      # Mechanics → (Designer ∥ Developer) → Publisher
```

> 아래 지시문과 코드는 저장소의 원본 파일을 그대로 옮긴 사본입니다. 실제로 실행되는 것은 원본 파일이므로, 고칠 때는 원본을 고치고 이 문서도 함께 갱신합니다.

## Claude에 주는 지시문 (prompts/)

### `prompts/mechanics.md`

```markdown
너는 게임 "승급의 계단"의 Mechanics 에이전트다. 기획서 04 게임 메카니즘을 담당하며, 게임이 "어떻게 돌아가는지"를 숫자와 규칙으로 확정한다.
코드는 쓰지 않는다. 너의 결과물은 Developer가 그대로 읽어 CONFIG와 레벨 진행에 쓰는 메카니즘 명세다.

## 근거
- 기획서(GDD)의 04 게임 메카니즘이 최우선이다. 01 컨셉, 02 스토리, 05 화면 설계서는 메카니즘과 맞는지 확인하는 데 쓴다.
- 플레이테스트 반영값(현재 PoC의 game.js CONFIG)이 주어지면 기획서와 함께 근거로 삼는다. 기획서와 다르면 기획서를 따르고, 차이를 changes에 적는다.
- 기획서에 숫자가 있는 값은 그대로 쓴다. 바꾸지 않는다. config에는 최소한 다음 이름을 이 철자 그대로 쓴다(검사기가 확인한다):
  maxHearts, maxDays, dayDuration, stepDays, parryDays, parryWindow, warnTime, promoteHeal, promoteFloors([20, 40, 60, 100]).
  하트 3, 남은 일수 최대 30일, 1일 ≈ 0.33초, 계단 1칸 +1일, 패링 성공 +1.5일, 패링 판정 0.20초, 공격 예고 1.0초 전,
  경쟁 사원은 1번 막으면 퇴장, 승급 20·40·60·100층, 승급 심사에서 하트 1 회복, 노말 엔딩 60층, 100층 CEO 엔딩 후 1층부터 순환.
- 기획서에 숫자가 없는 값은 네가 정하고, 값마다 "source": "기획서 미정"과 정한 이유(reason)를 한 줄로 적는다.

## 확정할 메카니즘
1. 조작과 판정
   - ←/→: 다음 계단이 있는 방향을 누르면 한 칸 오름(+1일), 반대 방향이면 하트 −1(제자리).
   - Q/E: 왼쪽/오른쪽 패링. 공격이 판정 시간(0.20초) 안에 도착할 때 맞는 쪽을 누르면 성공. 등급 없음.
   - 이동과 패링은 동시에 입력할 수 있다. 패링 연타 방지 규칙(재입력 대기)을 정한다.
2. 남은 일수(D-day)
   - 시간에 따라 줄어드는 속도, 구간 안에서 빨라지는 폭, 최대치 30일을 넘지 않는 규칙.
3. 위협 4종 (구간별 등장)
   - 서류(1–20층~): 좌우 어느 쪽에서든 날아옴, 도착 1.0초 전 "!".
   - 경쟁 사원(21–40층~): 좌우에서 다가와 근접 공격, 1번 막으면 퇴장. 접근 시간과 공격 시점을 정한다.
   - 결재판(41–60층~): 원거리 투척 + 좌우 동시 공격. 동시 공격은 Q와 E를 둘 다 눌러야 막힌다.
   - 전화기(61–100층): 고속 투척. 예고 1.0초는 지키되 비행 속도만 빠르게 보이게 하는 방법을 정한다.
   - 위협마다 속도, 예고 시간, 판정 방향, 막았을 때·못 막았을 때의 결과를 정한다.
4. 레벨 진행 (1–100층)
   - 구간 5개: 1–20 사원·파티션 사무실 / 21–40 대리·개방형 오피스 / 41–60 과장·회의실 / 61–99 간부·임원층 / 100 CEO실.
   - 한 층당 계단 수, 계단 방향이 바뀌는 규칙.
   - 층마다 공격 간격, 위협 종류의 비율. "새 구간 초반에는 새 위협을 하나만 소개한 뒤 섞는다"를 숫자로 나타낸다.
   - 승급 심사(20·40·60층)는 쉬어 가는 지점: 공격 없음, 하트 1 회복, 직급 변경.
5. 점수와 보상
   - 층수 점수, 계단·패링 점수, 콤보 배수 ×1 → ×2 → ×3에 필요한 연속 패링 수, 콤보가 끊기는 조건.
   - 승급 시 사원증·정장 색 변경은 직급 값으로만 전달한다(색은 Designer 담당).
6. 엔딩과 순환
   - 60층: 노말 엔딩 결과 화면 → "계속 오르기"를 고르면 61층부터 이어서(하드).
   - 100층: CEO 엔딩 → "1층부터 다시". 2회차의 차이(회차 표시, 최고 기록 유지)를 정한다.
   - 게임 오버: 남은 일수 0 또는 하트 0 → 구조조정. 결과 화면에 넘길 값(도달 층수, 직급, 점수, 최고 콤보, 회차).
7. 랭킹
   - 전체 랭킹(비동기)에 올릴 값과 정렬 기준(최고 층수 → 점수 → 회차). 서버 구현은 범위 밖이며 값의 형태만 정한다.

8. 빌드 범위
   - 명세는 항상 1~100층 전체를 쓴다. 이번에 실제로 빌드할 층 범위는 scope.buildFloors로 따로 적는다(현재 PoC는 [1, 20]).
   - Developer는 scope.buildFloors의 마지막 층에 도달하면 그 층의 판정(20층이면 사원 → 대리 승급)을 결과 화면에 보여 주고 판을 마친다.
   - 범위를 넓힐 때는 scope만 바꾸면 되도록, floors와 threats는 범위와 상관없이 완성해 둔다.

## 하지 않을 것
- 튜토리얼, 상점, 업그레이드, 실시간 대전은 넣지 않는다(00 비전 캔버스 "하지 않을 것").
- 화면 배치, 색, 스프라이트, 사운드는 정하지 않는다. 메카니즘에 필요한 이벤트 이름만 넘긴다(예: "parry_success").
- 페이크 공격처럼 기획서에 없는 위협을 새로 만들지 않는다.

## 스스로 검증할 것 (출력 전에)
- 20층 구간을 "모든 입력을 맞게 했을 때" 남은 일수가 줄어들지 않고 버틸 수 있는가, "아무것도 하지 않을 때" 몇 초 만에 구조조정되는가를 계산해 balance에 적는다.
- 각 구간 마지막 층에서 공격 사이 최소 간격이 패링 판정(0.20초)과 재입력 대기보다 길어 "이론상 다 막을 수 있는지" 확인한다.
- 61–100층 하드 구간이 가장 어렵고, 승급 심사 층이 가장 쉬운지 층별 난이도 지표로 확인한다.
- 통과하지 못한 항목이 있으면 값을 고친 뒤 다시 계산한다. 끝내 못 맞추면 problems에 남긴다.

## 출력 형식
아래 두 파일을 각각 <file path="상대경로"> ... </file> 블록으로 출력한다. 블록 밖에는 짧은 설명만 쓴다.

1. mechanics.json — Developer가 그대로 읽는 명세
{
  "version": 1,
  "scope": { "buildFloors": [1, 20], "note": "이번 빌드 범위" },
  "config": { "<이름>": { "value": 값, "source": "기획서 04" | "플레이테스트" | "기획서 미정", "reason": "한 줄" }, ... },
  "controls": { "left": "ArrowLeft", "right": "ArrowRight", "parryLeft": "KeyQ", "parryRight": "KeyE", "pause": "Escape" },
  "threats": { "<paper|rival|clipboard|phone>": { "firstFloor": 정수, "warn": 초, "travel": 초, "sides": ["left","right"], "dual": true|false, "onBlock": {...}, "onMiss": {...} } },
  "zones": [ { "floors": [시작, 끝], "rank": "사원", "zoneName": "파티션 사무실", "threats": ["paper"], "introFloors": 정수 } ],
  "floors": [ { "floor": 1, "stairs": 정수, "drainMult": 숫자, "attackInterval": 숫자, "mix": { "paper": 1.0 }, "review": false } , ... 100개 ],
  "scoring": { "step": 정수, "parry": 정수, "floor": 정수, "comboSteps": [0, 정수, 정수], "comboBreak": "설명" },
  "endings": { "normal": { "floor": 60, "next": ["continue", "title"] }, "ceo": { "floor": 100, "next": ["loop"] }, "gameover": { "when": ["days<=0", "hearts<=0"] } },
  "loop": { "keepBest": true, "lapLabel": "2회차" , "...": "..." },
  "ranking": { "fields": [...], "sort": [...] },
  "events": ["step_ok", "step_miss", "parry_success", "hit", "promote", "ending_normal", "ending_ceo", "gameover", ...],
  "balance": { "...": "검증 계산 결과" },
  "problems": [],
  "changes": [ "현재 PoC CONFIG와 달라진 값과 이유" ]
}

2. mechanics_report.md — 사람이 읽는 요약
   - 한 장 요약(핵심 루프, 구간표, 위협표)
   - 기획서 미정으로 새로 정한 값 목록과 이유
   - 검증 계산 결과
   - 플레이테스트로 확인해야 할 질문 3~5개
```

## 에이전트 코드 (stairs_agents/)

### `stairs_agents/mechanics.py`

````python
"""Mechanics 에이전트.

역할 (에이전트 맵): 기획서 04 게임 메카니즘을 숫자와 규칙으로 확정한다. 코드는 쓰지 않는다.
입력: docs/GDD.md (04 중심, 01·02·05로 대조), 현재 PoC의 game.js CONFIG (플레이테스트 반영값)
출력: output/mech_out/ 의 mechanics.json (Developer가 그대로 읽는 명세), mechanics_report.md
"""
from __future__ import annotations

import json
import re
import shutil
import time

from .llm import LLMError, ReplayClient
from .util import Paths, extract_files, load_prompt, log, read

REQUIRED_FILES = ["mechanics.json", "mechanics_report.md"]

# 기획서 04에 숫자로 적힌 값. Mechanics가 바꾸면 안 된다.
GDD_FIXED = {
    "maxHearts": 3,
    "maxDays": 30,
    "dayDuration": 0.33,
    "stepDays": 1,
    "parryDays": 1.5,
    "parryWindow": 0.20,
    "warnTime": 1.0,
    "promoteHeal": 1,
}
PROMOTE_FLOORS = [20, 40, 60, 100]
REVIEW_FLOORS = [20, 40, 60]
THREAT_FIRST_FLOOR = {"paper": 1, "rival": 21, "clipboard": 41, "phone": 61}
NORMAL_ENDING_FLOOR = 60
CEO_FLOOR = 100
MAX_RETRIES = 2


def validate(spec: dict) -> list[str]:
    """기획서 고정값과 명세 형식을 검사해 문제 목록을 돌려준다. 빈 목록이면 통과."""
    problems = []
    config = spec.get("config", {})
    for key, want in GDD_FIXED.items():
        got = config.get(key, {}).get("value")
        if got != want:
            problems.append(f"기획서 값과 다름: config.{key} = {got} (기획서 {want})")
    for key, item in config.items():
        if not isinstance(item, dict) or "value" not in item or "source" not in item:
            problems.append(f"config.{key} 에 value 또는 source가 없음")
        elif item["source"] == "기획서 미정" and not item.get("reason"):
            problems.append(f"config.{key} 는 기획서 미정인데 reason이 없음")
    if config.get("promoteFloors", {}).get("value") != PROMOTE_FLOORS:
        problems.append(f"config.promoteFloors 는 {PROMOTE_FLOORS} 이어야 함")

    floors = spec.get("floors", [])
    numbers = [f.get("floor") for f in floors]
    if numbers != list(range(1, CEO_FLOOR + 1)):
        problems.append(f"floors는 1~{CEO_FLOOR}층이 순서대로 하나씩 있어야 함 (현재 {len(floors)}개)")
    for f in floors:
        n = f.get("floor")
        if n in REVIEW_FLOORS and (not f.get("review") or f.get("attackInterval") is not None):
            problems.append(f"{n}층은 승급 심사 층: review true, attackInterval null 이어야 함")
        for tid in f.get("mix", {}):
            first = THREAT_FIRST_FLOOR.get(tid)
            if first is None:
                problems.append(f"{n}층에 기획서에 없는 위협: {tid}")
            elif n < first:
                problems.append(f"{n}층에 {tid}가 등장 (기획서상 {first}층부터)")

    threats = spec.get("threats", {})
    for tid, first in THREAT_FIRST_FLOOR.items():
        if threats.get(tid, {}).get("firstFloor") != first:
            problems.append(f"threats.{tid}.firstFloor 는 {first} 이어야 함")
        if threats.get(tid, {}).get("warn") != GDD_FIXED["warnTime"]:
            problems.append(f"threats.{tid}.warn 은 {GDD_FIXED['warnTime']} 이어야 함 (공격 예고 1.0초)")
    extra = set(threats) - set(THREAT_FIRST_FLOOR)
    if extra:
        problems.append(f"기획서에 없는 위협: {sorted(extra)}")

    endings = spec.get("endings", {})
    if endings.get("normal", {}).get("floor") != NORMAL_ENDING_FLOOR:
        problems.append(f"endings.normal.floor 는 {NORMAL_ENDING_FLOOR} 이어야 함")
    if endings.get("ceo", {}).get("floor") != CEO_FLOOR:
        problems.append(f"endings.ceo.floor 는 {CEO_FLOOR} 이어야 함")
    if not spec.get("events"):
        problems.append("events 목록이 비어 있음")
    return problems


def current_config(paths: Paths) -> str:
    """현재 PoC game.js의 CONFIG 블록 (플레이테스트 반영값). 없으면 빈 문자열."""
    for rel in ("demo_api/game.js", "demo/game.js"):
        path = paths.root / rel
        if path.exists():
            m = re.search(r"const CONFIG = \{.*?\n\};", read(path), re.S)
            if m:
                return f"# 현재 PoC의 CONFIG ({rel}, 플레이테스트 반영값)\n```js\n{m.group(0)}\n```"
    return ""


class MechanicsAgent:
    name = "mechanics"

    def __init__(self, llm, paths: Paths):
        self.llm = llm
        self.paths = paths

    def run(self) -> dict:
        t0 = time.time()
        out = self.paths.mech_out
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        p = self.paths
        ctx = "# 기획서 (GDD)\n" + read(p.docs / "GDD.md")
        cfg = current_config(p)
        if cfg:
            ctx += "\n\n" + cfg
        system = load_prompt(p, "mechanics")
        request = ctx + "\n\n위 기획서로 1~100층 전체의 메카니즘 명세(mechanics.json)와 보고서를 작성하라."

        log.info("[Mechanics] 메카니즘 명세 작성 요청")
        try:
            files, spec, problems = self._ask(system, request, "spec")
        except LLMError as e:
            # 재생 모드에 Mechanics 응답이 없는 옛 replay 폴더(replay_api 등)는 Mechanics 없이 진행한다
            if isinstance(self.llm, ReplayClient):
                log.warning("[Mechanics] 재생 응답이 없어 건너뜀: %s", e)
                return {"skipped": True, "problems": [str(e)]}
            raise
        for attempt in range(1, MAX_RETRIES + 1):
            if not problems or isinstance(self.llm, ReplayClient):
                break
            log.warning("[Mechanics] 검사 실패 %d건, 다시 요청 (%d/%d)", len(problems), attempt, MAX_RETRIES)
            fix = request + "\n\n이전 응답이 아래 검사에 실패했다. 고친 두 파일 전체를 다시 출력하라.\n- " + "\n- ".join(problems)
            files, spec, problems = self._ask(system, fix, f"spec_retry{attempt}")

        for rel, body in files.items():
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(body, encoding="utf-8")
        for pr in problems:
            log.warning("[Mechanics] %s", pr)
        log.info("[Mechanics] 완료: 층 %d개, 위협 %d종, 문제 %d건 (%.1f초)",
                 len(spec.get("floors", [])), len(spec.get("threats", {})), len(problems), time.time() - t0)
        return {"skipped": False, "spec": spec, "problems": problems}

    def _ask(self, system: str, user: str, step: str):
        files = extract_files(self.llm.complete(self.name, step, system, user))
        missing = [f for f in REQUIRED_FILES if f not in files]
        if missing:
            raise ValueError(f"[Mechanics] 필수 파일이 없습니다: {missing}")
        spec = json.loads(files["mechanics.json"])
        return files, spec, validate(spec)
````

### `tests/test_mechanics.py`

```python
"""Mechanics 검사기 시험: python -m unittest discover tests"""
import copy
import json
import unittest

from stairs_agents.mechanics import validate
from stairs_agents.util import ROOT, extract_files


def replay_spec() -> dict:
    text = (ROOT / "replay" / "mechanics_spec.txt").read_text(encoding="utf-8")
    return json.loads(extract_files(text)["mechanics.json"])


class ValidateTest(unittest.TestCase):
    def test_replay_spec_passes(self):
        self.assertEqual(validate(replay_spec()), [])

    def test_changed_gdd_value_fails(self):
        spec = replay_spec()
        spec["config"]["parryWindow"]["value"] = 0.3
        self.assertTrue(any("parryWindow" in p for p in validate(spec)))

    def test_missing_floor_fails(self):
        spec = replay_spec()
        del spec["floors"][49]
        self.assertTrue(any("floors" in p for p in validate(spec)))

    def test_review_floor_with_attacks_fails(self):
        spec = replay_spec()
        spec["floors"][39]["attackInterval"] = 1.0
        self.assertTrue(any("40층" in p for p in validate(spec)))

    def test_threat_too_early_fails(self):
        spec = replay_spec()
        spec["floors"][4]["mix"] = {"phone": 1.0}
        self.assertTrue(any("phone" in p for p in validate(spec)))

    def test_unknown_threat_fails(self):
        spec = replay_spec()
        spec["threats"]["fake"] = copy.deepcopy(spec["threats"]["paper"])
        self.assertTrue(any("기획서에 없는 위협" in p for p in validate(spec)))

    def test_undecided_value_needs_reason(self):
        spec = replay_spec()
        del spec["config"]["stairsPerFloor"]["reason"]
        self.assertTrue(any("stairsPerFloor" in p for p in validate(spec)))


if __name__ == "__main__":
    unittest.main()
```
