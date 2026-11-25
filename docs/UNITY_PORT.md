# Unity 이식 (1단계: 핵심 루프, 2단계: 경쟁 사원·uGUI·저장)

2026-11-25 시작. 에이전트 맵 v4(Unity 계획)의 첫 단계로, 웹 PoC의 규칙을 그대로 옮긴 Unity 프로젝트를 `unity/StairsOfPromotion/`에 두었다.
그림과 소리는 새로 만들지 않고, 에이전트 파이프라인이 만든 웹 빌드 에셋(`output/build/assets`)을 가져와 쓴다.

## 여는 방법

1. Unity Hub → Add → `unity/StairsOfPromotion` 폴더. Unity 6(6000.0 LTS)을 기준으로 했다. 2022.3 LTS도 될 것이다.
2. Edit > Project Settings > Player > Active Input Handling 을 **Input System Package** 또는 **Both** 로 둔다 (키 입력에 Input System을 쓴다).
3. 웹 에셋 만들기(이미 있으면 건너뜀): 저장소 루트에서 `python -m stairs_agents run --replay replay`
4. 메뉴 **Stairs > Import Web Build Assets**: PNG 시트를 픽셀 아트 설정(Point, 압축 없음, PPU 32)으로 가져와 프레임별로 자르고, ogg를 가져와 `Assets/Imported/SpriteCatalog.asset`을 만든다.
5. 메뉴 **Stairs > Create Game Scene** → `Assets/Scenes/Game.unity` → Play.
   - 한글 글꼴: 씬의 `Stairs Game` 오브젝트 → `GameController` → **Ui Font** 칸에 TTF를 넣는다. 권장은 픽셀 글꼴
     **NeoDunggeunmo(네오둥근모, SIL OFL 1.1)** `NeoDunggeunmo.ttf` 또는 **Galmuri11**, 깔끔한 쪽은 **Noto Sans KR**(OFL)이다.
     `Assets/Fonts/`에 TTF를 두고 Import Settings에서 Character = Dynamic으로 둔다. 저장소에는 글꼴을 넣지 않았다(내려받지 않음).
     비워 두면 OS 글꼴(맑은 고딕 → Apple SD Gothic Neo → Noto Sans CJK KR) 순서로 찾고, 그것도 없으면 Unity 기본 `LegacyRuntime.ttf`라 한글이 □로 나올 수 있다.
   - HUD는 uGUI `Text`(레거시)로 만든다. TextMeshPro를 쓰려면 Window > TextMeshPro > Font Asset Creator로 위 TTF에서
     한글 2,350자(KS X 1001) 아틀라스를 만들어야 해서, PoC에서는 동적 글꼴로 두었다.
6. Window > General > Test Runner > EditMode 에서 `ParityTests`를 돌려 웹과 같은지 확인한다.

조작은 웹과 같다: ← → 오르기, Q E 막기, Esc 일시정지, Enter 결정(메뉴는 방향키로 고르고 마우스로 눌러도 된다). `GameController`의 `bot`을 켜면 웹의 `?bot=1`처럼 혼자 오른다.

## 구조

| 폴더 | 내용 | 웹 PoC에서 |
|---|---|---|
| `Assets/Scripts/Core` (Stairs.Core, UnityEngine 없음) | `StairsConfig` 수치, `Mulberry32` 난수, `StairLayout` 계단·금 간 계단·젖은 계단·감전 주기, `RunSimulation` 한 판의 규칙(오르기, 패링, 콤보·배수, 일수, 하트, 승급, 위협 8종, 경쟁 사원 쫓아오기, 카메라 플래시, 봇) | `CONFIG`, `mulberry32`, `ensureStairs`, `isCracked`, `isWet`, `shockState`, `doStep`, `doParry`, `updatePlay`, `spawnAttack`, `updateRival`, `rivalPos`, `botTick` |
| `Assets/Scripts/Game` (Stairs.Game) | `GameController` 화면 전환·입력·월드 그리기(계단, 플레이어, 경쟁 사원, 위협, 불꽃, 플래시), `GameUi`+`UiKit` uGUI HUD·메뉴(코드로 만듦), `SaveData` PlayerPrefs 기록, `AudioDirector` 20층마다 단계 음악과 효과음, `SpriteCatalog`·`GameConfigAsset` ScriptableObject | `screen`, `drawPlayWorld`, `drawHud`, `drawTitle`, `drawLobby`, `drawPause`, `drawHelp`, `drawResult`, `save`, `syncAudio` |
| `Assets/Editor` | `StairsAssetImporter`(웹 에셋 가져오기, 씬 만들기), `MiniJson` | Publisher의 연결 단계 |
| `Assets/Tests/EditMode` | `ParityTests`: 난수, 계단 방향, 금 간·젖은 칸 목록이 웹과 같은지(node로 뽑은 기대값), 젖은 칸 감전, 봇이 100층 CEO까지 오르는지, 경쟁 사원의 잠금 쪽·잠금 시각·늦게 따라잡을 때 미뤄지는 공격·패링 소리 순서 | Publisher 동작 확인 |
| `Tools~` (Unity가 가져오지 않음) | `rival_expect.js`: 웹 `game.js`를 node에서 돌려 경쟁 사원 테스트 기대값을 다시 뽑는다. `cs_core.js`: C# Core를 한 줄씩 옮긴 JS. `playtest.js`: 웹과 `cs_core.js`를 같은 seed로 돌려 사건 기록을 맞대어 본다 (아래 "플레이테스트") | |

