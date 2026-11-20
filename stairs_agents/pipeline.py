"""에이전트 맵대로 실행한다: Mechanics로 규칙을 확정하고, Designer와 Developer를 동시에 돌린 뒤 Publisher를 돌린다.

Designer와 Developer 뒤에는 각자의 QA 에이전트(Designer QA, Developer QA)가 바로 이어서 돈다.
Publisher 뒤에는 Developer QA 2단계(화면 대조, qa_screens.py)가 실제 게임 화면을 컨셉 화면과 비교한다.
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
from .qa_screens import run_screen_qa
from .util import Paths, log


def run_pipeline(llm, paths: Paths, use_resource_db: bool = True, skip_test: bool = False,
                 qa: bool = True, strict_qa: bool = False) -> dict:
    t0 = time.time()
    # Developer가 mechanics.json을 읽으므로 Mechanics를 먼저 끝낸다
    mech = MechanicsAgent(llm, paths).run()
    designer = DesignerAgent(llm, paths, use_resource_db=use_resource_db)
    developer = DeveloperAgent(llm, paths)
    qa_results = {}

    def with_qa(agent, qa_agent, key):
        res = agent.run()
        if qa:
            qa_results[key] = qa_agent.run()
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
    if qa and not skip_test:  # Developer QA 2단계: Publisher가 찍은 화면을 컨셉 화면과 대조
        qa_results["screens"] = run_screen_qa(llm, paths)
    qa_dir = paths.out / "qa_out"
    if qa_dir.exists():  # QA 보고서를 배포 폴더에 함께 둔다
        shutil.copytree(qa_dir, paths.dist / "qa", dirs_exist_ok=True)
    log.info("파이프라인 완료 (%.1f초): %s", time.time() - t0, pub["zip"])
    return {"mechanics": mech, "designer": design, "developer": dev, "qa": qa_results, "publisher": pub}
