==============================================================
 승급의 계단 (Stairs of Sisyphean Torment and Promotion)
 에이전트 PoC 데모 안내
==============================================================

이 저장소는 게임 "승급의 계단"을 세 AI 에이전트(Designer, Developer,
Publisher)가 프로토 기획서를 바탕으로 만들어 내는 과정을 보여 주는
Proof of Concept(PoC)입니다. 에이전트는 Python으로 작성되었고, 결과물은
1~20층(사원 구간)을 플레이할 수 있는 웹 브라우저 게임입니다.


--------------------------------------------------------------
1. 폴더 구성
--------------------------------------------------------------

 demo/                 재생 모드로 만든 완성 게임 (바로 실행 가능)
 demo_api/             실제 Claude API로 만든 완성 게임 (바로 실행 가능)
 demo*/screens/        Publisher의 동작 확인 화면 캡처 6장
 demo*/publisher_report.md   Publisher 확인 보고서 (두 버전 모두 9개 항목 통과)
 stairs_agents/        에이전트 코드 (Python)
   designer.py           Designer 에이전트
   render.py, synth.py   Designer의 명세를 PNG, WAV로 만드는 도구
   developer.py          Developer 에이전트
   publisher.py          Publisher 에이전트
   pipeline.py           실행 순서 (Designer, Developer 동시 실행 후 Publisher)
   llm.py                Claude API 호출과 재생 모드
 prompts/              각 에이전트에게 주는 지시문
 docs/GDD.md           Figma 프로토 기획서 원문 (00~05)
 docs/ASSET_LIST.md    Designer와 Developer가 함께 쓰는 에셋 목록
 data/원본리소스_DB.json   Designer만 읽는 원본 리소스 데이터베이스
 replay/               재생 모드용 응답 (API 키 없이 데모할 때 사용)
 replay_api/           실제 Claude API로 실행했을 때 저장된 응답
 agent_map/            에이전트 맵 문서(docx), 그림(svg, png). Figma "에이전트 맵" 페이지와 같은 내용
 README.md             개발자용 상세 설명
 requirements.txt      Python 패키지 목록


--------------------------------------------------------------
2. 가장 빠른 데모: 완성된 게임 열기 (설치 불필요)
--------------------------------------------------------------

 demo/index.html 또는 demo_api/index.html 을 Chrome, Edge 등 브라우저로 엽니다.
 demo_api 는 Claude API가 실제로 만든 디자인과 코드라서 demo 와 화면 구성이 다릅니다.

 조작
  - 메뉴: 방향키로 선택, Enter 또는 Space로 결정 (마우스 클릭 가능)
  - 플레이: ← → 다음 계단 방향으로 이동
            Q 왼쪽 패링, E 오른쪽 패링
            ESC 일시정지
  - 게임 안에서 보기: 타이틀과 일시정지 메뉴의 "조작법" 버튼
  - 서류 위에 "!"가 뜨면 1초 뒤 도착합니다. 날아오는 쪽의 패링 키를
    도착 직전 0.2초 안에 누르면 막습니다.
  - 20층에 도착하면 대리로 승급하고 PoC가 끝납니다.

 시연용 주소 옵션 (주소 끝에 붙임)
  - index.html?bot=1    자동 플레이 (20층 승급까지 약 15초)
  - index.html?seed=7   난수 고정 (매번 같은 계단 모양)
  - index.html?mute=1   소리 끔


--------------------------------------------------------------
3. 준비 (에이전트를 직접 실행할 때)
--------------------------------------------------------------

 1) Python 3.10 이상
 2) 패키지 설치
      pip install -r requirements.txt
 3) 동작 확인용 브라우저
      playwright install chromium
    (Chrome이 설치되어 있고 PATH에 있으면 그것을 씁니다)
 4) ffmpeg 설치 (사운드 변환용, libvorbis와 libmp3lame 포함)
    Windows는 ffmpeg.exe가 있는 폴더를 PATH에 추가합니다.


--------------------------------------------------------------
4. 데모 A: API 키 없이 에이전트 파이프라인 시연 (재생 모드)
--------------------------------------------------------------

 저장소 최상위 폴더에서 실행합니다.

   python -m stairs_agents run --replay replay

 실제 API가 만든 결과를 재현하려면 replay_api 를 지정합니다.
   python -m stairs_agents run --replay replay_api --out output_api

 replay/ 에 저장된 응답을 Claude 응답 대신 사용하고, 그 뒤의 단계
 (렌더링, 합성, 확장자 확인과 변환, 연결, 동작 확인, 내보내기)는
 실제로 실행합니다. 약 30초가 걸리며 화면에 다음 순서로 기록이 나옵니다.

   [Developer] 게임 코드와 스프라이트 정의 작성 요청
   [Designer] 스프라이트와 이미지 설계 요청
   [Designer] 사운드 설계 요청
   [Publisher] 1. 확장자 확인과 변환
   [Publisher] 2. 코드와 디자인 연결
   [Publisher] 3. 동작 확인   (확인 항목 9개, 통과/실패 표시)
   [Publisher] 4. 게임 내보내기

 결과는 output/ 폴더에 생깁니다.
   output/design_out/   Designer 결과 (PNG, WAV, design_manifest.json)
   output/dev_out/      Developer 결과 (index.html, game.js, sprite_definition.json)
   output/build/        Publisher가 연결한 게임 (index.html로 실행)
   output/dist/         zip, publisher_report.md, screens/


