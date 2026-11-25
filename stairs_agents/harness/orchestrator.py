"""바깥 루프: 역할마다 안쪽 루프(LoopRunner)를 돌리고, 남은 문제를 owner별로 나눠 해당 역할부터 다시 돌린다.

    ┌──────────────────────────── 바깥 루프 (최대 outer_rounds) ────────────────────────────┐
    │  mechanics ──▶ (designer ∥ developer) ──▶ publisher ──▶ 플레이테스트(밸런스 재확인)   │
    │      ▲              ▲          ▲              │                    │                   │
    │      └──────────────┴──────────┴── 라우터: 문제의 owner로 되돌림 ◀─┘                   │
    └───────────────────────────────────────────────────────────────────────────────────────┘

- 의존 관계: mechanics가 바뀌면 developer와 publisher를 다시, designer가 바뀌면 publisher를 다시 돈다.
- 되돌린 문제는 그 역할의 첫 차례 피드백(initial_feedback)으로 들어간다.
- 결과: output/harness/ 에 ledger.jsonl(차례마다 한 줄), summary.json, summary.md
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from ..util import Paths, log, write_json
from .core import Budget, Issue, Ledger, LoopRunner, feedback_text
from .roles import DesignerRole, DeveloperRole, MechanicsRole, PublisherRole

ORDER = ["mechanics", "designer", "developer", "publisher"]
DOWNSTREAM = {"mechanics": {"developer", "publisher"}, "designer": {"publisher"},
              "developer": {"publisher"}, "publisher": set()}


def _closure(roles: set[str]) -> set[str]:
    out = set(roles)
    for r in roles:
        out |= DOWNSTREAM[r]
    return out


def run_harness(llm, paths: Paths, roles: list[str] | None = None, budget: Budget | None = None,
                outer_rounds: int = 3, use_resource_db: bool = True, skip_test: bool = False) -> dict:
    t0 = time.time()
    hdir = paths.out / "harness"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "ledger.jsonl").unlink(missing_ok=True)
    ledger = Ledger(hdir / "ledger.jsonl")
    runner = LoopRunner(ledger, budget or Budget())
    enabled = [r for r in ORDER if r in (roles or ORDER) and not (r == "publisher" and skip_test)]
    make = {"mechanics": lambda: MechanicsRole(llm, paths),
            "designer": lambda: DesignerRole(llm, paths, use_resource_db),
            "developer": lambda: DeveloperRole(llm, paths),
            "publisher": lambda: PublisherRole(llm, paths)}
    agents = {r: make[r]() for r in enabled}
    results: dict[str, dict] = {}
    todo, routed = set(enabled), {}

    for outer in range(1, outer_rounds + 1):
        log.info("[하네스] 바깥 루프 %d/%d: %s", outer, outer_rounds, ", ".join(r for r in ORDER if r in todo))
        ledger.write(event="outer", round=outer, todo=sorted(todo))

        def go(r):
            fb = routed.pop(r, None)
            return r, runner.run(agents[r], fb)

        if "mechanics" in todo:
            results["mechanics"] = go("mechanics")[1]
        par = [r for r in ("designer", "developer") if r in todo]
        with ThreadPoolExecutor(max_workers=2) as ex:
            for r, res in ex.map(go, par):
                results[r] = res
        if "publisher" in todo:
            results["publisher"] = go("publisher")[1]

        # 라우터: 남은 문제 중 다른 역할 책임(owner)인 것을 그 역할로 돌린다.
        # 자기 역할 문제는 안쪽 루프가 이미 예산을 다 썼으므로 다시 돌리지 않는다.
        cross: dict[str, list[Issue]] = {}
        for r, res in results.items():
            for i in res["issues"]:
                owner = i.get("owner") or r
                if owner != r and owner in agents and i["severity"] in ("high", "mid"):
                    cross.setdefault(owner, []).append(Issue(**i))
        for o in list(cross):   # 재생 모드처럼 다시 만들 수 없는 역할에 넘겨도 결과가 같으므로 넘기지 않는다
            if not agents[o].can_regenerate():
                log.info("[하네스] %s 책임 문제 %d건: 다시 만들 수 없어 넘기지 않음 (summary에 남김)", o, len(cross.pop(o)))
        if not cross:
            log.info("[하네스] 다른 역할로 넘길 문제가 없어 멈춤")
            break
        routed = {o: feedback_text(o, 1, iss, []) for o, iss in cross.items()}
        todo = _closure(set(cross)) & set(enabled)
        ledger.write(event="route", round=outer, to={o: len(i) for o, i in cross.items()})

    summary = {"seconds": round(time.time() - t0, 1),
               "roles": {r: {k: results[r][k] for k in ("verdict", "rounds", "best_round", "stop")} for r in results},
               "metrics": {r: results[r]["metrics"] for r in results}}
    write_json(hdir / "summary.json", {**summary, "issues": {r: results[r]["issues"] for r in results}})
    lines = ["# 하네스 실행 요약", "", "| 역할 | 판정 | 차례 | 최선 차례 | 멈춘 이유 |", "|---|---|---|---|---|"]
    lines += [f"| {r} | {v['verdict']} | {v['rounds']} | {v['best_round']} | {v['stop']} |" for r, v in summary["roles"].items()]
    (hdir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("[하네스] 완료 (%.1f초): %s", summary["seconds"],
             ", ".join(f"{r} {v['verdict']}" for r, v in summary["roles"].items()))
    return {**summary, "results": results}
