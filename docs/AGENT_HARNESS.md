# 에이전트 설계 v5 — 루프 기반 하네스

## 왜 바꾸나

v3까지의 파이프라인은 한 방향이다: Mechanics → (Designer ∥ Developer) → Publisher.
QA 고침 반복(qa_loop)이 있지만 다음 한계가 있었다.

| 한계 | 결과 |
|---|---|
| 되먹임이 자기 QA로만 간다 | Publisher·화면 대조에서 "Designer 책임"인 문제도 Developer에게만 간다. 플레이테스트 → Mechanics 화살표는 그림에만 있고 코드가 없다 |
| 직전 차례 문제만 돌려준다 | 고쳤다가 다시 깨진 문제(재발)를 모른다 |
| 마지막 결과를 그대로 쓴다 | 고치다 더 나빠져도 되돌리지 않는다 |
| 재생 모드는 1번만 돈다 | API 없이는 반복을 시험할 수 없다 |
| 평가 = QA 한 종류 | 시뮬레이션·동작 확인 같은 평가를 같은 틀에 꽂을 수 없다 |
| 검사 기준이 코드에 박혀 있다 | 게임이 위협 8종·80층 승급으로 바뀌었는데 Mechanics 검사기는 4종·100층 그대로였다 |

## 구조

```
                         ┌───────────────────── 바깥 루프 (orchestrator.py, 최대 3번) ─────────────────────┐
                         │                                                                                  │
  docs/GDD.md ──┐        │  ┌─ 안쪽 루프 (LoopRunner) ─┐                                                     │
  mechanics_    │        │  │ act → 평가기들 → 되먹임  │  mechanics ──▶ designer ∥ developer ──▶ publisher   │
  rules.json ───┼──────▶ │  │   ↑  (점수·최선본·기록)  │      ▲              ▲          ▲            │        │
  컨셉 아트 ────┘        │  └──────────────────────────┘      └──── 라우터: 남은 문제를 owner 역할로 ◀┘        │
                         └──────────────────────────────────────────────────────────────────────────────────┘
                                         │ 차례마다 한 줄
                                         ▼
                               output/harness/ledger.jsonl, summary.json, summary.md
```

### 안쪽 루프 (stairs_agents/harness/core.py `LoopRunner`)

1. **act**: 역할이 결과물을 만든다(LLM). 다시 만들 수 없으면(재생 모드) **repair**로 코드가 고친다.
2. **평가**: 역할에 꽂힌 평가기를 모두 돈다. 결과는 같은 형식 `Evaluation(issues, metrics, distance)`.
3. **점수**: 벌점 = 심각도 가중합(high 10, mid 3, low 1) + 목표까지 거리. 문제 수가 같아도 나아졌는지 구분한다.
4. **최선본 지키기**: 벌점이 가장 낮았던 결과물을 보관하고, 마지막이 더 나쁘면 되돌린다.
5. **기억**: 문제마다 처음 나온 차례, 고친 차례를 쌓아 "재발"을 표시해 돌려준다.
6. **멈춤**: 통과(high·mid 없음) / 예산(차례, 시간, LLM 호출) / 3차례 연속 나아지지 않음.

### 바깥 루프 (stairs_agents/harness/orchestrator.py)

- 순서: mechanics → designer ∥ developer → publisher.
- 라우터: 각 역할의 남은 문제 중 **owner가 다른 역할**인 것을 모아 그 역할의 첫 피드백으로 넘기고, 그 역할과 하류(mechanics → developer, publisher / designer → publisher / developer → publisher)를 다시 돈다.
- 예: 화면 대조에서 "배경 색이 컨셉과 다름(owner designer)" → designer부터 다시 → publisher 다시.

## 역할과 평가기 (stairs_agents/harness/roles.py)

| 역할 | 만들기 | 평가기 | LLM 없이 고치기 |
|---|---|---|---|
| **mechanics** | MechanicsAgent (prompts/mechanics.md) | ① 명세 검사 — docs/mechanics_rules.json 대조 (고정값, 위협 8종·첫 층, 승급 심사 층, 엔딩, **플레이 동기**) ② **밸런스 시뮬레이션** — stairs_agents/sim.py로 유형별 도달률을 재 balanceTargets와 비교 | 형식 수리 + 목표에서 벗어난 구간의 공격 간격·일수 감소·위험 칸 비율 자동 조정 |
| **developer** | DeveloperAgent | ① Developer QA(기존 규칙 검사 + Claude 코드 검토) ② 명세 일치 — mechanics.json 고정값이 CONFIG에 있는지 | 없음 |
| **designer** | DesignerAgent | Designer QA (기존) | 없음 |
| **publisher** | PublisherAgent | ① 동작 확인(Playwright) ② 화면 대조 | 없음 — 문제를 owner(developer/designer)로 넘김 |

## 실행

```bash
python -m stairs_agents harness --replay replay --roles mechanics      # API 없이 메카니즘 루프 (밸런스 자동 조정)
python -m stairs_agents harness --replay replay                        # 4역할 전부 (재생 모드)
python -m stairs_agents harness                                        # Claude API
python -m stairs_agents harness --rounds 12 --outer-rounds 3 --max-llm-calls 12
python -m stairs_agents run --replay replay                            # 기존 한 방향 파이프라인 (그대로 남김)
```

## 확인한 것 (재생 모드)

- 메카니즘 루프: 1차례 벌점 12.8(보통 60층 0.5%, 초보 20층 11.5%, 숙련자 100층 0%) → 자동 조정 10번 → 11차례 벌점 0 **통과**.
  주된 패배 원인이 "발판 실수"와 금 간·젖은 계단이어서, 위험 칸 비율을 함께 조정해야 수렴했다.
- 시험: tests/ 27개 통과 (검사기 10, 시뮬레이션 1, 루프 4 등).

## 아직 안 된 것

- API로 4역할 전체 루프를 돌려 보지 않았다(키 필요). 재생 모드의 developer·designer는 다시 만들 수 없어 1차례만 돈다.
- sim.py의 발판 위험 모델은 근사다. 실제 게임과의 차이는 tools/playtest.py(브라우저 자동 플레이) 결과로 balanceTargets를 보정해야 한다.
- 플레이 동기(연봉·고스트·사내 문서·재심 청구)는 명세와 Developer 지시문까지 들어갔고, 게임 코드는 API로 다시 만들어야 반영된다.
