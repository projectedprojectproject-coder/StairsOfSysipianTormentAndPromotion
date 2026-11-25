# 승급의 계단 에이전트 PoC

Figma 에이전트 맵(페이지 "에이전트 맵")의 세 에이전트를 Python으로 구현한 Proof of Concept입니다.
지금은 Mechanics를 더한 생산 에이전트 4개와 QA 에이전트 3단계(Designer QA, Developer QA, 화면 대조 QA, 고침 반복 최대 11번), 플레이테스트 순환 구조이며, 최신 그림과 문서는 `agent_map/`(v3: svg, png, docx)에 있습니다.
프로토 기획서를 입력으로 받아 1~100층(사원 → 대리 → 과장 → 간부 → CEO, 20·40·60·80층 승급 심사, 100층 CEO실에서 마무리)을 플레이할 수 있는 웹 브라우저 게임을 만들어 내보냅니다.

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

## 루프 하네스 (v5, 2026-11-25)

역할(mechanics, designer, developer, publisher)마다 "만들기 → 평가 → 되먹임"을 반복하고, 남은 문제를 책임 역할(owner)로 되돌리는 실행 방식입니다. 설계와 확인 결과는 [docs/AGENT_HARNESS.md](docs/AGENT_HARNESS.md).

```
python -m stairs_agents harness --replay replay --roles mechanics   # API 없이 메카니즘 밸런스 루프
python -m stairs_agents harness --replay replay                     # 4역할 전부
```

결과: `output/harness/summary.md`, `ledger.jsonl`(차례마다 한 줄). 메카니즘 검사 기준은 `docs/mechanics_rules.json` 하나에 모았고, 플레이 동기(기획서 01-1)도 검사합니다. 아래 `run`(한 방향 파이프라인)은 그대로 남아 있습니다.

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

선택 사항: `--model` (기본 claude-sonnet-5-5), `--max-tokens` (기본 64000), `--no-resource-db` (Designer가 원본 리소스 데이터베이스를 쓰지 않음), `--no-qa` (QA 에이전트 생략), `--strict-qa` (QA 판정이 fail이면 Publisher 전에 멈춤), `--qa-rounds` (QA 고침 반복 최대 횟수, 1~11, 기본 11).

QA 고침 반복: Designer QA, Developer QA, 화면 대조 QA마다 판정이 pass가 아니면 고칠 점을 만든 에이전트에게 돌려줘 다시 만들고 다시 확인하기를 최대 11번 되풀이합니다. 통과하거나, 앞 차례와 같은 문제만 남아 나아지지 않으면 일찍 멈추고, 차례마다의 판정은 `output/qa_out/<대상>_loop.json`에 남습니다. 재생 모드(`--replay`)는 다시 만들어도 같은 응답이 나오므로 1번만 확인합니다.

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
  - 예외: 플레이테스트 뒤 "새 층마다 하트 1 회복"(`floorHeal`), 타이틀·일시정지의 "조작법" 화면, 문구 겹침 수정, 계단 그리기(디딤판 + 몸체), 타이틀 로고 위치, 11층부터 패링할 수 있는 경쟁 사원(rival) 근접 공격, 60층 확장과 결재판·전화기·서류 위협, 컨셉 이미지(data/concept/)에 맞춘 2배 픽셀(pixel_scale 2)·HUD 판·톱니 타이틀·계단 받침과 난간·층 바닥과 소품(props)을 replay_api/developer_code.txt 와 demo_api/game.js 에 손으로 추가했습니다. 2배 해상도 스프라이트·이미지 명세(replay_api/designer_*.txt)도 손으로 다시 썼습니다. 그 밖의 코드는 API가 만든 그대로입니다.
- Designer가 모든 에셋을 한 번에 설계하면 응답이 64000 토큰을 넘어 잘렸기 때문에, 에셋마다 따로 요청하도록 바꾸었습니다.
- 두 버전 모두 Designer의 렌더링과 합성, Developer의 파일 생성, Publisher의 변환, 연결, 브라우저 동작 확인 9개 항목, 내보내기까지 모두 실행해 통과를 확인했습니다.
- 실제 API로 실행하면 Claude가 매번 다른 디자인과 코드를 만들기 때문에, Publisher의 동작 확인이 실패할 수 있습니다. 실패 내용은 dist/publisher_report.md에 남습니다.

## 기획서에 수치가 없어 정한 값 (game.js의 CONFIG, "기획서 미정" 표시)

