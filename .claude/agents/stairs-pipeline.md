---
name: stairs-pipeline
description: 승급의 계단 에이전트 파이프라인 조율자. Designer와 Developer를 동시에 실행한 뒤 Publisher를 실행하고, LLM 호출(API/재생/기록), 경로, 에셋 계약, 명령줄을 담당한다. 전체 파이프라인을 실행하거나 공통 계층을 고칠 때 사용한다.
tools: Read, Grep, Glob, Bash, Edit, Write
---

# 파이프라인 (조율과 공통 계층)

에이전트 맵의 실행 순서입니다. **Mechanics**로 규칙과 수치를 먼저 확정하고, **Designer → Designer QA**와 **Developer → Developer QA**를 동시에 돌린 뒤, 둘 다 끝나면 **Publisher**를 돌립니다. QA 보고서는 `output/qa_out/`과 배포 폴더 `output/dist/qa/`에 남습니다. 재생 폴더에 Mechanics 응답이 없으면(예: `replay_api`) Mechanics는 건너뜁니다.

## 구성

| 파일 | 하는 일 |
|---|---|
| `pipeline.py` | 실행 순서 |
| `llm.py` | `ClaudeClient`(API), `ReplayClient`(replay/ 응답 재사용), `RecordingClient`(응답 저장) |
| `util.py` | 경로, 문서 읽기, 응답 파싱 |
| `contract.py` | `docs/ASSET_LIST.md`의 에셋 ID·변형·애니메이션 이름을 읽어 세 에이전트가 같은 기준으로 검사 |
| `__main__.py` | 명령줄 |

## 실행

```bash
python -m stairs_agents run                    # Claude API (ANTHROPIC_API_KEY 필요)
python -m stairs_agents run --record           # 응답을 replay/ 에 저장
python -m stairs_agents run --replay replay    # API 키 없이 실행, 마지막에 "동작 확인 통과"
python -m stairs_agents qa --replay replay     # 이미 만든 결과물에 QA만
python -m unittest discover tests              # Mechanics 검사기, QA 시험
```

선택 사항: `--model`(기본 claude-sonnet-5-5), `--max-tokens`(기본 64000), `--no-resource-db`, `--no-qa`, `--strict-qa`(QA fail이면 Publisher 전에 멈춤).

API 키는 환경 변수 `ANTHROPIC_API_KEY`로만 넘기고, 파일에 적거나 저장소에 올리지 않습니다.

> 아래 지시문과 코드는 저장소의 원본 파일을 그대로 옮긴 사본입니다. 실제로 실행되는 것은 원본 파일이므로, 고칠 때는 원본을 고치고 이 문서도 함께 갱신합니다.

## 에이전트 코드 (stairs_agents/)

### `stairs_agents/pipeline.py`

