"""Developer 에이전트.

역할 (에이전트 맵): 코드와 시스템을 개발하고 스프라이트를 정의한다.
입력: docs/GDD.md (01, 04, 05 중심), docs/ASSET_LIST.md
출력: output/dev_out/ 의 index.html, game.js, sprite_definition.json
      sprite_definition.json의 accepted_formats는 이미지 JPEG, PNG 스프라이트 맵, 사운드 MP3, OGG.
"""
from __future__ import annotations

import json
import shutil
import time

from .contract import load_contract
from .util import Paths, extract_files, load_prompt, log, read

REQUIRED_FILES = ["index.html", "game.js", "sprite_definition.json"]


class DeveloperAgent:
    name = "developer"

    def __init__(self, llm, paths: Paths):
        self.llm = llm
        self.paths = paths

    def run(self) -> dict:
        t0 = time.time()
        out = self.paths.dev_out
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        p = self.paths
        ctx = ("# 기획서 (GDD)\n" + read(p.docs / "GDD.md") +
               "\n\n# 공통 에셋 목록 (ASSET_LIST)\n" + read(p.docs / "ASSET_LIST.md"))

        log.info("[Developer] 게임 코드와 스프라이트 정의 작성 요청")
        files = extract_files(self.llm.complete(
            self.name, "code", load_prompt(p, "developer"),
            ctx + "\n\n위 기획서로 1~20층 PoC 게임 코드와 스프라이트 정의를 작성하라."))
        missing = [f for f in REQUIRED_FILES if f not in files]
        if missing:
            raise ValueError(f"[Developer] 필수 파일이 없습니다: {missing}")
        for rel, body in files.items():
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(body, encoding="utf-8")

        definition = json.loads(files["sprite_definition.json"])
        contract = load_contract(p.docs / "ASSET_LIST.md")
        problems = []
        for group, ids in (("sprites", contract["sheets"]), ("images", contract["images"]), ("sounds", contract["sounds"])):
            for aid in ids:
                if aid not in definition.get(group, {}):
                    problems.append(f"스프라이트 정의에 없음: {group}.{aid}")
        for pr in problems:
            log.warning("[Developer] %s", pr)
        log.info("[Developer] 완료: 파일 %d개, 수용 형식 %s (%.1f초)",
                 len(files), definition.get("accepted_formats"), time.time() - t0)
        return {"files": sorted(files), "definition": definition, "problems": problems}