| 값 | PoC 설정 |
|---|---|
| 한 층을 오르는 계단 칸 수 | 5칸 |
| COMBO와 점수 배수 (2026-11-20 결정) | COMBO는 연속으로 막은 횟수. 점수 배수는 연속 3회마다 ×1씩 올라 최대 ×10 (`COMBO_PER_MULT`, `MAX_MULT`, `comboPerMult`, `maxMult`). 하트를 잃으면 둘 다 처음으로 |
| 구간 음악 (2026-11-25 결정) | 20층 구간마다 음악이 바뀐다: bgm_stage1(1~20, A단조 132bpm) · 2(21~40, D단조 138) · 3(41~60, E단조 112) · 4(61~80, C단조 148) · 5(81~100, G단조 156). 타이틀·로비는 bgm_loop |
| 구조조정 결과 화면 (2026-11-20 결정) | 위 가운데 "구조조정 대상" 판(승급이면 "승급" 판)이 도장처럼 크게 떨어져 쾅 찍힌다(화면 흔들림, 잉크 튐). 도장 뒤에 마지막으로 하트를 잃은 원인(장애물 종류, 발판, 금 간 계단, 일수)에 맞춘 한국어 팁이 떠오른다 |
| 점수 단위 | 계단 한 칸 10점, 패링 50점, 각각 콤보 배수를 곱함 |
| 구간 안 난이도 증가 | 일수 감소 속도 최대 +50%, 공격 간격 2.6초에서 1.3초로 |
| 불협화음 루프 전환 | 11층부터 |
| 패링 판정 0.20초의 위치 | 공격이 도착하기 직전 0.20초 |
| 층마다 하트 회복 (플레이테스트 반영) | 새 층에 오를 때마다 하트 1 회복, 최대 3 (`FLOOR_HEAL`) |
| 경쟁 사원 등장 (2026-11-19 결정) | 기획서는 21층부터지만 PoC에서 11층부터 공격의 40%, 걸어 들어오는 0.6초 + 예고 1.0초 뒤 근접 공격, 한 번 막으면 퇴장 (`RIVAL_FROM_FLOOR`, `rivalFromFloor`). Mechanics 명세(mechanics.json)는 아직 21층 그대로. 2026-11-20부터 경쟁 사원은 가장 가까운 층 바닥을 걸어 들어와 멈춘 뒤 플레이어 칸으로 뛰어올라 친다(허공에서 나타나지 않게, `RIVAL_LEAP` 0.3초) |
| PoC 범위 (2026-11-20 결정) | 1~100층. 20층(사원 → 대리), 40층(대리 → 과장), 60층(과장 → 간부), 80층(간부 → CEO)은 승급 문구와 하트 1 회복 뒤 계속 오르고(날아오던 장애물은 그대로), 100층(CEO실)에 오르면 결과 화면. 난이도는 20층 구간마다 처음 값부터 다시 오른다 (`PROMO_FLOORS`, `promoteFloors`) |
| 위협 구성 (2026-11-20 결정) | 결재판(1층~, 기본), 경쟁 사원(11층~), 컴퓨터 모니터(21층~, 위층 창이 깨지며 플레이어 옆으로 떨어짐, 나타날 때 유리 깨지는 소리), 전화기(31층~, 화면 아래에서 솟아 포물선으로 날아옴), 서류(41층~, 한쪽에서 던져져 머리 위로 넘어가 반대쪽에서 맞음). 비중은 결재판 1 : 경쟁 사원 0.7 : 모니터 0.6 : 전화기 0.6 : 서류 0.6 |
| 경쟁 사원 추격 (2026-11-20 결정) | 플레이어가 경쟁 사원이 걸어 온 층 바닥보다 높이 올라가 있으면, 경쟁 사원은 계단 아래 끝에서 계단을 따라(초당 10칸) 쫓아 올라와 바로 뒤 칸에서 친다. 막는 쪽은 경쟁 사원이 있는 쪽, 곧 플레이어가 마지막으로 오른 방향의 반대쪽이며 치기 직전 0.3초에 정해진다. 따라잡기 전에는 치지 않는다 (`RIVAL_CLIMB`, `rivalClimb`) |
| 게임 모드 (2026-11-20 결정) | 로비 아래 버튼 셋: 가운데 "업무 시작"(보통, 1~100층, Enter로 바로), 오른쪽 "무한 모드"(1층부터 모든 장애물·금 간 계단(2층~)·카메라 플래시, 100층에서 끝나지 않고 난이도가 60층에 걸쳐 끝까지 오름, 최고 층을 따로 저장), 왼쪽 "연습 모드"(계단 없는 평범한 사무실 바닥에 서서 계단을 오르지 않고, 남은 일수가 줄지 않으며 게임 오버가 없다. 계단 장애물 없이 모든 공격과 카메라 플래시가 나오고, 하트 대신 막은 수·맞은 수를 센다. ESC → 메인으로) |
| 금 간 계단 (2026-11-20 결정) | 21층부터 칸의 약 16%(층이 바뀌는 칸 빼고, 칸 번호로 정해짐)가 금 간 계단이다. 올라서면 삐걱이는 소리가 나고, 1.5초 넘게 서 있으면 흔들리고 붉어지다 무너져 바로 구조조정 (`CRACK_TIME`, `crackTime`) |
| Unity 이식 (2026-11-25) | Unity 판은 `unity` 브랜치에서 따로 만든다 (`git switch unity`). main은 웹 판만 둔다. 웹 규칙을 옮긴 C# 핵심 루프, uGUI 화면, 웹 빌드 에셋 가져오기 메뉴, 웹과 같은지 확인하는 테스트가 있고 여는 방법은 그 브랜치의 docs/UNITY_PORT.md |
| 외부 음악 (2026-11-25) | `data/music/<사운드 id>.ogg`(또는 wav·mp3 등)가 있으면 Publisher가 합성음 대신 쓴다. Suno 등으로 만든 곡은 `tools/music_import.py`로 마디 단위 루프로 다듬는다. Suno 공식 API 상황과 흐름은 docs/MUSIC_SUNO.md |
| 젖은 계단 WET HAZARD (2026-11-25 결정) | 30층부터 칸의 약 14%(층이 바뀌는 칸, 금 간 칸 빼고)는 물이 고이고 전선이 올라 있다. 3초마다 0.5초 동안 전기가 흐르며(0.6초 전부터 불꽃 예고, 흐를 때 sfx_electric), 흐르는 순간 그 칸에 있으면 바로 구조조정. 무한 모드는 3층부터, 연습 모드에는 없다 (`SHOCK_PERIOD`, `shockPeriod`) |
| 카메라 플래시 (2026-11-20 결정) | 61층부터 평균 3.5초마다 셔터 소리와 함께 화면이 0.28초 하얗게 번쩍인다. 막을 수 없고 피해도 없다 (눈부심만) |
| 서류가방 (2026-11-20 결정) | 71층부터. 검정 가죽 서류가방(금색 잠금쇠)이 전화기처럼 화면 아래에서 크게 솟아 날아오다가 플레이어 앞에서 터져 덮개가 젖혀지며 서류나 결재판이 쏟아진다. 터지는 순간(도착 0.1초 전, 판정 창 한가운데)이 패링할 때이고, "똑, 똑, 펑!"(sfx_cue_suitcase)의 펑이 그 순간에 온다 |
| 커피 (2026-11-20 결정) | 11층부터. 결재판처럼 옆에서 납작하게 돌며 날아오지만 막으면 안 된다: 막으면 하트 -1, 그냥 두면 지나간다. "!" 대신 빨간 ×, 경고음 대신 경쟁 사원의 "헤이!"를 높게 올린 소리(sfx_cue_coffee)가 박에 맞춰 울린다. 같은 쪽에 막을 공격이 함께 있으면 패링은 그 공격을 먼저 막는다 (`COFFEE_FROM_FLOOR`, `coffeeFromFloor`) |
| 포스트잇 (2026-11-20 결정) | 61층부터. 결재판처럼 날아오지만 막으면 튕겨 나갔다가 1초 뒤 같은 쪽으로 돌아와 1~5번(무작위) 막아야 없어진다. 남은 횟수는 색으로 보인다: 분홍 5, 파랑 4, 초록 3, 노랑 2, 흰색 1. 막을 때마다 패링 점수와 일수를 얻는다 (`STICKY_MAX`, `stickyMax`) |
| 모니터 예고와 떨어지는 느낌 (2026-11-20 결정) | 모니터는 형광등이 0.6초 깜박인 뒤(sfx_light_flicker) 유리가 깨지며 수평에서 70도 사선으로 중력처럼 빨라지며 떨어진다 (`MONITOR_ANGLE`, `FLICKER`). 모니터·전화기는 불규칙하게 돌고, 결재판은 납작하게 수평으로 돈다 |
| 패링 타이밍 소리 (2026-11-20 결정) | 공격마다 박이 있는 소리를 틀어, 그 박이 패링 판정 창(도착 전 0.2초)의 한가운데(도착 0.1초 전)에 오게 한다. 결재판 "딱… 딱!"(두 번째 딱), 경쟁 사원 "헤이!"(막을 쪽이 정해진 뒤), 전화기 벨 두 번(두 번째 벨, "!" 대신 경고음 없음), 서류 바스락 "착" 접는 소리. 모니터는 나타날 때 유리 깨지는 소리만 난다 (`CUES`, `cues`) |

## PoC 범위 밖

100층 엔딩 연출(기획서의 순환), 비동기 전체 랭킹 서버, 설정의 화면과 키 설정은 구현하지 않았습니다. 100층 CEO실 배경(bg_zone5)과 계단(zone5)은 Designer가 만든 것을 씁니다.
