"""하네스에 꽂는 역할 4종과 평가기.

| 역할 | 만들기(act) | 평가기 | LLM 없이 고치기(repair) |
|---|---|---|---|
| mechanics | MechanicsAgent | 명세 검사(규칙표) · 밸런스 시뮬레이션 | 형식 수리 + 구간별 난이도 자동 조정 |
| developer | DeveloperAgent | Developer QA · 명세 일치(CONFIG ↔ mechanics.json) | 없음 |
| designer  | DesignerAgent  | Designer QA | 없음 |
| publisher | PublisherAgent | 브라우저 동작 확인 · 화면 대조 | 없음 (문제는 owner로 다른 역할에 넘긴다) |
"""
from __future__ import annotations

import json
import re

from ..designer import DesignerAgent
from ..developer import DeveloperAgent
from ..llm import ReplayClient
from ..mechanics import MechanicsAgent, assist_profile, load_rules, repair, validate
from ..publisher import PublisherAgent
from ..qa_designer import DesignerQAAgent
from ..qa_developer import DeveloperQAAgent
from ..qa_screens import run_screen_qa
from ..sim import reach_rates
from ..util import Paths, extract_files, log, read, write_json
from .core import Evaluation, Issue, Role


def _from_qa(name: str, rep: dict, owner: str) -> Evaluation:
    """기존 QA 보고(qa.py QAReport.to_dict)를 하네스 평가 형식으로 바꾼다."""
    issues = [Issue(name, i["severity"], i.get("asset", ""), i["problem"], i.get("fix", ""), i.get("owner", owner).lower())
              for i in rep.get("issues", [])]
    return Evaluation(name, issues, rep.get("metrics", {}))


class _LLMRole(Role):
    def __init__(self, llm, paths: Paths):
        self.llm, self.paths = llm, paths

    def can_regenerate(self) -> bool:
        return self.llm is not None and not isinstance(self.llm, ReplayClient)


# ── Mechanics ──────────────────────────────────────────────────────────────