규칙은 Core에만 있고 화면을 모르기 때문에 웹과 같은 seed면 같은 계단, 같은 금 간·젖은 칸이 나온다.
수치는 `Assets/Settings/GameConfig.asset` 인스펙터에서 고친다 (기본값은 demo_api의 CONFIG, 한 층 6칸).

## 2단계에서 바뀐 것 (2026-11-25)

- **C# 검토**: Unity·.NET이 없어 눈으로 읽어 확인했다. 컴파일 오류는 찾지 못했고, 대신 그리기 버그 하나를 고쳤다:
  1단계는 i번째 칸을 Unity y = `-i * stepH`에 두어 계단이 화면 **아래로** 내려갔다. 이제 Core는 웹 좌표(아래가 +y)를 쓰고
  `GameController.W2U`/`StairUY`가 Unity 쪽(위가 +y)으로 뒤집는다. uGUI를 붙이며 `UnityEngine.UI`를 `Stairs.Game.asmdef`에 더했다.
- **경쟁 사원 쫓아오기**: 웹 `updateRival`/`rivalPos`를 `RunSimulation`에 옮겼다 (Core는 여전히 UnityEngine 없음).
  화면 끝(`camX ± (viewW/2 + 16)`)에서 가장 가까운 층 바닥(`floorStep`)을 `rivalSpeed` 240px/초로 걸어오고, 플레이어가 그 바닥보다
  높으면 계단 아래 끝에서 `rivalClimb` 10칸/초로 바로 뒤 칸까지 쫓아 오른다. 치기 `rivalLeap` 0.3초 전에 막을 쪽이 잠기며,
  계단에서는 **플레이어가 마지막으로 오른 방향의 반대쪽**이다. 아직 따라잡지 못했으면 붙을 때까지 공격이 미뤄진다.
  패링 타이밍 소리와 봇은 잠긴 뒤에만 반응한다(웹 `p.locked !== false`). `StairsConfig`에 `rivalLeap`, `rivalSpeed`, `rivalClimb`,
  `showRivalCameo`, `viewW/viewH`를 웹 값으로 더했다.
- 경쟁 사원이 들어오는 자리가 카메라에 기대므로 웹의 `pvx/pvy/camX/camY` 따라가기, 연출 타이머(`hitTimer`, `stepTimer`, `shake`,
  `hurtFlash`), 패링 불꽃·물러나는 경쟁 사원·장식 경쟁 사원(`rivalIdx`)도 Core로 옮겼다. 덕분에 `decor` 난수를 웹과 같은 순서로 써서
  카메라 플래시 시각도 웹과 맞는다. `Bot = true`면 웹처럼 `Tick` 안에서 봇이 돈다.
