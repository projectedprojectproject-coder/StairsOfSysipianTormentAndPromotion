# Unity 이식 (1단계: 핵심 루프)

2026-11-25 시작. 에이전트 맵 v4(Unity 계획)의 첫 단계로, 웹 PoC의 규칙을 그대로 옮긴 Unity 프로젝트를 `unity/StairsOfPromotion/`에 두었다.
그림과 소리는 새로 만들지 않고, 에이전트 파이프라인이 만든 웹 빌드 에셋(`output/build/assets`)을 가져와 쓴다.

## 여는 방법

1. Unity Hub → Add → `unity/StairsOfPromotion` 폴더. Unity 6(6000.0 LTS)을 기준으로 했다. 2022.3 LTS도 될 것이다.
2. Edit > Project Settings > Player > Active Input Handling 을 **Input System Package** 또는 **Both** 로 둔다 (키 입력에 Input System을 쓴다).
3. 웹 에셋 만들기(이미 있으면 건너뜀): 저장소 루트에서 `python -m stairs_agents run --replay replay`
4. 메뉴 **Stairs > Import Web Build Assets**: PNG 시트를 픽셀 아트 설정(Point, 압축 없음, PPU 32)으로 가져와 프레임별로 자르고, ogg를 가져와 `Assets/Imported/SpriteCatalog.asset`을 만든다.
5. 메뉴 **Stairs > Create Game Scene** → `Assets/Scenes/Game.unity` → Play.
6. Window > General > Test Runner > EditMode 에서 `ParityTests`를 돌려 웹과 같은지 확인한다.

조작은 웹과 같다: ← → 오르기, Q E 막기, Esc 일시정지, Enter 결정. `GameController`의 `bot`을 켜면 웹의 `?bot=1`처럼 혼자 오른다.

## 구조

| 폴더 | 내용 | 웹 PoC에서 |
|---|---|---|
| `Assets/Scripts/Core` (Stairs.Core, UnityEngine 없음) | `StairsConfig` 수치, `Mulberry32` 난수, `StairLayout` 계단·금 간 계단·젖은 계단·감전 주기, `RunSimulation` 한 판의 규칙(오르기, 패링, 콤보·배수, 일수, 하트, 승급, 위협 8종, 카메라 플래시, 봇) | `CONFIG`, `mulberry32`, `ensureStairs`, `isCracked`, `isWet`, `shockState`, `doStep`, `doParry`, `updatePlay`, `spawnAttack`, `botTick` |
| `Assets/Scripts/Game` (Stairs.Game) | `GameController` 화면 전환·입력·그리기·HUD(임시 IMGUI), `AudioDirector` 20층마다 단계 음악과 효과음, `SpriteCatalog`·`GameConfigAsset` ScriptableObject | `screen`, `drawWorld`, `drawHud`, `drawResult`, `syncAudio` |
| `Assets/Editor` | `StairsAssetImporter`(웹 에셋 가져오기, 씬 만들기), `MiniJson` | Publisher의 연결 단계 |
| `Assets/Tests/EditMode` | `ParityTests`: 난수, 계단 방향, 금 간·젖은 칸 목록이 웹과 같은지(node로 뽑은 기대값), 젖은 칸 감전, 봇이 100층 CEO까지 오르는지 | Publisher 동작 확인 |

규칙은 Core에만 있고 화면을 모르기 때문에 웹과 같은 seed면 같은 계단, 같은 금 간·젖은 칸이 나온다.
수치는 `Assets/Settings/GameConfig.asset` 인스펙터에서 고친다 (기본값은 demo_api의 CONFIG, 한 층 6칸).

## 아직 웹과 다른 점 (다음 단계)

- 경쟁 사원: 층 바닥을 걸어와 계단을 쫓아 오르는 움직임 없이, 같은 시각에 같은 쪽을 치는 단순한 형태다.
- HUD와 메뉴는 IMGUI 글자다. 다음 단계에서 uGUI 또는 UI Toolkit과 `hud_icons` 시트, 로비·결과 배경 배치(05-2·05-5)로 바꾼다.
- 위협의 비행 경로, 모니터 유리 조각, 서류가방이 터지는 연출, 패링 불꽃, 화면 흔들림, 결과 화면의 도장 그림이 단순하다.
- 저장(최고 기록, 무한 모드 기록), 설정·조작법 화면, 기록 공유가 없다.
- 이 저장소의 환경에 Unity와 .NET이 없어 C#을 컴파일해 보지 못했다. 처음 열 때 콘솔 오류가 나오면 그 내용을 알려 주면 고친다.

## 에이전트 파이프라인과의 관계 (맵 v4)

- Designer와 Publisher는 그대로 웹 에셋을 만든다. Unity 판은 `Stairs > Import Web Build Assets`로 그 결과를 받는다.
- Developer가 웹 `game.js` 대신 C#을 쓰게 하려면 `prompts/developer.md`에 Unity 규칙(Core에 규칙, Game에 표현)을 더하고, Developer QA의 정적 검사(JS 문법 → C# 컴파일, CONFIG 수치 → `StairsConfig` 수치)를 바꾼다.
- Publisher의 Playwright 동작 확인은 Unity Test Runner(`-batchmode -runTests -testPlatform EditMode`)와 WebGL 빌드 확인으로 바꾼다.