class MechanicsRole(_LLMRole):
    name = "mechanics"

    def __init__(self, llm, paths: Paths, sim_runs: int = 200):
        super().__init__(llm, paths)
        self.output_dir = paths.mech_out
        self.agent = MechanicsAgent(llm, paths)
        self.rules = load_rules(paths)
        self.sim_runs = sim_runs

    @property
    def spec_path(self):
        return self.paths.mech_out / "mechanics.json"

    def spec(self) -> dict:
        return json.loads(read(self.spec_path))

    def act(self, feedback, round_no):
        res = self.agent.run(feedback, round_no)
        if res.get("skipped"):
            raise RuntimeError("Mechanics 응답이 없습니다 (재생 폴더에 mechanics_spec.txt 필요)")

    def evaluators(self):
        return [self.eval_schema, self.eval_balance, self.eval_bm_fairness]

    def eval_bm_fairness(self, _role) -> Evaluation:
        """노동 경감 단계별로 도달률이 얼마나 오르는지 재고, '돈 > 실력'이 되면 문제로 돌려준다."""
        spec, g = self.spec(), self.rules["bm"]["guard"]
        if not spec.get("bm", {}).get("assist"):
            return Evaluation("BM 공정성")
        base = reach_rates(spec, runs=self.sim_runs)
        tiers = {t: reach_rates(spec, runs=self.sim_runs, assist=assist_profile(spec, t))[g["paidProfile"]]["reach"]
                 for t in (1, 2, 3)}
        paid = tiers[g["paidTier"]][g["floor"]]
        skilled = base[g["mustStayBelow"]]["reach"][g["floor"]]
        issues = []
        if paid >= skilled:
            issues.append(Issue("BM 공정성", "mid", f"bm.assist.tier{g['paidTier']}",
                                f"{g['paidTier']}단계까지 산 {g['paidProfile']} {g['floor']}층 도달률 {paid:.0%} ≥ 무지원 "
                                f"{g['mustStayBelow']} {skilled:.0%} — 돈이 실력을 앞지름",
                                "3단계 효과(autoFloors, drainFactor, shield)를 줄인다"))
        metrics = {"unpaid": base[g["paidProfile"]]["reach"], **{f"tier{t}": r for t, r in tiers.items()},
                   "skilledUnpaid": base[g["mustStayBelow"]]["reach"]}
        return Evaluation("BM 공정성", issues, metrics, round(max(0.0, paid - skilled) * 10, 2))

    def eval_schema(self, _role) -> Evaluation:
        return Evaluation("명세 검사", [Issue("명세 검사", p["severity"], p["target"], p["problem"], p["fix"])
                                    for p in validate(self.spec(), self.rules)])

    def eval_balance(self, _role) -> Evaluation:
        rates = reach_rates(self.spec(), runs=self.sim_runs)
        issues, dist = [], 0.0
        for prof, goals in self.rules["balanceTargets"].items():
            if prof.startswith("_"):
                continue
            for floor, (lo, hi) in goals.items():
                got = rates[prof]["reach"][floor]
                if not lo <= got <= hi:
                    dist += 10 * (lo - got if got < lo else got - hi)
                    way = "너무 어렵다" if got < lo else "너무 쉽다"
                    issues.append(Issue("밸런스", "mid", f"balance.{prof}.{floor}층",
                                        f"{prof} {floor}층 도달률 {got:.0%} — 목표 {lo:.0%}~{hi:.0%}, {way}",
                                        f"해당 구간 attackInterval/drainMult를 {'늘리고 줄여' if got < lo else '줄이고 늘려'} 조정"
                                        f" (주된 패배 원인: {', '.join(rates[prof]['topCauses']) or '-'})"))
        return Evaluation("밸런스", issues, {"reach": {k: v["reach"] for k, v in rates.items()},
                                          "causes": {k: v["topCauses"] for k, v in rates.items()}}, round(dist, 2))

    def repair(self, evaluations, round_no) -> bool:
        """재생 모드: 형식 수리 후, 밸런스 목표에서 벗어난 구간의 난이도를 비율로 조정한다."""
        spec = self.spec()
        changed = repair(spec, self.rules)
        for e in evaluations:   # BM 공정성: 3단계 효과를 20%씩 줄인다
            for i in e.issues:
                if i.source == "BM 공정성":
                    for a in spec.get("bm", {}).get("assist", []):
                        if a.get("tier") == 3:
                            eff = a["effect"]
                            if "autoFloors" in eff:
                                eff["autoFloors"] = max(0, int(eff["autoFloors"] * 0.8))
                            if "drainFactor" in eff:
                                eff["drainFactor"] = round(1 - (1 - eff["drainFactor"]) * 0.8, 3)
                    changed.append("3단계 노동 경감 효과 20% 축소")
        zone_of = {"20": (1, 20), "40": (21, 40), "60": (21, 60), "80": (61, 80), "100": (61, 99)}
        for e in evaluations:
            for i in e.issues:
                m = re.match(r"balance\.(.+)\.(\d+)층", i.target)
                if not m:
                    continue
                lo, hi = zone_of[m.group(2)]
                easier = "어렵다" in i.problem
                # 주된 패배 원인에 맞는 손잡이를 더 세게 돌린다 (발판 위험이면 위험 칸 비율, 아니면 공격 간격·일수 감소)
                hazard_led = any(h in i.fix for h in ("cracked", "wet"))
                k_int, k_drain = (1.07, 0.96) if easier else (0.94, 1.04)
                k_hz = (0.75 if hazard_led else 0.9) if easier else 1.1
                for f in spec["floors"]:
                    if lo <= f["floor"] <= hi and f.get("attackInterval"):
                        f["attackInterval"] = round(f["attackInterval"] * k_int, 3)
                        f["drainMult"] = round(f["drainMult"] * k_drain, 3)
                        for h in f.get("hazards", {}):
                            f["hazards"][h] = round(min(0.3, f["hazards"][h] * k_hz), 4)
                changed.append(f"{lo}~{hi}층 {'쉽게' if easier else '어렵게'} (간격 x{k_int}, 감소 x{k_drain}, 위험 칸 x{k_hz})")
        if not changed:
            return False
        spec.setdefault("changes", []).extend(f"[하네스 {round_no}차례 자동 조정] {c}" for c in changed)
        write_json(self.spec_path, spec)
        log.info("[하네스:mechanics] 코드로 고침 %d건: %s", len(changed), "; ".join(changed[:4]))
        return True


