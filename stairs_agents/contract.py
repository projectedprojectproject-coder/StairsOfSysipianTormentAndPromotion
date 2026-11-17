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
