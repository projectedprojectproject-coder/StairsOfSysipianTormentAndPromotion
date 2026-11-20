"""Developer QA 에이전트.

역할: Developer 결과물(output/dev_out)이 기획서 04 수치, Mechanics 명세, 조작·화면 규칙, 스프라이트 정의 계약,
      PoC 제약(파일로 직접 열기, 외부 요청 없음)을 지키는지 정적으로 확인하고 고칠 점을 정리한다.
      실제로 띄워 보는 동작 확인은 Publisher가 맡는다.
입력: output/dev_out/ (index.html, game.js, sprite_definition.json), docs/ASSET_LIST.md,
      output/mech_out/mechanics.json (있으면), prompts/developer.md (규칙 목록)
출력: output/qa_out/developer_qa.json, developer_qa.md
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time

from .contract import load_contract
from .qa import QAReport, ask_review, save
from .util import Paths, read

# 기획서 04 주요 수치 (mechanics.json이 없을 때 쓰는 기본 목록)
GDD_VALUES = {"하트": 3, "남은 일수 최대": 30, "1일 길이(초)": 0.33, "패링 성공 +일": 1.5, "패링 판정(초)": 0.2,
              "공격 예고(초)": 1.0, "승급 층": 20}
KEYS = {"←": "ArrowLeft", "→": "ArrowRight", "Q 패링": "KeyQ", "E 패링": "KeyE", "ESC 일시정지": "Escape", "Enter 결정": "Enter"}
SCREENS = ["title", "lobby", "play", "pause", "result"]


def config_block(js: str) -> str:
    """game.js의 CONFIG = { ... } 블록 (중괄호 짝 맞춤)."""
    m = re.search(r"CONFIG\s*=\s*\{", js)
    if not m:
        return ""
    depth, i = 0, m.end() - 1
    for j in range(i, len(js)):
        depth += {"{": 1, "}": -1}.get(js[j], 0)
        if depth == 0:
            return js[i: j + 1]
    return js[i:]


def numbers(block: str) -> set[float]:
    code = re.sub(r"//[^\n]*|/\*.*?\*/", "", block, flags=re.S)
    return {float(n) for n in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])", code)}


class DeveloperQAAgent:
    name = "qa_developer"

    def __init__(self, llm, paths: Paths):
        self.llm = llm
        self.paths = paths

    def _required_values(self) -> dict:
        mech = self.paths.mech_out / "mechanics.json"
        if not mech.exists():
            return dict(GDD_VALUES)
        cfg = json.loads(read(mech)).get("config", {})
        out = {}
        for k, v in cfg.items():
            val = v.get("value") if isinstance(v, dict) else v
            src = (v.get("source", "") if isinstance(v, dict) else "")
            if "04" in src and isinstance(val, (int, float)) and not isinstance(val, bool):
                out[k] = val
        return out or dict(GDD_VALUES)

    def run(self, round_no: int = 1) -> dict:
        t0 = time.time()
        p = self.paths
        d = p.dev_out
        rep = QAReport("developer")
        missing = [f for f in ("index.html", "game.js", "sprite_definition.json") if not (d / f).exists()]
        if not rep.check("필수 파일", not missing, "없음: " + ", ".join(missing) if missing else "3개 모두 있음", "high",
                         fix="Developer를 다시 실행해 빠진 파일을 만든다"):
            return save(p, rep, "Developer QA 보고서", t0)
        html, js = read(d / "index.html"), read(d / "game.js")
        try:
            sd = json.loads(read(d / "sprite_definition.json"))
            rep.check("스프라이트 정의 JSON", True, "읽음")
        except json.JSONDecodeError as e:
            rep.check("스프라이트 정의 JSON", False, f"JSON 오류: {e}", "high", "sprite_definition.json")
            return save(p, rep, "Developer QA 보고서", t0)

        # ---- 불러오는 순서와 문법
        i_def, i_js = html.find("sprite_definition.js"), html.find("game.js")
        order_ok = 0 <= i_def < i_js
        rep.check("스크립트 순서", order_ok, "sprite_definition.js → game.js 순서" + ("" if order_ok else "가 아님"), "high",
                  "index.html", "<script src=\"assets/sprite_definition.js\">를 game.js 앞에 둔다")
        node = shutil.which("node")
        if node:
            r = subprocess.run([node, "--check", str(d / "game.js")], capture_output=True, text=True, encoding="utf-8")
            rep.check("JS 문법 (node --check)", r.returncode == 0, (r.stderr or "통과").strip()[:300], "high", "game.js",
                      "문법 오류를 고친다")
        else:
            rep.check("JS 문법 (node --check)", True, "node 없음, 건너뜀", "low")

        # ---- CONFIG와 수치
        block = config_block(js)
        if rep.check("CONFIG 객체", bool(block), "game.js에 CONFIG = { ... } 가 있어야 함", "high", "game.js",
                     "기획서 04 수치를 game.js 맨 위 CONFIG에 모은다"):
            nums = numbers(block)
            req = self._required_values()
            miss = [f"{k}={v}" for k, v in req.items() if float(v) not in nums]
            rep.metrics["확인한 수치"] = ", ".join(f"{k}={v}" for k, v in req.items())
            rep.check("기획서 04 수치", not miss, "CONFIG에 없는 값: " + (", ".join(miss) or "없음"), "mid", "CONFIG",
                      "빠진 값을 CONFIG에 넣는다 (기획서 초안 값 그대로)")
            rep.check("기획서 미정 표시", "기획서 미정" in block, "'기획서 미정' 주석 " + ("있음" if "기획서 미정" in block else "없음"), "low",
                      "CONFIG", "기획서에 없는 값마다 '기획서 미정' 주석을 단다")

        # ---- 조작과 화면
        lost = [n for n, code in KEYS.items() if code not in js]
        rep.check("조작 키", not lost, "처리하지 않는 키: " + (", ".join(lost) or "없음"), "high", "입력",
                  "기획서 04 조작(← → Q E, ESC, Enter)을 모두 처리한다")
        gone = [s for s in SCREENS if not re.search(rf"['\"]{s}['\"]", js)]
        rep.check("화면 5종", not gone, "없는 화면: " + (", ".join(gone) or "없음"), "high", "화면",
                  "05-1~05-5 화면을 모두 만든다")
        rep.check("시험 훅", "__stairs" in js, "window.__stairs " + ("있음" if "__stairs" in js else "없음 (Publisher 동작 확인용)"), "high", "game.js",
                  "window.__stairs에 ready, screen, floor, log를 노출한다")

        # ---- 스프라이트 정의 계약
        contract = load_contract(p.docs / "ASSET_LIST.md")
        absent = [f"{g}.{a}" for g, ids in (("sprites", contract["sheets"]), ("images", contract["images"]),
                                              ("sounds", contract["sounds"])) for a in ids if a not in sd.get(g, {})]
        rep.check("정의에 에셋 모두", not absent, "없음: " + (", ".join(absent) or "없음"), "high", "sprite_definition.json",
                  "ASSET_LIST의 모든 ID를 정의에 넣는다")
        bad_names = []
        for aid, c in contract["sheets"].items():
            s = sd.get("sprites", {}).get(aid, {})
            bad_names += [f"{aid}.{v}" for v in c["variants"] if s and v not in s.get("variants", [])]
            bad_names += [f"{aid}.{a}" for a in c["animations"] if s and a not in s.get("animations", [])]
        rep.check("변형·애니메이션 이름", not bad_names, ", ".join(bad_names[:10]) or "ASSET_LIST와 같음", "high",
                  "sprite_definition.json", "ASSET_LIST와 같은 이름을 쓴다")
        fmt = sd.get("accepted_formats", {})
        rep.check("수용 형식", "png" in fmt.get("image", []) and {"mp3", "ogg"} & set(fmt.get("audio", [])),
                  f"{fmt}", "mid", "sprite_definition.json", "이미지 png, 사운드 mp3/ogg를 받는다")

        def used(aid: str) -> bool:
            stem = re.sub(r"\d+$", "", aid)
            return bool(re.search(rf"['\"]{re.escape(aid)}['\"]", js) or
                        (stem != aid and re.search(rf"['\"]{re.escape(stem)}['\"]", js)))
        unused = [f"{g}.{a}" for g in ("sprites", "images", "sounds") for a in sd.get(g, {}) if not used(a)]
        rep.check("정의한 에셋 사용", not unused, "game.js에서 쓰지 않음: " + (", ".join(unused) or "없음"), "low",
                  "game.js", "정의한 에셋을 화면에 쓰거나 정의에서 뺀다")
        ps = sd.get("pixel_scale")
        if ps:
            rep.check("pixel_scale 사용", "pixel_scale" in js, f"정의 pixel_scale={ps}인데 game.js가 읽지 않음", "mid",
                      "game.js", "DEF.pixel_scale로 스프라이트를 1/pixel_scale 크기로 그린다")

        # ---- PoC 제약
        ext = sorted(set(re.findall(r"https?://[^\s'\"`)]+", js + html)))
        rep.check("외부 요청 없음", not ext, "외부 주소: " + (", ".join(ext[:5]) or "없음"), "mid", "game.js",
                  "모든 에셋을 assets/에서 불러온다 (오프라인, file:// 실행)")
        rep.check("fetch 없음", "fetch(" not in js, "fetch는 file://에서 막힌다", "mid", "game.js",
                  "sprite_definition.js(전역 변수)와 Image/Audio 요소로 불러온다")
        rep.check("eval 없음", not re.search(r"\beval\(|new Function\(", js), "eval/new Function 사용", "mid", "game.js")
        rep.metrics["game.js"] = f"{len(js.splitlines())}줄, {len(js)}자"

        rules = read(p.prompts / "developer.md")
        user = ("# Developer 규칙 검사 결과\n" + json.dumps(rep.to_dict(), ensure_ascii=False, indent=1) +
                "\n\n# Developer가 지켜야 할 규칙 (prompts/developer.md)\n" + rules +
                "\n\n# game.js\n" + js + "\n\n위 출력 형식으로 검토하라.")
        ask_review(self.llm, p, rep, self.name, user, round_no=round_no)
        return save(p, rep, "Developer QA 보고서", t0)
