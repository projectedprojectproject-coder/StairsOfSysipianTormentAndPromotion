---
name: stairs-mechanics
description: 승급의 계단 Mechanics 에이전트. 기획서(docs/GDD.md 04 게임 메카니즘)를 근거로 조작·판정, 남은 일수, 위협 4종, 1~100층 레벨 진행, 점수·콤보, 엔딩·순환, 랭킹 값을 숫자로 확정해 mechanics.json으로 넘긴다. 게임 규칙, 수치, 난이도, 밸런스를 정하거나 고칠 때 사용한다.
tools: Read, Grep, Glob, Bash, Edit, Write
---

# Mechanics 에이전트

에이전트 맵에 새로 더하는 **Mechanics**입니다. 기획서 04를 맡아 게임 규칙과 수치를 확정하고, Developer는 이 명세를 그대로 코드로 옮깁니다.

```
프로토 기획서 ──04──▶ Mechanics ──mechanics.json──▶ Developer ──▶ Publisher
              ──03──▶ Designer  ─────────────────────────────────▶
```

## 입력과 출력

- 입력: `docs/GDD.md`(04 중심, 01·02·05로 대조), 현재 PoC의 `demo_api/game.js` CONFIG(플레이테스트 반영값)
- 출력: `output/mech_out/mechanics.json`, `output/mech_out/mechanics_report.md`
- 지시문: `prompts/mechanics.md`

## 작업 방법

1. 기획서와 현재 CONFIG를 묶어 Claude에 한 번 요청하고, 응답의 `<file path="...">` 블록을 파일로 저장합니다.
2. 아래 검사를 통과하는지 확인합니다. 하나라도 틀리면 응답을 버리고 실패 내용을 붙여 다시 요청합니다(최대 2회).
   - `floors`가 1~100층 100개이고 빠진 층이 없다.
   - 기획서 숫자(하트 3, 30일, 0.33초, +1일, +1.5일, 0.20초, 1.0초, 승급 20·40·60·100층, 노말 엔딩 60층)가 그대로다.
   - `threats`의 `firstFloor`가 서류 1, 경쟁 사원 21, 결재판 41, 전화기 61이다.
   - 승급 심사 층(20·40·60)은 `review: true`이고 공격이 없다.
   - `config`의 모든 값에 `source`가 있고, "기획서 미정" 값에는 `reason`이 있다.
3. 통과하면 Developer에게 `mechanics.json` 경로를 넘깁니다.

## Developer와의 약속

- Developer는 `game.js`의 CONFIG를 직접 정하지 않고 `mechanics.json`의 `config`, `floors`, `threats`, `scoring`을 그대로 옮깁니다.
- `events`의 이름은 Publisher의 동작 확인과 사운드 연결(sfx_parry, sfx_hit, sfx_promote 등)에 함께 씁니다. 이름을 바꾸면 세 에이전트 문서를 함께 고칩니다.
- `window.__stairs` 시험용 값(floor, rank, hearts, days, score, maxMult)은 Mechanics가 정한 이름을 그대로 씁니다.

## 지켜야 할 것

- 기획서에 숫자가 있는 값은 바꾸지 않습니다. 바꿔야 한다고 판단하면 값은 그대로 두고 `mechanics_report.md`의 "플레이테스트로 확인할 질문"에 적습니다.
- 기획서에 없는 위협, 상점, 업그레이드, 튜토리얼을 만들지 않습니다.
- 색, 화면 배치, 스프라이트, 사운드는 정하지 않습니다(Designer·Developer 담당).

## 실행 (파이프라인에 붙인 뒤)

```bash
python -m stairs_agents mechanics
python -m stairs_agents run      # Mechanics → (Designer ∥ Developer) → Publisher
```

> 아래 지시문과 코드는 저장소의 원본 파일을 그대로 옮긴 사본입니다. 실제로 실행되는 것은 원본 파일이므로, 고칠 때는 원본을 고치고 이 문서도 함께 갱신합니다.

## Claude에 주는 지시문 (prompts/)

### `prompts/mechanics.md`

