# 공통 에셋 목록 (기획서 기반)

Designer와 Developer가 같은 에셋 ID, 변형(variant) 이름, 애니메이션 이름을 쓰기 위한 목록이다. 근거는 docs/GDD.md의 해당 항목이다.
프레임 크기와 프레임 배치는 Designer가 정해 design_manifest.json에 기록하고, Publisher가 이를 Developer의 sprite_definition.json에 연결한다.
게임 논리 해상도는 320x180 픽셀이며 화면에서는 정수배로 확대한다.
에셋은 논리 해상도의 2배 밀도(이미지 640x360 기준, 스프라이트도 2배 프레임)로 그리고, 게임은 절반 크기로 그린다 (sprite_definition.pixel_scale = 2).
외형 기준은 컨셉 이미지 data/concept/05-1_title.png(타이틀), data/concept/05-3_play.png(플레이 화면)이다.

## 스프라이트 맵 (sheet)
한 장의 이미지에 프레임을 격자로 배치한다. 행(row)은 변형, 열(column)은 프레임이다.

| 에셋 ID | 변형 (행) | 애니메이션 (열) | 내용과 기획서 근거 |
|---|---|---|---|
| player | 사원, 대리, 과장, 간부, CEO | idle, step, parry_left, parry_right, hit, box_exit, proud | 주인공. 직급은 정장 색과 사원증 색으로만 구분 (03 캐릭터 디자인, 04 보상 성장). box_exit는 짐 상자를 들고 고개 숙여 퇴장, proud는 승급 자세 (05-5 요소 1) |
| rival | default | walk, attack, leave | 경쟁 사원 (04 레벨 구성, 05-3 요소 5) |
| commuter | default | walk | 타이틀 거리를 걷는 직장인, 고개 숙이고 서류가방 (05-1 요소 4). 게임이 좌우로 걸어 다니게 그린다 |
| projectiles | default | document, clipboard, phone, monitor, coffee, suitcase, suitcase_open | 서류, 결재판, 전화기 (04 레벨 구성), 위에서 떨어지는 컴퓨터 모니터 (21층~), 막으면 안 되는 커피 컵 (11층~), 날아오다 터지는 서류가방과 터져 열린 모습 (71층~) |
| sticky | pink, blue, green, yellow, white | fly | 61층~ 포스트잇. 색이 남은 패링 횟수 (분홍 5, 파랑 4, 초록 3, 노랑 2, 흰색 1) |
| warning | default | blink | 공격 예고 "!" (05-3 요소 4) |
| stairs | zone1, zone2, zone3, zone4, zone5 | tile, riser, cracked | 계단 칸(디딤판)과 그 아래 계단 몸체, 구간별 5종 (03 배경 레벨 무드) |
| hud_icons | default | heart, heart_empty, calendar, arrow_left, arrow_right, shield_q, shield_e, badge, gear | HUD 아이콘 (03 UI 톤, 05-2 요소 3, 05-3 요소 2와 4). gear는 타이틀 오른쪽 위 설정 버튼 (05-1 요소 2) |
| props | default | cooler, boxes, plant, cabinet | 층 바닥 위 사무실 소품: 정수기, 서류 상자, 화분, 서류함 (05-3 컨셉) |

## 단일 이미지 (image), 크기 640x360 (2배 밀도, logo 제외)