--------------------------------------------------------------
5. 데모 B: 실제 Claude API로 실행
--------------------------------------------------------------

 1) API 키를 환경 변수로 설정합니다. 키를 파일에 적거나 저장소에 올리지 마세요.
      Windows PowerShell :  $env:ANTHROPIC_API_KEY="본인 키"
      Windows 명령 프롬프트:  set ANTHROPIC_API_KEY=본인 키
      macOS, Linux        :  export ANTHROPIC_API_KEY="본인 키"
 2) 실행
      python -m stairs_agents run --record --out output_api
    --record 를 붙이면 Claude 응답이 replay_api/ 에 저장되어, 나중에
      python -m stairs_agents run --replay replay_api
    로 같은 결과를 API 호출 없이 다시 볼 수 있습니다.

 선택 옵션
   --model         Claude 모델 (기본 claude-sonnet-5-5)
   --max-tokens    한 번의 응답 최대 길이 (기본 64000)
   --no-resource-db   Designer가 원본 리소스 데이터베이스를 쓰지 않음

 에이전트 하나만 실행
   python -m stairs_agents designer
   python -m stairs_agents developer
   python -m stairs_agents publisher   (앞의 두 결과가 output/ 에 있어야 함)

 주의
  - Claude는 실행할 때마다 다른 디자인과 코드를 만듭니다. 결과가
    Publisher의 동작 확인을 통과하지 못할 수 있으며, 그 내용은
    output_api/dist/publisher_report.md 에 남습니다.
  - 응답이 길어 실행에 수 분이 걸립니다. API 사용 요금이 발생합니다.


--------------------------------------------------------------
6. 발표용 시연 순서 예시 (약 5분)
--------------------------------------------------------------

 1) Figma "에이전트 맵" 페이지 또는 agent_map/ 의 그림으로 세 에이전트의
    역할과 흐름을 설명합니다.
 2) 터미널에서 데모 A 명령을 실행하고, Designer와 Developer가 동시에
    시작한 뒤 Publisher가 1~4단계를 차례로 진행하는 기록을 보여 줍니다.
 3) output/dist/publisher_report.md 에서
    - Designer가 낸 WAV를 정의된 MP3, OGG로 변환한 표 (1. 확장자 확인과 변환)
    - 동작 확인 9개 항목 결과 (3. 동작 확인)
    를 보여 줍니다.
 4) output/build/index.html?bot=1 로 자동 플레이를 보여 준 뒤,
    index.html 로 직접 플레이합니다.


--------------------------------------------------------------
7. 문제 해결
--------------------------------------------------------------

 - "ANTHROPIC_API_KEY 환경 변수가 설정되어 있지 않습니다"
     5장의 1)을 실행한 같은 터미널에서 다시 실행합니다.
 - "응답이 max_tokens에서 잘렸습니다"
     --max-tokens 128000 처럼 값을 올려 다시 실행합니다.
 - ffmpeg 오류
     터미널에서 ffmpeg -version 이 실행되는지 확인합니다.
 - 동작 확인에서 브라우저를 찾지 못함
     playwright install chromium 을 실행합니다.
 - 게임에서 소리가 나지 않음
     브라우저 정책상 첫 키 입력이나 클릭 뒤부터 소리가 납니다.


--------------------------------------------------------------
8. PoC 범위와 기획서 미정 값
--------------------------------------------------------------

 구현 범위: 타이틀, 로비, 플레이, 일시정지, 결과 화면 / 1~20층 / 서류 투척과
 패링 / 하트와 남은 일수 / 콤보 배수 / 20층 승급 / 최고 기록 저장(브라우저)

 범위 밖: 21층 이후 구간(경쟁 사원, 결재판, 전화기), 60층과 100층 엔딩,
 전체 랭킹 서버, 설정의 화면과 키 설정

 기획서에 수치가 없어 PoC에서 정한 값 (game.js 맨 위 CONFIG, "기획서 미정")
  - 한 층을 오르는 계단 칸 수: 5칸
  - 콤보 배수가 한 단계 오르는 연속 패링 수: 5회
  - 점수: 계단 한 칸 10점, 패링 50점, 각각 콤보 배수를 곱함
  - 구간 안 난이도 증가: 일수 감소 속도 최대 +50%, 공격 간격 2.6초에서 1.3초로
  - 불협화음 음악 전환: 11층부터