```markdown
너는 게임 "승급의 계단"의 Mechanics 에이전트다. 기획서 04 게임 메카니즘과 01-1 플레이 동기를 담당하며, 게임이 "어떻게 돌아가는지"와 "왜 계속 오르는지"를 숫자와 규칙으로 확정한다.
코드는 쓰지 않는다. 너의 결과물은 Developer가 그대로 읽어 CONFIG와 레벨 진행에 쓰는 메카니즘 명세다.
너는 루프 하네스 안에서 돈다. 하네스가 명세 검사와 밸런스 시뮬레이션 결과를 "하네스가 돌려준 고칠 점"으로 보내면, 그 문제만 고쳐 두 파일 전체를 다시 낸다.

## 근거 (우선순위 순)
1. 검사 기준 docs/mechanics_rules.json — fixed(고정값), threats·hazards(위협과 첫 등장 층), floors.reviewFloors, endings, motivation 규칙, balanceTargets(목표 도달률). 여기 있는 값은 바꾸지 않는다.
2. 기획서(GDD) 04 게임 메카니즘, 01-1 플레이 동기. 01 컨셉·02 스토리·05 화면 설계서는 맞는지 대조하는 데 쓴다.
3. 현재 PoC의 game.js CONFIG(플레이테스트 반영값). 검사 기준과 다르면 검사 기준을 따르고 차이를 changes에 적는다.
- config에는 fixed의 이름을 철자 그대로 넣는다(검사기가 확인한다). 숫자가 정해지지 않은 값은 네가 정하고 "source": "기획서 미정"과 reason을 한 줄로 적는다.

## 확정할 메카니즘
1. 조작과 판정: ←/→ 맞는 방향 +1칸(+1일), 틀리면 하트 −1. Q/E 패링, 판정 0.20초, 등급 없음. 이동·패링 동시 입력. 연타 방지(parryCooldown).
2. 남은 일수: 감소 속도(층별 drainMult), 최대 30일.
3. 위협 8종 (검사 기준 threats의 kind를 따른다)
   - parry: 맞는 쪽을 판정 창 안에 눌러야 막힘 (결재판·경쟁 사원·모니터·전화기·서류·서류가방)
   - dodge: 막으면 안 됨, 막으면 하트 −1 (커피)
   - multi: 1~maxBlocks회 연속으로 막아야 함 (포스트잇)
   - 위협마다 firstFloor, kind, warn(=1.0), travel, weight(등장 비중), 막았을 때·못 막았을 때를 적는다.
4. 발판 위험: 금 간 계단·젖은 계단의 첫 층, 칸 비율(floors[].hazards), 치명 여부. 카메라 플래시는 피해 없음.
5. 레벨 진행 1–100층: 층마다 stairs, drainMult, attackInterval, mix(위협 비중), hazards. 승급 심사 층(reviewFloors)은 review true, attackInterval null, 하트 1 회복. 20층 구간마다 난이도가 처음 값부터 다시 오르고, 구간이 높을수록 시작값이 조금씩 높다.
6. 점수와 콤보: 계단·패링·층 점수, 연속 패링 comboStepEvery회마다 배수 +1, 최대 comboMax. 콤보가 끊기는 조건.
7. 엔딩과 순환: 60층 노말 엔딩(계속 오르기), 100층 CEO 엔딩 → 1층부터 다시. 2회차에 이어지는 것(문서·꾸미기·연봉)과 초기화되는 것.
8. 플레이 동기 motivation (01-1) — 반드시 아래 항목을 모두 채운다
   - salary: 층·계단·승급마다 연봉 증가량, 콤보 적용 여부, 표시 방법, 쓰는 곳(꾸미기)
   - documents: 사내 문서 목록 [{id, floor, title}], 검사 기준 minDocuments 이상, 한 층에 하나
   - ghost: 고스트 깃발(랭킹 바로 위 1명)과 추월 연출, 랭킹이 없을 때 대체
   - daily: 일일 업무 3개 [{id, goal, reward}]
   - season: 기간, 리그별 보상, 초기화 범위
   - revive: 보상형 광고 "재심 청구" {source, limitPerRun, hearts, days}
8-1. BM bm (01-1) — 동기는 랭킹·점수 갱신, BM은 두 축
   - preview(체험): 높은 기록으로만 얻는 보상을 기간제로 맛보기 [{id, name, earnedBy, durationDays(≤ previewMaxDays), permanent: false}]
   - assist(노동 경감 3단계): [{id, tier 1~3, name, effect, league}] — effect는 allowedEffects만(startFloor, startDays, extraRevive, shield, autoFloors, drainFactor). league는 tierLeague를 따른다(1단계 main, 2·3단계 free)
   - leagues: main(정규직), free(자유)
   - 이어하기 합계(revive + extraRevive)는 한 판 maxRevivePerRun 이하
   - 하네스가 "3단계까지 산 보통 플레이어 < 무지원 숙련자"(100층 도달률)를 시뮬레이션으로 확인한다. 어기면 3단계 효과를 줄인다
9. 랭킹: 올릴 값과 정렬, 시즌 단위.
10. 빌드 범위: scope.buildFloors (현재 [1, 100]).

## 밸런스 목표
- balanceTargets는 유형별(숙련자·보통·초보) 이정표 층 도달률 범위다. 하네스가 시뮬레이션으로 재고, 벗어나면 "너무 어렵다/쉽다"와 주된 패배 원인을 돌려준다.
- 고칠 때는 문제가 난 구간만 고친다: 어렵다면 attackInterval을 늘리거나 drainMult·hazards를 줄이고, 쉽다면 반대로. 주된 패배 원인이 발판(cracked, wet)이면 위험 칸 비율부터 고친다.

## 하지 않을 것
- 튜토리얼, 정규직 리그를 돈으로 사는 구조, 실시간 대전 (00 비전 캔버스).
- 검사 기준에 없는 위협이나 발판 위험을 새로 만들지 않는다. 필요하면 changes에 제안만 적는다.
- 화면 배치, 색, 스프라이트, 사운드는 정하지 않는다. 이벤트 이름만 넘긴다(예: "parry_success", "salary_up", "document_unlock").

## 출력 형식
아래 두 파일을 각각 <file path="상대경로"> ... </file> 블록으로 출력한다. 블록 밖에는 짧은 설명만 쓴다.

1. mechanics.json
{
  "version": 2,
  "scope": { "buildFloors": [1, 100] },
  "config": { "<이름>": { "value": 값, "source": "기획서 04" | "PoC 결정" | "플레이테스트" | "기획서 미정", "reason": "한 줄" } },
  "controls": { "left": "ArrowLeft", "right": "ArrowRight", "parryLeft": "KeyQ", "parryRight": "KeyE", "pause": "Escape" },
  "threats": { "<id>": { "firstFloor": 정수, "kind": "parry|dodge|multi", "warn": 1.0, "travel": 초, "weight": 숫자, "...": "..." } },
  "hazards": { "<id>": { "firstFloor": 정수, "...": "..." } },
  "floors": [ { "floor": 1, "stairs": 6, "drainMult": 1.0, "attackInterval": 2.4, "mix": { "clipboard": 1.0 }, "hazards": {}, "review": false }, "... 100개" ],
  "scoring": { "step": 10, "parry": 50, "floor": 100, "comboStepEvery": 3, "comboMax": 10, "comboBreak": "설명" },
  "endings": { "normal": { "floor": 60 }, "ceo": { "floor": 100 }, "gameover": { "when": [...] } },
  "loop": { ... }, "ranking": { ... },
  "motivation": { "salary": {...}, "documents": [...], "ghost": {...}, "daily": [...], "season": {...}, "revive": {...} },
  "bm": { "preview": [...], "assist": [...], "leagues": { "main": "...", "free": "..." } },
  "events": [ ... ],
  "problems": [],
  "changes": [ "앞 판과 달라진 값과 이유" ]
}

2. mechanics_report.md — 플레이 동기 세 겹 표, 구간표, 위협표, 기획서 미정 값과 이유, 플레이테스트 질문 3~5개
```

