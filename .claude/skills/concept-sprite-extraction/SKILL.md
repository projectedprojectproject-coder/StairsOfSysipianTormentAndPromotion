---
name: concept-sprite-extraction
description: 승급의 계단 컨셉 아트(data/concept/*.png)에서 캐릭터·위협·소품·아이콘을 잘라 배경을 지우고 프레임 크기(예 32x48)로 줄여 Designer 명세의 글자 격자(rows + palette)와 참고 PNG로 뽑는다. 컨셉 아트를 따라 스프라이트를 새로 그리거나 고칠 때, 만든 스프라이트를 컨셉과 비교(색 거리, 실루엣 겹침)할 때, 컨셉의 주요 색을 뽑을 때 쓴다. Designer와 Designer QA 에이전트가 쓴다.
---

# 컨셉 아트에서 스프라이트 뽑기

도구는 `stairs_agents/concept.py`(LLM 호출 없음, Pillow만 씀)입니다. 저장소 루트에서 실행합니다.
Windows에서는 한글 출력이 깨지지 않게 `PYTHONIOENCODING=utf-8`을 먼저 둡니다.

## 1. 컨셉 보기와 주요 색

```bash
python -m stairs_agents.concept palette data/concept/05-3_play.png -k 12
python -m stairs_agents.concept palette data/concept/05-3_play.png --box 272,140,36,74   # 한 영역만
```

컨셉 원본은 Read 도구로 이미지를 직접 보고 영역을 고릅니다. 좌표는 원본 픽셀 기준 `x,y,w,h`입니다.
영역 후보가 필요하면 배경과 다른 덩어리를 자동으로 찾습니다 (큰 것부터):

```bash
python -m stairs_agents.concept boxes data/concept/05-3_play.png --tol 60 --min-area 120
```

## 2. 한 영역 뽑기

```bash
python -m stairs_agents.concept extract data/concept/05-3_play.png --box 276,143,31,70 --size 32x48 --colors 10 --out player_x4.png
```

- 출력: 첫 줄은 `{"palette": {"A": "#RRGGBB", ...}}`, 그다음 `size` 높이만큼의 글자 격자 (`.`은 투명). Designer 명세의 `frames` 한 장과 같은 형식입니다.
- 처리 순서: 자르기 → 테두리 색에서 이어진 배경을 flood fill로 투명하게 (`--tol`) → 불투명 부분만 남겨 비율을 지켜 줄이고 가운데 아래(발 위치)에 놓기 → 색 `--colors`개로 줄이기.
- `--out`으로 4배 미리보기를 만들어 Read로 꼭 확인합니다.

배경이 잘 안 지워질 때:
- 남는 배경이 있으면 `--tol`을 올리고, 인물의 머리카락·정장처럼 어두운 부분까지 지워지면 내립니다 (보통 35~95).
- 상자가 숫자 표시(분홍 원)나 계단·벽 조각을 덮지 않게 상자를 좁힙니다.
- 그래도 남는 조각은 `data/concept/regions.json`의 `clear`([x,y,w,h], 자른 영역 기준)로 지웁니다.
- 배경째 쓰고 싶으면 `--keep-bg`.

## 3. 영역 목록으로 한꺼번에 (에이전트가 쓰는 방식)

`data/concept/regions.json`에 영역을 적어 두면 파이프라인이 매번 뽑습니다.

```json
{"id": "player_idle", "image": "05-3_play", "box": [276, 143, 31, 70], "tol": 60, "clear": [[0, 0, 9, 18]],
 "size": [32, 48], "colors": 10, "sheet": "player", "anim": "idle", "variant": "사원", "note": "05-3 요소 3"}
```

```bash
python -m stairs_agents.concept regions      # -> output/concept_refs/
```

- `output/concept_refs/<id>.png`, `<id>_x4.png`: 뽑은 참고 스프라이트
- `output/concept_refs/_regions_<이미지>.png`: 원본 위에 상자를 그린 확인용 이미지 (상자가 맞는지 Read로 확인)
- `output/concept_refs/refs.json`: 컨셉 이미지별 주요 색과 밝기, 영역별 격자와 팔레트

`sheet`/`anim`/`variant`를 적은 영역은
- **Designer**가 그 시트를 설계할 때 요청에 참고 격자로 붙고 (`concept.ref_text`),
- **Designer QA**가 만든 프레임과 비교합니다 (`concept.palette_distance` 색 거리 90 이하, `concept.silhouette_iou` 실루엣 겹침 0.4 이상 목표).
`sheet`가 `null`인 영역(예: 타이틀 거리의 사원)은 이미지(title_bg) 설계 요청에 붙습니다.

## 4. 참고 격자를 스프라이트로 옮길 때

- 그대로 베끼지 않습니다. 컨셉은 일러스트라 픽셀 격자가 맞지 않고 명암이 많습니다. 실루엣, 등신(4~5등신), 자세, 색 배치를 따르고 색은 03 팔레트(#5A5F66, #8A9A5B, #A13D3D, #1E1F22, #E8E6DF)와 그 명암 단계로 바꿉니다.
- 외곽선 1px을 두르고, 색 수는 시트당 48색 이하로 둡니다.
- 프레임 크기는 2배 밀도 기준입니다: player·rival·props 32x48, projectiles·hud_icons 24x24, warning 16x24, 이미지 640x360.
- 고친 뒤에는 `python -m stairs_agents qa-designer --replay replay`로 대조표 `output/qa_out/designer_contact.png`(왼쪽 컨셉, 오른쪽 만든 프레임)를 다시 보고 비교합니다.

## 5. 코드에서 쓰기

```python
from stairs_agents import concept
res = concept.extract(Path("data/concept/05-3_play.png"), [276, 143, 31, 70], [32, 48], colors=10, tol=60)
res["rows"], res["palette"], res["image"]          # 격자, 팔레트, RGBA 이미지
concept.palette_distance(["#A13D3D"], ["#9E3B3B"])  # 낮을수록 비슷
concept.silhouette_iou(img_a, img_b)                # 0~1
```
