# Publisher 보고서

## 1. 확장자 확인과 변환

| 에셋 | 종류 | Designer 파일 | 결과 파일 | 판정 |
|---|---|---|---|---|
| player | image | player.png | player.png | 일치, 복사 |
| rival | image | rival.png | rival.png | 일치, 복사 |
| commuter | image | commuter.png | commuter.png | 일치, 복사 |
| projectiles | image | projectiles.png | projectiles.png | 일치, 복사 |
| sticky | image | sticky.png | sticky.png | 일치, 복사 |
| warning | image | warning.png | warning.png | 일치, 복사 |
| stairs | image | stairs.png | stairs.png | 일치, 복사 |
| hud_icons | image | hud_icons.png | hud_icons.png | 일치, 복사 |
| props | image | props.png | props.png | 일치, 복사 |
| bg_zone1 | image | bg_zone1.png | bg_zone1.png | 일치, 복사 |
| bg_zone2 | image | bg_zone2.png | bg_zone2.png | 일치, 복사 |
| bg_zone3 | image | bg_zone3.png | bg_zone3.png | 일치, 복사 |
| bg_zone4 | image | bg_zone4.png | bg_zone4.png | 일치, 복사 |
| bg_zone5 | image | bg_zone5.png | bg_zone5.png | 일치, 복사 |
| title_bg | image | title_bg.png | title_bg.png | 일치, 복사 |
| logo | image | logo.png | logo.png | 일치, 복사 |
| bg_lobby | image | bg_lobby.png | bg_lobby.png | 일치, 복사 |
| bg_result | image | bg_result.png | bg_result.png | 일치, 복사 |
| bg_practice | image | bg_practice.png | bg_practice.png | 일치, 복사 |
| bgm_loop | audio | bgm_loop.wav | bgm_loop.mp3, bgm_loop.ogg | 불일치, wav -> mp3, ogg 변환 |
| bgm_loop_tense | audio | bgm_loop_tense.wav | bgm_loop_tense.mp3, bgm_loop_tense.ogg | 불일치, wav -> mp3, ogg 변환 |
| amb_office | audio | amb_office.wav | amb_office.mp3, amb_office.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_step | audio | sfx_step.wav | sfx_step.mp3, sfx_step.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_parry | audio | sfx_parry.wav | sfx_parry.mp3, sfx_parry.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_hit | audio | sfx_hit.wav | sfx_hit.mp3, sfx_hit.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_warning | audio | sfx_warning.wav | sfx_warning.mp3, sfx_warning.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_promote | audio | sfx_promote.wav | sfx_promote.mp3, sfx_promote.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_gameover | audio | sfx_gameover.wav | sfx_gameover.mp3, sfx_gameover.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_click | audio | sfx_click.wav | sfx_click.mp3, sfx_click.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_phone_ring | audio | sfx_phone_ring.wav | sfx_phone_ring.mp3, sfx_phone_ring.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_cue_clipboard | audio | sfx_cue_clipboard.wav | sfx_cue_clipboard.mp3, sfx_cue_clipboard.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_cue_rival | audio | sfx_cue_rival.wav | sfx_cue_rival.mp3, sfx_cue_rival.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_cue_paper | audio | sfx_cue_paper.wav | sfx_cue_paper.mp3, sfx_cue_paper.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_monitor_shatter | audio | sfx_monitor_shatter.wav | sfx_monitor_shatter.mp3, sfx_monitor_shatter.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_light_flicker | audio | sfx_light_flicker.wav | sfx_light_flicker.mp3, sfx_light_flicker.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_cue_coffee | audio | sfx_cue_coffee.wav | sfx_cue_coffee.mp3, sfx_cue_coffee.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_stair_crack | audio | sfx_stair_crack.wav | sfx_stair_crack.mp3, sfx_stair_crack.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_camera_flash | audio | sfx_camera_flash.wav | sfx_camera_flash.mp3, sfx_camera_flash.ogg | 불일치, wav -> mp3, ogg 변환 |
| sfx_cue_suitcase | audio | sfx_cue_suitcase.wav | sfx_cue_suitcase.mp3, sfx_cue_suitcase.ogg | 불일치, wav -> mp3, ogg 변환 |

## 2. 코드와 디자인 연결

- 문제 없음 (정의의 모든 에셋, 변형, 애니메이션이 연결됨)

## 3. 동작 확인

| 확인 항목 | 결과 | 내용 |
|---|---|---|
| 에셋 불러오기 | 통과 |  |
| 타이틀 화면 | 통과 | title |
| 타이틀 -> 로비 이동 | 통과 |  |
| 로비 -> 플레이 이동 | 통과 |  |
| 일시정지 (ESC)와 남은 일수 정지 | 통과 | 29.83 -> 29.83 |
| 100층 도달과 승급 판정 | 통과 | 층 100, 직급 CEO (목표 100층 CEO), 점수 17220, 최고 배수 x3 |
| 입력 없음 -> 구조조정 (게임 오버) | 통과 | 8.1초 뒤, 하트 0, 남은 일수 5.4 |
| 파일로 직접 열기 (file://) | 통과 |  |
| 브라우저 오류 없음 | 통과 |  |

## 4. 내보내기

- 파일: 승급의계단_PoC_web.zip
- 포함 파일 수: 63
- 동작 확인 전체 통과: 예
