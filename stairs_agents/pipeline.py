"""에이전트 맵대로 실행한다: Designer와 Developer를 동시에 돌린 뒤 Publisher를 돌린다."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from .designer import DesignerAgent
from .developer import DeveloperAgent
from .publisher import PublisherAgent
from .util import Paths, log


def run_pipeline(llm, paths: Paths, use_resource_db: bool = True, skip_test: bool = False) -> dict:
    t0 = time.time()
    designer = DesignerAgent(llm, paths, use_resource_db=use_resource_db)
    developer = DeveloperAgent(llm, paths)
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_des, f_dev = ex.submit(designer.run), ex.submit(developer.run)
        errors = {}
        for name, f in (("Designer", f_des), ("Developer", f_dev)):
            if f.exception():
                errors[name] = f.exception()
                log.error("[%s] 실패: %s", name, f.exception())
        if errors:
            raise RuntimeError("에이전트 실패: " + ", ".join(f"{k}: {v}" for k, v in errors.items()))
        design, dev = f_des.result(), f_dev.result()

    publisher = PublisherAgent(paths)
    if skip_test:
        publisher.test = lambda: False
    pub = publisher.run()
    log.info("파이프라인 완료 (%.1f초): %s", time.time() - t0, pub["zip"])
    return {"designer": design, "developer": dev, "publisher": pub}
