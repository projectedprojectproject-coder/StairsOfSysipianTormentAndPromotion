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
| Designer QA | stairs_agents/qa_designer.py, qa.py, concept.py | Designer 결과물을 에셋 계약·03 팔레트·2배 밀도·컨셉 아트와 비교하고(규칙 검사 + Claude 시각 검토), 고칠 점을 output/qa_out/designer_qa.md로 보고한다 |
| Developer | stairs_agents/developer.py | Claude에 게임 코드(index.html, game.js)와 스프라이트 정의(sprite_definition.json)를 요청한다. mechanics.json이 있으면 그 값을 그대로 옮긴다 |
| Developer QA | stairs_agents/qa_developer.py, qa.py | Developer 결과물을 기획서 04 수치·조작·화면·스프라이트 정의 계약·PoC 제약으로 정적 검사하고(규칙 검사 + Claude 코드 검토), output/qa_out/developer_qa.md로 보고한다 |
| Publisher | stairs_agents/publisher.py | 1. 확장자 확인과 변환 2. 코드와 디자인 연결 3. 동작 확인 4. 게임 내보내기 |
| 실행 순서 | stairs_agents/pipeline.py | Mechanics를 먼저 실행하고, Designer → Designer QA와 Developer → Developer QA를 동시에 실행한 뒤 Publisher를 실행 |
| 컨셉 아트 | data/concept/ (05-1_title.png, 05-3_play.png, regions.json) | concept.py가 영역별로 참고 스프라이트를 뽑아 Designer 요청에 붙이고, Designer QA가 비교 기준으로 쓴다 |

같은 에이전트를 Claude Code 서브에이전트로도 쓸 수 있도록 `.claude/agents/`에 md 파일로 정리했습니다(역할, 지시문, 전체 코드 포함): `stairs-mechanics.md`, `stairs-designer.md`, `stairs-designer-qa.md`, `stairs-developer.md`, `stairs-developer-qa.md`, `stairs-publisher.md`, `stairs-pipeline.md`.
컨셉 아트에서 스프라이트를 뽑는 방법은 스킬 `.claude/skills/concept-sprite-extraction/SKILL.md`에 있습니다 (`python -m stairs_agents.concept palette|extract|boxes|regions`).
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

# 이미 만든 결과물에 QA만 (Designer QA, Developer QA)
python -m stairs_agents qa --replay replay
python -m stairs_agents qa-designer --replay replay
```

선택 사항: `--model` (기본 claude-sonnet-5-5), `--max-tokens` (기본 64000), `--no-resource-db` (Designer가 원본 리소스 데이터베이스를 쓰지 않음), `--no-qa` (QA 에이전트 생략), `--strict-qa` (QA 판정이 fail이면 Publisher 전에 멈춤).

QA의 Claude 검토는 API로 실행할 때 돌고, `--record`면 replay 폴더에 `qa_designer_review.txt`, `qa_developer_review.txt`로 저장됩니다. 재생 모드에서 이 파일이 없으면 규칙 검사만 하고 보고서에 "건너뜀"이라고 적습니다.

## 결과물 (output/)

- design_out/ : Designer가 만든 PNG, WAV, design_manifest.json, Claude가 낸 설계 명세(_spec_*.json)
- mech_out/ : Mechanics가 만든 mechanics.json(1~100층 규칙·수치 명세), mechanics_report.md
- dev_out/ : Developer가 만든 index.html, game.js, sprite_definition.json
- build/ : Publisher가 연결한 실행용 게임. index.html을 브라우저로 바로 열 수 있음
- qa_out/ : Designer QA·Developer QA 보고서(designer_qa.md, developer_qa.md, .json)와 컨셉 대조표(designer_contact.png)
- concept_refs/ : 컨셉 아트에서 뽑은 참고 스프라이트(PNG, refs.json)와 영역 표시 이미지
- dist/ : 승급의계단_PoC_web.zip, publisher_report.md, 동작 확인 화면 캡처(screens/), QA 보고서(qa/)

## 게임 조작

규칙, 점수, 공략 팁까지 포함한 플레이어용 안내는 [HOWTOPLAY.txt](HOWTOPLAY.txt)에 있습니다.
플레이테스트 결과(유형별 자동 플레이, 1~100층 명세 시뮬레이션, 전체화면 직접 플레이)와 그에 따른 수정 내역은 [docs/PLAYTEST_REPORT.md](docs/PLAYTEST_REPORT.md)에 정리했습니다.
같은 테스트를 다시 돌리는 도구는 `tools/playtest.py`(실시간 자동 플레이, `--game demo` 또는 `--game demo_api`)와 `tools/sim_spec.py`(1~100층 명세 시뮬레이션)입니다.

- 메뉴: 방향키로 선택, Enter 또는 Space로 결정, 마우스 클릭 가능
- 플레이: ← → 다음 계단 방향으로 이동, Q 왼쪽 패링, E 오른쪽 패링, ESC 일시정지
- 게임 안에서 보기: 타이틀 오른쪽 위 톱니(설정) 안의 "조작법", 일시정지 메뉴의 "조작법" 버튼 (닫기 버튼 또는 ESC로 닫음)
- URL 매개변수: `?seed=7` 난수 고정, `?bot=1` 자동 플레이, `?mute=1` 소리 끔

## 이 PoC에서 확인한 것과 확인하지 못한 것

- replay/ 의 응답은 이 PoC를 만들 때 Claude(대화 세션)가 각 에이전트의 출력 형식에 맞춰 작성한 것입니다.
- replay_api/ 의 응답은 claude-sonnet-5-5 API로 실제 실행해 저장한 것이며, 그 결과물이 demo_api/ 입니다. Developer 응답 약 6분, Designer 응답(에셋별 8건 동시 요청) 약 3분이 걸렸습니다.
  - 예외: 플레이테스트 뒤 "새 층마다 하트 1 회복"(`floorHeal`), 타이틀·일시정지의 "조작법" 화면, 문구 겹침 수정, 계단 그리기(디딤판 + 몸체), 타이틀 로고 위치, 11층부터 패링할 수 있는 경쟁 사원(rival) 근접 공격, 컨셉 이미지(data/concept/)에 맞춘 2배 픽셀(pixel_scale 2)·HUD 판·톱니 타이틀·계단 받침과 난간·층 바닥과 소품(props)을 replay_api/developer_code.txt 와 demo_api/game.js 에 손으로 추가했습니다. 2배 해상도 스프라이트·이미지 명세(replay_api/designer_*.txt)도 손으로 다시 썼습니다. 그 밖의 코드는 API가 만든 그대로입니다.
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
| 경쟁 사원 등장 (2026-11-19 결정) | 기획서는 21층부터지만 PoC에서 11층부터 공격의 40%, 걸어 들어오는 0.6초 + 예고 1.0초 뒤 근접 공격, 한 번 막으면 퇴장 (`RIVAL_FROM_FLOOR`, `rivalFromFloor`). Mechanics 명세(mechanics.json)는 아직 21층 그대로 |

## PoC 범위 밖

21층 이후 구간(경쟁 사원, 결재판, 전화기)과 60층, 100층 엔딩, 비동기 전체 랭킹 서버, 설정의 화면과 키 설정은 구현하지 않았습니다. 경쟁 사원과 21층 이후 배경 스프라이트는 Designer가 이미 만들어 두었습니다.
