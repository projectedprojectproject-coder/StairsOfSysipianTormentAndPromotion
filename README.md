# 승급의 계단 에이전트 PoC

Figma 에이전트 맵(페이지 "에이전트 맵")의 세 에이전트를 Python으로 구현한 Proof of Concept입니다.
프로토 기획서를 입력으로 받아 1~20층(사원 구간)을 플레이할 수 있는 웹 브라우저 게임을 만들어 내보냅니다.

## 에이전트 맵과 코드의 대응

| 에이전트 맵 | 코드 | 하는 일 |
|---|---|---|
| 프로토 기획서 (Figma) | docs/GDD.md | Figma 기획서 00~05의 입력 내용을 옮긴 원문 |
| 원본 리소스 데이터베이스 파일 | data/원본리소스_DB.json | Designer만 읽는 컨셉아트 기반 원본 데이터 |
| Designer | stairs_agents/designer.py, render.py, synth.py | Claude에 스프라이트와 사운드 설계를 요청하고, 그 명세를 PNG 스프라이트 맵과 WAV로 만든다 |
| Mechanics | stairs_agents/mechanics.py | 기획서 04를 근거로 1~100층 규칙과 수치를 mechanics.json으로 확정하고 검사한다 (코드는 쓰지 않음) |
| Developer | stairs_agents/developer.py | Claude에 게임 코드(index.html, game.js)와 스프라이트 정의(sprite_definition.json)를 요청한다. mechanics.json이 있으면 그 값을 그대로 옮긴다 |
| Publisher | stairs_agents/publisher.py | 1. 확장자 확인과 변환 2. 코드와 디자인 연결 3. 동작 확인 4. 게임 내보내기 |
| 실행 순서 | stairs_agents/pipeline.py | Mechanics를 먼저 실행하고, Designer와 Developer를 동시에 실행한 뒤 Publisher를 실행 |

같은 에이전트를 Claude Code 서브에이전트로도 쓸 수 있도록 `.claude/agents/`에 md 파일로 정리했습니다(역할, 지시문, 전체 코드 포함): `stairs-mechanics.md`, `stairs-designer.md`, `stairs-developer.md`, `stairs-publisher.md`, `stairs-pipeline.md`.
md 안의 코드는 원본의 사본이므로, `stairs_agents/`나 `prompts/`를 고친 뒤에는 다시 만들어야 합니다.

```
python tools/export_agents_md.py           # md 다시 만들기
python tools/export_agents_md.py --check   # md가 원본과 같은지 검사 (다르면 종료 코드 1)
```

두 에이전트가 같은 에셋 이름을 쓰도록 docs/ASSET_LIST.md에 에셋 ID, 변형, 애니메이션 이름을 정해 두었습니다.
각 에이전트에게 주는 지시문은 prompts/ 폴더에 있습니다.

## 준비

1. Python 3.10 이상
2. 패키지 설치: `pip install -r requirements.txt`
3. 동작 확인용 브라우저: `playwright install chromium` (Chrome이 이미 설치되어 있고 PATH에 있으면 그것을 씁니다)
4. 사운드 변환용 ffmpeg (libvorbis, libmp3lame 포함). Windows는 ffmpeg.exe가 PATH에 있어야 합니다.
5. Claude API 키: 환경 변수 `ANTHROPIC_API_KEY`

## 실행

```
# Claude API로 세 에이전트 실행
python -m stairs_agents run

# 실행하면서 Claude 응답을 replay/ 에 저장 (다음 실행에서 재사용 가능)
python -m stairs_agents run --record

# API 없이 replay/ 에 저장된 응답으로 실행
python -m stairs_agents run --replay replay

# 에이전트 하나씩 실행
python -m stairs_agents designer
python -m stairs_agents mechanics
python -m stairs_agents developer
python -m stairs_agents publisher
```

선택 사항: `--model` (기본 claude-sonnet-5-5), `--max-tokens` (기본 64000), `--no-resource-db` (Designer가 원본 리소스 데이터베이스를 쓰지 않음).

