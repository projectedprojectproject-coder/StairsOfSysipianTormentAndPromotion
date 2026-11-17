# 전달 문서 — Mechanics 에이전트 추가 (메카니즘·Developer 담당)

브랜치: `feature/mechanics-agent`

## 한 줄 요약

기획서 04(게임 메카니즘)를 맡는 **Mechanics 에이전트**를 새로 만들었습니다. 규칙과 수치를 `mechanics.json`으로 먼저 확정하고, Developer는 그 값을 그대로 코드로 옮깁니다.

```
프로토 기획서 ──04──▶ Mechanics ──mechanics.json──▶ Developer ─┐
              ──03──▶ Designer ─────────────────────────────────┼──▶ Publisher ──▶ 웹 게임
```

## 바뀐 파일

| 파일 | 변경 |
|---|---|
| `stairs_agents/mechanics.py` | 새 파일. Mechanics 에이전트와 검사기 `validate()` |
| `prompts/mechanics.md` | 새 파일. Mechanics에 주는 지시문 |
| `replay/mechanics_spec.txt` | 새 파일. 재생 모드용 Mechanics 응답 (1~100층 명세) |
| `tests/test_mechanics.py` | 새 파일. 검사기 시험 7개 |
| `.claude/agents/stairs-mechanics.md` | 새 파일. 서브에이전트 정의 |
| `stairs_agents/pipeline.py` | Mechanics를 맨 먼저 실행 |
| `stairs_agents/developer.py` | `output/mech_out/mechanics.json`이 있으면 Developer 입력에 붙임 |
| `stairs_agents/util.py` | `Paths.mech_out` 추가 |
| `stairs_agents/__main__.py` | `python -m stairs_agents mechanics` 명령 추가 |
| `prompts/developer.md` | "명세를 받았을 때는 CONFIG·층 진행·점수를 직접 정하지 말고 옮긴다" 절 추가 |
| `README.md` | 에이전트 표, 실행 명령, 결과 폴더에 Mechanics 추가 |

Designer와 Publisher 코드는 **건드리지 않았습니다.**

## 확인한 것

| 확인 | 결과 |
|---|---|
| `python -m unittest discover tests` | 7개 통과 |
| `python -m stairs_agents run --replay replay` | Publisher 동작 확인 9개 모두 통과, zip 생성 |
| `python -m stairs_agents run --replay replay_api --out output_api` | Mechanics 응답이 없는 옛 replay라 Mechanics를 건너뛰고, 9개 모두 통과 |
| `python -m stairs_agents mechanics --replay replay` | 층 100개, 위협 4종, 문제 0건 |

## 확인하지 못한 것

- **API 실행(`python -m stairs_agents run`)은 돌리지 않았습니다.** API 키가 필요해서입니다. 재생 모드의 Developer 응답(`replay/developer_code.txt`)은 Mechanics 이전에 만든 것이라, 지금 데모의 game.js는 아직 mechanics.json을 읽지 않습니다. 실제로 연결된 코드는 API로 한 번 돌려야 나옵니다.
- API로 돌린 뒤 결과를 남기려면: `python -m stairs_agents run --record` → `replay_api/`에 mechanics, developer 응답이 함께 저장됩니다.

## Publisher 담당에게

1. **지금 동작 확인 9개는 그대로 통과합니다.** 빌드 범위는 `mechanics.json`의 `scope.buildFloors = [1, 20]`이라 20층 승급에서 끝나는 기존 시나리오와 같습니다.
2. **범위를 넓힐 때 바꿀 것:** `scope.buildFloors`를 `[1, 60]`이나 `[1, 100]`으로 바꾸면 게임이 60층 노말 엔딩·100층 CEO 엔딩까지 이어집니다. 그때 `publisher.py`의 "20층 도달과 승급 판정" 확인을 엔딩 층 기준으로 고쳐 주세요.
3. **새로 확인하면 좋은 값:** API로 다시 만든 game.js부터는 `mechanics.json`의 `events` 이름(`parry_success`, `hit`, `promote`, `ending_normal` 등)이 `window.__stairs.log`에 찍히도록 Developer 지시문에 넣었습니다. 효과음 연결 확인에 쓸 수 있습니다.
4. 결과 폴더가 하나 늘었습니다: `output/mech_out/` (mechanics.json, mechanics_report.md). zip에는 넣지 않아도 됩니다.

## 저장소 관리자에게

1. **병합 순서:** 이 브랜치는 `main`의 `05a7cbb`(새 층마다 하트 1 회복) 위에서 만들었습니다. 충돌 없이 병합됩니다.
2. **API 키:** 새로 필요한 키는 없습니다. 기존과 같이 `ANTHROPIC_API_KEY` 환경 변수만 씁니다. 키를 파일에 넣지 않았습니다.
3. **`.claude/agents/stairs-developer.md`, `stairs-pipeline.md`의 코드 사본**은 이 변경 전 코드입니다. 그 문서들은 "원본을 고치면 함께 갱신"이 규칙이라, 병합 뒤 두 문서의 코드 사본을 원본으로 다시 붙여 넣어야 합니다.
4. `.gitignore`는 바꾸지 않았습니다(`output/`은 이미 제외).

## 다음 할 일 (메카니즘·Developer)

- API로 한 번 실행해 mechanics.json을 실제로 읽는 game.js를 만들고 `demo_api/`를 갱신
- 플레이테스트 질문 확인 (`output/mech_out/mechanics_report.md` 끝부분)
- 21~40층(경쟁 사원) 범위로 넓히기
