---
name: stairs-developer-qa
description: 승급의 계단 Developer QA 에이전트. Developer 결과물(index.html, game.js, sprite_definition.json)이 기획서 04 수치, Mechanics 명세, 조작·화면 규칙, 스프라이트 정의 계약, PoC 제약을 지키는지 정적 검사와 Claude 코드 검토로 확인하고 고칠 점을 보고한다. 게임 코드를 쓴 뒤 품질을 확인할 때 사용한다.
tools: Read, Grep, Glob, Bash
---

# Developer QA 에이전트

Developer 바로 뒤에 도는 품질 확인 에이전트입니다. 코드를 고치지 않고, Developer가 고칠 수 있는 지시를 보고합니다. 실제로 띄워 보는 동작 확인(9개 항목)은 Publisher가 맡습니다.

## 입력과 출력

- 입력: `output/dev_out/`, `docs/ASSET_LIST.md`, `output/mech_out/mechanics.json`(있으면), `prompts/developer.md`
- 출력: `output/qa_out/developer_qa.md`·`developer_qa.json`

## 확인 방법

1. 규칙 검사(LLM 없음): 필수 파일, `sprite_definition.js`를 `game.js`보다 먼저 불러오는지, `node --check` 문법, `CONFIG` 객체와 기획서 04 수치(mechanics.json에서 출처가 04인 값), "기획서 미정" 표시, 조작 키(← → Q E ESC Enter), 화면 5종, 시험 훅 `window.__stairs`, 정의에 ASSET_LIST 에셋·이름 모두, 수용 형식, 정의한 에셋 사용 여부, `pixel_scale` 사용, 외부 주소·`fetch`·`eval` 없음.
2. Claude 검토: 규칙 결과, Developer 규칙, `game.js`를 보내 판정 규칙·진행·화면 흐름·버그 위험을 검토받습니다(`prompts/qa_developer.md`). 재생 모드에 `qa_developer_review.txt`가 없으면 건너뜁니다.
3. 판정과 고침 반복(최대 11번)은 Designer QA와 같습니다. 차례별 판정: `output/qa_out/developer_loop.json`

## 2단계: 화면 대조 (Publisher 뒤)

`qa_screens.py`가 Publisher가 찍은 실제 게임 화면(`output/dist/screens`)을 컨셉 화면(`data/concept/05-1_title.png`, `05-2_lobby.png`, `05-3_play.png`, `05-5_result_gameover.png`)과 비교합니다. 비교할 화면과 컨셉의 번호 요소는 `data/concept/regions.json`의 `screens`에 있습니다.

- 규칙 검사: 밝고 어두운 배치의 상관(구도, 0.3 이상), 강조색(빨강) 요소 자리의 겹침(0.25 이상), 색 거리, 밝기 차
- Claude 검토: 대조표(`output/qa_out/screens_contact.png`, 왼쪽 컨셉, 오른쪽 게임)와 번호 요소 목록으로 요소마다 있는지, 자리와 모양이 맞는지 보고 고칠 쪽(Developer/Designer)을 적습니다 (`prompts/qa_screens.md`)
- 보고서: `output/qa_out/screens_qa.md`
- 고침 반복: pass가 아니면 Developer를 고쳐 다시 만들고 Developer QA, Publisher, 화면 대조를 다시 돈다 (최대 11번, `screens_loop.json`)

## 실행

```bash
python -m stairs_agents qa-screens --replay replay   # 화면 대조만
python -m stairs_agents qa-developer --replay replay
python -m stairs_agents qa --replay replay      # Designer QA와 함께
```

> 아래 지시문과 코드는 저장소의 원본 파일을 그대로 옮긴 사본입니다. 실제로 실행되는 것은 원본 파일이므로, 고칠 때는 원본을 고치고 이 문서도 함께 갱신합니다.

## Claude에 주는 지시문 (prompts/)

### `prompts/qa_developer.md`