```python
"""에이전트 맵대로 실행한다: Mechanics로 규칙을 확정하고, Designer와 Developer를 동시에 돌린 뒤 Publisher를 돌린다.

Designer와 Developer 뒤에는 각자의 QA 에이전트(Designer QA, Developer QA)가 바로 이어서 돈다.
Publisher 뒤에는 Developer QA 2단계(화면 대조, qa_screens.py)가 실제 게임 화면을 컨셉 화면과 비교한다.
QA마다 판정이 pass가 아니면 고칠 점을 만든 에이전트에게 돌려줘 다시 만들고 다시 확인하기를 최대 11번 되풀이한다(qa_rounds).
화면 대조가 pass가 아니면 Developer를 고쳐 다시 만들고 Developer QA, Publisher, 화면 대조를 다시 돈다.
QA 판정이 fail이면 경고만 남기고 계속하며, strict_qa=True면 Publisher 전에 멈춘다.
"""
from __future__ import annotations

import shutil
import time
from concurrent.futures import ThreadPoolExecutor

from .designer import DesignerAgent
from .developer import DeveloperAgent
from .mechanics import MechanicsAgent
from .publisher import PublisherAgent
from .qa_designer import DesignerQAAgent
from .qa_developer import DeveloperQAAgent
from .qa import MAX_ROUNDS, qa_loop
from .qa_screens import run_screen_qa
from .llm import ReplayClient
from .util import Paths, log


def run_pipeline(llm, paths: Paths, use_resource_db: bool = True, skip_test: bool = False,
                 qa: bool = True, strict_qa: bool = False, qa_rounds: int = MAX_ROUNDS) -> dict:
    t0 = time.time()
    # Developer가 mechanics.json을 읽으므로 Mechanics를 먼저 끝낸다
    mech = MechanicsAgent(llm, paths).run()
    designer = DesignerAgent(llm, paths, use_resource_db=use_resource_db)
    developer = DeveloperAgent(llm, paths)
    qa_results = {}
    can_retry = llm is not None and not isinstance(llm, ReplayClient)   # 재생 모드는 다시 만들어도 같은 응답

    def with_qa(agent, qa_agent, key):
        if not qa:
            return agent.run()
        res, qa_results[key] = qa_loop(paths, key, lambda fb, n: agent.run(feedback=fb, round_no=n),
                                       lambda n: qa_agent.run(round_no=n), qa_rounds, can_retry)
        return res

    with ThreadPoolExecutor(max_workers=2) as ex:
        f_des = ex.submit(with_qa, designer, DesignerQAAgent(llm, paths), "designer")
        f_dev = ex.submit(with_qa, developer, DeveloperQAAgent(llm, paths), "developer")
        errors = {}
        for name, f in (("Designer", f_des), ("Developer", f_dev)):
            if f.exception():
                errors[name] = f.exception()
                log.error("[%s] 실패: %s", name, f.exception())
        if errors:
            raise RuntimeError("에이전트 실패: " + ", ".join(f"{k}: {v}" for k, v in errors.items()))
        design, dev = f_des.result(), f_dev.result()

    failed = [k for k, r in qa_results.items() if r["verdict"] == "fail"]
    for k in failed:
        log.warning("[%s QA] 판정 fail: output/qa_out/%s_qa.md 를 보세요", k.capitalize(), k)
    if strict_qa and failed:
        raise RuntimeError("QA 판정 fail: " + ", ".join(failed))

    publisher = PublisherAgent(paths)
    if skip_test:
        publisher.test = lambda: False
    pub = publisher.run()
    if qa and not skip_test:  # Developer QA 2단계: Publisher가 찍은 화면을 컨셉 화면과 대조, 고치면 Developer부터 다시
        state = {"pub": pub}

        def rebuild(fb, n):
            if n == 1:
                return state["pub"]
            developer.run(feedback=fb, round_no=n)
            qa_results["developer"] = DeveloperQAAgent(llm, paths).run(round_no=n)
            state["pub"] = publisher.run()
            return state["pub"]
        pub, qa_results["screens"] = qa_loop(paths, "screens", rebuild, lambda n: run_screen_qa(llm, paths, round_no=n),
                                             qa_rounds, can_retry)
    qa_dir = paths.out / "qa_out"
    if qa_dir.exists():  # QA 보고서를 배포 폴더에 함께 둔다
        shutil.copytree(qa_dir, paths.dist / "qa", dirs_exist_ok=True)
    log.info("파이프라인 완료 (%.1f초): %s", time.time() - t0, pub["zip"])
    return {"mechanics": mech, "designer": design, "developer": dev, "qa": qa_results, "publisher": pub}
```

### `stairs_agents/llm.py`

