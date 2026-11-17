"""Combine the screen recording, narration and burned-in Japanese subtitles into the final MP4."""

import json
import re
import subprocess
import wave
from pathlib import Path

LINE_CHARS = 34  # characters per subtitle line at 1280x720


def build_narration(timeline, audio_dir: Path, offset: float, total: float, out_path: Path) -> None:
    """Place each scene's narration at the moment its scene starts in the video."""
    clips = [(item, wave.open(str(audio_dir / f"{item['id']}.wav"))) for item in timeline]
    params = clips[0][1].getparams()
    frame_bytes = params.sampwidth * params.nchannels
    track = bytearray(int(total * params.framerate) * frame_bytes)
    for item, clip in clips:
        data = clip.readframes(clip.getnframes())
        pos = int((item["start"] - offset) * params.framerate) * frame_bytes
        track[pos : pos + len(data)] = data[: max(0, len(track) - pos)]
        clip.close()
    with wave.open(str(out_path), "wb") as out:
        out.setparams(params)
        out.writeframes(bytes(track))


def wrap(text: str) -> list[str]:
    """Wrap Japanese text (no spaces) into balanced lines, preferring breaks after 、 or 」."""
    lines_needed = -(-len(text) // LINE_CHARS)  # ceiling division
    lines = []
    while lines_needed > 1:
        target = len(text) // lines_needed
        breaks = [i + 1 for i, ch in enumerate(text) if ch in "、」" and abs(i + 1 - target) <= 8 and i + 1 <= LINE_CHARS]
        cut = min(breaks, key=lambda b: abs(b - target)) if breaks else min(target, LINE_CHARS)
        lines.append(text[:cut])
        text = text[cut:]
        lines_needed -= 1
    return lines + [text]


def cues(scenes, timeline, durations, offset: float):
    """One cue per sentence, timed in proportion to its length across the narration."""
    by_id = {s.id: s for s in scenes}
    for item in timeline:
        sentences = [s for s in re.split(r"(?<=。)", by_id[item["id"]].subtitle) if s.strip()]
        start = item["start"] - offset
        total_chars = sum(len(s) for s in sentences)
        for sentence in sentences:
            length = durations[item["id"]] * len(sentence) / total_chars
            yield start, start + length, wrap(sentence)
            start += length


def _ts(seconds: float) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_subtitles(cue_list, ass_path: Path) -> None:
    """ASS subtitles for ffmpeg to burn into the picture."""
    ass = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1280",
        "PlayResY: 720",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
        "Style: Default,Noto Sans CJK JP,30,&H00FFFFFF,&H90000000,&H90000000,1,3,10,0,2,40,40,26",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for start, end, lines in cue_list:
        text = "\\N".join(lines)  # \N is a forced line break in ASS
        ass.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Default,,0,0,0,,{text}")
    ass_path.write_text("\n".join(ass) + "\n", encoding="utf-8")


def video_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout)


def load_timeline(build_dir: Path) -> list[dict]:
    """Scene times mapped onto the recording's own clock.

    Playwright's recording ends up a few percent longer than the wall-clock time it covers, so
    wall-clock scene times drift ahead of the picture. Scale them to the recording's real length.
    """
    data = json.loads((build_dir / "timeline.json").read_text())
    scale = video_duration(build_dir / "recording.webm") / data["wall_duration"]
    print(f"  recording/wall-clock ratio: {scale:.3f}")
    return [{**s, "start": s["start"] * scale, "end": s["end"] * scale} for s in data["scenes"]]


def run(scenes, durations: dict[str, float], build_dir: Path, out_dir: Path) -> Path:
    timeline = load_timeline(build_dir)
    offset = timeline[0]["start"]  # drop the page-loading frames before the first scene
    total = timeline[-1]["end"] - offset + 1.0

    out_dir.mkdir(parents=True, exist_ok=True)
    narration = build_dir / "narration.wav"
    build_narration(timeline, build_dir / "audio", offset, total, narration)
    write_subtitles(list(cues(scenes, timeline, durations, offset)), build_dir / "subtitles.ass")

    out = out_dir / "tutorial-ja.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{offset:.3f}", "-i", str(build_dir / "recording.webm"),
            "-i", str(narration),
            "-map", "0:v", "-map", "1:a",
            "-vf", f"subtitles={build_dir / 'subtitles.ass'}:fontsdir=/usr/share/fonts",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total:.3f}", "-movflags", "+faststart",
            str(out),
        ],
        check=True,
    )
    return out
