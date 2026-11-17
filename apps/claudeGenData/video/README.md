# Tutorial video (Japanese)

Generates `out/tutorial-ja.mp4`, a ~2½ minute Japanese walkthrough of the Biz Doc generator, narrated
with macOS's built-in `say` voice (Kyoko) and with Japanese subtitles burned into the picture.

Nothing is filmed by hand: a script drives the real app in a headless browser while the narration plays,
then everything is combined with ffmpeg. Re-running it produces the same video, so after a UI change you
just generate it again.

## Generate the video

Requires a Mac (for `say`) and Docker.

1. Start the stack (from the synthetic-data-manager repo root). The recorder opens the real frontend:

   ```bash
   docker compose -f docker-compose.dev.yml up -d
   ```

2. Generate the video (from this folder):

   ```bash
   cd video
   ./make_video.sh
   ```

   This makes the narration on your Mac with `say`, then records and renders in Docker. The first run
   downloads a Playwright browser image (about 2 GB) and builds the recorder image; after that a run
   takes about 3 minutes, mostly the recording in real time.

3. Open `out/tutorial-ja.mp4`.

It doesn't use your Claude plan: the document-generation API is mocked during recording (see below).

### Options

```bash
python3 tts.py --list-voices                 # Japanese voices installed on this Mac
./make_video.sh --voice Otoya                # a different voice (default: Kyoko)
./make_video.sh --rate 220                   # speak faster (words per minute)
docker compose run --rm video                # re-record and render, reusing the last narration
docker compose run --rm video --render-only  # re-encode only (e.g. after changing subtitle style)
```

More Japanese voices can be added in System Settings → Accessibility → Spoken Content → System Voice →
Manage Voices.

## How it works

```
scenes.py ──► tts.py (Mac, `say`) ──► build/audio/*.wav, durations.json
          └─► record.py (Docker) ───► build/recording.webm, timeline.json   (Playwright drives the app)
                 render.py (Docker) ─► out/tutorial-ja.mp4                    (ffmpeg: audio + burned-in subtitles)
```

| File | Purpose |
| --- | --- |
| `scenes.py` | **The script.** Each scene has the narration, the subtitle text and the browser actions. |
| `make_video.sh` | Runs the narration on the Mac, then the recorder container. |
| `tts.py` | Speaks each scene's narration with `say` into a WAV file. |
| `generate.py` | Container entry point: recording, then rendering. |
| `record.py` | Opens the app at 1280×720, plays each scene's actions, and paces it to its narration. |
| `mock_api.py` | Fake document API used during recording (sample invoice, scripted queued → running → done). |
| `render.py` | Lays the narration on the timeline, burns in the subtitles, encodes H.264/AAC MP4. |
| `assets/` | Visible cursor, title/info card styles, and the sample invoice shown in the video. |
| `docker-compose.yml`, `Dockerfile` | Recorder image (Playwright, ffmpeg, Japanese fonts). |

Details worth knowing:

- **Mocked generation.** Real generation takes a minute and uses your Claude plan limits, so the recorder
  intercepts `/api/bizdoc/...` document calls and serves `assets/sample-invoice.html` (a fictional invoice
  generated earlier with this app). Document types, settings and the UI itself are real. The Settings
  scene picks the same options the sample was generated with, so the "Settings used" tab matches.
- **Pacing.** Each scene lasts at least as long as its narration plus a short pause. Playwright's video runs
  about 5% longer than real time, so `render.py` rescales the scene times to the recording's actual length
  to keep voice, subtitles and picture in sync.
- **Two texts per scene.** `narration` spells English UI names in katakana (ビズドック, ジェネレート) so the
  voice pronounces them well; `subtitle` keeps the real names (「Biz Doc」「Generate」) and is what appears
  on screen.
- **Networking.** The recorder joins the stack's Docker network (`synthetic-data-manager`) and opens
  `http://claudegendata-frontend:5101/claudeGenData`; `frontend/vite.config.js` allows any host name.

## Changing the video

- **Narration or subtitles:** edit the text in `scenes.py`, then run `./make_video.sh`.
- **What happens on screen:** edit the scene's action function in `scenes.py`. Helpers: `d.click(locator)`,
  `d.choose("^Label", "option")` for dropdowns, `d.scroll(px)`, `d.wait(seconds)`, `d.show_card(html)` /
  `d.hide_card()`, and `d.mock.finish_running(n)` to advance fake jobs. Then `docker compose run --rm video`.
- **Subtitle look:** the `Style:` line in `render.py` (font, size, colors), then `--render-only`.
- **Sample document:** replace `assets/sample-invoice.html` and `assets/sample-labels.json` with any
  document from `data/bizdoc/<type>/<id>/` (and update `SAMPLE_TITLE` in `mock_api.py`).

## Troubleshooting

- **`Scene … failed`**: a button or label in the UI changed. Look at `build/failure.png` (screenshot at the
  moment of failure) and update the locator in `scenes.py`.
- **`No narration found` / `Narration is missing`**: run `./make_video.sh` (or `python3 tts.py`) after editing scenes.
- **`network synthetic-data-manager not found`**: start the app first (step 1).
- **Blocked request / "host is not allowed"**: `frontend/vite.config.js` must keep `allowedHosts: true`.