```python
"""LLM 호출 계층.

ClaudeClient   Anthropic Messages API를 스트리밍으로 호출한다 (ANTHROPIC_API_KEY 필요).
ReplayClient   replay/ 폴더에 저장된 응답을 돌려준다. API 키 없이 파이프라인을 시험할 때 쓴다.
RecordingClient 실제 응답을 replay/ 형식으로 저장해 다음 실행에서 재사용할 수 있게 한다.

세 클라이언트 모두 complete(agent, step, system, user, images=None) 하나의 메서드만 가진다.
images는 PNG 파일 경로 목록이며 ClaudeClient만 메시지에 이미지로 넣는다 (QA 에이전트가 화면을 보고 검토할 때 쓴다).
"""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5-5"


class LLMError(RuntimeError):
    pass


class ClaudeClient:
    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 64000, retries: int = 3):
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise LLMError("anthropic 패키지가 없습니다. pip install anthropic") from e
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY 환경 변수가 설정되어 있지 않습니다.")
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        self.retries = retries

    def complete(self, agent: str, step: str, system: str, user: str, images=None) -> str:
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                    "data": base64.b64encode(Path(p).read_bytes()).decode()}} for p in images or []]
        content.append({"type": "text", "text": user})
        last_err = None
        for attempt in range(1, self.retries + 1):
            try:
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": content}],
                ) as stream:
                    msg = stream.get_final_message()
                text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
                if msg.stop_reason == "max_tokens":
                    dbg = Path("llm_truncated"); dbg.mkdir(exist_ok=True)
                    (dbg / f"{agent}_{step}.txt").write_text(text, encoding="utf-8")
                    raise LLMError(f"[{agent}/{step}] 응답이 max_tokens({self.max_tokens})에서 잘렸습니다.")
                return text
            except (self._anthropic.APIConnectionError, self._anthropic.RateLimitError,
                    self._anthropic.InternalServerError) as e:
                last_err = e
                time.sleep(2 * attempt)
        raise LLMError(f"[{agent}/{step}] API 호출 실패: {last_err}")


class ReplayClient:
    """replay/<agent>_<step>.txt 파일을 응답으로 돌려준다."""

    def __init__(self, replay_dir: Path):
        self.replay_dir = Path(replay_dir)

    def complete(self, agent: str, step: str, system: str, user: str, images=None) -> str:
        path = self.replay_dir / f"{agent}_{step}.txt"
        if not path.exists():
            raise LLMError(f"재생 응답 파일이 없습니다: {path}")
        return path.read_text(encoding="utf-8")


class RecordingClient:
    """다른 클라이언트의 응답을 replay 형식으로 저장한다."""

    def __init__(self, inner, replay_dir: Path):
        self.inner = inner
        self.replay_dir = Path(replay_dir)
        self.replay_dir.mkdir(parents=True, exist_ok=True)

    def complete(self, agent: str, step: str, system: str, user: str, images=None) -> str:
        text = self.inner.complete(agent, step, system, user, images)
        (self.replay_dir / f"{agent}_{step}.txt").write_text(text, encoding="utf-8")
        return text
```

### `stairs_agents/util.py`

````python
"""경로, 입력 문서 읽기, LLM 응답 파싱 도구."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

log = logging.getLogger("stairs_agents")


@dataclass
class Paths:
    root: Path = ROOT
    out: Path = ROOT / "output"

    @property
    def docs(self) -> Path: return self.root / "docs"
    @property
    def prompts(self) -> Path: return self.root / "prompts"
    @property
    def data(self) -> Path: return self.root / "data"
    @property
    def design_out(self) -> Path: return self.out / "design_out"
    @property
    def mech_out(self) -> Path: return self.out / "mech_out"
    @property
    def dev_out(self) -> Path: return self.out / "dev_out"
    @property
    def build(self) -> Path: return self.out / "build"
    @property
    def dist(self) -> Path: return self.out / "dist"


def read(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_prompt(paths: Paths, name: str) -> str:
    return read(paths.prompts / f"{name}.md")


def extract_json(text: str, tag: str = "json") -> dict:
    """<json>...</json> 블록, 없으면 ```json 펜스, 없으면 첫 { 부터 마지막 } 까지를 JSON으로 읽는다."""
    m = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", text, re.S)
    if not m:
        m = re.search(r"```json\s*(.*?)```", text, re.S)
    raw = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답의 JSON을 읽지 못했습니다: {e}") from e


FILE_RE = re.compile(r'<file\s+path="([^"]+)"\s*>\n?(.*?)\n?</file>', re.S)


def extract_files(text: str) -> dict[str, str]:
    """<file path="...">내용</file> 블록들을 {경로: 내용}으로 돌려준다."""
    files = {p.strip(): body for p, body in FILE_RE.findall(text)}
    if not files:
        raise ValueError("LLM 응답에서 <file path=\"...\"> 블록을 찾지 못했습니다.")
    for p in files:
        if p.startswith("/") or ".." in Path(p).parts:
            raise ValueError(f"허용되지 않는 파일 경로입니다: {p}")
    return files


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
````

### `stairs_agents/contract.py`

```python
"""docs/ASSET_LIST.md 의 에셋 ID, 변형, 애니메이션 이름을 읽어 세 에이전트가 같은 기준으로 검사하게 한다."""
from __future__ import annotations

