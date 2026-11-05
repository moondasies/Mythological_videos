#!/usr/bin/env python3
"""
Place per-line narration wavs on the subtitle timeline, then mix with the music bed
(music ducked under the voice via sidechain compression) and mux onto the rendered video.

Usage: python3 pipeline/mix_voiceover.py <lines_dir> <video_in> <music_wav> <video_out>
"""
import os, subprocess, sys, glob
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sample_trijata import SUBS, DUR

SR = 48000

def load_trim(p):
    x, sr = sf.read(p, dtype="float32")
    if x.ndim > 1: x = x.mean(1)
    if sr != SR:  # simple high-quality resample via numpy interpolation is poor; use ffmpeg
        tmp = p + ".48k.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-ar", str(SR), "-af", "aresample=resampler=soxr", tmp], check=True)
        x, _ = sf.read(tmp, dtype="float32"); os.remove(tmp)
    thr = 0.02 * np.abs(x).max()
    idx = np.where(np.abs(x) > thr)[0]
    a, b = max(0, idx[0] - int(0.03 * SR)), min(len(x), idx[-1] + int(0.12 * SR))
    y = x[a:b].copy()
    f = int(0.01 * SR); y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
    return y

def main():
    lines_dir, vin, music, vout = sys.argv[1:5]
    N = int(DUR * SR)
    vo = np.zeros(N, np.float32)
    for i, (a, b, s) in enumerate(SUBS):
        y = load_trim(os.path.join(lines_dir, f"line_{i:02d}.wav"))
        st = int((a + 0.05) * SR)
        end = min(N, st + len(y))
        vo[st:end] += y[: end - st]
        nxt = SUBS[i + 1][0] if i + 1 < len(SUBS) else DUR
        print(f"line {i:02d}: {a+0.05:5.2f}s -> {a+0.05+len(y)/SR:5.2f}s (next starts {nxt:5.2f}s)")
    narr = os.path.join(lines_dir, "narration_timeline.wav")
    sf.write(narr, vo, SR)
    fc = ("[1:a]aformat=sample_rates=48000:channel_layouts=mono,highpass=f=70,"
          "equalizer=f=160:t=q:w=1:g=2.5,equalizer=f=3200:t=q:w=1.2:g=2,"
          "acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=3,"
          "aecho=0.85:0.55:45|80:0.10|0.06,pan=stereo|c0=c0|c1=c0,asplit=2[v][key];"
          "[2:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=0.55[m];"
          "[m][key]sidechaincompress=threshold=0.03:ratio=8:attack=30:release=450[md];"
          "[v][md]amix=inputs=2:weights=1 0.9:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vin, "-i", narr, "-i", music, "-filter_complex", fc,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", vout], check=True)
    print("done ->", vout)

if __name__ == "__main__":
    main()
