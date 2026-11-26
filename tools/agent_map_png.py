"""지금의 에이전트 맵을 PNG로 그린다 → agent_map/승급의계단_에이전트맵_v5.png
(A 에이전트 파이프라인, B Claude Code 세션의 도구·서브에이전트, C QA run_all.py, D Unity 판). 지금 빌드에 있는 파일만 그린다.
사용: python tools/agent_map_png.py <글꼴 폴더(NotoSansKR-Regular.ttf, NotoSansKR-Bold.ttf)> [출력 png]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = Path(sys.argv[1]); OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'agent_map' / '승급의계단_에이전트맵_v5.png'
W, H = 3200, 2620
img = Image.new('RGB', (W, H), '#FFFFFF'); d = ImageDraw.Draw(img)
def F(sz, bold=False): return ImageFont.truetype(str(FONTS / ('NotoSansKR-Bold.ttf' if bold else 'NotoSansKR-Regular.ttf')), sz)
INK, MUTED, OLIVE, RED, DARK, CREAM, PAPER = '#1F2023', '#6E737A', '#6B7A3E', '#9B3232', '#1F2023', '#ECE9E1', '#F6F4EF'


def text_c(x, y, s, f, fill=INK): d.text((x, y), s, font=f, fill=fill, anchor='mm')


def box(x, y, w, h, title, lines=(), kind='plain', badge=None, small=None):
    fill, edge, tcol, lcol = {'plain': (CREAM, '#5A5E66', INK, INK), 'qa': (PAPER, OLIVE, INK, INK), 'run': (CREAM, RED, INK, INK),
                              'dark': (DARK, DARK, '#FFFFFF', '#E6E6E6'), 'doc': ('#FFFFFF', '#5A5E66', INK, INK)}[kind]
    d.rounded_rectangle([x, y, x + w, y + h], 22 if kind != 'doc' else 4, fill=fill, outline=edge, width=5 if kind in ('qa', 'run') else 3)
    if kind == 'doc': d.polygon([(x + w - 34, y), (x + w, y + 34), (x + w - 34, y + 34)], fill='#E2E2E2', outline=edge)
    ty = y + 46
    text_c(x + w / 2, ty, title, F(36, True), tcol)
    for i, ln in enumerate(lines): text_c(x + w / 2, ty + 50 + i * 36, ln, F(26), lcol)
    if small: text_c(x + w / 2, ty + (50 + len(lines) * 36 + 2 if lines else 42), small, F(22), MUTED if kind != 'dark' else '#B8B8B8')
    if badge:
        bc = RED if kind == 'run' else OLIVE
        bw = d.textlength(badge, font=F(22, True)) + 36
        d.rounded_rectangle([x + 20, y + 16, x + 20 + bw, y + 52], 18, fill=bc); text_c(x + 20 + bw / 2, y + 34, badge, F(22, True), '#FFFFFF')


LABELS = []
def band(x, y, w, h, label):
    d.rounded_rectangle([x, y, x + w, y + h], 28, fill='#FBFAF7', outline='#C9C6BD', width=3)
    LABELS.append((x + 30, y + 34, label))   # 띠 이름은 맨 나중에 (지나가는 화살표가 이름 뒤로 가게)
def band_labels():
    for x, y, label in LABELS:
        tw = d.textlength(label, font=F(30, True))
        d.rectangle([x - 10, y - 22, x + tw + 10, y + 22], fill='#FBFAF7'); d.text((x, y), label, font=F(30, True), fill=INK, anchor='lm')


def arrow(pts, color='#5A5E66', dash=False, width=5, label=None, lpos=None):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if dash:
            L = max(abs(x2 - x1), abs(y2 - y1)); n = int(L // 18)
            for k in range(0, n, 2):
                a, b = k / max(1, n), min(1, (k + 1) / max(1, n))
                d.line([(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a), (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)], fill=color, width=width)
        else: d.line([(x1, y1), (x2, y2)], fill=color, width=width)
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    import math
    a = math.atan2(y2 - y1, x2 - x1); s = 22
    d.polygon([(x2, y2), (x2 - s * math.cos(a - 0.45), y2 - s * math.sin(a - 0.45)), (x2 - s * math.cos(a + 0.45), y2 - s * math.sin(a + 0.45))], fill=color)
    if label:
        lx, ly = lpos or ((x1 + x2) / 2, (y1 + y2) / 2)
        tw = d.textlength(label, font=F(24)); d.rectangle([lx - tw / 2 - 6, ly - 16, lx + tw / 2 + 6, ly + 16], fill='#FFFFFF')
        text_c(lx, ly, label, F(24), color if color != '#5A5E66' else MUTED)


# 제목
d.text((60, 50), '승급의 계단 에이전트 맵', font=F(64, True), fill=INK)
d.text((62, 132), 'v5 · 2026-11-26 · 지금 빌드: 에이전트 파이프라인 · Claude Code 세션의 도구와 서브에이전트 · QA · Unity 판', font=F(30), fill=MUTED)

# 입력
box(60, 200, 560, 160, '원본 리소스 데이터베이스', ['data/원본리소스_DB.json'], 'doc', small='스타일 · 배경 · 사운드 (Designer 전용)')
box(700, 200, 920, 160, '프로토 기획서 (Figma → docs/GDD.md)', ['00 비전 · 01 컨셉 · 02 스토리', '03 디자인 · 04 메카니즘 · 05 화면'], 'dark')
box(1700, 200, 680, 160, '컨셉 아트', ['data/concept/ 05-1 · 05-2 · 05-3 · 05-5'], 'doc', small='regions.json: 뽑을 영역')
box(2460, 200, 680, 160, '참고 영상 (컷신 그림체)', ['밤 사무실 · D-30 통보 · 창가의 뒷모습'], 'doc', small='청록 하늘 · 하얀 테두리 빛 실루엣')

# A 에이전트 파이프라인 (띠 420~1340)
band(40, 420, 1560, 920, 'A. 에이전트 파이프라인 — stairs_agents (python -m stairs_agents run)')
box(500, 490, 640, 160, 'Mechanics', ['기획서 04 → mechanics.json (규칙 · 수치)'], 'plain', '① 먼저', 'mechanics.py')
box(80, 700, 660, 160, 'Designer', ['스프라이트 · 배경 · 소리 → PNG · WAV'], 'plain', '② 동시', 'designer.py · render.py · synth.py · concept.py')
box(80, 900, 660, 200, 'Designer QA', ['에셋 계약 · 밀도 · 팔레트 · 컨셉 대조', '+ Claude 시각 검토'], 'qa', 'QA', 'qa_designer.py')
box(900, 700, 660, 160, 'Developer', ['index.html · game.js · sprite_definition.json'], 'plain', '② 동시', 'developer.py')
box(900, 900, 660, 200, 'Developer QA', ['CONFIG 수치 · 조작 · 화면 · 정의 계약', '+ Claude 코드 검토'], 'qa', 'QA', 'qa_developer.py')
box(80, 1140, 900, 160, 'Publisher', ['변환 · 연결 · Playwright 동작 확인 · zip'], 'run', '③ 마지막', 'publisher.py')
box(1020, 1140, 540, 160, '화면 대조 QA', ['Publisher 화면 ↔ 컨셉 05'], 'qa', 'QA', 'qa_screens.py')
arrow([(1160, 360), (1160, 490)], label='04', lpos=(1200, 425))
arrow([(820, 360), (820, 460), (410, 460), (410, 700)])
arrow([(1500, 360), (1500, 700)])
arrow([(340, 360), (340, 700)], dash=True)
arrow([(1140, 570), (1230, 570), (1230, 700)], label='규칙 · 수치', lpos=(1340, 640))
arrow([(410, 860), (410, 900)]); arrow([(1230, 860), (1230, 900)])
arrow([(740, 1000), (790, 1000), (790, 780), (740, 780)], OLIVE)
d.text((800, 890), '고칠 점 → 다시', font=F(24), fill=OLIVE, anchor='lm')
arrow([(1560, 1000), (1585, 1000), (1585, 780), (1560, 780)], OLIVE)
arrow([(410, 1100), (410, 1140)]); arrow([(1100, 1100), (900, 1140)])
arrow([(980, 1220), (1020, 1220)])
d.text((80, 1320), 'llm.py: Claude API · 재생 · 기록 · QA 고침 반복 최대 11번', font=F(22), fill=MUTED, anchor='lm')

# B Claude Code 세션 (띠 420~1340)
band(1640, 420, 1520, 920, 'B. Claude Code 세션 — 웹 판을 이어 만든다')
box(1680, 490, 760, 170, '웹 게임 demo_api/', ['game.js · index.html · assets/', '32비트 시트 · 컷신 · 소리 · sprite_definition'], 'dark')
box(1680, 700, 760, 200, '스프라이트 tools/sprites', ['src16 → fix_arms → upgrade32 → edge_close', 'Unity Tools~: puppet · upgrade16 · make_obstacles'], 'plain', small='make_sounds.py (장애물 소리)')
box(1680, 940, 760, 160, '컷신 tools/cutscenes', ['make_cutscenes.py · make_cs_sounds.py'], 'plain', small='대본 CUTSCENES (game.js)')
box(1680, 1140, 760, 170, '눈으로 보는 갤러리', ['cs_gallery.py · hazard_gallery.py', '?cs=…&csfreeze=1 · ?demo=<장면>'], 'plain')
box(2480, 490, 640, 610, '서브에이전트 (.claude/agents)', [], 'qa')
sub = [('stairs-mechanics · designer · developer', '· publisher · pipeline (파이프라인 에이전트)'),
       ('stairs-designer-qa', '장면 갤러리 육안 검토 (스프라이트 · 효과 · 컷신)'),
       ('stairs-developer-qa', '코드 규칙 검토'),
       ('stairs-docs-factcheck', 'README · 안내 사실 확인 (코드가 근거)')]
for k, (t, s2) in enumerate(sub):
    y = 620 + k * 116
    text_c(2800, y, t, F(28, True)); text_c(2800, y + 38, s2, F(23))
box(2480, 1140, 640, 170, '플레이테스트 · 시뮬레이션', ['tools/playtest.py · tools/sim_spec.py'], 'plain')
arrow([(950, 1300), (950, 1360), (1620, 1360), (1620, 575), (1680, 575)], label='PoC 기반', lpos=(1290, 1360))
arrow([(2060, 700), (2060, 660)]); arrow([(2060, 940), (2060, 900)])
arrow([(2800, 360), (2800, 395), (2460, 395), (2460, 1020), (2440, 1020)], dash=True, label='그림체', lpos=(2630, 395))
arrow([(2480, 575), (2440, 575)], OLIVE, dash=True)

# C QA (띠 1400~1750)
band(40, 1400, 3120, 350, 'C. QA — python tools/qa/run_all.py (하나라도 문제면 종료 코드 1)')
row1 = [('움직임 · 상호작용', 'qa_physics.js'), ('스프라이트', 'sprite_qa.py'), ('애니메이션', 'anim_qa.py'), ('팔 · 손 해부학', 'anatomy_qa.py'), ('컷신 대본', 'cutscene_qa.js'), ('README 사실', 'doc_factcheck.py')]
row2 = [('단위 테스트', 'pytest tests/'), ('Developer QA 규칙', 'qa_developer.py'), ('Designer QA 규칙', 'qa_designer.py'), ('Publisher 동작 확인', 'Playwright'), ('화면 대조 QA', 'qa_screens.py'), ('Unity EditMode', 'ParityTests (Unity 판)')]
for r, row in enumerate((row1, row2)):
    for i, (t, s2) in enumerate(row):
        box(80 + i * 512, 1470 + r * 135, 480, 115, t, [], 'qa', small=s2)
arrow([(2060, 1310), (2060, 1470)], label='검사', lpos=(2110, 1375))

# D Unity 판 (띠 1800~2290)
band(40, 1800, 3120, 490, 'D. Unity 판 — unity 브랜치 unity/StairsOfPromotion · Unity 판 저장소')
box(80, 1870, 560, 170, 'WebReference/', ['웹 판 demo_api 사본'], 'doc', small='고치지 않고 기준으로만')
box(720, 1870, 620, 170, '웹 사건 기록', ['web_expect.js → WebRuns.txt'], 'plain', small='10판 + 장면 4개')
box(1420, 1870, 660, 170, 'Core (규칙)', ['RunSimulation · StairLayout', 'StairsConfig · Mulberry32'], 'plain')
box(2160, 1870, 520, 170, 'ParityTests', ['WebRuns와 프레임 단위로'], 'qa', 'QA', 'EditMode 14개')
box(80, 2080, 560, 180, '가져오기 · 빌드', ['StairsAssetImporter'], 'plain', small='Stairs 메뉴 · 명령줄 빌드')
box(720, 2080, 620, 180, '컷신 대본 옮기기', ['gen_cs_data.py', '→ CutsceneData.cs'], 'plain')
box(1420, 2080, 660, 180, 'Game (화면 · 입력 · 소리)', ['GameController (+Cutscenes)', 'WebCanvas · AudioDirector · SpriteCatalog'], 'plain')
box(2160, 2080, 520, 180, '화면 맞대기', ['PlaytestDriver ↔ web_shots.py'], 'qa', 'QA', '같은 seed · 같은 순간')
box(2760, 1870, 360, 390, 'Windows', ['실행 파일', 'PlayNow_Windows/', '+ zip'], 'run', small='subtree → 저장소')
arrow([(640, 1955), (720, 1955)]); arrow([(1340, 1955), (1420, 1955)], dash=True); arrow([(2080, 1955), (2160, 1955)])
arrow([(640, 2010), (680, 2010), (680, 2170), (720, 2170)], label='대본', lpos=(680, 2060))
arrow([(1340, 2170), (1420, 2170)]); arrow([(2080, 2170), (2160, 2170)])
arrow([(360, 2260), (360, 2280), (1750, 2280), (1750, 2260)], dash=True, label='에셋 · 씬', lpos=(1050, 2280))
arrow([(2080, 2060), (2760, 2060)])

# 결과
box(380, 2340, 1100, 130, 'PC 웹 브라우저 게임', ['demo_api/index.html (보통 · 무한 · 연습 · 컷신)'], 'dark')
box(1720, 2340, 1100, 130, 'Windows 게임 (웹 판과 같은 규칙 · 화면 · 그림 · 소리)', ['PlayNow_Windows/StairsOfPromotion.exe'], 'dark')
arrow([(2940, 2260), (2940, 2310), (2270, 2310), (2270, 2340)])

# 범례
lx, ly = 60, 2510
items = [('#5A5E66', False, '산출물 전달 · 입력'), ('#5A5E66', True, '참조 · 사본'), (OLIVE, False, 'QA 고칠 점 → 다시'), (OLIVE, True, '서브에이전트 검토')]
for i, (c, dash, lab) in enumerate(items):
    x0 = lx + i * 760
    arrow([(x0, ly + 20), (x0 + 120, ly + 20)], c, dash)
    d.text((x0 + 140, ly + 20), lab, font=F(26), fill=INK, anchor='lm')
d.text((lx, ly + 70), '실행 순서: ① Mechanics → ② (Designer → Designer QA) ∥ (Developer → Developer QA) → ③ Publisher → 화면 대조 QA.  웹 판이 바뀌면 WebReference를 바꾸고 WebRuns · CutsceneData를 다시 만들어 Unity 테스트로 맞댄다.', font=F(24), fill=MUTED, anchor='lm')
band_labels()
OUT.parent.mkdir(parents=True, exist_ok=True); img.save(OUT); print('saved', OUT, img.size)
