"""루프 하네스의 뼈대: 역할(Role)을 '만들기 → 평가 → 되먹임' 반복으로 돌린다.

기존 qa_loop와 다른 점
- 평가기(Evaluator)를 여러 개 꽂는다: 규칙 검사, 시뮬레이션, 브라우저 동작 확인 등이 같은 형식(Evaluation)으로 결과를 낸다.
- 점수로 비교해 가장 좋았던 결과물을 지킨다(퇴보 방지). 더 나빠지면 그 차례 결과를 버리고 최선본으로 되돌린다.
- 고칠 점을 차례마다 쌓는다(Memory). 한 번 고쳤다가 다시 생긴 문제는 "재발"로 표시해 돌려준다.
- 예산(Budget): 차례 수, 시간, LLM 호출 수 중 하나라도 넘으면 멈춘다.
- LLM이 다시 만들 수 없을 때(재생 모드)는 역할의 repair()가 코드로 결과물을 고친다. 그래서 API 없이도 반복이 돈다.
- 모든 차례를 ledger.jsonl에 한 줄씩 남긴다(무엇을 받고, 무엇을 고쳤고, 점수가 어땠는지).
"""
from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..util import log

SEV_WEIGHT = {"high": 10.0, "mid": 3.0, "low": 1.0}


@dataclass
class Issue:
    source: str               # 평가기 이름
    severity: str             # high | mid | low
    target: str               # 문제가 난 곳 (예: floors.37, threats.coffee)
    problem: str
    fix: str = ""
    owner: str = ""           # 고칠 역할 (mechanics | developer | designer | publisher). 비우면 평가 대상 역할

    def key(self) -> tuple:
        return (self.source, self.target, self.problem)


@dataclass
class Evaluation:
    evaluator: str
    issues: list[Issue] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    distance: float = 0.0     # 목표까지 남은 거리 (예: 도달률 차이). 문제 수가 같아도 나아졌는지 구분한다

    @property
    def penalty(self) -> float:
        return sum(SEV_WEIGHT.get(i.severity, 1.0) for i in self.issues) + self.distance


@dataclass
class Budget:
    max_rounds: int = 6
    max_seconds: float = 1800.0
    max_llm_calls: int = 12
    patience: int = 3         # 점수가 나아지지 않은 차례가 이만큼 이어지면 멈춘다


class Memory:
    """역할별로 받은 고칠 점과 해결 여부를 쌓는다."""

    def __init__(self):
        self.seen: dict[tuple, int] = {}       # 문제 -> 처음 나온 차례
        self.resolved: set[tuple] = set()

    def update(self, round_no: int, issues: list[Issue]) -> dict:
        now = {i.key() for i in issues}
        new = [k for k in now if k not in self.seen]
        relapsed = [k for k in now if k in self.resolved]
        for k in new:
            self.seen[k] = round_no
        fixed = [k for k in self.seen if k not in now and k not in self.resolved]
        self.resolved |= set(fixed)
        self.resolved -= set(relapsed)
        return {"new": len(new), "fixed": len(fixed), "relapsed": relapsed}


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, **row):
        row["t"] = round(time.time(), 2)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


class Role:
    """하네스에 꽂는 역할. 서브클래스가 act / evaluators / (선택) repair 를 채운다."""
    name = "role"
    output_dir: Path | None = None   # 최선본 보관을 위해 결과물이 놓이는 폴더

    def act(self, feedback: str | None, round_no: int):
        raise NotImplementedError

    def evaluators(self) -> list:
        return []

    def can_regenerate(self) -> bool:
        """LLM으로 다시 만들 수 있으면 True (재생 모드면 False)."""
        return True

    def repair(self, evaluations: list[Evaluation], round_no: int) -> bool:
        """LLM 없이 코드로 고칠 수 있으면 고치고 True. 기본은 고칠 수 없음."""
        return False


def feedback_text(role: str, round_no: int, issues: list[Issue], relapsed: list[tuple]) -> str:
    order = {"high": 0, "mid": 1, "low": 2}
    lines = [f"# 하네스가 돌려준 고칠 점 ({role}, {round_no}번째 만들기)",
             "아래 문제를 고쳐 같은 출력 형식으로 전체를 다시 내라. 문제가 없는 부분은 바꾸지 않는다."]
    rel = set(relapsed)
    for i in sorted(issues, key=lambda i: order.get(i.severity, 9)):
        tag = " (재발: 앞에서 고쳤다가 다시 생김)" if i.key() in rel else ""
        lines.append(f"- [{i.severity}] {i.target}: {i.problem}{tag}" + (f" -> {i.fix}" if i.fix else ""))
    return "\n".join(lines)


