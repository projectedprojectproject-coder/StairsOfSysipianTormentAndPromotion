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
    ap.add_argument("command", choices=["run", "mechanics", "designer", "developer", "publisher", "qa", "qa-designer", "qa-developer", "qa-screens"])
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