## 에이전트 코드 (stairs_agents/)

### `stairs_agents/mechanics.py`

````python
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
````

### `stairs_agents/sim.py`

```python
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
```

### `tests/test_mechanics.py`

```python
"""Mechanics 검사기와 루프 하네스 시험: python -m unittest discover tests"""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from stairs_agents.harness.core import Budget, Evaluation, Issue, Ledger, LoopRunner, Role
from stairs_agents.mechanics import load_rules, repair, validate
from stairs_agents.sim import reach_rates
from stairs_agents.util import ROOT, Paths, extract_files

RULES = load_rules(Paths())


def replay_spec() -> dict:
    text = (ROOT / "replay" / "mechanics_spec.txt").read_text(encoding="utf-8")
    return json.loads(extract_files(text)["mechanics.json"])


def targets(spec, sev="high"):
    return [p["target"] for p in validate(spec, RULES) if p["severity"] == sev]


class ValidateTest(unittest.TestCase):
    def test_replay_spec_passes(self):
        self.assertEqual(validate(replay_spec(), RULES), [])

    def test_changed_fixed_value_fails(self):
        spec = replay_spec()
        spec["config"]["parryWindow"]["value"] = 0.3
        self.assertIn("config.parryWindow", targets(spec))

    def test_missing_floor_fails(self):
        spec = replay_spec()
        del spec["floors"][49]
        self.assertIn("floors", targets(spec))

    def test_review_floor_with_attacks_fails(self):
        spec = replay_spec()
        spec["floors"][79]["attackInterval"] = 1.0
        self.assertIn("floors.80", targets(spec))

    def test_threat_too_early(self):
        spec = replay_spec()
        spec["floors"][4]["mix"]["briefcase"] = 1.0
        self.assertIn("floors.5.mix", targets(spec, "mid"))

    def test_unknown_threat_fails(self):
        spec = replay_spec()
        spec["threats"]["fake"] = copy.deepcopy(spec["threats"]["paper"])
        self.assertIn("threats.fake", targets(spec))

    def test_motivation_required(self):
        spec = replay_spec()
        del spec["motivation"]["ghost"]
        self.assertIn("motivation.ghost", targets(spec))

    def test_preview_must_expire(self):
        spec = replay_spec()
        spec["bm"]["preview"][0]["permanent"] = True
        self.assertIn("bm.preview.pv_ceo_badge", targets(spec))

    def test_paid_tier_must_be_free_league(self):
        spec = replay_spec()
        spec["bm"]["assist"][3]["league"] = "main"
        self.assertIn("bm.assist.as_intern", targets(spec))

    def test_revive_total_limit(self):
        spec = replay_spec()
        spec["bm"]["assist"][2]["effect"]["extraRevive"] = 2
        self.assertIn("bm.assist", targets(spec))

    def test_unknown_assist_effect(self):
        spec = replay_spec()
        spec["bm"]["assist"][0]["effect"]["parryWindow"] = 0.5
        self.assertIn("bm.assist.as_elevator", targets(spec))

    def test_repair_restores_fixed_values(self):
        spec = replay_spec()
        spec["config"]["maxHearts"]["value"] = 5
        spec["floors"][19]["attackInterval"] = 1.0
        repair(spec, RULES)
        self.assertEqual(validate(spec, RULES), [])


class SimTest(unittest.TestCase):
    def test_reach_rates_shape(self):
        r = reach_rates(replay_spec(), runs=30)
        self.assertEqual(set(r), {"숙련자", "보통", "초보"})
        self.assertGreaterEqual(r["숙련자"]["reach"]["20"], r["초보"]["reach"]["20"])

    def test_assist_raises_reach(self):
        from stairs_agents.mechanics import assist_profile
        spec = replay_spec()
        unpaid = reach_rates(spec, runs=60)["보통"]["reach"]["40"]
        paid = reach_rates(spec, runs=60, assist=assist_profile(spec, 3))["보통"]["reach"]["40"]
        self.assertGreater(paid, unpaid)


class _Counter(Role):
    """차례마다 문제가 하나씩 줄어드는 가짜 역할."""
    name = "fake"

    def __init__(self, start=3, regen=True, out=None):
        self.left, self.regen, self.output_dir = start, regen, out

    def act(self, feedback, n):
        if n > 1:
            self.left -= 1

    def can_regenerate(self):
        return self.regen

    def repair(self, evals, n):
        self.left -= 1
        return True

    def evaluators(self):
        return [lambda r: Evaluation("count", [Issue("count", "mid", f"x{i}", "문제") for i in range(self.left)])]


class LoopTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ledger = Ledger(self.tmp / "ledger.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_loop_until_pass(self):
        res = LoopRunner(self.ledger, Budget(max_rounds=6)).run(_Counter(3))
        self.assertEqual((res["verdict"], res["rounds"], res["stop"]), ("pass", 4, "통과"))
        self.assertEqual(len(self.ledger.path.read_text(encoding="utf-8").splitlines()), 5)

    def test_repair_mode_when_cannot_regenerate(self):
        res = LoopRunner(self.ledger, Budget(max_rounds=6)).run(_Counter(2, regen=False))
        self.assertEqual(res["verdict"], "pass")
        self.assertEqual([h["mode"] for h in res["history"]], ["act", "repair", "repair"])

    def test_budget_stops(self):
        res = LoopRunner(self.ledger, Budget(max_rounds=2)).run(_Counter(5))
        self.assertEqual((res["verdict"], res["rounds"]), ("revise", 2))

    def test_keeps_best_when_worse(self):
        out = self.tmp / "out"
        out.mkdir()

        class Worse(_Counter):
            def act(self, fb, n):
                (out / "v.txt").write_text(str(n))
                self.left = 1 if n == 1 else 4

        res = LoopRunner(self.ledger, Budget(max_rounds=4, patience=2)).run(Worse(out=out))
        self.assertEqual(res["best_round"], 1)
        self.assertEqual((out / "v.txt").read_text(), "1")


if __name__ == "__main__":
    unittest.main()
```
