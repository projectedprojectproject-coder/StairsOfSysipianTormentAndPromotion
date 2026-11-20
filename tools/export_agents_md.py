"""stairs_agents 코드와 지시문을 Claude Code 서브에이전트 md(.claude/agents/*.md)로 내보낸다.

각 md에는 역할 설명과 함께 prompts/, stairs_agents/ 원본의 사본이 들어간다.
원본(코드나 지시문)을 고친 뒤에는 이 스크립트로 md를 다시 만든다.

  python tools/export_agents_md.py           # md 다시 만들기
  python tools/export_agents_md.py --check   # md가 원본과 같은지만 검사 (다르면 종료 코드 1)

새 에이전트 모듈을 추가하면 아래 AGENTS 중 한 곳의 sources에 넣는다. 어디에도 없으면 --check가 알려 준다.
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".claude" / "agents"

AGENTS = [
    {
        # 본문은 담당자(JH)가 쓴 기존 파일을 그대로 두고, 지시문과 코드 사본만 붙인다
        "file": "stairs-mechanics.md",
        "keep_body": True,
        "prompts": ["prompts/mechanics.md"],
        "sources": ["stairs_agents/mechanics.py", "tests/test_mechanics.py"],
    },
    {
        "file": "stairs-designer.md",
        "name": "stairs-designer",
        "description": "승급의 계단 Designer 에이전트. 기획서(docs/GDD.md 03)와 에셋 목록, 원본 리소스 DB를 근거로 16비트 픽셀 스프라이트·배경·8비트 사운드를 설계하고 PNG/WAV로 만든다. 스프라이트, 이미지, 사운드 에셋을 만들거나 고칠 때 사용한다.",
        "tools": "Read, Grep, Glob, Bash, Edit, Write",
        "body": """# Designer 에이전트

에이전트 맵의 **Designer**입니다. 생성형 AI로 스프라이트, 리소스, 사운드를 제작하고, 필요하면 원본 리소스 데이터베이스 파일을 사용합니다.

## 입력과 출력

- 입력: `docs/GDD.md`(특히 03 디자인 컨셉), `docs/ASSET_LIST.md`, `data/원본리소스_DB.json`, 컨셉 아트 `data/concept/`(영역 목록 `regions.json`)
- 출력: `output/design_out/` 의 PNG, WAV, `design_manifest.json`, 설계 명세 `_spec_*.json`
- 결과물은 바로 **Designer QA**(`stairs-designer-qa`)가 검사합니다. 보고서: `output/qa_out/designer_qa.md`
- 내보내는 형식은 Designer 도구가 만드는 그대로입니다. 형식 맞춤은 Publisher가 맡습니다.

## 작업 방법

1. 에셋마다 따로 Claude에 설계를 요청합니다(스프라이트 시트 6종 각각, 이미지 1건, 사운드 1건). 한 번에 요청하면 응답이 64000 토큰을 넘어 잘립니다.
2. 스프라이트·이미지 명세(JSON)는 `render.py`가 PNG로 그리고, 사운드 명세는 `synth.py`가 WAV로 합성합니다.
3. `contract.py`로 ASSET_LIST의 ID, 변형, 애니메이션 이름이 모두 있는지 검사합니다.
4. 컨셉 아트 참고: `concept.py`가 `data/concept/regions.json`의 영역을 뽑아(`output/concept_refs/`) 시트별 설계 요청에 참고 격자와 컨셉 주요 색을 붙입니다. 직접 그릴 때는 스킬 `.claude/skills/concept-sprite-extraction/SKILL.md`를 따릅니다.

## 실행

```bash
python -m stairs_agents designer               # Claude API (ANTHROPIC_API_KEY 필요)
python -m stairs_agents designer --replay replay  # 저장된 응답으로 실행
```

## 지켜야 할 것