```markdown
너는 게임 "승급의 계단"의 Developer QA 에이전트다. Developer가 쓴 game.js가 기획서와 Developer 규칙을 지키는지 코드를 읽고 검토하고, Developer가 바로 고칠 수 있는 지시를 돌려준다. 실제로 띄워 보는 동작 확인(Playwright 9개 항목)은 Publisher가 따로 하므로, 너는 코드에서만 보이는 문제를 찾는다.

## 받는 것
- 규칙 검사 결과 JSON (코드로 잰 항목: 필수 파일, 스크립트 순서, JS 문법, CONFIG 수치, 조작 키, 화면 5종, 시험 훅, 스프라이트 정의 계약, pixel_scale, 외부 요청)
- Developer 규칙 (prompts/developer.md)
- game.js 전체

## 볼 것
1. 판정 규칙 (04): 남은 일수가 계속 줄고 계단 이동(+1일)과 패링 성공(+1.5일)으로 늘어나는가. 방향 실수와 막지 못한 공격은 하트 -1인가. 남은 일수 0 또는 하트 0이면 구조조정인가. 패링 판정 창(도착 직전 0.20초)과 예고(1.0초 전)가 코드대로인가.
2. 진행: 20층 도달 시 승급 결과, 승급 시 하트 1 회복, 새 층마다 하트 1 회복(최대 3), 11층부터 경쟁 사원이 공격의 약 40%이고 Q/E로 막히는가.
3. 화면 흐름: 타이틀 → 로비 → 플레이 → 일시정지(ESC, 남은 일수 멈춤) → 결과. 타이틀의 톱니 → 설정 → 조작법.
4. 버그 위험: 프레임 시간(dt)에 따라 판정이 바뀌는 곳, 키 반복 처리, 일시정지 중 시간이 흐르는 곳, 배열을 돌며 지우는 곳, 화면 밖 좌표, 탭 전환 시 멈춤.
5. 상수: 기획서 수치가 코드 곳곳에 숫자로 흩어져 있지 않고 CONFIG에 모여 있는가.
6. 규칙 검사에서 문제로 나온 항목이 실제로 문제인지 판단해 설명한다.

## 하지 말 것
- 기획서에 없는 기능을 요구하지 않는다. 스타일 취향만으로 high를 주지 않는다.
- high는 규칙이 틀리거나 게임이 멈추거나 진행이 막히는 경우에만 쓴다.

## 출력 형식
<json> 와 </json> 사이에 아래 JSON만 넣는다.
{
  "verdict": "pass" 또는 "revise",
  "summary": "두세 문장 총평",
  "issues": [
    { "asset": "함수나 위치 (예: game.js update() 패링 판정)", "severity": "high" | "mid" | "low",
      "problem": "무엇이 틀렸고 어떤 상황에서 드러나는가", "fix": "고칠 코드 방향" }
  ]
}
```

### `prompts/qa_screens.md`

```markdown
너는 게임 "승급의 계단"의 화면 대조 QA 에이전트다(Developer QA 2단계). Publisher가 실제 게임에서 찍은 화면을 기획서 컨셉 화면과 비교해, 빠지거나 다른 요소를 찾고 누가 무엇을 고칠지 지시한다.

## 받는 것
- 규칙 검사 결과 JSON: 화면마다 구도 상관(밝고 어두운 배치), 강조색(빨강) 위치 겹침, 색 거리, 밝기 차
- 화면별 컨셉 번호 요소 목록 (컨셉 그림의 분홍 번호와 같다)
- 대조표 이미지: 줄마다 왼쪽이 컨셉, 오른쪽이 실제 게임 화면 (타이틀, 로비, 플레이, 구조조정 결과)

## 볼 것
1. 번호 요소마다: 있는가, 자리(화면의 어느 쪽)와 크기가 비슷한가, 모양(판, 버튼, 카드, 표)이 같은 종류인가.
2. 분위기: 배경 장면(사무실, 거리)과 조명, 색이 컨셉과 같은 게임으로 보이는가.
3. 글자: 컨셉의 문구와 같은 정보가 같은 자리에 있는가 (값은 실제 플레이 기록이라 달라도 된다).
4. 고칠 쪽: 배치·버튼·표·글자는 Developer(game.js), 배경 그림·캐릭터·소품은 Designer(명세).

## 하지 말 것
- 컨셉에 없는 요소를 요구하지 않는다. 플레이 기록 값(층, 점수)이 다른 것은 문제로 보지 않는다.
- high는 컨셉의 번호 요소가 통째로 없거나 화면의 뜻이 달라지는 경우에만 쓴다.

## 출력 형식
<json> 와 </json> 사이에 아래 JSON만 넣는다.
{
  "verdict": "pass" 또는 "revise",
  "summary": "두세 문장 총평",
  "issues": [
    { "asset": "화면/요소 번호 (예: 2_lobby/3)", "severity": "high" | "mid" | "low",
      "problem": "컨셉과 무엇이 다른가", "fix": "Developer: ... 또는 Designer: ..." }
  ]
}
```

