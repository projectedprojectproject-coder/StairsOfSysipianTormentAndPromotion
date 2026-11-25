"""Mechanics 명세(mechanics.json)만으로 판정을 계산하는 밸런스 시뮬레이션 (하네스 평가기용).

tools/sim_spec.py를 하네스에서 부를 수 있게 패키지로 옮기고, PoC 결정으로 늘어난 위협을 다룬다.
- parry: 맞는 쪽을 판정 창 안에 눌러야 막힌다 (결재판, 경쟁 사원, 모니터, 전화기, 서류, 서류가방)
- dodge: 막으면 안 된다. 잘못 누르면 하트 -1 (커피)
- multi: 1~5회 연속으로 막아야 한다 (포스트잇)
- 발판 위험(금 간 계단, 젖은 계단)은 칸 비율과 플레이어의 머뭇거림으로 근사한다 (모델 근사, 실제 게임과 다를 수 있음)
"""
from __future__ import annotations

import random
from collections import Counter

# (초당 계단 수, 방향 실수, 패링 타이밍 표준편차, 패링 놓침, 커피 잘못 막기, 발판 위험 회피) — tools/playtest.py 유형에 두 값을 더함
PROFILES = {
    "숙련자": (6.0, 0.02, 0.05, 0.03, 0.03, 0.97),
    "보통": (4.5, 0.04, 0.08, 0.08, 0.08, 0.92),
    "초보": (3.5, 0.07, 0.12, 0.15, 0.15, 0.85),
}
DT = 1 / 30
MILESTONES = (20, 40, 60, 80, 100)


class Sim:
    def __init__(self, spec: dict):
        self.C = {k: v["value"] for k, v in spec["config"].items()}
        self.floors = {f["floor"]: f for f in spec["floors"]}
        self.threats = spec["threats"]

    def _parry(self, rng, sigma, miss) -> bool:
        if rng.random() < miss:
            return False
        off = 0.1 + rng.gauss(0, sigma)   # 도착 0.1초 전을 노린다
        return 0 <= off <= self.C["parryWindow"]

    def run(self, prof, rng, start_floor: int = 1, max_floor: int = 100):
        rate, miss_dir, sigma, miss_parry, coffee_err, hazard_avoid = prof
        C, FL, TH = self.C, self.floors, self.threats
        hearts, days, t = C["maxHearts"], C["maxDays"], 0.0
        floor, step = start_floor, 0
        next_step, next_atk, pending = 1 / rate, C.get("firstAttackDelay", 3.0), []
        hits = Counter()
        gap = C.get("minAttackGap", 0.8)
        while True:
            if floor >= max_floor or FL[floor].get("ending") == "ceo":
                return "CEO", floor, hits
            f = FL[floor]
            t += DT
            days -= DT / C["dayDuration"] * f["drainMult"]
            if days <= 0:
                hits["일수 소진"] += 1
                return "구조조정", floor, hits
            if f.get("attackInterval") and t >= next_atk and f.get("mix"):
                kind = rng.choices(list(f["mix"]), weights=list(f["mix"].values()))[0]
                arrive = t + TH[kind].get("warn", C["warnTime"])
                if pending and arrive - pending[-1][0] < gap:
                    arrive = pending[-1][0] + gap
                pending.append((arrive, kind))
                next_atk = t + f["attackInterval"] * (0.8 + rng.random() * 0.4)
            for a in [a for a in pending if a[0] <= t]:
                pending.remove(a)
                kind = a[1]
                th = TH[kind]
                if th.get("kind") == "dodge":
                    ok = rng.random() >= coffee_err
                elif th.get("kind") == "multi":
                    need = rng.randint(1, th.get("maxBlocks", 5))
                    ok = all(self._parry(rng, sigma, miss_parry) for _ in range(need))
                else:
                    ok = self._parry(rng, sigma, miss_parry)
                if ok:
                    if th.get("kind") != "dodge":
                        days = min(C["maxDays"], days + C["parryDays"])
                else:
                    hearts -= 1
                    hits[kind] += 1
                    if hearts <= 0:
                        return "구조조정", floor, hits
            if t >= next_step:
                next_step = t + max(0.05, rng.gauss(1 / rate, 0.15 / rate))
                if rng.random() < miss_dir:
                    hearts -= 1
                    hits["발판 실수"] += 1
                    if hearts <= 0:
                        return "구조조정", floor, hits
                    continue
                hz = f.get("hazards", {})
                for name, p in hz.items():   # 위험 칸에 올라섰고 피하지 못하면 즉시 구조조정
                    if rng.random() < p and rng.random() > hazard_avoid:
                        hits[name] += 1
                        return "구조조정", floor, hits
                days = min(C["maxDays"], days + C["stepDays"])
                step += 1
                if step >= f["stairs"]:
                    step, floor = 0, floor + 1
                    if f.get("review"):
                        hearts = min(C["maxHearts"], hearts + C["promoteHeal"])
                    if "floorHeal" in C:
                        hearts = min(C["maxHearts"], hearts + C["floorHeal"])


def reach_rates(spec: dict, runs: int = 200, seed: int = 7) -> dict:
    """유형별 이정표(20/40/60/80/100층) 도달률과 주된 패배 원인."""
    sim, out = Sim(spec), {}
    for name, prof in PROFILES.items():
        rng = random.Random(f"{seed}-{name}")
        reach, cause, total = Counter(), Counter(), 0
        for _ in range(runs):
            res, fl, hits = sim.run(prof, rng)
            total += fl
            for m in MILESTONES:
                if fl >= m or res == "CEO":
                    reach[m] += 1
            if res != "CEO" and hits:
                cause[max(hits, key=hits.get)] += 1
        out[name] = {"reach": {str(m): round(reach[m] / runs, 3) for m in MILESTONES},
                     "avgFloor": round(total / runs, 1),
                     "topCauses": [k for k, _ in cause.most_common(3)]}
    return out