- 03 컬러 팔레트(#5A5F66, #8A9A5B, #A13D3D, #1E1F22, #E8E6DF)를 기본으로 씁니다.
- 변형 이름과 애니메이션 이름은 `docs/ASSET_LIST.md`와 정확히 같아야 합니다(Developer와 Publisher가 같은 이름을 씁니다).
""",
        "prompts": ["prompts/designer_sprites.md", "prompts/designer_sound.md"],
        "sources": ["stairs_agents/designer.py", "stairs_agents/render.py", "stairs_agents/synth.py",
                    "stairs_agents/concept.py"],
    },
    {
        "file": "stairs-designer-qa.md",
        "name": "stairs-designer-qa",
        "description": "승급의 계단 Designer QA 에이전트. Designer 결과물(스프라이트·이미지·사운드)이 에셋 계약, 03 팔레트, 2배 밀도, 컨셉 아트(data/concept)와 맞는지 규칙 검사와 Claude 시각 검토로 확인하고 고칠 점을 보고한다. 스프라이트나 배경을 만든 뒤 품질을 확인하거나 컨셉과 비교할 때 사용한다.",
        "tools": "Read, Grep, Glob, Bash",
        "body": """# Designer QA 에이전트

Designer 바로 뒤에 도는 품질 확인 에이전트입니다. 결과물을 고치지 않고, Designer가 고칠 수 있는 지시를 보고합니다.

## 입력과 출력

- 입력: `output/design_out/`(PNG, WAV, `design_manifest.json`), `docs/ASSET_LIST.md`, 03 팔레트, `data/concept/`
- 출력: `output/qa_out/designer_qa.md`·`designer_qa.json`(판정, 문제와 고칠 점), `designer_contact.png`(왼쪽 컨셉에서 뽑은 참고, 오른쪽 만든 프레임)

## 확인 방법

1. 규칙 검사(LLM 없음): 에셋 계약, 빈 프레임, 캐릭터·소품 배경 투명, 2배 밀도(프레임 크기 짝수, 이미지 640x360), 시트별 색 수(48 이하), 03 팔레트 근접도, 컨셉 대조(색 거리 90 이하, 실루엣 겹침 0.4 이상, title_bg·bg_zone1과 컨셉 화면의 색·밝기), 사운드 길이·클리핑.
2. Claude 검토: 규칙 결과와 대조표·컨셉 원본 이미지를 보내 실루엣, 읽힘, 팔레트, 애니메이션을 검토받습니다(`prompts/qa_designer.md`). 재생 모드에 `qa_designer_review.txt`가 없으면 건너뛰고 보고서에 적습니다.
3. 판정: 규칙 high → fail, mid 또는 Claude revise → revise, 그 밖 pass. `--strict-qa`면 fail일 때 Publisher 전에 멈춥니다.
4. 고침 반복: pass가 아니면 고칠 점(`qa.feedback_text`)을 Designer에게 돌려줘 다시 만들고 다시 확인하기를 최대 11번(`--qa-rounds`) 되풀이합니다. 나아지지 않으면 일찍 멈추고, 재생 모드는 1번만 확인합니다. 차례별 판정: `output/qa_out/designer_loop.json`

직접 검토할 때는 대조표를 Read로 보고, 컨셉 영역을 더 뽑아야 하면 스킬 `.claude/skills/concept-sprite-extraction/SKILL.md`를 따릅니다.

## 실행

```bash
python -m stairs_agents qa-designer --replay replay
python -m stairs_agents qa-designer --replay replay_api --out output_api
```
""",
        "prompts": ["prompts/qa_designer.md"],
        "sources": ["stairs_agents/qa_designer.py", "stairs_agents/qa.py", "stairs_agents/concept.py"],
    },
    {
        "file": "stairs-developer.md",
        "name": "stairs-developer",
        "description": "승급의 계단 Developer 에이전트. 기획서(docs/GDD.md 01·04·05)로 1~20층 PoC 웹 게임 코드(index.html, game.js)와 스프라이트 정의(sprite_definition.json)를 작성한다. 게임 규칙, 수치, 화면, 입력 코드를 만들거나 고칠 때 사용한다.",
        "tools": "Read, Grep, Glob, Bash, Edit, Write",
        "body": """# Developer 에이전트

에이전트 맵의 **Developer**입니다. 코드와 시스템을 개발해 게임이 돌아가게 하고, 스프라이트 정의를 작성합니다.

## 입력과 출력

- 입력: `docs/GDD.md`(01, 04, 05 중심), `docs/ASSET_LIST.md`, `output/mech_out/mechanics.json`(Mechanics 명세, 있으면 CONFIG와 층 진행 값을 그대로 옮김)
- 출력: `output/dev_out/` 의 `index.html`, `game.js`, `sprite_definition.json`
- `sprite_definition.json`의 수용 형식: 이미지 JPEG·PNG 스프라이트 맵, 사운드 MP3·OGG

## 작업 방법

1. 기획서와 에셋 목록을 묶어 Claude에 한 번 요청하고, 응답의 `<file path="...">` 블록을 파일로 저장합니다.
2. 필수 파일 3개가 모두 있는지, 스프라이트 정의에 ASSET_LIST의 에셋이 모두 있는지 검사합니다.
3. 기획서 04 수치는 `game.js` 맨 위 `CONFIG`에 모으고, 기획서에 없는 값은 "기획서 미정" 주석으로 표시합니다.

## 현재 게임 규칙에서 기억할 것

- 하트 3, 남은 일수 최대 30일(1일 ≈ 0.33초), 계단 1칸 +1일, 패링 성공 +1.5일, 패링 판정 0.20초, 공격 예고 1.0초.
- 계단 방향 실수와 막지 못한 공격은 하트 -1. 남은 일수 0 또는 하트 0이면 구조조정.
- 플레이테스트 반영: 새 층에 오를 때마다 하트 1 회복(`CONFIG.FLOOR_HEAL`, 최대 3).
- 재생 모드 응답은 `replay/developer_code.txt`에 있습니다. 게임 코드를 고칠 때는 이 파일을 고친 뒤 파이프라인을 다시 돌리고, 결과(`output/build/game.js`)를 `demo/game.js`에 반영합니다.
- API 버전(`replay_api/developer_code.txt`, `demo_api/game.js`)에도 같은 규칙이 `CONFIG.floorHeal`로 들어가 있습니다. 확인: `python -m stairs_agents run --replay replay_api --out output_api`
- 재생 응답 두 개는 Mechanics 이전에 만든 것이라 아직 `mechanics.json`을 읽지 않습니다. 명세를 반영한 코드는 API로 다시 실행해야 나옵니다.

## 실행

```bash
python -m stairs_agents developer
python -m stairs_agents developer --replay replay
```
""",
        "prompts": ["prompts/developer.md"],
        "sources": ["stairs_agents/developer.py"],
    },
    {
        "file": "stairs-developer-qa.md",
        "name": "stairs-developer-qa",
        "description": "승급의 계단 Developer QA 에이전트. Developer 결과물(index.html, game.js, sprite_definition.json)이 기획서 04 수치, Mechanics 명세, 조작·화면 규칙, 스프라이트 정의 계약, PoC 제약을 지키는지 정적 검사와 Claude 코드 검토로 확인하고 고칠 점을 보고한다. 게임 코드를 쓴 뒤 품질을 확인할 때 사용한다.",
        "tools": "Read, Grep, Glob, Bash",
        "body": """# Developer QA 에이전트

Developer 바로 뒤에 도는 품질 확인 에이전트입니다. 코드를 고치지 않고, Developer가 고칠 수 있는 지시를 보고합니다. 실제로 띄워 보는 동작 확인(9개 항목)은 Publisher가 맡습니다.

## 입력과 출력

- 입력: `output/dev_out/`, `docs/ASSET_LIST.md`, `output/mech_out/mechanics.json`(있으면), `prompts/developer.md`
- 출력: `output/qa_out/developer_qa.md`·`developer_qa.json`

## 확인 방법

1. 규칙 검사(LLM 없음): 필수 파일, `sprite_definition.js`를 `game.js`보다 먼저 불러오는지, `node --check` 문법, `CONFIG` 객체와 기획서 04 수치(mechanics.json에서 출처가 04인 값), "기획서 미정" 표시, 조작 키(← → Q E ESC Enter), 화면 5종, 시험 훅 `window.__stairs`, 정의에 ASSET_LIST 에셋·이름 모두, 수용 형식, 정의한 에셋 사용 여부, `pixel_scale` 사용, 외부 주소·`fetch`·`eval` 없음.
2. Claude 검토: 규칙 결과, Developer 규칙, `game.js`를 보내 판정 규칙·진행·화면 흐름·버그 위험을 검토받습니다(`prompts/qa_developer.md`). 재생 모드에 `qa_developer_review.txt`가 없으면 건너뜁니다.
3. 판정과 고침 반복(최대 11번)은 Designer QA와 같습니다. 차례별 판정: `output/qa_out/developer_loop.json`

## 2단계: 화면 대조 (Publisher 뒤)

`qa_screens.py`가 Publisher가 찍은 실제 게임 화면(`output/dist/screens`)을 컨셉 화면(`data/concept/05-1_title.png`, `05-2_lobby.png`, `05-3_play.png`, `05-5_result_gameover.png`)과 비교합니다. 비교할 화면과 컨셉의 번호 요소는 `data/concept/regions.json`의 `screens`에 있습니다.

- 규칙 검사: 밝고 어두운 배치의 상관(구도, 0.3 이상), 강조색(빨강) 요소 자리의 겹침(0.25 이상), 색 거리, 밝기 차
- Claude 검토: 대조표(`output/qa_out/screens_contact.png`, 왼쪽 컨셉, 오른쪽 게임)와 번호 요소 목록으로 요소마다 있는지, 자리와 모양이 맞는지 보고 고칠 쪽(Developer/Designer)을 적습니다 (`prompts/qa_screens.md`)
- 보고서: `output/qa_out/screens_qa.md`
- 고침 반복: pass가 아니면 Developer를 고쳐 다시 만들고 Developer QA, Publisher, 화면 대조를 다시 돈다 (최대 11번, `screens_loop.json`)

## 실행

```bash
python -m stairs_agents qa-screens --replay replay   # 화면 대조만
python -m stairs_agents qa-developer --replay replay
python -m stairs_agents qa --replay replay      # Designer QA와 함께
```
""",
        "prompts": ["prompts/qa_developer.md", "prompts/qa_screens.md"],
        "sources": ["stairs_agents/qa_developer.py", "stairs_agents/qa_screens.py", "stairs_agents/qa.py"],
    },
    {
        "file": "stairs-publisher.md",
        "name": "stairs-publisher",
        "description": "승급의 계단 Publisher 에이전트. Designer 결과물의 확장자를 Developer의 스프라이트 정의에 맞게 변환하고, 코드와 디자인을 연결하고, Playwright로 9개 항목 동작 확인을 한 뒤 zip으로 내보낸다. 빌드, 동작 확인, 배포 패키지를 다룰 때 사용한다.",
        "tools": "Read, Grep, Glob, Bash, Edit, Write",
        "body": """# Publisher 에이전트

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
""",
        "prompts": [],
        "sources": ["stairs_agents/publisher.py"],
    },
    {
        "file": "stairs-pipeline.md",
        "name": "stairs-pipeline",
        "description": "승급의 계단 에이전트 파이프라인 조율자. Designer와 Developer를 동시에 실행한 뒤 Publisher를 실행하고, LLM 호출(API/재생/기록), 경로, 에셋 계약, 명령줄을 담당한다. 전체 파이프라인을 실행하거나 공통 계층을 고칠 때 사용한다.",
        "tools": "Read, Grep, Glob, Bash, Edit, Write",
        "body": """# 파이프라인 (조율과 공통 계층)

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
""",
        "prompts": [],
        "sources": ["stairs_agents/pipeline.py", "stairs_agents/llm.py", "stairs_agents/util.py",
                    "stairs_agents/contract.py", "stairs_agents/__main__.py", "stairs_agents/__init__.py"],
    },
]


def fence(text: str) -> str:
    runs = [len(m) for m in re.findall(r"`{3,}", text)]
    return "`" * max(3, max(runs, default=0) + 1)


def section(path: str, lang: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n")
    f = fence(text)
    return f"### `{path}`\n\n{f}{lang}\n{text}\n{f}\n"


def build(a: dict) -> str:
    """에이전트 하나의 md 전체 내용을 만든다."""
    if a.get("keep_body"):
        head = (OUT / a["file"]).read_text(encoding="utf-8").replace("\r\n", "\n")
        head = head.split("\n> 아래 지시문과 코드는")[0].rstrip("\n")
        parts = [head, ""]
    else:
        parts = [
            "---",
            f"name: {a['name']}",
            f"description: {a['description']}",
            f"tools: {a['tools']}",
            "---",
            "",
            a["body"].rstrip("\n"),
            "",
        ]
    parts += [
        "> 아래 지시문과 코드는 저장소의 원본 파일을 그대로 옮긴 사본입니다. 실제로 실행되는 것은 원본 파일이므로, 고칠 때는 원본을 고치고 이 문서도 함께 갱신합니다.",
        "",
    ]
    if a["prompts"]:
        parts += ["## Claude에 주는 지시문 (prompts/)", ""]
        parts += [section(p, "markdown") for p in a["prompts"]]
    parts += ["## 에이전트 코드 (stairs_agents/)", ""]
    parts += [section(s, "python") for s in a["sources"]]
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description="에이전트 md(.claude/agents/*.md) 생성")
    ap.add_argument("--check", action="store_true", help="파일을 쓰지 않고 원본과 같은지만 검사")
    args = ap.parse_args()

    stale = []
    OUT.mkdir(parents=True, exist_ok=True)
    for a in AGENTS:
        path = OUT / a["file"]
        text = build(a)
        if args.check:
            old = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.exists() else None
            if old != text:
                stale.append(a["file"])
        else:
            path.write_text(text, encoding="utf-8", newline="\n")
            print("작성:", path.relative_to(ROOT).as_posix())

    covered = {s for a in AGENTS for s in a["sources"]}
    modules = {p.relative_to(ROOT).as_posix() for p in (ROOT / "stairs_agents").glob("*.py")}
    missing = sorted(modules - covered)
    for m in missing:
        print("어느 md에도 없는 모듈:", m)
    if args.check:
        for f in stale:
            print("원본과 다름 (다시 만들어야 함):", f)
        if stale or missing:
            return 1
        print("모든 에이전트 md가 원본과 같습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