| 에셋 ID | 내용과 기획서 근거 |
|---|---|
| bg_zone1 | 1~20층 파티션 사무실 (03) |
| bg_zone2 | 21~40층 개방형 오피스 (03) |
| bg_zone3 | 41~60층 텅 빈 회의실 (03) |
| bg_zone4 | 61~99층 임원층 (03) |
| bg_zone5 | 100층 CEO실, 유일한 따뜻한 조명 (03) |
| title_bg | 어두운 빌딩 숲, 가운데 가장 높은 본사 꼭대기 층만 따뜻한 불빛, 아래 거리 (05-1 요소 4). 걷는 사원들은 게임이 commuter 시트로 그린다 |
| bg_lobby | 05-2 로비 배경: 형광등 천장(원근 격자)의 파티션 사무실, 오른쪽 벽 화이트보드(STATISTICS 칸, 게임이 기록을 그 위에 씀), 가운데 책상의 스탠드 불빛·모니터·앉아 일하는 사원 뒷모습. 왼쪽은 사원증, 아래는 업무 시작 버튼이 덮는다 |
| bg_practice | 연습 모드 배경: 계단 없는 사무실을 옆에서 본 모습. 벽(창, 형광등, 시계, 게시물), 플레이어 키에 맞춘 파티션과 모니터, 발 높이(y 256)에 바닥. 가운데 x 250~390은 비운다. 소품은 게임이 바닥 위에 놓는다 |
| bg_result | 05-5 결과 배경: 어둡게 가라앉은 사무실, 천장 형광등 두 줄, 왼쪽 서류장과 선반의 상자, 의자, 오른쪽 불 켜진 창 하나와 책상. 가운데는 인사 평가 표, 왼쪽은 큰 캐릭터가 덮는다 |
| logo | 회사 로고를 패러디한 픽셀 제목 "승급의 계단" (05-1 요소 1). 크기는 Designer가 정함 |

## 사운드 (sound)

| 에셋 ID | 반복 | 내용과 기획서 근거 |
|---|---|---|
| bgm_loop | 예 | 단조로운 8비트 루프 (03 사운드 음악) |
| bgm_loop_tense | 예 | 같은 루프에 불협화음을 섞은 버전, 높은 층용 (03 사운드 음악) |
| amb_office | 예 | 타자기, 도장, 형광등 소리 환경음 (03 사운드 음악) |
| sfx_step | 아니오 | 계단 이동 (04 조작) |
| sfx_parry | 아니오 | 패링 성공 (04 결과) |
| sfx_hit | 아니오 | 하트 감소 (04 규칙) |
| sfx_warning | 아니오 | 공격 예고 (05-3 요소 4) |
| sfx_promote | 아니오 | 승급 (04 성장) |
| sfx_gameover | 아니오 | 구조조정 (04 규칙) |
| sfx_click | 아니오 | 버튼 선택 (05 화면) |
| sfx_cue_clipboard | 아니오 | 결재판 패링 타이밍: 나무판 "딱… 딱!" 두 번, 두 번째 딱이 0.30초에 시작 |
| sfx_cue_rival | 아니오 | 경쟁 사원 패링 타이밍: 짧은 "헤이!", 모음이 0.045초에 시작 |
| sfx_cue_paper | 아니오 | 서류 패링 타이밍: 바스락 잡았다가 "착" 접는 소리, 접는 소리가 0.25초에 시작 |
| sfx_light_flicker | 아니오 | 모니터 예고: 형광등이 '틱' 꺼졌다 '지잉' 켜지기를 불규칙하게 되풀이 (0.6초 안팎, 유리 깨지기 전) |
| sfx_monitor_shatter | 아니오 | 모니터가 나타날 때(도착 1.0초 전) 위층 창 유리가 깨지는 소리 |
| sfx_cue_coffee | 아니오 | 커피 타이밍: 경쟁 사원의 "헤이!"를 높게 올린 소리 (막지 말라는 신호), 모음이 0.035초에 시작 |
| sfx_stair_crack | 아니오 | 금 간 계단에 올라설 때와 무너질 때: 낮게 삐걱이다 콘크리트가 부스러지는 소리 |
| sfx_camera_flash | 아니오 | 61층~ 카메라 플래시: 셔터 "찰칵"과 충전되는 높은 소리 |
| sfx_cue_suitcase | 아니오 | 서류가방 타이밍: "똑, 똑, 펑!", 펑이 0.36초에 시작 (터지는 순간) |
| sfx_phone_ring | 아니오 | 전화기 벨 두 번 (31층~ 전화기 공격). 두 번째 벨이 0.4초 뒤에 시작하며, 게임은 이 벨이 패링하기 가장 좋은 순간에 오도록 튼다 |

## 컬러 팔레트 (03)
주색 #5A5F66, 보조색 #8A9A5B, 강조색 #A13D3D, 배경 #1E1F22, 글자 #E8E6DF
