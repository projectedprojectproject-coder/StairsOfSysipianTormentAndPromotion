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

    def run(self, prof, rng, start_floor: int = 1, max_floor: int = 100, assist: dict | None = None):
        """assist: 노동 경감 효과 (mechanics.assist_profile). 없으면 무지원."""
        a = assist or {}
        rate, miss_dir, sigma, miss_parry, coffee_err, hazard_avoid = prof
        C, FL, TH = self.C, self.floors, self.threats
        hearts, t = C["maxHearts"], 0.0
        days = min(C["maxDays"], C["maxDays"] + a.get("startDays", 0))
        floor = max(start_floor, a.get("startFloor", 1)) + a.get("autoFloors", 0)   # 인턴 비서: 시작층부터 n층 자동
        step, revives, shield, drain_k = 0, a.get("extraRevive", 0), a.get("shield", 0), a.get("drainFactor", 1.0)
        result = self._loop(prof, rng, floor, max_floor, hearts, days, t, step, revives, shield, drain_k)
        return result

    def _loop(self, prof, rng, floor, max_floor, hearts, days, t, step, revives, shield, drain_k):
        rate, miss_dir, sigma, miss_parry, coffee_err, hazard_avoid = prof
        C, FL, TH = self.C, self.floors, self.threats
        next_step, next_atk, pending = 1 / rate, C.get("firstAttackDelay", 3.0), []
        hits = Counter()
        gap = C.get("minAttackGap", 0.8)

        def down(cause):
            """구조조정 사유가 생겼을 때: 이어하기가 남았으면 하트 1, 일수 10으로 이어 간다. 이어 가면 True."""
            nonlocal hearts, days, revives
            hits[cause] += 1
            if revives > 0:
                revives -= 1
                hearts, days = 1, max(days, 10)
                return True
            return False

        def hurt(cause):
            nonlocal hearts, shield
            if shield > 0:          # 방탄 서류철: 피격 1회 무시
                shield -= 1
                return True
            hearts -= 1
            if hearts > 0:
                hits[cause] += 1
                return True
            return down(cause)

        while True:
            if floor >= max_floor or FL[floor].get("ending") == "ceo":
                return "CEO", floor, hits
            f = FL[floor]
            t += DT
            days -= DT / C["dayDuration"] * f["drainMult"] * drain_k
            if days <= 0 and not down("일수 소진"):
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
                elif not hurt(kind):
                    return "구조조정", floor, hits
            if t >= next_step:
                next_step = t + max(0.05, rng.gauss(1 / rate, 0.15 / rate))
                if rng.random() < miss_dir:
                    if not hurt("발판 실수"):
                        return "구조조정", floor, hits
                    continue
                fell = False
                for name, p in f.get("hazards", {}).items():   # 위험 칸에 올라섰고 피하지 못하면 즉시 구조조정
                    if rng.random() < p and rng.random() > hazard_avoid:
                        fell = True
                        if not down(name):
                            return "구조조정", floor, hits
                if fell:
                    continue
                days = min(C["maxDays"], days + C["stepDays"])
                step += 1
                if step >= f["stairs"]:
                    step, floor = 0, floor + 1
                    if f.get("review"):
                        hearts = min(C["maxHearts"], hearts + C["promoteHeal"])
                    if "floorHeal" in C:
                        hearts = min(C["maxHearts"], hearts + C["floorHeal"])

def reach_rates(spec: dict, runs: int = 200, seed: int = 7, assist: dict | None = None) -> dict:
    """유형별 이정표(20/40/60/80/100층) 도달률과 주된 패배 원인. assist를 주면 노동 경감을 산 경우."""
    sim, out = Sim(spec), {}
    for name, prof in PROFILES.items():
        rng = random.Random(f"{seed}-{name}")
        reach, cause, total = Counter(), Counter(), 0
        for _ in range(runs):
            res, fl, hits = sim.run(prof, rng, assist=assist)
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
