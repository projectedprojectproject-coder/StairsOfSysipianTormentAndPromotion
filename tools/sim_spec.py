"""Mechanics 명세(mechanics.json, 1~100층)의 수치와 규칙으로 판정만 계산하는 시뮬레이션.

실제 게임 코드가 아니라 명세 표(floors, threats, config)를 그대로 따르는 모델이다.
아직 빌드가 없는 21층 이후의 난이도 경향을 보는 데 쓴다. 플레이어 유형은 tools/playtest.py와 같다.

  python tools/sim_spec.py                                  # replay/mechanics_spec.txt, 유형마다 300판
  python tools/sim_spec.py --spec output/mech_out/mechanics.json --runs 1000

한계: 결재판 좌우 동시(Q+E)와 전화기 고속 비행의 "체감" 난도는 모델링하지 않는다(두 키를 각각 같은 오차로 누른다고 가정).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES = {  # (초당 계단 수, 방향 실수, 패링 타이밍 표준편차, 패링 놓침) — tools/playtest.py와 같다
    "숙련자": (6.0, 0.02, 0.05, 0.03),
    "보통": (4.5, 0.04, 0.08, 0.08),
    "초보": (3.5, 0.07, 0.12, 0.15),
}
DT = 1 / 60


def load_spec(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.search(r'<file path="mechanics.json">\n(.*?)\n</file>', text, re.S)  # 재생 응답 형식
    return json.loads(m.group(1) if m else text)


class Sim:
    def __init__(self, spec: dict):
        self.spec = spec
        self.C = {k: v["value"] for k, v in spec["config"].items()}
        self.floors = {f["floor"]: f for f in spec["floors"]}
        self.threats = spec["threats"]

    def parry_ok(self, rng, sigma, miss):
        """도착 0.1초 전을 노리고 누른다. 판정은 도착 직전 parryWindow 초."""
        if rng.random() < miss:
            return False
        off = 0.1 + rng.gauss(0, sigma)
        return 0 <= off <= self.C["parryWindow"]

    def run(self, prof, rng, floor_heal=True, start_floor=1):
        rate, miss_dir, sigma, miss_parry = prof
        C, FL, TH = self.C, self.floors, self.threats
        hearts, days, t = C["maxHearts"], C["maxDays"], 0.0
        floor, step_in_floor = start_floor, 0
        next_step, next_atk, pending = 1 / rate, C["firstAttackDelay"], []
        hits = Counter()
        while True:
            f = FL[floor]
            if f.get("ending") == "ceo":
                return "CEO", floor, hits
            t += DT
            days -= DT / C["dayDuration"] * f["drainMult"]
            if days <= 0:
                hits["일수 소진"] += 1
                return "구조조정", floor, hits
            if f["attackInterval"] and t >= next_atk:
                kind = rng.choices(list(f["mix"]), weights=list(f["mix"].values()))[0]
                th = TH[kind]
                dual = th.get("dual") and rng.random() < th.get("dualChance", 0)
                arrive = t + th["warn"]
                if pending and arrive - pending[-1][0] < C["minAttackGap"]:
                    arrive = pending[-1][0] + C["minAttackGap"]
                pending.append((arrive, kind, dual))
                next_atk = t + f["attackInterval"] * (0.8 + rng.random() * 0.4)
            for a in [a for a in pending if a[0] <= t]:
                pending.remove(a)
                _, kind, dual = a
                ok = self.parry_ok(rng, sigma, miss_parry) and (not dual or self.parry_ok(rng, sigma, miss_parry))
                if ok:
                    days = min(C["maxDays"], days + C["parryDays"])
                else:
                    hearts -= 1
                    hits[kind + (" 동시" if dual else "")] += 1
                    if hearts <= 0:
                        return "구조조정", floor, hits
            if t >= next_step:
                next_step = t + max(0.05, rng.gauss(1 / rate, 0.15 / rate))
                if rng.random() < miss_dir:
                    hearts -= 1
                    hits["발판"] += 1
                    if hearts <= 0:
                        return "구조조정", floor, hits
                else:
                    days = min(C["maxDays"], days + C["stepDays"])
                    step_in_floor += 1
                    if step_in_floor >= f["stairs"]:
                        step_in_floor, floor = 0, floor + 1
                        if f.get("review"):
                            hearts = min(C["maxHearts"], hearts + C["promoteHeal"])
                        if floor_heal and "floorHeal" in C:
                            hearts = min(C["maxHearts"], hearts + C["floorHeal"])

    def hold_rate(self):
        """패링을 모두 성공할 때 남은 일수를 지키는 데 필요한 초당 이동 수 (명세 balance 대조용)."""
        out = {}
        for n in (1, 19, 39, 59, 99):
            f = self.floors[n]
            out[n] = round((f["drainMult"] / self.C["dayDuration"] - self.C["parryDays"] / f["attackInterval"]) / self.C["stepDays"], 2)
        return out


def table(sim, label, runs, floor_heal, start_floor=1):
    print(f"\n### {label}")
    print("| 유형 | 20층 | 40층 | 60층(노말) | 100층(CEO) | 평균 도달 층 | 주된 패배 원인 |")
    print("|---|---|---|---|---|---|---|")
    for name, prof in PROFILES.items():
        rng = random.Random(name + label)
        reach, cause, floors = Counter(), Counter(), []
        for _ in range(runs):
            res, fl, hits = sim.run(prof, rng, floor_heal, start_floor)
            floors.append(fl)
            for m in (20, 40, 60, 100):
                if fl >= m or res == "CEO":
                    reach[m] += 1
            if res != "CEO" and hits:
                cause[max(hits, key=hits.get)] += 1
        pct = lambda m: f"{reach[m] / runs * 100:.0f}%"
        top = ", ".join(f"{k} {v / runs * 100:.0f}%" for k, v in cause.most_common(3)) or "-"
        print(f"| {name} | {pct(20)} | {pct(40)} | {pct(60)} | {pct(100)} | {sum(floors) / runs:.1f} | {top} |")


def main() -> int:
    ap = argparse.ArgumentParser(description="Mechanics 명세 1~100층 시뮬레이션")
    ap.add_argument("--spec", default=str(ROOT / "replay" / "mechanics_spec.txt"),
                    help="mechanics.json 또는 재생 응답 파일 (기본 replay/mechanics_spec.txt)")
    ap.add_argument("--runs", type=int, default=300, help="유형마다 판 수 (기본 300)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sim = Sim(load_spec(Path(args.spec)))
    print(f"명세: {args.spec}, 유형마다 {args.runs}판")
    print("명세 balance.stepsPerSecToHold:", sim.spec.get("balance", {}).get("stepsPerSecToHold"))
    print("재계산 (패링 모두 성공):", sim.hold_rate())
    table(sim, "명세 그대로 (층마다 하트 회복 O)", args.runs, True)
    table(sim, "층마다 하트 회복 X (비교용)", args.runs, False)
    table(sim, "61층부터 시작 (하드 구간만, 회복 O)", args.runs, True, 61)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
