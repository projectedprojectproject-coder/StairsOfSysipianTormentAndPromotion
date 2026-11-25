"""외부 음악(Suno 등으로 만든 곡)을 게임용 루프로 다듬어 data/music/ 에 둔다.

Publisher는 data/music/<사운드 id>.(wav|flac|ogg|mp3|m4a) 가 있으면 Designer의 8비트 합성음 대신 그 파일을 쓴다.
지우면 다시 합성음으로 돌아간다.

사용:
  python tools/music_import.py 받은곡.mp3 bgm_stage2                 # prompts.json의 bpm으로 16마디를 잘라 루프로
  python tools/music_import.py 받은곡.mp3 bgm_stage2 --start 12.5 --bars 8
  python tools/music_import.py 받은곡.mp3 bgm_stage4 --seconds 30     # 마디 대신 초로
  python tools/music_import.py --prompts                              # 단계별 프롬프트 출력(서비스에 붙여 넣기용)

하는 일: 앞쪽 무음 건너뛰기(--start 없을 때) → 마디 단위로 자르기 → 끝 30ms 페이드(루프 이음매 딸깍 방지)
→ 음량 맞추기(loudnorm -16 LUFS) → 44.1kHz 스테레오 ogg 저장. ffmpeg가 필요하다.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUSIC = ROOT / "data" / "music"
PROMPTS = MUSIC / "prompts.json"


def first_sound(src: Path) -> float:
    """앞쪽 무음이 끝나는 시각(초)."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af", "silencedetect=n=-45dB:d=0.2", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"silence_start: (-?[\d.]+)\s.*?silence_end: ([\d.]+)", p.stderr, re.S)
    return float(m.group(2)) if m and float(m.group(1)) <= 0.05 else 0.0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?", help="받은 음악 파일")
    ap.add_argument("id", nargs="?", help="사운드 id (예: bgm_stage1 ~ bgm_stage5, bgm_loop)")
    ap.add_argument("--start", type=float, help="자르기 시작 초 (기본: 앞쪽 무음 뒤)")
    ap.add_argument("--bars", type=int, default=16, help="루프 길이(마디, 4/4박자). 기본 16")
    ap.add_argument("--bpm", type=float, help="곡 빠르기 (기본: prompts.json 값)")
    ap.add_argument("--seconds", type=float, help="마디 대신 초로 루프 길이 지정")
    args = ap.parse_args()

    cfg = json.loads(PROMPTS.read_text(encoding="utf-8"))
    if args.src is None:
        for tid, t in cfg["tracks"].items():
            print(f"[{tid}] {t['floors']} · {t['bpm']} BPM · {t['key']}\n  {cfg['common_style']}, {t['prompt']}, {t['bpm']} BPM, {t['key']}\n")
        return 0
    if not args.id:
        ap.error("사운드 id가 필요합니다 (예: bgm_stage2)")
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg가 없습니다. winget install Gyan.FFmpeg 로 설치하세요.")
    src = Path(args.src)
    if not src.exists():
        sys.exit(f"{src} 가 없습니다.")

    bpm = args.bpm or cfg["tracks"].get(args.id, {}).get("bpm")
    if args.seconds:
        length = args.seconds
    elif bpm:
        length = args.bars * 4 * 60.0 / bpm
    else:
        sys.exit("--bpm 또는 --seconds 가 필요합니다 (prompts.json에 없는 id).")
    start = args.start if args.start is not None else first_sound(src)
    fade = 0.03
    MUSIC.mkdir(parents=True, exist_ok=True)
    for old in MUSIC.glob(f"{args.id}.*"):
        old.unlink()
    out = MUSIC / f"{args.id}.ogg"
    af = f"atrim=0:{length:.3f},afade=t=in:d={fade},afade=t=out:st={length - fade:.3f}:d={fade},loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", str(src), "-af", af, "-ac", "2",
                    "-c:a", "libvorbis", "-q:a", "5", str(out)], check=True)
    print(f"저장: {out.relative_to(ROOT)} (시작 {start:.2f}초, 길이 {length:.2f}초{f', {bpm} BPM {args.bars}마디' if not args.seconds else ''})")
    print("파이프라인을 다시 돌리면 Publisher가 이 파일을 씁니다: python -m stairs_agents run --replay replay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
