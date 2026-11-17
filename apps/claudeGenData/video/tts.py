"""Synthesize each scene's Japanese narration with macOS's built-in `say` command.

Runs on the Mac itself (not in Docker), since `say` only exists on macOS:
    python3 tts.py [--voice Kyoko] [--rate 200]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import wave
from pathlib import Path

from scenes import SCENES

BUILD = Path(__file__).parent / "build"


def list_voices() -> None:
    voices = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=True).stdout
    print("".join(line + "\n" for line in voices.splitlines() if "ja_JP" in line), end="")


def synthesize(text: str, voice: str, rate: int | None, out_path: Path) -> float:
    cmd = ["say", "-v", voice, "--file-format=WAVE", "--data-format=LEI16@24000", "-o", str(out_path)]
    if rate:
        cmd += ["-r", str(rate)]
    subprocess.run(cmd + [text], check=True)
    with wave.open(str(out_path)) as w:
        return w.getnframes() / w.getframerate()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--voice", default="Kyoko", help="macOS Japanese voice (default: Kyoko)")
    parser.add_argument("--rate", type=int, help="speaking rate in words per minute (default: the voice's own)")
    parser.add_argument("--list-voices", action="store_true", help="print the Japanese voices and exit")
    args = parser.parse_args()

    if sys.platform != "darwin":
        sys.exit("tts.py uses macOS's `say` command; run it on a Mac.")
    if args.list_voices:
        list_voices()
        return

    audio_dir = BUILD / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    print(f"Narration ({args.voice})")
    durations = {}
    for scene in SCENES:
        durations[scene.id] = synthesize(scene.narration, args.voice, args.rate, audio_dir / f"{scene.id}.wav")
        print(f"  {scene.id}: {durations[scene.id]:.1f}s")
    (BUILD / "durations.json").write_text(json.dumps(durations, indent=2))


if __name__ == "__main__":
    main()
