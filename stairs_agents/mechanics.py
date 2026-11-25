"""Mechanics 에이전트.

역할 (에이전트 맵): 기획서 04 게임 메카니즘을 숫자와 규칙으로 확정한다. 코드는 쓰지 않는다.
입력: docs/GDD.md (04 중심, 01·02·05로 대조), docs/mechanics_rules.json (검사 기준),
      현재 PoC의 game.js CONFIG (플레이테스트 반영값), 하네스가 돌려준 고칠 점
출력: output/mech_out/ 의 mechanics.json (Developer가 그대로 읽는 명세), mechanics_report.md

검사 기준은 docs/mechanics_rules.json 하나에 모은다. 게임 규칙이 바뀌면 그 파일만 고친다.
반복(고칠 점 → 다시 만들기)은 harness/가 맡는다. 이 파일은 한 번 만들기(run)와 검사(validate), 코드 수리(repair)만 가진다.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from .llm import LLMError, ReplayClient
from .util import Paths, extract_files, load_prompt, log, read

REQUIRED_FILES = ["mechanics.json", "mechanics_report.md"]


def load_rules(paths: Paths) -> dict:
    return json.loads(read(paths.docs / "mechanics_rules.json"))


def validate(spec: dict, rules: dict) -> list[dict]:
    """명세를 검사 기준과 대조한다. 문제마다 {severity, target, problem, fix}를 돌려준다. 빈 목록이면 통과."""
    out = []

    def bad(sev, target, problem, fix=""):
        out.append({"severity": sev, "target": target, "problem": problem, "fix": fix})

    fixed, cfg = rules["fixed"], spec.get("config", {})
    for key, want in fixed.items():
        got = cfg.get(key, {}).get("value")
        if got != want:
            bad("high", f"config.{key}", f"기획서·PoC 결정 값과 다름: {got}", f"{want} 로 둔다")
    for key, item in cfg.items():
        if not isinstance(item, dict) or "value" not in item or "source" not in item:
            bad("mid", f"config.{key}", "value 또는 source가 없음", '{"value":..,"source":..} 형식')
        elif item["source"] == "기획서 미정" and not item.get("reason"):
            bad("low", f"config.{key}", "기획서 미정인데 reason이 없음", "정한 이유를 한 줄로")

    fr = rules["floors"]
    floors = spec.get("floors", [])
    if [f.get("floor") for f in floors] != list(range(fr["first"], fr["last"] + 1)):
        bad("high", "floors", f"{fr['first']}~{fr['last']}층이 순서대로 하나씩 있어야 함 (현재 {len(floors)}개)")
    cat, hz_cat = rules["threats"], rules.get("hazards", {})
    for f in floors:
        n = f.get("floor")
        if n in fr["reviewFloors"] and (not f.get("review") or f.get("attackInterval") is not None):
            bad("high", f"floors.{n}", "승급 심사 층인데 공격이 있음", "review true, attackInterval null")
        for tid in f.get("mix", {}):
            if tid not in cat:
                bad("high", f"floors.{n}.mix", f"검사 기준에 없는 위협: {tid}")
            elif n < cat[tid]["firstFloor"]:
                bad("mid", f"floors.{n}.mix", f"{tid}가 {cat[tid]['firstFloor']}층보다 일찍 나옴")
        for hid in f.get("hazards", {}):
            if hid not in hz_cat:
                bad("high", f"floors.{n}.hazards", f"검사 기준에 없는 발판 위험: {hid}")
            elif n < hz_cat[hid]["firstFloor"]:
                bad("mid", f"floors.{n}.hazards", f"{hid}가 {hz_cat[hid]['firstFloor']}층보다 일찍 나옴")

    th = spec.get("threats", {})
    for tid, c in cat.items():
        if tid not in th:
            bad("high", f"threats.{tid}", "위협 정의가 없음", f"firstFloor {c['firstFloor']}, kind {c['kind']}")
            continue
        if th[tid].get("firstFloor") != c["firstFloor"]:
            bad("mid", f"threats.{tid}.firstFloor", f"{th[tid].get('firstFloor')} (기준 {c['firstFloor']})")
        if th[tid].get("kind") != c["kind"]:
            bad("mid", f"threats.{tid}.kind", f"{th[tid].get('kind')} (기준 {c['kind']})")
        if th[tid].get("warn") != fixed["warnTime"]:
            bad("mid", f"threats.{tid}.warn", f"공격 예고는 {fixed['warnTime']}초여야 함")
    for tid in set(th) - set(cat):
        bad("high", f"threats.{tid}", "검사 기준에 없는 위협", "docs/mechanics_rules.json에 먼저 추가하거나 뺀다")

    en = spec.get("endings", {})
    for k, floor in rules["endings"].items():
        if en.get(k, {}).get("floor") != floor:
            bad("high", f"endings.{k}", f"{floor}층이어야 함")
    if not spec.get("events"):
        bad("mid", "events", "이벤트 이름 목록이 비어 있음")

    mv_rule, mv = rules["motivation"], spec.get("motivation", {})
    for k in mv_rule["required"]:
        if k not in mv:
            bad("high", f"motivation.{k}", "플레이 동기 항목이 없음 (왜 오르는가)")
    docs = mv.get("documents", [])
    if docs and len(docs) < mv_rule["minDocuments"]:
        bad("mid", "motivation.documents", f"사내 문서가 {len(docs)}개 (최소 {mv_rule['minDocuments']})")
    if len({d.get("floor") for d in docs}) != len(docs):
        bad("low", "motivation.documents", "같은 층에 문서가 둘 이상")

    br, bm = rules["bm"], spec.get("bm", {})
    for k in br["required"]:
        if k not in bm:
            bad("high", f"bm.{k}", "BM 항목이 없음")
    for p in bm.get("preview", []):   # 체험: 높은 기록 보상을 기간제로만. 영구 지급하면 진짜 보상의 가치가 무너진다
        if p.get("permanent") or not 0 < p.get("durationDays", 0) <= br["previewMaxDays"]:
            bad("high", f"bm.preview.{p.get('id')}", f"체험 보상은 {br['previewMaxDays']}일 이하 기간제여야 함",
                "permanent false, durationDays 설정")
        if not p.get("earnedBy"):
            bad("mid", f"bm.preview.{p.get('id')}", "실제로 얻는 조건(earnedBy)이 없음")
    revives = 0
    for a in bm.get("assist", []):    # 노동 경감 3단계
        aid, tier = a.get("id"), str(a.get("tier"))
        if tier not in br["tierLeague"]:
            bad("high", f"bm.assist.{aid}", f"tier는 1~3 (현재 {tier})")
            continue
        if a.get("league") != br["tierLeague"][tier]:
            bad("high", f"bm.assist.{aid}", f"{tier}단계는 {br['tierLeague'][tier]} 리그에만 기록되어야 함",
                f"league \"{br['tierLeague'][tier]}\"")
        unknown = set(a.get("effect", {})) - set(br["allowedEffects"])
        if unknown:
            bad("high", f"bm.assist.{aid}", f"정의되지 않은 효과: {sorted(unknown)}")
        revives += a.get("effect", {}).get("extraRevive", 0)
    if revives + spec.get("motivation", {}).get("revive", {}).get("limitPerRun", 0) > br["maxRevivePerRun"]:
        bad("high", "bm.assist", f"이어하기 합계가 한 판 {br['maxRevivePerRun']}번을 넘음")
    leagues = bm.get("leagues", {})
    if not {"main", "free"} <= set(leagues):
        bad("high", "bm.leagues", "main(정규직)·free(자유) 두 리그가 있어야 함")
    return out


def assist_profile(spec: dict, tier: int) -> dict:
    """tier 이하 노동 경감 효과를 모두 산 경우의 효과 합 (시뮬레이션용)."""
    eff = {"startFloor": 1, "startDays": 0, "extraRevive": 0, "shield": 0, "autoFloors": 0, "drainFactor": 1.0}
    for a in spec.get("bm", {}).get("assist", []):
        if a.get("tier", 9) <= tier:
            for k, v in a.get("effect", {}).items():
                if k == "drainFactor":
                    eff[k] *= v
                elif k == "startFloor":
                    eff[k] = max(eff[k], v)
                else:
                    eff[k] += v
    return eff


def repair(spec: dict, rules: dict) -> list[str]:
    """LLM 없이 고칠 수 있는 형식 문제를 바로잡는다 (재생 모드에서 하네스가 부른다). 고친 내용 목록을 돌려준다."""
    done = []
    for key, want in rules["fixed"].items():
        item = spec.setdefault("config", {}).setdefault(key, {"source": "기획서 04"})
        if item.get("value") != want:
            item["value"] = want
            done.append(f"config.{key} -> {want}")
    for f in spec.get("floors", []):
        if f["floor"] in rules["floors"]["reviewFloors"] and (not f.get("review") or f.get("attackInterval")):
            f.update(review=True, attackInterval=None, mix={})
            done.append(f"floors.{f['floor']} 승급 심사 층으로")
        for tid in list(f.get("mix", {})):
            c = rules["threats"].get(tid)
            if c is None or f["floor"] < c["firstFloor"]:
                f["mix"].pop(tid)
                done.append(f"floors.{f['floor']}.mix에서 {tid} 뺌")
    return done


def current_config(paths: Paths) -> str:
    """현재 PoC game.js의 CONFIG 블록 (플레이테스트 반영값). 없으면 빈 문자열."""
    for rel in ("demo/game.js", "demo_api/game.js"):
        path = paths.root / rel
        if path.exists():
            m = re.search(r"const CONFIG = \{.*?\n\s*\};", read(path), re.S)
            if m:
                return f"# 현재 PoC의 CONFIG ({rel}, 플레이테스트 반영값)\n```js\n{m.group(0)}\n```"
    return ""


class MechanicsAgent:
    name = "mechanics"

    def __init__(self, llm, paths: Paths):
        self.llm = llm
        self.paths = paths

    def context(self) -> str:
        p = self.paths
        ctx = ("# 기획서 (GDD)\n" + read(p.docs / "GDD.md") +
               "\n\n# 검사 기준 (docs/mechanics_rules.json)\n" + read(p.docs / "mechanics_rules.json"))
        cfg = current_config(p)
        return ctx + ("\n\n" + cfg if cfg else "")

    def run(self, feedback: str | None = None, round_no: int = 1) -> dict:
        """한 번 만든다. 재생 응답이 없으면 skipped를 돌려준다."""
        t0, out = time.time(), self.paths.mech_out
        request = self.context() + "\n\n위 기획서와 검사 기준으로 1~100층 메카니즘 명세(mechanics.json)와 보고서를 작성하라."
        if feedback:
            request += "\n\n" + feedback
        step = "spec" if round_no == 1 else f"spec_r{round_no}"
        log.info("[Mechanics] 메카니즘 명세 작성 요청 (%d번째)", round_no)
        try:
            files = extract_files(self.llm.complete(self.name, step, load_prompt(self.paths, "mechanics"), request))
        except LLMError as e:
            if isinstance(self.llm, ReplayClient):
                log.warning("[Mechanics] 재생 응답이 없어 건너뜀: %s", e)
                return {"skipped": True, "problems": [str(e)]}
            raise
        missing = [f for f in REQUIRED_FILES if f not in files]
        if missing:
            raise ValueError(f"[Mechanics] 필수 파일이 없습니다: {missing}")
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        for rel, body in files.items():
            (out / rel).write_text(body, encoding="utf-8")
        spec = json.loads(files["mechanics.json"])
        problems = validate(spec, load_rules(self.paths))
        log.info("[Mechanics] 완료: 층 %d개, 위협 %d종, 문제 %d건 (%.1f초)",
                 len(spec.get("floors", [])), len(spec.get("threats", {})), len(problems), time.time() - t0)
        return {"skipped": False, "spec": spec, "problems": problems}


def load_spec(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