## 에이전트 코드 (stairs_agents/)

### `stairs_agents/qa_developer.py`

```python
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
```

### `stairs_agents/qa_screens.py`

```python
"""화면 대조 QA (Developer QA 2단계, Publisher 뒤에 돈다).

역할: Publisher가 실제 게임에서 찍은 화면(output/dist/screens)을 컨셉 화면(data/concept)과 나란히 놓고
      구도, 강조색(빨강) 위치, 색, 밝기를 재고, 컨셉의 번호 요소 목록과 함께 Claude 시각 검토를 받는다.
      화면 배치와 UI는 Developer, 그림은 Designer의 몫이므로 문제마다 어느 쪽이 고칠지 적는다.
입력: output/dist/screens/*.png, data/concept/regions.json 의 "screens" (화면 -> 컨셉 이미지, 번호 요소)
출력: output/qa_out/screens_qa.md, screens_qa.json, screens_contact.png
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from PIL import Image, ImageDraw

from . import concept
from .qa import QAReport, ask_review, save
from .util import Paths, log

ACCENT = concept.rgb("#A13D3D")
GRID = (64, 36)


def _gray(im: Image.Image) -> list[float]:
    g = im.convert("L").resize(GRID, Image.Resampling.BOX)
    return list(g.get_flattened_data() if hasattr(g, "get_flattened_data") else g.getdata())


def layout_corr(a: Image.Image, b: Image.Image) -> float:
    """두 화면의 밝고 어두운 배치 상관계수 (-1~1, 1이면 구도가 같다)."""
    x, y = _gray(a), _gray(b)
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sum((p - mx) * (q - my) for p, q in zip(x, y))
    sx = sum((p - mx) ** 2 for p in x) ** 0.5
    sy = sum((q - my) ** 2 for q in y) ** 0.5
    return round(sxy / (sx * sy), 3) if sx and sy else 0.0


def accent_mask(im: Image.Image) -> list[bool]:
    small = im.convert("RGB").resize(GRID, Image.Resampling.BOX)
    px = small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata()
    return [concept.dist(c, ACCENT) < 95 and c[0] > c[1] + 35 for c in px]


def accent_iou(a: Image.Image, b: Image.Image) -> tuple[float, float]:
    """강조색(빨강) 영역의 겹침과, 컨셉에서 강조색이 차지하는 비율."""
    ma, mb = accent_mask(a), accent_mask(b)
    inter = sum(p and q for p, q in zip(ma, mb)); union = sum(p or q for p, q in zip(ma, mb))
    return (round(inter / union, 3) if union else 1.0), round(sum(mb) / len(mb), 3)


def run_screen_qa(llm, paths: Paths, round_no: int = 1) -> dict:
    t0 = time.time()
    rep = QAReport("screens")
    spec = concept.load_regions()
    screens = spec.get("screens") or {}
    shots = paths.dist / "screens"
    base = concept.REGIONS.parent
    pairs = []
    if not rep.check("화면 캡처", shots.exists(), "output/dist/screens " + ("있음" if shots.exists() else "없음 (Publisher를 먼저 실행)"), "high"):
        return save(paths, rep, "화면 대조 QA 보고서 (Developer QA 2단계)", t0)
    for name, s in screens.items():
        shot = shots / f"{name}.png"
        cfile = base / spec["images"][s["concept"]]
        if not shot.exists() or not cfile.exists():
            rep.check(f"{name} 파일", False, f"없음: {shot.name if not shot.exists() else cfile.name}", "mid", name)
            continue
        a, b = Image.open(shot).convert("RGB"), Image.open(cfile).convert("RGB")
        corr = layout_corr(a, b)
        iou, share = accent_iou(a, b)
        pd = concept.palette_distance([c["hex"] for c in concept.dominant(b, 8)], [c["hex"] for c in concept.dominant(a, 8)])
        dl = round(abs(concept.luminance(a) - concept.luminance(b)), 1)
        rep.metrics[name] = f"컨셉 {s['concept']}: 구도 상관 {corr}, 강조색 겹침 {iou} (컨셉 강조색 {share:.0%}), 색 거리 {pd}, 밝기 차 {dl}"
        who = s.get("owner", "Developer")
        rep.check(f"{name} 구도", corr >= 0.3, f"밝고 어두운 배치 상관 {corr} (0.3 이상 목표)", "mid", name,
                  f"{who}: 컨셉 {s['concept']}의 요소 배치를 따른다 — " + "; ".join(s["elements"][:3]))
        if share >= 0.01:
            rep.check(f"{name} 강조색 위치", iou >= 0.25, f"빨간 요소 겹침 {iou} (0.25 이상 목표)", "mid", name,
                      f"{who}: 컨셉에서 빨간 요소(버튼·판정 판·D-일수)가 있는 자리에 같은 강조색 요소를 둔다")
        rep.check(f"{name} 색·밝기", pd <= 80 and dl <= 35, f"색 거리 {pd}, 밝기 차 {dl}", "low", name,
                  "Designer: 배경 이미지의 색과 밝기를 컨셉에 맞춘다")
        pairs.append((name, s, a, b))
    contact = _contact(pairs, paths)
    rep.metrics["대조표"] = str(contact)
    user = ("# 화면 대조 규칙 검사 결과\n" + json.dumps(rep.to_dict(), ensure_ascii=False, indent=1) +
            "\n\n# 화면별 컨셉 번호 요소\n" + "\n".join(
                f"## {n} (컨셉 {s['concept']})\n" + "\n".join("- " + e for e in s["elements"]) for n, s, _, _ in pairs) +
            "\n\n대조표 이미지는 줄마다 왼쪽이 컨셉, 오른쪽이 실제 게임 화면이다. 요소마다 있는지, 자리와 모양이 맞는지 보고, "
            "issues의 asset에는 '화면/요소 번호', fix 앞에는 고칠 쪽(Developer 또는 Designer)을 적어라.")
    ask_review(llm, paths, rep, "qa_screens", user, images=[str(contact)], round_no=round_no)
    return save(paths, rep, "화면 대조 QA 보고서 (Developer QA 2단계)", t0)


def _contact(pairs, paths: Paths) -> Path:
    W, H, pad = 640, 360, 10
    sheet = Image.new("RGB", (W * 2 + pad * 3, (H + pad + 14) * max(1, len(pairs)) + pad), (40, 42, 47))
    d = ImageDraw.Draw(sheet)
    y = pad
    for name, s, shot, con in pairs:
        d.text((pad, y), f"concept {s['concept']}", fill=(232, 230, 223))
        d.text((W + pad * 2, y), f"game {name}", fill=(232, 230, 223))
        sheet.paste(con.resize((W, H)), (pad, y + 14)); sheet.paste(shot.resize((W, H)), (W + pad * 2, y + 14))
        y += H + pad + 14
    out = paths.out / "qa_out" / "screens_contact.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    log.info("[화면 QA] 대조표: %s", out)
    return out
```

