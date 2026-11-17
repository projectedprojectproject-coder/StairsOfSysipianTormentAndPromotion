"""명령줄 실행.

  python -m stairs_agents run                       # Claude API로 실행 (ANTHROPIC_API_KEY 필요)
  python -m stairs_agents run --record              # API 응답을 replay/ 에 저장
  python -m stairs_agents run --replay replay       # 저장된 응답으로 실행 (API 키 불필요)
  python -m stairs_agents designer|developer|publisher [...]   # 에이전트 하나만 실행
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .designer import DesignerAgent
from .developer import DeveloperAgent
from .llm import DEFAULT_MODEL, ClaudeClient, LLMError, RecordingClient, ReplayClient
from .pipeline import run_pipeline
from .publisher import PublisherAgent
from .util import ROOT, Paths


def make_llm(args):
    if args.replay:
        return ReplayClient(Path(args.replay))
    client = ClaudeClient(model=args.model, max_tokens=args.max_tokens)
    return RecordingClient(client, Path(args.record_dir)) if args.record else client


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="stairs_agents", description="승급의 계단 에이전트 PoC")
    ap.add_argument("command", choices=["run", "designer", "developer", "publisher"])
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude 모델 (기본 {DEFAULT_MODEL})")
    ap.add_argument("--max-tokens", type=int, default=64000)
    ap.add_argument("--replay", help="저장된 응답 폴더로 실행 (API 호출 없음)")
    ap.add_argument("--record", action="store_true", help="API 응답을 --record-dir 에 저장")
    ap.add_argument("--record-dir", default=str(ROOT / "replay_api"), help="응답 저장 폴더 (기본 replay_api)")
    ap.add_argument("--no-resource-db", action="store_true", help="Designer가 원본 리소스 데이터베이스를 쓰지 않음")
    ap.add_argument("--out", default=str(ROOT / "output"), help="출력 폴더")
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
    if args.command == "designer":
        DesignerAgent(llm, paths, use_resource_db=not args.no_resource_db).run()
        return 0
    if args.command == "developer":
        DeveloperAgent(llm, paths).run()
        return 0
    result = run_pipeline(llm, paths, use_resource_db=not args.no_resource_db)
    return 0 if result["publisher"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
