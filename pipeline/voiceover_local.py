#!/usr/bin/env python3
"""
TEMPORARY local Hindi voiceover for the sample (Piper TTS, offline).
Placeholder only — to be replaced by the approved ElevenLabs / user-supplied voice.
NOTE: these Piper Hindi voices are trained on datasets with non-commercial licences
(pratham: CC BY-NC-SA 4.0; rohan: IIT-M IndicTTS licence) -> NOT for publishing.

Usage: python3 pipeline/voiceover_local.py <model.onnx> <out_dir> [length_scale]
Writes one wav per subtitle line + timing report (line fits its subtitle window?).
"""
import os, subprocess, sys, wave, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sample_trijata import SUBS

def tts_text(s):
    # TTS-friendly punctuation: ellipsis/dash -> comma pause
    return s.replace("…", ",").replace(" — ", ", ").replace("—", ", ").strip(" ,")

def main():
    model, out_dir = sys.argv[1], sys.argv[2]
    ls = sys.argv[3] if len(sys.argv) > 3 else "1.1"
    os.makedirs(out_dir, exist_ok=True)
    report = []
    for i, (a, b, s) in enumerate(SUBS):
        p = os.path.join(out_dir, f"line_{i:02d}.wav")
        subprocess.run([sys.executable, "-m", "piper", "-m", model, "-f", p, "--length-scale", ls],
                       input=tts_text(s).encode(), check=True, capture_output=True)
        with wave.open(p) as w:
            d = w.getnframes() / w.getframerate()
        report.append({"i": i, "start": a, "window": round(b - a, 2), "dur": round(d, 2), "fits": d <= (b - a) + 0.3, "text": s})
        print(f"{i:02d} start={a:5.1f} window={b-a:4.1f}s voice={d:4.2f}s {'OK' if d <= (b-a)+0.3 else 'LONG'}")
    json.dump(report, open(os.path.join(out_dir, "timing.json"), "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
