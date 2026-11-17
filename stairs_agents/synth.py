"""Designer의 사운드 JSON 명세를 WAV로 합성하는 8비트 신시사이저 (numpy)."""
from __future__ import annotations

import re
import wave
from pathlib import Path

import numpy as np

NOTE_IDX = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
TOKEN = re.compile(r"^(-|[A-G]#?\d):(\d+)$")


def note_freq(name: str) -> float:
    pitch, octave = name[:-1], int(name[-1])
    midi = 12 * (octave + 1) + NOTE_IDX[pitch]
    return 440.0 * 2 ** ((midi - 69) / 12)


def osc(wave_type: str, freq: np.ndarray | float, n: int, sr: int, duty: float = 0.5, rng=None) -> np.ndarray:
    if wave_type == "noise":
        rng = rng or np.random.default_rng(0)
        # 8비트풍 노이즈: 주파수에 따라 샘플을 유지
        f = float(np.mean(freq)) if np.ndim(freq) else float(freq)
        hold = max(1, int(sr / max(f, 1)))
        vals = rng.uniform(-1, 1, n // hold + 1)
        return np.repeat(vals, hold)[:n]
    phase = np.cumsum(np.broadcast_to(freq, (n,)) / sr) % 1.0
    if wave_type == "square":
        return np.where(phase < duty, 1.0, -1.0)
    if wave_type == "triangle":
        return 4 * np.abs(phase - 0.5) - 1
    raise ValueError(f"알 수 없는 파형: {wave_type}")


def envelope(n: int, sr: int, attack=0.005, release=0.03) -> np.ndarray:
    env = np.ones(n)
    a, r = min(n, int(attack * sr)), min(n, int(release * sr))
    if a:
        env[:a] = np.linspace(0, 1, a)
    if r:
        env[-r:] *= np.linspace(1, 0, r)
    return env


def render_music(spec: dict, sr: int) -> np.ndarray:
    step = 60.0 / spec["bpm"] / 4  # 16분음표 길이(초)
    tracks, lengths = [], []
    for ch in spec["channels"]:
        parts = []
        for tok in ch["notes"].split():
            m = TOKEN.match(tok)
            if not m:
                raise ValueError(f"음표 토큰 형식 오류: {tok}")
            name, units = m.group(1), int(m.group(2))
            n = int(round(units * step * sr))
            if name == "-":
                parts.append(np.zeros(n))
            else:
                sig = osc(ch["wave"], note_freq(name), n, sr, ch.get("duty", 0.5))
                parts.append(sig * envelope(n, sr))
        tr = np.concatenate(parts) * ch.get("volume", 0.3)
        tracks.append(tr)
        lengths.append(len(tr))
    n = max(lengths)
    mix = np.zeros(n)
    for tr in tracks:
        mix[: len(tr)] += tr
    return mix


def render_ambience(spec: dict, sr: int) -> np.ndarray:
    n = int(spec["duration"] * sr)
    t = np.arange(n) / sr
    mix = np.zeros(n)
    for layer in spec["layers"]:
        kind, vol = layer["type"], layer.get("volume", 0.2)
        if kind == "hum":
            f = layer["freq"]
            mix += vol * (0.7 * np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t))
        elif kind == "typewriter":
            rng = np.random.default_rng(layer.get("seed", 1))
            count = int(spec["duration"] * layer["rate"])
            for s in rng.uniform(0, spec["duration"] - 0.05, count):
                i, k = int(s * sr), int(0.012 * sr)
                click = rng.uniform(-1, 1, k) * np.linspace(1, 0, k) ** 2
                mix[i:i + k] += vol * click
        elif kind == "stamp":
            k = int(0.12 * sr)
            tt = np.arange(k) / sr
            thud = np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 35)
            thud += 0.4 * np.random.default_rng(3).uniform(-1, 1, k) * np.exp(-tt * 60)
            for s in layer["times"]:
                i = int(s * sr)
                mix[i:i + k] += vol * thud[: max(0, min(k, n - i))]
        else:
            raise ValueError(f"알 수 없는 환경음 층: {kind}")
    return mix


def render_sfx(spec: dict, sr: int) -> np.ndarray:
    parts = []
    for seg in spec["segments"]:
        n = int(seg["dur"] * sr)
        freq = np.linspace(seg["f0"], seg["f1"], n)
        sig = osc(seg["wave"], freq, n, sr, seg.get("duty", 0.5))
        parts.append(sig * envelope(n, sr, 0.002, min(0.02, seg["dur"] / 3)) * seg.get("volume", 0.4))
    return np.concatenate(parts)


def write_wav(path: Path, sig: np.ndarray, sr: int) -> float:
    peak = np.max(np.abs(sig)) if len(sig) else 0
    if peak > 0.98:
        sig = sig / peak * 0.98
    data = (sig * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())
    return len(data) / sr


def render_all(spec: dict, out_dir: Path) -> dict:
    sr = spec.get("sample_rate", 22050)
    manifest = {}
    groups = [("music", render_music), ("ambience", render_ambience), ("sfx", render_sfx)]
    for group, fn in groups:
        for sid, s in spec.get(group, {}).items():
            fname = f"{sid}.wav"
            dur = write_wav(out_dir / fname, fn(s, sr), sr)
            manifest[sid] = {"file": fname, "loop": bool(s.get("loop", False)), "duration": round(dur, 3)}
    return manifest