# ── Developer ──────────────────────────────────────────────────────────────

class DeveloperRole(_LLMRole):
    name = "developer"

    def __init__(self, llm, paths: Paths):
        super().__init__(llm, paths)
        self.output_dir = paths.dev_out
        self.agent, self.qa = DeveloperAgent(llm, paths), DeveloperQAAgent(llm, paths)

    def act(self, feedback, round_no):
        self.agent.run(feedback=feedback, round_no=round_no)

    def evaluators(self):
        return [lambda r: _from_qa("Developer QA", self.qa.run(round_no=1), "developer"), self.eval_conformance]

    def eval_conformance(self, _role) -> Evaluation:
        """mechanics.json의 고정값(기획서 04)이 game.js CONFIG에 들어 있는지 본다."""
        mech, game = self.paths.mech_out / "mechanics.json", self.paths.dev_out / "game.js"
        if not mech.exists() or not game.exists():
            return Evaluation("명세 일치")
        cfg = re.search(r"const CONFIG = \{.*?\n\s*\};", read(game), re.S)
        nums = {float(n) for n in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])", cfg.group(0) if cfg else "")}
        issues = []
        for k, item in json.loads(read(mech))["config"].items():
            v = item.get("value")
            if "04" in str(item.get("source")) and isinstance(v, (int, float)) and float(v) not in nums:
                issues.append(Issue("명세 일치", "mid", f"CONFIG.{k}", f"mechanics.json 값 {v}가 CONFIG에 없음",
                                    "명세 값을 그대로 옮긴다"))
        return Evaluation("명세 일치", issues)


# ── Designer ───────────────────────────────────────────────────────────────

class DesignerRole(_LLMRole):
    name = "designer"

    def __init__(self, llm, paths: Paths, use_resource_db=True):
        super().__init__(llm, paths)
        self.output_dir = paths.design_out
        self.agent = DesignerAgent(llm, paths, use_resource_db=use_resource_db)
        self.qa = DesignerQAAgent(llm, paths)

    def act(self, feedback, round_no):
        self.agent.run(feedback=feedback, round_no=round_no)

    def evaluators(self):
        return [lambda r: _from_qa("Designer QA", self.qa.run(round_no=1), "designer")]


# ── Publisher ──────────────────────────────────────────────────────────────

class PublisherRole(Role):
    """Publisher는 LLM이 없다. 동작 확인과 화면 대조의 문제를 owner(developer/designer)로 넘기는 것이 핵심이다."""
    name = "publisher"

    def __init__(self, llm, paths: Paths, screens=True):
        self.llm, self.paths, self.screens = llm, paths, screens
        self.output_dir = None
        self.agent, self.last = PublisherAgent(paths), None

    def can_regenerate(self):
        return True

    def act(self, feedback, round_no):
        self.last = self.agent.run()

    def evaluators(self):
        evs = [self.eval_tests]
        if self.screens:
            evs.append(lambda r: _from_qa("화면 대조", run_screen_qa(self.llm, self.paths, round_no=1), "developer"))
        return evs

    def eval_tests(self, _role) -> Evaluation:
        rep = (self.last or {}).get("report", {})
        issues = [Issue("동작 확인", "high", t["name"], t.get("detail") or "실패", owner="developer")
                  for t in rep.get("tests", []) if not t["ok"]]
        return Evaluation("동작 확인", issues, {"passed": (self.last or {}).get("passed")})