## 결과물 (output/)

- design_out/ : Designer가 만든 PNG, WAV, design_manifest.json, Claude가 낸 설계 명세(_spec_*.json)
- mech_out/ : Mechanics가 만든 mechanics.json(1~100층 규칙·수치 명세), mechanics_report.md
- dev_out/ : Developer가 만든 index.html, game.js, sprite_definition.json
- build/ : Publisher가 연결한 실행용 게임. index.html을 브라우저로 바로 열 수 있음
- dist/ : 승급의계단_PoC_web.zip, publisher_report.md, 동작 확인 화면 캡처(screens/)

## 게임 조작

- 메뉴: 방향키로 선택, Enter 또는 Space로 결정, 마우스 클릭 가능
- 플레이: ← → 다음 계단 방향으로 이동, Q 왼쪽 패링, E 오른쪽 패링, ESC 일시정지
- 게임 안에서 보기: 타이틀과 일시정지 메뉴의 "조작법" 버튼 (닫기 버튼 또는 ESC로 닫음)
- URL 매개변수: `?seed=7` 난수 고정, `?bot=1` 자동 플레이, `?mute=1` 소리 끔

## 이 PoC에서 확인한 것과 확인하지 못한 것

- replay/ 의 응답은 이 PoC를 만들 때 Claude(대화 세션)가 각 에이전트의 출력 형식에 맞춰 작성한 것입니다.
- replay_api/ 의 응답은 claude-sonnet-5-5 API로 실제 실행해 저장한 것이며, 그 결과물이 demo_api/ 입니다. Developer 응답 약 6분, Designer 응답(에셋별 8건 동시 요청) 약 3분이 걸렸습니다.
  - 예외: 플레이테스트 뒤 "새 층마다 하트 1 회복"(`floorHeal`)과 타이틀·일시정지의 "조작법" 화면을 replay_api/developer_code.txt 와 demo_api/game.js 에 손으로 추가했습니다. 그 밖의 코드는 API가 만든 그대로입니다.
- Designer가 모든 에셋을 한 번에 설계하면 응답이 64000 토큰을 넘어 잘렸기 때문에, 에셋마다 따로 요청하도록 바꾸었습니다.
- 두 버전 모두 Designer의 렌더링과 합성, Developer의 파일 생성, Publisher의 변환, 연결, 브라우저 동작 확인 9개 항목, 내보내기까지 모두 실행해 통과를 확인했습니다.
- 실제 API로 실행하면 Claude가 매번 다른 디자인과 코드를 만들기 때문에, Publisher의 동작 확인이 실패할 수 있습니다. 실패 내용은 dist/publisher_report.md에 남습니다.

## 기획서에 수치가 없어 정한 값 (game.js의 CONFIG, "기획서 미정" 표시)

| 값 | PoC 설정 |
|---|---|
| 한 층을 오르는 계단 칸 수 | 5칸 |
| 콤보 배수가 한 단계 오르는 연속 패링 수 | 5회 |
| 점수 단위 | 계단 한 칸 10점, 패링 50점, 각각 콤보 배수를 곱함 |
| 구간 안 난이도 증가 | 일수 감소 속도 최대 +50%, 공격 간격 2.6초에서 1.3초로 |
| 불협화음 루프 전환 | 11층부터 |
| 패링 판정 0.20초의 위치 | 서류가 도착하기 직전 0.20초 |
| 층마다 하트 회복 (플레이테스트 반영) | 새 층에 오를 때마다 하트 1 회복, 최대 3 (`FLOOR_HEAL`) |

## PoC 범위 밖

21층 이후 구간(경쟁 사원, 결재판, 전화기)과 60층, 100층 엔딩, 비동기 전체 랭킹 서버, 설정의 화면과 키 설정은 구현하지 않았습니다. 경쟁 사원과 21층 이후 배경 스프라이트는 Designer가 이미 만들어 두었습니다.
