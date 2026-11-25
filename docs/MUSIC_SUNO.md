# 외부 음악 연결 (Suno 등)

2026-11-25 기준 정리. 배경음악은 지금 Designer가 만든 8비트 합성음(`synth.py`)이고, 이 문서는 Suno처럼 음악을 만들어 주는 서비스의 곡으로 바꾸는 방법이다.

## Suno API 상황

- Suno는 일반 개발자용 공식 공개 API가 없다. 2026년 7월부터 파트너 프로그램(승인된 회사만)으로 API를 준다.
- 인터넷의 "Suno API"(sunoapi.org 등)는 대부분 웹 앱을 흉내 내는 비공식 래퍼다. 약관 위반 소지가 있고 계정이 막힐 수 있어 파이프라인에 넣지 않았다.
- 상업적으로 쓰려면 유료 요금제(Pro/Premier)에서 만든 곡이어야 한다. 무료 요금제 곡은 비상업용이다.
- 그래서 이 저장소는 특정 서비스에 묶이지 않게 했다. 어떤 방법으로 받은 곡이든 `data/music/`에 두면 게임에 들어간다.

## 흐름

1. 프롬프트 보기: `python tools/music_import.py --prompts`
   - 단계별(1~20층 … 81~100층) 스타일, BPM, 조성은 `data/music/prompts.json`에 있다. 지금 합성음과 같은 BPM이다.
2. Suno 웹(또는 파트너 API, 다른 서비스)에서 **Instrumental**로 만들고 파일을 받는다.
3. 루프로 다듬기: `python tools/music_import.py 받은곡.mp3 bgm_stage2`
   - 앞쪽 무음을 건너뛰고 16마디(BPM 기준)를 잘라, 끝을 30ms 페이드하고 음량을 -16 LUFS로 맞춰 `data/music/bgm_stage2.ogg`로 저장한다.
   - 좋은 구간을 직접 고르려면 `--start 12.5 --bars 8`, 초로 자르려면 `--seconds 30`.
4. 파이프라인 다시 실행: `python -m stairs_agents run --replay replay`
   - Publisher가 `data/music/<id>.*`를 찾으면 합성음 대신 그 파일을 mp3/ogg로 변환해 쓴다. 보고서의 형식 확인에 "외부 음악 사용"으로 남는다.
   - 파일을 지우면 합성음으로 돌아간다. 효과음(`sfx_*`)도 같은 방법으로 바꿀 수 있다.

## 파트너 API를 받으면

`tools/music_import.py` 앞에 "생성 → 완료 기다리기 → 내려받기"만 붙이면 된다. 키는 코드에 쓰지 말고 환경 변수(`SUNO_API_KEY` 등)로 받고, 저장소에는 올리지 않는다. 엔드포인트 형식은 파트너 문서를 받은 뒤 맞춘다.
