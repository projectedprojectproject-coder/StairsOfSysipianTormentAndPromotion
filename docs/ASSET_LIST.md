# 공통 에셋 목록 (기획서 기반)

Designer와 Developer가 같은 에셋 ID, 변형(variant) 이름, 애니메이션 이름을 쓰기 위한 목록이다. 근거는 docs/GDD.md의 해당 항목이다.
프레임 크기와 프레임 배치는 Designer가 정해 design_manifest.json에 기록하고, Publisher가 이를 Developer의 sprite_definition.json에 연결한다.
게임 논리 해상도는 320x180 픽셀이며 화면에서는 정수배로 확대한다.

## 스프라이트 맵 (sheet)
한 장의 이미지에 프레임을 격자로 배치한다. 행(row)은 변형, 열(column)은 프레임이다.

| 에셋 ID | 변형 (행) | 애니메이션 (열) | 내용과 기획서 근거 |
|---|---|---|---|
| player | 사원, 대리, 과장, 간부, CEO | idle, step, parry_left, parry_right, hit, box_exit, proud | 주인공. 직급은 정장 색과 사원증 색으로만 구분 (03 캐릭터 디자인, 04 보상 성장). box_exit는 짐 상자를 들고 고개 숙여 퇴장, proud는 승급 자세 (05-5 요소 1) |
| rival | default | walk, attack, leave | 경쟁 사원 (04 레벨 구성, 05-3 요소 5) |
| projectiles | default | document, clipboard, phone | 서류, 결재판, 전화기 (04 레벨 구성) |
| warning | default | blink | 공격 예고 "!" (05-3 요소 4) |
| stairs | zone1, zone2, zone3, zone4, zone5 | tile | 계단 칸, 구간별 5종 (03 배경 레벨 무드) |
| hud_icons | default | heart, heart_empty, calendar, arrow_left, arrow_right, shield_q, shield_e, badge | HUD 아이콘 (03 UI 톤, 05-2 요소 3, 05-3 요소 2와 4) |

## 단일 이미지 (image), 크기 320x180 (logo 제외)

| 에셋 ID | 내용과 기획서 근거 |
|---|---|
| bg_zone1 | 1~20층 파티션 사무실 (03) |
| bg_zone2 | 21~40층 개방형 오피스 (03) |
| bg_zone3 | 41~60층 텅 빈 회의실 (03) |
| bg_zone4 | 61~99층 임원층 (03) |
| bg_zone5 | 100층 CEO실, 유일한 따뜻한 조명 (03) |
| title_bg | 어두운 빌딩 숲, 가운데 가장 높은 본사 꼭대기 층만 따뜻한 불빛, 바닥에 고개 숙인 사원들 (05-1 요소 4) |
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

## 컬러 팔레트 (03)
주색 #5A5F66, 보조색 #8A9A5B, 강조색 #A13D3D, 배경 #1E1F22, 글자 #E8E6DF