import re
from pathlib import Path


def _rows(md: str, header_start: str) -> list[list[str]]:
    """header_start 로 시작하는 표의 본문 행을 돌려준다."""
    lines = md.splitlines()
    out, inside = [], False
    for ln in lines:
        if ln.startswith("| " + header_start):
            inside = True
            continue
        if inside:
            if ln.startswith("|---"):
                continue
            if not ln.startswith("|"):
                break
            out.append([c.strip() for c in ln.strip("|").split("|")])
    return out


def load_contract(asset_list: Path) -> dict:
    md = Path(asset_list).read_text(encoding="utf-8")
    sheets = {}
    for aid, variants, anims, *_ in _rows(md, "에셋 ID | 변형"):
        sheets[aid] = {
            "variants": [v.strip() for v in variants.split(",")],
            "animations": [a.strip() for a in anims.split(",")],
        }
    images = [r[0] for r in _rows(md, "에셋 ID | 내용과")]
    sounds = {r[0]: r[1] == "예" for r in _rows(md, "에셋 ID | 반복")}
    if not sheets or not images or not sounds:
        raise ValueError("ASSET_LIST.md 에서 표를 읽지 못했습니다.")
    return {"sheets": sheets, "images": images, "sounds": sounds}


def check_manifest(contract: dict, manifest: dict) -> list[str]:
    """Designer 매니페스트가 계약을 모두 덮는지 검사하고 문제 목록을 돌려준다."""
    problems = []
    for aid, c in contract["sheets"].items():
        s = manifest.get("sprites", {}).get(aid)
        if not s:
            problems.append(f"스프라이트 없음: {aid}")
            continue
        for v in c["variants"]:
            if v not in s["variants"]:
                problems.append(f"{aid}: 변형 없음 {v}")
        for a in c["animations"]:
            if a not in s["animations"]:
                problems.append(f"{aid}: 애니메이션 없음 {a}")
    for aid in contract["images"]:
        if aid not in manifest.get("images", {}):
            problems.append(f"이미지 없음: {aid}")
    for aid in contract["sounds"]:
        if aid not in manifest.get("sounds", {}):
            problems.append(f"사운드 없음: {aid}")
    return problems
