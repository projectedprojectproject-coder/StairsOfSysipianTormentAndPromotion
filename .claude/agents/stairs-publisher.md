---
name: stairs-publisher
description: 승급의 계단 Publisher 에이전트. Designer 결과물의 확장자를 Developer의 스프라이트 정의에 맞게 변환하고, 코드와 디자인을 연결하고, Playwright로 9개 항목 동작 확인을 한 뒤 zip으로 내보낸다. 빌드, 동작 확인, 배포 패키지를 다룰 때 사용한다.
tools: Read, Grep, Glob, Bash, Edit, Write
---

# Publisher 에이전트

에이전트 맵의 **Publisher**입니다.

1. 디자인 파일과 사운드 파일의 확장자가 Developer의 스프라이트 정의와 같은지 확인하고, 다르면 변환합니다(PNG 유지, WAV → OGG/MP3는 ffmpeg).
2. 코드와 디자인 파일을 연결합니다(`assets/sprite_definition.js`에 파일 이름과 프레임 크기를 채움).
3. 잘 돌아가는지 확인합니다(Playwright Chromium으로 9개 항목).
4. 게임을 내보냅니다(`output/dist/승급의계단_PoC_web.zip`, 보고서, 화면 캡처).

## 입력과 출력

- 입력: `output/design_out`(Designer), `output/dev_out`(Developer)
- 출력: `output/build`(실행 가능한 웹 게임), `output/dist`(zip, `publisher_report.md`, `screens/`)

## 동작 확인 9개 항목

