"""Record the app and render the Japanese tutorial video (runs in Docker).

Narration must exist first: run ./make_video.sh, or `python3 tts.py` on the Mac.
    docker compose run --rm video [--render-only]
"""

import argparse
import json
import sys
from pathlib import Path

import record
import render
from scenes import SCENES

ROOT = Path(__file__).parent
BUILD, OUT = ROOT / "build", ROOT / "out"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--render-only", action="store_true", help="only re-encode from the last recording")
    args = parser.parse_args()

    durations_file = BUILD / "durations.json"
    if not durations_file.exists():
        sys.exit("No narration found. Run ./make_video.sh (or `python3 tts.py` on the Mac) first.")
    durations = json.loads(durations_file.read_text())
    missing = [s.id for s in SCENES if s.id not in durations]
    if missing:
        sys.exit(f"Narration is missing for {', '.join(missing)}. Run `python3 tts.py` again.")

    if not args.render_only:
        print("Recording the app")
        record.run(SCENES, durations, BUILD)

    print("Rendering")
    out = render.run(SCENES, durations, BUILD, OUT)
    print(f"Done: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
