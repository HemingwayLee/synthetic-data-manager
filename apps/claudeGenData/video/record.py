"""Play the scenes in a headless browser against the running app and record the screen."""

import json
import os
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from mock_api import MockDocuments

APP_URL = os.environ.get("APP_URL", "http://localhost:5101/claudeGenData")
ASSETS = Path(__file__).parent / "assets"
WIDTH, HEIGHT = 1280, 720
SCENE_GAP = 0.7  # seconds of silence after each narration


class Director:
    """Helpers the scene actions use to drive the page like a person would."""

    def __init__(self, page, mock: MockDocuments):
        self.page = page
        self.mock = mock
        self.re = re.compile
        self._mouse = (WIDTH * 0.5, HEIGHT * 0.5)
        page.mouse.move(*self._mouse)

    def wait(self, seconds: float) -> None:
        # wait_for_timeout (not time.sleep) so mocked API requests keep being answered.
        self.page.wait_for_timeout(int(seconds * 1000))

    def move_to(self, x: float, y: float) -> None:
        distance = ((x - self._mouse[0]) ** 2 + (y - self._mouse[1]) ** 2) ** 0.5
        self.page.mouse.move(x, y, steps=max(8, int(distance / 25)))
        self._mouse = (x, y)

    def click(self, locator) -> None:
        locator.wait_for(state="visible", timeout=15000)
        locator.scroll_into_view_if_needed()
        box = locator.bounding_box()
        self.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        self.wait(0.25)
        self.page.mouse.down()
        self.wait(0.08)
        self.page.mouse.up()

    def choose(self, label_pattern: str, option: str) -> None:
        """Open a dropdown (MUI select) by its label and pick an option."""
        self.click(self.page.get_by_role("combobox", name=re.compile(label_pattern)))
        self.wait(0.7)
        self.click(self.page.get_by_role("option", name=option, exact=True))

    def scroll(self, dy: int, steps: int = 3) -> None:
        self.move_to(WIDTH * 0.62, HEIGHT * 0.55)
        for _ in range(steps):
            for _ in range(15):
                self.page.mouse.wheel(0, dy / steps / 15)
                self.page.wait_for_timeout(16)
            self.wait(0.3)

    def show_card(self, html: str) -> None:
        self.page.evaluate(
            """([html, css]) => {
                let card = document.getElementById('tc-card');
                if (!card) {
                    const style = document.createElement('style');
                    style.textContent = css;
                    document.head.appendChild(style);
                    card = document.createElement('div');
                    card.id = 'tc-card';
                    document.body.appendChild(card);
                }
                card.innerHTML = html;
                requestAnimationFrame(() => card.classList.add('visible'));
            }""",
            [html, (ASSETS / "card.css").read_text()],
        )
        self.wait(0.6)

    def hide_card(self) -> None:
        self.page.evaluate("() => document.getElementById('tc-card')?.classList.remove('visible')")
        self.wait(0.6)


def run(scenes, durations: dict[str, float], build_dir: Path) -> Path:
    """Record build/recording.webm and build/timeline.json (scene start/end, wall-clock)."""
    video_dir = build_dir / "raw"
    video_dir.mkdir(parents=True, exist_ok=True)
    for old in video_dir.glob("*.webm"):
        old.unlink()

    timeline = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            record_video_dir=str(video_dir),
            record_video_size={"width": WIDTH, "height": HEIGHT},
            color_scheme="light",
            locale="ja-JP",
        )
        context.add_init_script(path=str(ASSETS / "cursor.js"))
        page = context.new_page()
        video_start = time.monotonic()  # the recording starts with the page

        mock = MockDocuments()
        mock.install(page)
        page.goto(f"{APP_URL}/chat", wait_until="networkidle")
        director = Director(page, mock)

        for scene in scenes:
            start = time.monotonic()
            print(f"  {scene.id}")
            try:
                scene.action(director)
            except Exception as exc:
                page.screenshot(path=str(build_dir / "failure.png"))
                raise SystemExit(f"Scene {scene.id} failed (screenshot: build/failure.png): {exc}") from exc
            remaining = durations[scene.id] + SCENE_GAP - (time.monotonic() - start)
            if remaining > 0:
                director.wait(remaining)
            timeline.append({"id": scene.id, "start": start - video_start, "end": time.monotonic() - video_start})

        director.wait(1.0)
        video_path = Path(page.video.path())
        wall_duration = time.monotonic() - video_start
        context.close()  # finalizes the video file
        browser.close()

    recording = build_dir / "recording.webm"
    video_path.replace(recording)
    # Times are wall-clock seconds since the recording started; render.py rescales them to the
    # recording's actual length because Playwright's video runs slightly longer than real time.
    (build_dir / "timeline.json").write_text(
        json.dumps({"wall_duration": wall_duration, "scenes": timeline}, indent=2)
    )
    return recording