- **uGUI HUD·메뉴** (IMGUI 제거): `GameUi`가 320x180 논리 화면을 코드로 만들고 `CanvasScaler`(Expand)로 키운다. 배치는 웹 05-1~05-5 그대로:
  층·직급 명판(사원증 아이콘), D-day 명판(달력 아이콘, 7일 이하 빨강, 일수 게이지), 하트(`heart`/`heart_empty`), 콤보 "N COMBO / 점수 ×M"(×10이면 빨강),
  조작 키 아이콘(`arrow_left/right`, `shield_q/e`, 누르면 올리브), 감전 예고, 승급·층 문구, 맞으면 붉게 번쩍.
  로비는 `bg_lobby` 위에 1F·D-30 명판, 사원증(최고 직급), 화이트보드 기록, 모드 버튼 3개(연습 · 업무 시작 · 무한)와 고른 모드 설명.
  결과는 `bg_result` 위에 큰 플레이어(구조조정은 회색, 상자 들고 나감), 도장(구조조정 빨강·승급 올리브: 0.15초 뒤 0.22초 동안 크게 떨어져 찍히고,
  흔들림·잉크 튐·`sfx_hit`), 인사 평가 표, NEW 표시, 도장 뒤 떠오르는 TIP 띠. 키보드 포커스와 마우스 클릭(EventSystem + InputSystemUIInputModule을 없으면 만든다) 둘 다 된다.
- **저장**: `SaveData`(PlayerPrefs, 웹 localStorage와 같은 키 `stairs_best_floor`, `stairs_best_score`, `stairs_best_endless`)와 소리 켜기·끄기(`stairs_muted`).
  보통 모드는 최고 층·점수, 무한 모드는 최고 층만. 연습 모드는 기록하지 않는다(웹은 연습도 보통 기록에 섞는다: 웹 쪽 후속 과제).
- **일시정지**: Esc 또는 창이 가려지면 멈춘다. 계속하기 · 조작법(웹 drawHelp 내용) · 소리 켜짐/꺼짐 · 메인으로.
- **테스트**: 기존 6개는 그대로 두고(봇 테스트는 `Bot = true`로 웹과 같은 순서), 경쟁 사원 5개를 더했다. 기대값은 웹 `game.js`를 node로 돌려 뽑았고
  (`Tools~/rival_expect.js`), 웹 봇은 seed 1~4 모두 경쟁 사원과 함께 100층 CEO에 닿는 것을 node로 확인했다.
  (플레이테스트 뒤 Core를 double로 바꿔 지금은 프레임 번호까지 정확히 맞춘다.)

## 플레이테스트와 고친 것 (2026-11-25, Unity 없이)

Unity를 설치하지 못해(샌드박스가 Program Files에 쓰지 못함) Unity 없이 두 갈래로 확인했다.

1. **규칙 플레이테스트 (node)**: `Tools~/cs_core.js`는 C# Core(`Mulberry32`, `StairLayout`, `RunSimulation`)를 한 줄씩 옮긴 JS다.
   `node unity/StairsOfPromotion/Tools~/playtest.js demo_api/game.js` 가 웹 `game.js`와 이것을 같은 seed·모드로 1/60초씩 돌려
   사건 기록(공격, 경쟁 사원 잠금, 패링, 하트, 층, 승급, 끝난 까닭)과 점수를 맞대어 본다.
   - 봇: 보통 6판(모두 100층 CEO), 무한 3판(4분, 196층), 연습 2판 / 사람 흉내: 오르기만(하트 소진, 무한은 감전), 가만히(하트 소진), 틀린 쪽(하트 소진), 느리게.
   - **처음 결과: 보통·무한 9판이 웹과 달랐다** (예: seed 1 점수 웹 110,160 / Unity 146,700). 규칙은 같았다:
     `cs_core.js`를 double로 돌리면 11판이 모두 같았다. 원인은 C# `float`였다. 2분 동안 시간·봇 타이머가 쌓이며 오차가 커지고,
     `0.33f`, `0.19f` 같은 수치가 웹의 0.33, 0.19와 조금씩 달라 한두 프레임씩 밀렸다. 그 결과 경쟁 사원 잠금이 0.15초 늦어지고
     오르는 순간의 배수가 달라 점수가 갈렸다.
   - **고침**: Core 상태를 모두 `double`로 바꾸고, 인스펙터의 float 수치는 `StairsConfig.D(v) = (double)(decimal)v`로 읽는다
     (`(double)0.33f`는 0.32999998이지만 `(double)(decimal)0.33f`는 0.33). 이제 위 19판이 **모두 웹과 프레임 단위로 같다**.
     `GameController`도 웹처럼 1/60초 고정 간격(`RunSimulation.Step60`, 한 번에 최대 0.1초)으로 `Tick`한다.
   - `ParityTests`: 경쟁 사원 테스트의 ±1~2 허용을 없애고 웹 값과 정확히 비교한다. 한 판 전체(보통 seed 1·2, 무한 7, 연습 10)의
     점수·패링 수·최고 콤보를 웹과 비교하는 `BotRun_MatchesWebFrameForFrame`, 수치 읽기 `ConfigValues_ReadAsWebDoubles`를 더했다.
