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