class LoopRunner:
    """Role 하나를 예산 안에서 반복한다. 반환: {verdict, rounds, best_round, evaluations, stop}"""

    def __init__(self, ledger: Ledger, budget: Budget | None = None):
        self.ledger = ledger
        self.budget = budget or Budget()

    def evaluate(self, role: Role) -> list[Evaluation]:
        out = []
        for ev in role.evaluators():
            try:
                out.append(ev(role))
            except Exception as e:  # 평가기 자체가 깨지면 high 문제로 기록하고 계속
                out.append(Evaluation(getattr(ev, "__name__", "evaluator"),
                                      [Issue("harness", "high", "evaluator", f"평가기 오류: {e}")]))
        return out

    def run(self, role: Role, initial_feedback: str | None = None) -> dict:
        b, t0, mem = self.budget, time.time(), Memory()
        best_pen, best_round, stale, llm_calls = None, 0, 0, 0
        feedback, history, stop = initial_feedback, [], "최대 차례"
        snap = (role.output_dir.parent / f"_best_{role.name}") if role.output_dir else None
        evals: list[Evaluation] = []
        for n in range(1, b.max_rounds + 1):
            mode = "act"
            if n == 1 or role.can_regenerate():
                role.act(feedback, n)
                llm_calls += 1
            elif role.repair(evals, n):
                mode = "repair"
            else:
                stop = "다시 만들 수 없음 (재생 모드이고 코드로 고칠 수도 없음)"
                break
            evals = self.evaluate(role)
            issues = [i for e in evals for i in e.issues]
            pen = sum(e.penalty for e in evals)
            delta = mem.update(n, issues)
            improved = best_pen is None or pen < best_pen
            if improved:
                best_pen, best_round, stale = pen, n, 0
                if snap and role.output_dir.exists():
                    shutil.rmtree(snap, ignore_errors=True)
                    shutil.copytree(role.output_dir, snap)
            else:
                stale += 1
            row = {"role": role.name, "round": n, "mode": mode, "penalty": pen, "issues": len(issues),
                   "high": sum(i.severity == "high" for i in issues), "new": delta["new"], "fixed": delta["fixed"],
                   "relapsed": len(delta["relapsed"]), "best_round": best_round,
                   "metrics": {e.evaluator: e.metrics for e in evals if e.metrics}}
            history.append(row)
            self.ledger.write(**row)
            log.info("[하네스:%s] %d차례 %s — 벌점 %.0f, 문제 %d (새 %d, 고침 %d, 재발 %d)", role.name, n, mode,
                     pen, len(issues), delta["new"], delta["fixed"], len(delta["relapsed"]))
            if not any(i.severity in ("high", "mid") for i in issues):
                stop = "통과"; break
            own = [i for i in issues if i.severity in ("high", "mid") and (not i.owner or i.owner == role.name)]
            if not own:
                stop = "남은 문제는 다른 역할 책임 (바깥 루프가 owner로 넘김)"; break
            if stale >= b.patience:
                stop = f"{b.patience}차례 연속 나아지지 않음"; break
            if time.time() - t0 > b.max_seconds:
                stop = "시간 예산 초과"; break
            if llm_calls >= b.max_llm_calls and role.can_regenerate():
                stop = "LLM 호출 예산 초과"; break
            feedback = feedback_text(role.name, n + 1, issues, delta["relapsed"])
        # 퇴보 방지: 마지막 결과가 최선이 아니면 최선본으로 되돌린다
        if snap and snap.exists() and best_round != history[-1]["round"]:
            shutil.rmtree(role.output_dir, ignore_errors=True)
            shutil.copytree(snap, role.output_dir)
            log.info("[하네스:%s] 마지막 결과가 더 나빠 %d차례 최선본으로 되돌림", role.name, best_round)
            evals = self.evaluate(role)
        if snap:
            shutil.rmtree(snap, ignore_errors=True)
        final = [i for e in evals for i in e.issues]
        verdict = "pass" if not any(i.severity in ("high", "mid") for i in final) else (
            "fail" if any(i.severity == "high" for i in final) else "revise")
        result = {"role": role.name, "verdict": verdict, "rounds": len(history), "best_round": best_round,
                  "stop": stop, "history": history, "issues": [asdict(i) for i in final],
                  "metrics": {e.evaluator: e.metrics for e in evals if e.metrics}}
        self.ledger.write(role=role.name, event="done", verdict=verdict, stop=stop, best_round=best_round)
        return result