에셋 불러오기 · 타이틀 화면 · 타이틀 → 로비 · 로비 → 플레이 · 일시정지(ESC)와 남은 일수 정지 · 마지막 승급 층(60층) 도달과 승급 판정 · 입력 없음 → 구조조정 · 파일로 직접 열기(file://) · 브라우저 오류 없음

## 필요한 것

- `playwright install chromium`
- PATH에 있는 ffmpeg(libvorbis, libmp3lame)

## 실행

```bash
python -m stairs_agents publisher
```

> 아래 지시문과 코드는 저장소의 원본 파일을 그대로 옮긴 사본입니다. 실제로 실행되는 것은 원본 파일이므로, 고칠 때는 원본을 고치고 이 문서도 함께 갱신합니다.

## 에이전트 코드 (stairs_agents/)

### `stairs_agents/publisher.py`

```python
"""Publisher 에이전트.

역할 (에이전트 맵):
 1. 디자인 파일과 사운드 파일의 확장자가 Developer의 스프라이트 정의와 같은지 확인하고, 다르면 변환
 2. 코드와 디자인 파일을 연결
 3. 잘 돌아가는지 확인
 4. 게임 내보내기
입력: output/design_out (Designer), output/dev_out (Developer)
출력: output/build (실행 가능한 웹 게임), output/dist (zip, 확인 보고서, 화면 캡처)
"""
from __future__ import annotations

import functools
import http.server
import json
import shutil
import subprocess
import threading
import time
import zipfile
from pathlib import Path

from PIL import Image

from .util import Paths, log, read, write_json

EXTERNAL_AUDIO = ("wav", "flac", "ogg", "mp3", "m4a")
AUDIO_CODECS = {"ogg": ["-c:a", "libvorbis", "-q:a", "4"], "mp3": ["-c:a", "libmp3lame", "-b:a", "128k"]}


class PublisherAgent:
    name = "publisher"

    def __init__(self, paths: Paths, browser: str | None = None, test_timeout: float = 240.0):
        self.paths = paths
        self.browser = browser or shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
        self.test_timeout = test_timeout
        self.report: dict = {"format_checks": [], "link_problems": [], "tests": [], "export": {}}

    # ------------------------------------------------------------ 1. 확장자 확인과 변환
    def check_and_convert(self, manifest: dict, definition: dict) -> dict:
        src, dst = self.paths.design_out, self.paths.build / definition.get("assets_dir", "assets")
        dst.mkdir(parents=True, exist_ok=True)
        acc_img = [e.lower() for e in definition["accepted_formats"]["image"]]
        acc_aud = [e.lower() for e in definition["accepted_formats"]["audio"]]
        resolved = {"sprites": {}, "images": {}, "sounds": {}}

        def handle_image(aid, entry):
            f = Path(entry["file"])
            ext = f.suffix.lower().lstrip(".")
            if ext in acc_img:
                shutil.copy2(src / f, dst / f.name)
                out, action = f.name, "일치, 복사"
            else:
                out = f.stem + ".png"   # 투명 영역을 유지하려고 PNG로 변환
                Image.open(src / f).convert("RGBA").save(dst / out)
                action = f"불일치, {ext} -> png 변환"
            self.report["format_checks"].append({"asset": aid, "type": "image", "from": f.name, "to": out, "result": action})
            return out

        for aid, e in manifest["sprites"].items():
            resolved["sprites"][aid] = {**e, "file": handle_image(aid, e)}
        for aid, e in manifest["images"].items():
            resolved["images"][aid] = {**e, "file": handle_image(aid, e)}

        music_dir = self.paths.data / "music"   # 외부 음악(예: Suno로 만든 곡)이 있으면 Designer의 합성음 대신 쓴다
        for aid, e in manifest["sounds"].items():
            f = Path(e["file"])
            ext = f.suffix.lower().lstrip(".")
            files = {}
            ext_src = next((music_dir / f"{aid}.{x}" for x in EXTERNAL_AUDIO if (music_dir / f"{aid}.{x}").exists()), None)
            if ext_src:
                for target in acc_aud:
                    out = f"{aid}.{target}"
                    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(ext_src), *AUDIO_CODECS[target], str(dst / out)]
                    subprocess.run(cmd, check=True)
                    files[target] = out
                action = f"외부 음악 사용 (data/music/{ext_src.name})"
            elif ext in acc_aud:
                shutil.copy2(src / f, dst / f.name)
                files[ext] = f.name
                action = "일치, 복사"
            else:
                for target in acc_aud:
                    out = f"{f.stem}.{target}"
                    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src / f), *AUDIO_CODECS[target], str(dst / out)]
                    subprocess.run(cmd, check=True)
                    files[target] = out
                action = f"불일치, {ext} -> {', '.join(acc_aud)} 변환"
            resolved["sounds"][aid] = {"loop": e["loop"], "files": files}
            self.report["format_checks"].append({"asset": aid, "type": "audio", "from": f.name, "to": ", ".join(files.values()), "result": action})
        return resolved

    # ------------------------------------------------------------ 2. 코드와 디자인 연결
    def link(self, resolved: dict, definition: dict) -> dict:
        build = self.paths.build
        for item in self.paths.dev_out.iterdir():
            if item.name == "sprite_definition.json":
                continue
            target = build / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
        final = {k: v for k, v in definition.items() if k not in ("sprites", "images", "sounds")}
        final.update({"sprites": {}, "images": {}, "sounds": {}})
        probs = self.report["link_problems"]
        for group in ("sprites", "images", "sounds"):
            for aid, want in definition[group].items():
                got = resolved[group].get(aid)
                if not got:
                    probs.append(f"{group}.{aid}: Designer 결과 없음")
                    continue
                if group == "sprites":
                    for v in want.get("variants", []):
                        if v not in got["variants"]:
                            probs.append(f"{aid}: 변형 '{v}' 없음")
                    for a in want.get("animations", []):
                        if a not in got["animations"]:
                            probs.append(f"{aid}: 애니메이션 '{a}' 없음")
                    final[group][aid] = {k: got[k] for k in ("file", "frame_w", "frame_h", "variants", "animations")}
                elif group == "images":
                    final[group][aid] = {k: got[k] for k in ("file", "w", "h")}
                else:
                    final[group][aid] = {"loop": want.get("loop", got["loop"]), "files": got["files"]}
        assets = build / definition.get("assets_dir", "assets")
        write_json(assets / "sprite_definition.json", final)
        (assets / "sprite_definition.js").write_text(
            "window.SPRITE_DEF = " + json.dumps(final, ensure_ascii=False) + ";\n", encoding="utf-8")
        for pr in probs:
            log.warning("[Publisher] 연결 문제: %s", pr)
        return final

    # ------------------------------------------------------------ 3. 동작 확인
    def test(self) -> bool:
        from playwright.sync_api import sync_playwright

        shots = self.paths.dist / "screens"
        shots.mkdir(parents=True, exist_ok=True)
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
        handler = functools.partial(Quiet, directory=str(self.paths.build))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}/index.html"
        all_ok = True

        def record(name, ok, detail=""):
            nonlocal all_ok
            all_ok &= ok
            self.report["tests"].append({"name": name, "ok": ok, "detail": detail})
            (log.info if ok else log.error)("[Publisher] 확인 %s: %s %s", "통과" if ok else "실패", name, detail)

        try:
            with sync_playwright() as pw:
                # 설치된 Chrome이 있으면 사용하고, 없으면 `playwright install chromium`으로 받은 브라우저를 사용
                opts = {"headless": True, "args": ["--autoplay-policy=no-user-gesture-required"]}
                if self.browser:
                    opts["executable_path"] = self.browser
                br = pw.chromium.launch(**opts)
                page = br.new_page(viewport={"width": 1280, "height": 720})
                errors = []
                page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
                # 브라우저가 스스로 요청하는 favicon.ico는 게임 리소스가 아니므로 판정에서 제외
                bad = lambda url: not url.endswith("/favicon.ico")
                page.on("console", lambda m: errors.append(f"console: {m.text}")
                        if m.type == "error" and "status of 404" not in m.text else None)
                page.on("response", lambda r: errors.append(f"HTTP {r.status}: {r.url}")
                        if r.status >= 400 and bad(r.url) else None)
                page.on("requestfailed", lambda r: errors.append(f"requestfailed: {r.url}") if bad(r.url) else None)
                state = lambda: page.evaluate("window.__stairs ? JSON.parse(JSON.stringify(window.__stairs)) : null")

                def wait_for(cond_js, timeout):
                    page.wait_for_function(cond_js, timeout=timeout * 1000)

                # 시나리오 1: 자동 플레이로 마지막 승급 층까지 (게임이 __stairs.finalFloor·finalRank로 알려 줌, 없으면 20층·대리)
                page.goto(base + "?seed=7&bot=1&mute=1")
                wait_for("window.__stairs && window.__stairs.ready", 15)
                s = state()
                record("에셋 불러오기", not s["assetErrors"], ", ".join(s["assetErrors"]))
                record("타이틀 화면", s["screen"] == "title", s["screen"])
                page.screenshot(path=str(shots / "1_title.png"))
                page.keyboard.press("Enter")
                wait_for("window.__stairs.screen === 'lobby'", 5)
                record("타이틀 -> 로비 이동", True)
                page.screenshot(path=str(shots / "2_lobby.png"))
                page.keyboard.press("Enter")
                wait_for("window.__stairs.screen === 'play'", 5)
                record("로비 -> 플레이 이동", True)
                page.wait_for_timeout(3000)
                page.screenshot(path=str(shots / "3_play.png"))
                page.keyboard.press("Escape")
                wait_for("window.__stairs.screen === 'pause'", 5)
                d0 = state()["days"]
                page.wait_for_timeout(1000)
                d1 = state()["days"]
                record("일시정지 (ESC)와 남은 일수 정지", abs(d0 - d1) < 1e-6, f"{d0:.2f} -> {d1:.2f}")
                page.screenshot(path=str(shots / "4_pause.png"))
                page.keyboard.press("Enter")   # 계속하기
                wait_for("window.__stairs.screen === 'play'", 5)
                wait_for("window.__stairs.screen === 'result'", self.test_timeout)
                s = state()
                goal, goal_rank = s.get("finalFloor") or 20, s.get("finalRank") or "대리"
                record(f"{goal}층 도달과 승급 판정", s["floor"] >= goal and s["rank"] == goal_rank,
                       f"층 {s['floor']}, 직급 {s['rank']} (목표 {goal}층 {goal_rank}), 점수 {s['score']}, 최고 배수 x{s['maxMult']}")
                page.wait_for_timeout(600)
                page.screenshot(path=str(shots / "5_result_promote.png"))

                # 시나리오 2: 아무 입력 없이 두면 구조조정
                page.goto(base + "?seed=3&mute=1")
                wait_for("window.__stairs && window.__stairs.ready", 15)
                page.keyboard.press("Enter")
                wait_for("window.__stairs.screen === 'lobby'", 5)
                page.keyboard.press("Enter")
                wait_for("window.__stairs.screen === 'play'", 5)
                t0 = time.time()
                wait_for("window.__stairs.screen === 'result'", 30)
                s = state()
                record("입력 없음 -> 구조조정 (게임 오버)", s["hearts"] == 0 or s["days"] <= 0,
                       f"{time.time() - t0:.1f}초 뒤, 하트 {s['hearts']}, 남은 일수 {max(0, s['days']):.1f}")
                page.wait_for_timeout(600)
                page.screenshot(path=str(shots / "6_result_gameover.png"))

                # 시나리오 3: 웹 서버 없이 파일로 열기
                page.goto((self.paths.build / "index.html").as_uri() + "?mute=1")
                wait_for("window.__stairs && window.__stairs.ready", 15)
                s = state()
                record("파일로 직접 열기 (file://)", not s["assetErrors"], ", ".join(s["assetErrors"]))
                record("브라우저 오류 없음", not errors, " | ".join(errors[:5]))
                br.close()
        except Exception as e:  # 시험 도중 시간 초과 등
            record("시험 진행", False, f"{type(e).__name__}: {e}")
        finally:
            server.shutdown()
        return all_ok

    # ------------------------------------------------------------ 4. 내보내기
    def export(self, passed: bool) -> Path:
        dist = self.paths.dist
        dist.mkdir(parents=True, exist_ok=True)
        zpath = dist / "승급의계단_PoC_web.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(self.paths.build.rglob("*")):
                if f.is_file():
                    z.write(f, Path("승급의계단") / f.relative_to(self.paths.build))
        self.report["export"] = {"zip": zpath.name, "passed": passed, "files": sum(1 for f in self.paths.build.rglob("*") if f.is_file())}
        write_json(dist / "publisher_report.json", self.report)
        (dist / "publisher_report.md").write_text(self._report_md(), encoding="utf-8")
        return zpath

    def _report_md(self) -> str:
        r = self.report
        lines = ["# Publisher 보고서", "", "## 1. 확장자 확인과 변환", "",
                 "| 에셋 | 종류 | Designer 파일 | 결과 파일 | 판정 |", "|---|---|---|---|---|"]
        for c in r["format_checks"]:
            lines.append(f"| {c['asset']} | {c['type']} | {c['from']} | {c['to']} | {c['result']} |")
        lines += ["", "## 2. 코드와 디자인 연결", ""]
        lines += [f"- {p}" for p in r["link_problems"]] or ["- 문제 없음 (정의의 모든 에셋, 변형, 애니메이션이 연결됨)"]
        lines += ["", "## 3. 동작 확인", "", "| 확인 항목 | 결과 | 내용 |", "|---|---|---|"]
        for t in r["tests"]:
            lines.append(f"| {t['name']} | {'통과' if t['ok'] else '실패'} | {t['detail']} |")
        e = r["export"]
        lines += ["", "## 4. 내보내기", "", f"- 파일: {e.get('zip')}", f"- 포함 파일 수: {e.get('files')}",
                  f"- 동작 확인 전체 통과: {'예' if e.get('passed') else '아니오'}", ""]
        return "\n".join(lines)

    # ------------------------------------------------------------ 전체
    def run(self) -> dict:
        t0 = time.time()
        for d in (self.paths.build, self.paths.dist):
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)
        manifest = json.loads(read(self.paths.design_out / "design_manifest.json"))
        definition = json.loads(read(self.paths.dev_out / "sprite_definition.json"))
        log.info("[Publisher] 1. 확장자 확인과 변환")
        resolved = self.check_and_convert(manifest, definition)
        log.info("[Publisher] 2. 코드와 디자인 연결")
        self.link(resolved, definition)
        log.info("[Publisher] 3. 동작 확인")
        passed = self.test()
        log.info("[Publisher] 4. 게임 내보내기")
        z = self.export(passed)
        log.info("[Publisher] 완료: %s, 동작 확인 %s (%.1f초)", z.name, "통과" if passed else "실패 있음", time.time() - t0)
        return {"zip": str(z), "passed": passed, "report": self.report}
```