2. **코드 다시 읽기**로 찾아 고친 Unity 쪽 버그:
   - 끝난 뒤 결과로 넘어가기 전 1초(endDelay)에 Esc를 누르면 일시정지가 열리고 "계속하기"가 끝난 판을 거부해 **일시정지 화면에 갇혔다**.
     이제 그 1초에는 일시정지하지 않고, 계속하기도 끝난 판을 받아 결과로 넘어간다.
   - 버튼을 마우스로 누른 뒤 Enter를 치면 EventSystem의 Submit과 키보드 처리가 겹쳐 **두 번 실행**됐다. 버튼의 방향키 이동을 끄고 누른 뒤 선택을 푼다.
   - `SpriteCatalog.Get`에 음수 시간이 들어오면 **배열 밖 예외**가 났다 (경쟁 사원은 `minAttackGap` 때문에 등장 시각이 미뤄지면 생길 수 있다).
     웹처럼 0으로 자르고, 한 번만 도는 동작(step, parry, hit, box_exit, proud, attack, leave)은 웹 `ONCE`처럼 마지막 프레임에 멈춘다 (결과 화면에서 상자 들고 나가는 동작이 되풀이되던 것).
   - 연습 모드에 웹에는 없는 계단이 그려졌다 → 그리지 않는다. 층 바닥(콘크리트 슬래브)을 그려 경쟁 사원이 허공을 걷지 않게 했다.
   - "!" 예고가 경쟁 사원에게만 있었다 → 모든 위협 위에 "!", 커피 위에는 "막지 말라"는 빨간 ×.
   - 카메라 플래시가 사라지지 않고 같은 밝기였다 → 웹처럼 줄어든다. 맞았을 때 붉은 번쩍임을 웹 세기(0.35)로, 금 간 계단은 흔들림과 함께 붉어진다.
   - 비활성 패널에서 `GetComponentsInChildren`이 테두리를 못 찾던 것(`includeInactive`).

## 아직 웹과 다른 점 (다음 단계)

- **컴파일 확인 못 함**: 이 환경에 Unity와 .NET(최신 csc)이 없어 C#을 한 번도 컴파일하지 못했고 EditMode 테스트도 돌리지 못했다.
  규칙은 위 node 플레이테스트로 웹과 같음을 확인했지만, 그것은 C#을 옮긴 JS로 확인한 것이라 C# 자체의 컴파일·실행과는 다르다.
  화면(배치, 글꼴, 스프라이트 위치)도 눈으로 보지 못했다.
  처음 열 때 콘솔 오류나 테스트 실패가 나오면 그 내용을 알려 주면 고친다. 특히 확인할 것: `using static Stairs.Game.UiKit` 이름 충돌,
  Input System의 `InputSystemUIInputModule`(ugui 패키지가 있어야 켜짐), 레거시 `Text`의 한글 표시.
- 위협의 비행 경로(서류가방이 터지며 쏟아지는 것, 모니터 유리 조각, 커피 × 표시, 포스트잇 색별 튕김 궤적)가 웹보다 단순하다. `Threat.debris`·`wob`·`ph`는 Core에 있지만 아직 안 그린다.
- 타이틀의 출근하는 사원들(commuter), 설정 화면(볼륨 단계, 전체 화면), 기록 공유(결과 이미지 저장)는 아직 없다. 결과의 "기록 공유" 자리에는 "로비로"를 두었다.
- 픽셀이 딱 맞는 화면(Pixel Perfect Camera) 설정, WebGL 빌드, 터치 입력은 아직이다.

## 에이전트 파이프라인과의 관계 (맵 v4)

- Designer와 Publisher는 그대로 웹 에셋을 만든다. Unity 판은 `Stairs > Import Web Build Assets`로 그 결과를 받는다.
- Developer가 웹 `game.js` 대신 C#을 쓰게 하려면 `prompts/developer.md`에 Unity 규칙(Core에 규칙, Game에 표현)을 더하고, Developer QA의 정적 검사(JS 문법 → C# 컴파일, CONFIG 수치 → `StairsConfig` 수치)를 바꾼다.
- Publisher의 Playwright 동작 확인은 Unity Test Runner(`-batchmode -runTests -testPlatform EditMode`)와 WebGL 빌드 확인으로 바꾼다.
