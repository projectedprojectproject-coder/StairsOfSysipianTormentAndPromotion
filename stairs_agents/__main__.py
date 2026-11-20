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
    result = run_pipeline(llm, paths, use_resource_db=not args.no_resource_db, qa=not args.no_qa, strict_qa=args.strict_qa)
    return 0 if result["publisher"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