```

### `stairs_agents/__main__.py`

```python
"""명령줄 실행.

  python -m stairs_agents run                       # Claude API로 실행 (ANTHROPIC_API_KEY 필요)
  python -m stairs_agents run --record              # API 응답을 replay/ 에 저장
  python -m stairs_agents run --replay replay       # 저장된 응답으로 실행 (API 키 불필요)
  python -m stairs_agents mechanics|designer|developer|publisher [...]   # 에이전트 하나만 실행
  python -m stairs_agents qa --replay replay        # 이미 만든 결과물에 Designer QA, Developer QA만 실행
  python -m stairs_agents qa-designer|qa-developer  # QA 하나만
  python -m stairs_agents qa-screens --replay replay # Publisher가 찍은 화면을 컨셉 화면과 대조
  python -m stairs_agents harness --replay replay    # 루프 하네스: 역할마다 만들기→평가→되먹임, 바깥 루프에서 owner로 되돌림
  python -m stairs_agents harness --roles mechanics  # 한 역할만 하네스로 (예: 메카니즘 밸런스 조정)
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .designer import DesignerAgent
from .developer import DeveloperAgent
from .llm import DEFAULT_MODEL, ClaudeClient, LLMError, RecordingClient, ReplayClient
from .mechanics import MechanicsAgent
from .pipeline import run_pipeline
from .publisher import PublisherAgent
from .qa_designer import DesignerQAAgent
from .qa_developer import DeveloperQAAgent
from .qa_screens import run_screen_qa
from .util import ROOT, Paths


def make_llm(args):
    if args.replay:
        return ReplayClient(Path(args.replay))
    client = ClaudeClient(model=args.model, max_tokens=args.max_tokens)
    return RecordingClient(client, Path(args.record_dir)) if args.record else client


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="stairs_agents", description="승급의 계단 에이전트 PoC")
    ap.add_argument("command", choices=["run", "harness", "mechanics", "designer", "developer", "publisher", "qa", "qa-designer", "qa-developer", "qa-screens"])
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude 모델 (기본 {DEFAULT_MODEL})")
    ap.add_argument("--max-tokens", type=int, default=64000)
    ap.add_argument("--replay", help="저장된 응답 폴더로 실행 (API 호출 없음)")
    ap.add_argument("--record", action="store_true", help="API 응답을 --record-dir 에 저장")
    ap.add_argument("--record-dir", default=str(ROOT / "replay_api"), help="응답 저장 폴더 (기본 replay_api)")
    ap.add_argument("--no-resource-db", action="store_true", help="Designer가 원본 리소스 데이터베이스를 쓰지 않음")
    ap.add_argument("--out", default=str(ROOT / "output"), help="출력 폴더")
    ap.add_argument("--no-qa", action="store_true", help="QA 에이전트를 돌리지 않음")
    ap.add_argument("--strict-qa", action="store_true", help="QA 판정이 fail이면 Publisher 전에 멈춤")
    ap.add_argument("--qa-rounds", type=int, default=11, help="QA 고침 반복 최대 횟수 (1~11, 기본 11)")
    ap.add_argument("--roles", help="harness: 돌릴 역할 (쉼표 구분, 기본 mechanics,designer,developer,publisher)")
    ap.add_argument("--rounds", type=int, default=12, help="harness: 역할마다 안쪽 루프 최대 차례 (기본 12)")
    ap.add_argument("--outer-rounds", type=int, default=3, help="harness: 바깥 루프 최대 차례 (기본 3)")
    ap.add_argument("--max-llm-calls", type=int, default=12, help="harness: 역할마다 LLM 호출 상한 (기본 12)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    paths = Paths(out=Path(args.out).resolve())

    if args.command == "publisher":
        result = PublisherAgent(paths).run()
        return 0 if result["passed"] else 1
    try:
        llm = make_llm(args)
    except LLMError as e:
        print(f"오류: {e}\nAPI 키 없이 시험하려면 --replay replay 를 붙여 실행하세요.", file=sys.stderr)
        return 2
    if args.command == "harness":
        from .harness import Budget, run_harness
        roles = args.roles.split(",") if args.roles else None
        res = run_harness(llm, paths, roles=roles, outer_rounds=args.outer_rounds,
                          budget=Budget(max_rounds=args.rounds, max_llm_calls=args.max_llm_calls),
                          use_resource_db=not args.no_resource_db)
        return 0 if all(v["verdict"] != "fail" for v in res["roles"].values()) else 1
    if args.command == "mechanics":
        result = MechanicsAgent(llm, paths).run()
        return 1 if result["problems"] and not result["skipped"] else 0
    if args.command == "qa-screens":
        return 1 if run_screen_qa(llm, paths)["verdict"] == "fail" else 0
    if args.command in ("qa", "qa-designer", "qa-developer"):
        verdicts = []
        if args.command != "qa-developer":
            verdicts.append(DesignerQAAgent(llm, paths).run()["verdict"])
        if args.command != "qa-designer":
            verdicts.append(DeveloperQAAgent(llm, paths).run()["verdict"])
        return 1 if "fail" in verdicts else 0
    if args.command == "designer":
        DesignerAgent(llm, paths, use_resource_db=not args.no_resource_db).run()
        return 0
    if args.command == "developer":
        DeveloperAgent(llm, paths).run()
        return 0
    result = run_pipeline(llm, paths, use_resource_db=not args.no_resource_db, qa=not args.no_qa, strict_qa=args.strict_qa,
                          qa_rounds=args.qa_rounds)
    return 0 if result["publisher"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

### `stairs_agents/__init__.py`

```python
"""승급의 계단 에이전트 PoC: Designer, Developer, Publisher."""
```

### `stairs_agents/harness/__init__.py`

```python
"""루프 기반 에이전트 하네스. core(반복·평가·기록) + roles(역할 4종) + orchestrator(바깥 루프와 라우팅)."""
from .core import Budget, Evaluation, Issue, Ledger, LoopRunner, Role
from .orchestrator import run_harness

__all__ = ["Budget", "Evaluation", "Issue", "Ledger", "LoopRunner", "Role", "run_harness"]
```

### `stairs_agents/harness/core.py`

```python
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
```

### `stairs_agents/harness/roles.py`

```python
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
```

### `stairs_agents/harness/orchestrator.py`

```python
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
```
