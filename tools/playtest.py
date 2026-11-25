"""승급의 계단 실시간 플레이테스트: 실제 키 입력으로 플레이어 유형별 플레이를 흉내 낸다.

게임 폴더를 임시 폴더로 복사하고 game.js에 내부 상태를 읽는 한 줄만 더한 뒤(원본은 그대로),
Playwright Chromium으로 유형마다 여러 판을 실제 키 입력으로 플레이한다.

  python tools/playtest.py                         # demo, 유형마다 5판
  python tools/playtest.py --game demo_api         # demo_api
  python tools/playtest.py --game output/build --runs 3
  python tools/playtest.py --game demo --json result.json

--game 에는 index.html 과 game.js 가 있는 폴더를 준다. 엔진 종류(demo 계열 / demo_api 계열)는
game.js 내용으로 알아낸다. 유형의 수치는 가정값이므로 결과는 실제 사람의 승률이 아니라 경향을 보는 용도다.
필요한 것: pip install -r requirements.txt, playwright install chromium
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 이름: (초당 계단 수, 방향 실수 확률, 패링 타이밍 표준편차(초), 패링 놓침 확률)
PROFILES = {
    "숙련자": (6.0, 0.02, 0.05, 0.03),
    "보통": (4.5, 0.04, 0.08, 0.08),
    "초보": (3.5, 0.07, 0.12, 0.15),
}

# 엔진별: game.js에 더할 줄, 상태 읽기, 결과 읽기
# 커피는 막으면 안 되므로 계획하지 않는다. 경쟁 사원은 막을 쪽이 정해진 뒤(locked)에만 패링을 계획한다 (계단을 따라오는 동안 쪽과 도착 시각이 바뀐다)
ENGINES = {
    "demo": {
        "anchor": "    if (G) Object.assign(T, {",
        "inject": "    window.__G = G; ",
        "inject_before": True,
        "state": """() => { const G = window.__G, T = window.__stairs; if (!G) return null;
          const hz = T.hazard || {};
          return {t: G.t, dir: G.dirs[G.step], days: G.days, ended: T.screen !== 'play' && T.screen !== 'pause',
                  wetDanger: !!(hz.nextWet && (hz.live || hz.shockIn < 0.3)),
                  atk: G.attacks.filter(a => !a.done && a.locked !== false && a.kind !== 'coffee').map(a => ({side: a.side, hitAt: a.hitAt}))}; }""",
        "result": """() => { const G = window.__G, T = window.__stairs;
          return {kind: G.result, floor: T.floor, steps: T.steps, score: T.score, hearts: T.hearts,
                  wrong: T.log.filter(x => x === 'hurt:wrong-step').length, coffee: T.log.filter(x => x === 'hurt:coffee').length, fell: T.log.includes('crack:fall'),
                  attack: T.log.filter(x => x === 'hurt:attack').length,
                  heal: T.log.filter(x => x.startsWith('heal:')).length}; }""",
        "ended_wait": "window.__stairs.screen === 'result'",
    },
    "demo_api": {
        "anchor": "function dirAt(i) { ensureStairs(i + 1); return st.dirs[i]; }",
        "inject": "\nwindow.__dirAt = dirAt; window.__run = () => run;",
        "inject_before": False,
        "state": """() => { const r = window.__run(); if (!r) return null;
          const hz = window.__stairs.hazard || {};
          return {t: r.time, dir: window.__dirAt(r.steps), days: r.days, ended: !!r.ended,
                  wetDanger: !!(hz.nextWet && (hz.live || hz.shockIn < 0.3)),
                  atk: r.projs.filter(p => !p.done && p.locked !== false && p.type !== 'coffee').map(p => ({side: p.side, hitAt: p.impactT}))}; }""",
        "result": """() => { const r = window.__run(), log = window.__stairs.log;
          return {kind: r.ended.kind, floor: r.floor, steps: r.steps, score: r.score, hearts: r.hearts,
                  wrong: log.filter(l => l.includes('(wrong)')).length,
                  attack: log.filter(l => l.includes('(attack)')).length,
                  heal: log.filter(l => l.includes('(floor)')).length}; }""",
        "ended_wait": "window.__run() && window.__run().ended",
    },
}


def detect(game_js: str) -> str:
    if ENGINES["demo_api"]["anchor"] in game_js:
        return "demo_api"
    if ENGINES["demo"]["anchor"] in game_js:
        return "demo"
    sys.exit("game.js 형식을 알 수 없습니다 (demo / demo_api 계열이 아님).")


def instrument(game_dir: Path, work: Path) -> tuple[Path, str]:
    """게임 폴더를 work로 복사하고 상태 노출 줄을 더한다. (index.html 경로, 엔진 이름)"""
    dst = work / "game"
    shutil.copytree(game_dir, dst)
    js_path = dst / "game.js"
    js = js_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    name = detect(js)
    e = ENGINES[name]
    new = e["inject"] + e["anchor"] if e["inject_before"] else e["anchor"] + e["inject"]
    js_path.write_text(js.replace(e["anchor"], new, 1), encoding="utf-8")
    return dst / "index.html", name


def start(page, url: str):
    page.goto(url)
    page.wait_for_function("window.__stairs && window.__stairs.ready")
    page.keyboard.press("Enter")
    page.wait_for_function("window.__stairs.screen === 'lobby'")
    page.keyboard.press("Enter")
    page.wait_for_function("window.__stairs.screen === 'play'")


def run_one(page, engine: dict, url: str, prof, rng) -> dict:
    rate, miss_dir, sigma, miss_parry = prof
    start(page, url)
    t0 = time.perf_counter()
    next_step, planned, min_days, injected = t0, {}, 99.0, 0
    while True:
        s = page.evaluate(engine["state"])
        now = time.perf_counter()
        if s is None or s["ended"]:
            break
        min_days = min(min_days, s["days"])
        off = now - s["t"]  # 게임 시간 -> 실제 시간
        for a in s["atk"]:
            key = (a["side"], round(a["hitAt"], 4))
            if key not in planned:  # 도착 0.1초 전을 노린다 (판정은 도착 직전 0.20초)
                planned[key] = None if rng.random() < miss_parry else off + a["hitAt"] - 0.1 + rng.gauss(0, sigma)
        for key in [k for k, w in planned.items() if w is not None and w <= now]:
            page.keyboard.press("KeyQ" if key[0] < 0 else "KeyE")
            planned[key] = None
        if now >= next_step and s.get("wetDanger"):   # 다음 칸이 젖었고 전기가 흐르거나 곧 흐르면 사람처럼 잠깐 기다린다
            next_step = now + 0.05
        if now >= next_step:
            d = s["dir"]
            if rng.random() < miss_dir:
                d, injected = -d, injected + 1
            page.keyboard.press("ArrowLeft" if d < 0 else "ArrowRight")
            next_step = now + rng.gauss(1 / rate, 0.15 / rate)
    r = page.evaluate(engine["result"])
    return {
        "결과": "승급" if r["kind"] == "promote" else "구조조정",
        "층": r["floor"], "칸": r["steps"], "점수": r["score"], "남은하트": r["hearts"],
        "시간": round(time.perf_counter() - t0, 1), "최저일수": round(min_days, 1),
        "피격_공격": r["attack"], "피격_발판": r["wrong"], "의도한실수": injected, "층회복": r["heal"],
    }


def bot_run(page, engine: dict, url: str) -> dict:
    page.goto(url.replace("?", "?bot=1&", 1))
    page.wait_for_function("window.__stairs && window.__stairs.ready")
    page.keyboard.press("Enter")
    page.keyboard.press("Enter")
    t0 = time.perf_counter()
    page.wait_for_function(engine["ended_wait"], timeout=120000)
    page.wait_for_timeout(100)
    r = page.evaluate(engine["result"])
    return {"결과": "승급" if r["kind"] == "promote" else "구조조정", "층": r["floor"], "남은하트": r["hearts"],
            "점수": r["score"], "시간": round(time.perf_counter() - t0, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description="승급의 계단 실시간 플레이테스트")
    ap.add_argument("--game", default="demo", help="index.html과 game.js가 있는 폴더 (기본 demo)")
    ap.add_argument("--runs", type=int, default=5, help="유형마다 판 수 (기본 5)")
    ap.add_argument("--profiles", default=",".join(PROFILES), help="쉼표로 구분한 유형 (기본 전부)")
    ap.add_argument("--no-bot", action="store_true", help="내장 봇(?bot=1) 기준선을 건너뜀")
    ap.add_argument("--headed", action="store_true", help="브라우저 창을 띄워서 실행")
    ap.add_argument("--json", help="결과를 JSON 파일로 저장")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    game_dir = (ROOT / args.game) if not Path(args.game).is_absolute() else Path(args.game)
    if not (game_dir / "index.html").exists() or not (game_dir / "game.js").exists():
        sys.exit(f"{game_dir} 에 index.html, game.js 가 없습니다.")
    from playwright.sync_api import sync_playwright

    out = {"game": str(game_dir), "runs": {}, "bot": None, "page_errors": []}
    with tempfile.TemporaryDirectory(prefix="stairs_playtest_") as tmp:
        index, name = instrument(game_dir, Path(tmp))
        engine = ENGINES[name]
        url = index.as_uri() + "?seed={seed}&mute=1"
        print(f"게임: {game_dir} (엔진 {name}), 유형마다 {args.runs}판")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not args.headed)
            page = browser.new_page(viewport={"width": 960, "height": 540})
            page.on("pageerror", lambda e: out["page_errors"].append(str(e)))
            for pname in [x.strip() for x in args.profiles.split(",") if x.strip()]:
                if pname not in PROFILES:
                    sys.exit(f"알 수 없는 유형: {pname} (가능: {', '.join(PROFILES)})")
                rng = random.Random(pname)
                rows = []
                for seed in range(1, args.runs + 1):
                    row = run_one(page, engine, url.format(seed=seed), PROFILES[pname], rng)
                    rows.append(row)
                    print(pname, json.dumps(row, ensure_ascii=False), flush=True)
                out["runs"][pname] = rows
            if not args.no_bot:
                out["bot"] = bot_run(page, engine, url.format(seed=1))
                print("봇", json.dumps(out["bot"], ensure_ascii=False))
            browser.close()

    print("\n| 유형 | 승급 | 도달 층 | 평균 피격(공격/발판) | 최저 남은 일수 |")
    print("|---|---|---|---|---|")
    for pname, rows in out["runs"].items():
        wins = sum(r["결과"] == "승급" for r in rows)
        floors = sorted(r["층"] for r in rows)
        atk = sum(r["피격_공격"] for r in rows) / len(rows)
        wrong = sum(r["피격_발판"] for r in rows) / len(rows)
        print(f"| {pname} | {wins}/{len(rows)} | {floors[0]}~{floors[-1]}층 | {atk:.1f} / {wrong:.1f} | {min(r['최저일수'] for r in rows)} |")
    mismatch = [r for rows in out["runs"].values() for r in rows if r["피격_발판"] != r["의도한실수"]]
    print("입력 확인:", "발판 피격 = 의도한 실수 (정상)" if not mismatch else f"{len(mismatch)}판에서 불일치")
    print("페이지 오류:", out["page_errors"] or "없음")
    if args.json:
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("저장:", args.json)
    return 1 if out["page_errors"] or mismatch else 0


if __name__ == "__main__":
    raise SystemExit(main())
