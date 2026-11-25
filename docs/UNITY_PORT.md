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
| `Tools~` (Unity가 가져오지 않음) | `rival_expect.js`: 웹 `game.js`를 node에서 돌려 경쟁 사원 테스트 기대값을 다시 뽑는다 (`node unity/StairsOfPromotion/Tools~/rival_expect.js demo_api/game.js`) | |

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
  프레임 번호는 웹(double)과 Core(float)의 시간 누적 차이로 한 프레임 갈릴 수 있어 ±1~2를 허용했다.

## 아직 웹과 다른 점 (다음 단계)

- **컴파일 확인 못 함**: 이 환경에 Unity와 .NET(최신 csc)이 없어 C#을 한 번도 컴파일하지 못했고 EditMode 테스트도 돌리지 못했다.
  처음 열 때 콘솔 오류나 테스트 실패가 나오면 그 내용을 알려 주면 고친다. 특히 확인할 것: `using static Stairs.Game.UiKit` 이름 충돌,
  Input System의 `InputSystemUIInputModule`(ugui 패키지가 있어야 켜짐), 레거시 `Text`의 한글 표시.
- 위협의 비행 경로(서류가방이 터지며 쏟아지는 것, 모니터 유리 조각, 커피 × 표시, 포스트잇 색별 튕김 궤적)가 웹보다 단순하다. `Threat.debris`·`wob`·`ph`는 Core에 있지만 아직 안 그린다.
- 타이틀의 출근하는 사원들(commuter), 설정 화면(볼륨 단계, 전체 화면), 기록 공유(결과 이미지 저장)는 아직 없다. 결과의 "기록 공유" 자리에는 "로비로"를 두었다.
- 픽셀이 딱 맞는 화면(Pixel Perfect Camera) 설정, WebGL 빌드, 터치 입력은 아직이다.

## 에이전트 파이프라인과의 관계 (맵 v4)

- Designer와 Publisher는 그대로 웹 에셋을 만든다. Unity 판은 `Stairs > Import Web Build Assets`로 그 결과를 받는다.
- Developer가 웹 `game.js` 대신 C#을 쓰게 하려면 `prompts/developer.md`에 Unity 규칙(Core에 규칙, Game에 표현)을 더하고, Developer QA의 정적 검사(JS 문법 → C# 컴파일, CONFIG 수치 → `StairsConfig` 수치)를 바꾼다.
- Publisher의 Playwright 동작 확인은 Unity Test Runner(`-batchmode -runTests -testPlatform EditMode`)와 WebGL 빌드 확인으로 바꾼다.