### `stairs_agents/qa.py`

```python
"""품질 확인(QA) 에이전트 공통 부분: 문제 기록, Claude 검토 요청, 보고서 쓰기.

QA 에이전트는 두 단계로 확인한다.
1. 규칙 검사: 코드로 재는 항목 (LLM 없이 항상 돈다)
2. Claude 검토: 규칙 검사 결과와 결과물(이미지 또는 코드)을 Claude에 보내 기획서·컨셉과 맞는지 묻는다.
   재생 모드에서 응답 파일(replay/qa_<대상>_review.txt)이 없으면 이 단계는 건너뛰고 그 사실을 보고서에 적는다.

판정: 규칙 검사에 high 문제가 하나라도 있으면 fail, high는 없고 mid가 있거나 Claude가 revise라고 하면 revise, 아니면 pass.

고침 반복 (qa_loop): 판정이 pass가 아니면 QA의 고칠 점을 만든 에이전트에게 돌려줘 다시 만들게 하고 다시 확인한다.
최대 MAX_ROUNDS(11)번까지 돌고, 통과하거나, 문제 목록이 앞 차례와 같아 나아지지 않거나,
재생 모드처럼 다시 만들어도 같은 응답이 나오는 경우에는 일찍 멈춘다. 차례마다의 판정은 qa_out/<대상>_loop.json에 남는다.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .llm import LLMError
from .util import Paths, extract_json, load_prompt, log, write_json

SEVERITIES = ("high", "mid", "low")
MAX_ROUNDS = 11


@dataclass
class QAReport:
    target: str                          # "designer" 또는 "developer"
    checks: list = field(default_factory=list)   # {"id","ok","detail"}
    issues: list = field(default_factory=list)   # {"source","asset","severity","problem","fix"}
    metrics: dict = field(default_factory=dict)
    review: dict | None = None
    review_note: str = ""

    def check(self, cid: str, ok: bool, detail: str = "", severity: str = "mid", asset: str = "", fix: str = ""):
        self.checks.append({"id": cid, "ok": bool(ok), "detail": detail})
        if not ok:
            self.issues.append({"source": "규칙", "asset": asset or cid, "severity": severity,
                                "problem": detail or cid, "fix": fix})
        return ok

    @property
    def verdict(self) -> str:
        rule = [i for i in self.issues if i["source"] == "규칙"]
        if any(i["severity"] == "high" for i in rule):
            return "fail"
        if any(i["severity"] == "high" for i in self.issues if i["source"] == "Claude"):
            return "revise"
        if any(i["severity"] == "mid" for i in self.issues) or (self.review or {}).get("verdict") == "revise":
            return "revise"
        return "pass"

    def to_dict(self) -> dict:
        return {"target": self.target, "verdict": self.verdict, "checks": self.checks, "issues": self.issues,
                "metrics": self.metrics, "review": self.review, "review_note": self.review_note}

    def markdown(self, title: str) -> str:
        ok = sum(c["ok"] for c in self.checks)
        lines = [f"# {title}", "", f"판정: **{self.verdict}** · 규칙 검사 {ok}/{len(self.checks)} 통과", ""]
        if self.review_note:
            lines += [f"Claude 검토: {self.review_note}", ""]
        elif self.review:
            lines += ["Claude 검토 요약: " + str(self.review.get("summary", "")), ""]
        lines += ["## 문제와 고칠 점", ""]
        if not self.issues:
            lines.append("없음")
        else:
            lines += ["| 심각도 | 출처 | 대상 | 문제 | 고칠 점 |", "|---|---|---|---|---|"]
            order = {s: i for i, s in enumerate(SEVERITIES)}
            for i in sorted(self.issues, key=lambda x: order.get(x["severity"], 9)):
                cells = [i["severity"], i["source"], i["asset"], i["problem"], i.get("fix", "")]
                lines.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in cells) + " |")
        lines += ["", "## 규칙 검사", "", "| 항목 | 결과 | 내용 |", "|---|---|---|"]
        for c in self.checks:
            lines.append(f"| {c['id']} | {'통과' if c['ok'] else '문제'} | {c['detail']} |")
        if self.metrics:
            lines += ["", "## 수치", ""]
            for k, v in self.metrics.items():
                lines.append(f"- {k}: {v}")
        return "\n".join(lines) + "\n"


def ask_review(llm, paths: Paths, report: QAReport, agent: str, user: str, images=None, round_no: int = 1) -> None:
    """Claude에 검토를 요청하고 응답의 issues를 report에 더한다. 응답이 없으면 건너뛴 이유를 적는다."""
    if llm is None:
        report.review_note = "건너뜀 (LLM 없이 실행)"
        return
    try:
        text = llm.complete(agent, "review" + (f"_r{round_no}" if round_no > 1 else ""), load_prompt(paths, agent), user, images=images)
    except LLMError as e:
        report.review_note = f"건너뜀 ({e})"
        log.info("[%s] Claude 검토 건너뜀: %s", agent, e)
        return
    try:
        rv = extract_json(text)
    except ValueError as e:
        report.review_note = f"응답을 읽지 못함 ({e})"
        return
    report.review = rv
    for i in rv.get("issues", []):
        sev = i.get("severity", "low")
        report.issues.append({"source": "Claude", "asset": i.get("asset", ""),
                              "severity": sev if sev in SEVERITIES else "low",
                              "problem": i.get("problem", ""), "fix": i.get("fix", "")})


def save(paths: Paths, report: QAReport, title: str, t0: float) -> dict:
    out = paths.out / "qa_out"
    out.mkdir(parents=True, exist_ok=True)
    d = report.to_dict()
    write_json(out / f"{report.target}_qa.json", d)
    (out / f"{report.target}_qa.md").write_text(report.markdown(title), encoding="utf-8")
    high = sum(i["severity"] == "high" for i in report.issues)
    log.info("[%s QA] 판정 %s: 문제 %d개 (high %d), 규칙 %d/%d 통과 (%.1f초)", report.target.capitalize(), report.verdict,
             len(report.issues), high, sum(c["ok"] for c in report.checks), len(report.checks), time.time() - t0)
    return d


def feedback_text(report: dict, round_no: int) -> str:
    """QA 보고를 만든 에이전트에게 돌려줄 고칠 점 문구."""
    order = {s: i for i, s in enumerate(SEVERITIES)}
    issues = sorted(report.get("issues", []), key=lambda i: order.get(i["severity"], 9))
    lines = [f"# {report['target']} QA가 돌려준 고칠 점 ({round_no}번째 만들기, 앞 차례 판정 {report['verdict']})",
             "아래 문제를 고쳐 같은 출력 형식으로 다시 내라. 문제가 없는 부분은 그대로 둔다."]
    lines += [f"- [{i['severity']}] {i['asset']}: {i['problem']}" + (f" -> {i['fix']}" if i.get("fix") else "") for i in issues]
    return "\n".join(lines)


def _signature(report: dict) -> tuple:
    return tuple(sorted((i["severity"], i["asset"], i["problem"]) for i in report.get("issues", [])))


def qa_loop(paths: Paths, target: str, produce, check, rounds: int = MAX_ROUNDS, can_retry: bool = True):
    """produce(feedback, round_no)로 만들고 check(round_no)로 확인하기를 판정이 pass가 될 때까지 최대 rounds(<=11)번 되풀이한다.
    (첫 차례의 produce는 feedback=None으로 부른다.) 마지막 결과와 QA 보고를 돌려준다."""
    rounds = max(1, min(MAX_ROUNDS, rounds))
    result = produce(None, 1)
    rep = check(1)
    history, stop = [{"round": 1, "verdict": rep["verdict"], "issues": len(rep["issues"])}], "최대 차례"
    for n in range(2, rounds + 1):
        if rep["verdict"] == "pass":
            stop = "통과"; break
        if not can_retry:
            stop = "다시 만들 수 없음 (재생 모드는 같은 응답을 돌려준다)"; break
        prev = _signature(rep)
        log.info("[%s QA] %d번째 고침: 문제 %d개를 돌려준다", target.capitalize(), n, len(rep["issues"]))
        result = produce(feedback_text(rep, n), n)
        rep = check(n)
        history.append({"round": n, "verdict": rep["verdict"], "issues": len(rep["issues"])})
        if _signature(rep) == prev and rep["verdict"] != "pass":
            stop = "나아지지 않음 (앞 차례와 같은 문제)"; break
    else:
        if rep["verdict"] == "pass":
            stop = "통과"
    rep["loop"] = {"rounds": len(history), "max": rounds, "stop": stop, "history": history}
    write_json(paths.out / "qa_out" / f"{target}_loop.json", rep["loop"])
    log.info("[%s QA] 고침 반복 %d/%d번에서 멈춤: %s (판정 %s)", target.capitalize(), len(history), rounds, stop, rep["verdict"])
    return result, rep
```
