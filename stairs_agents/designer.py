"""Designer 에이전트.

역할 (에이전트 맵): 생성형 AI로 스프라이트, 리소스, 사운드를 제작한다. 필요하면 원본 리소스 데이터베이스 파일을 사용한다.
입력: docs/GDD.md (특히 03 디자인 컨셉), docs/ASSET_LIST.md, data/원본리소스_DB.json
출력: output/design_out/ 의 디자인 파일(PNG, WAV)과 design_manifest.json
      내보내는 형식은 Designer의 도구가 만드는 그대로이며, 형식 맞춤은 Publisher가 맡는다.
"""
from __future__ import annotations

import shutil
import time
from concurrent.futures import ThreadPoolExecutor

from . import render, synth
from .contract import check_manifest, load_contract
from .util import Paths, extract_json, load_prompt, log, read, write_json


class DesignerAgent:
    name = "designer"

    def __init__(self, llm, paths: Paths, use_resource_db: bool = True):
        self.llm = llm
        self.paths = paths
        self.use_resource_db = use_resource_db

    def _context(self) -> str:
        p = self.paths
        parts = [
            "# 기획서 (GDD)\n" + read(p.docs / "GDD.md"),
            "# 공통 에셋 목록 (ASSET_LIST)\n" + read(p.docs / "ASSET_LIST.md"),
        ]
        db = p.data / "원본리소스_DB.json"
        if self.use_resource_db and db.exists():
            parts.append("# 원본 리소스 데이터베이스 (원본리소스_DB.json)\n" + read(db))
        return "\n\n".join(parts)

    def run(self) -> dict:
        t0 = time.time()
        out = self.paths.design_out
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        ctx = self._context()
        contract = load_contract(self.paths.docs / "ASSET_LIST.md")

        system_sprites = load_prompt(self.paths, "designer_sprites")
        system_sound = load_prompt(self.paths, "designer_sound")

        def ask_sheet(aid):
            c = contract["sheets"][aid]
            req = (f"이번 요청에서는 sheet '{aid}' 하나만 설계하라. 변형: {', '.join(c['variants'])}. "
                   f"애니메이션: {', '.join(c['animations'])}. 출력 JSON에는 palette와 sheets.{aid}만 넣는다.")
            return aid, extract_json(self.llm.complete(self.name, f"sprite_{aid}", system_sprites, ctx + "\n\n" + req))

        def ask_images():
            req = ("이번 요청에서는 images만 설계하라: " + ", ".join(contract["images"]) +
                   ". 출력 JSON에는 images만 넣는다.")
            return extract_json(self.llm.complete(self.name, "images", system_sprites, ctx + "\n\n" + req))

        def ask_sound():
            return extract_json(self.llm.complete(self.name, "sound", system_sound,
                                                  ctx + "\n\nASSET_LIST의 모든 사운드를 위 출력 형식으로 설계하라."))

        log.info("[Designer] 스프라이트 %d종, 이미지, 사운드 설계를 동시에 요청", len(contract["sheets"]))
        with ThreadPoolExecutor(max_workers=8) as ex:
            f_sheets = [ex.submit(ask_sheet, aid) for aid in contract["sheets"]]
            f_images, f_sound = ex.submit(ask_images), ex.submit(ask_sound)
            sheet_specs = [f.result() for f in f_sheets]
            image_spec, sound_spec = f_images.result(), f_sound.result()
        write_json(out / "_spec_sprites.json", {aid: sp for aid, sp in sheet_specs})
        write_json(out / "_spec_images.json", image_spec)
        write_json(out / "_spec_sound.json", sound_spec)

        manifest = {"generator": "Designer agent", "sprites": {}, "images": {}, "sounds": {}}
        for aid, sp in sheet_specs:
            manifest["sprites"][aid] = render.render_sheet(aid, sp["sheets"][aid], sp.get("palette", {}), out)
        for aid, spec in image_spec["images"].items():
            manifest["images"][aid] = render.render_image(aid, spec, out)
        manifest["sounds"] = synth.render_all(sound_spec, out)

        problems = check_manifest(contract, manifest)
        manifest["problems"] = problems
        write_json(out / "design_manifest.json", manifest)
        for pr in problems:
            log.warning("[Designer] %s", pr)
        log.info("[Designer] 완료: 스프라이트 %d, 이미지 %d, 사운드 %d (%.1f초)",
                 len(manifest["sprites"]), len(manifest["images"]), len(manifest["sounds"]), time.time() - t0)
        return manifest
