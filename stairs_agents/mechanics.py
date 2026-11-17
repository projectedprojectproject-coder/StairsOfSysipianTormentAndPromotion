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
