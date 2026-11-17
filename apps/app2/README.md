# app2: random-table2image

Generates random synthetic table images, each paired with a random-rectangle inpainting mask, for training a
[LaMa](https://github.com/advimman/lama) model. The web UI lets you pick N and an optional seed, watch the run's
progress, browse the image + mask pairs, and download them as a zip.

Served at https://localhost/app2/ (API docs: https://localhost/app2/api/docs) by the main stack, see the
[root README](../../README.md).

## Output

Each run executes `generate.sh <N> /output/<run id> [seed]` in `app2-backend`, so files land in
`apps/app2/output/<run id>/` on your machine (git-ignored). Run records (status, seed, log) are in
`apps/app2/output/.runs/`.

```
<run id>/
├── table_00000.png           # table image
├── table_00000_mask001.png   # its mask
├── table_00001.png
├── table_00001_mask001.png
└── ...
```

- **Image:** a random table (rows, columns, merged cells, borders, colored or patterned cells) on a white margin.
- **Mask:** same size as its image; black background with 2–5 separate white rectangles. White marks the region
  LaMa should inpaint.

The `<name>_mask001.png` naming is what LaMa uses to pair masks with images, so a run's folder can be used
directly as a LaMa `val/` or `visual_test/` set. LaMa's default `train/` loader instead reads only `*.jpg` images
and creates masks on the fly, so it won't pick up these PNGs.

## Behavior

- Without a seed, the random seed `generate.sh` picks is read from its output and shown on the run, so any run can
  be reproduced. The same seed and N always give the same images and masks.
- At most `APP2_MAX_CONCURRENT_RUNS` (default 2) runs generate at once; the rest wait. N is capped at
  `APP2_MAX_COUNT` (default 100000). Set either in `.env`.
- Cancel stops the run (its pairs so far are kept). Delete removes its folder.
- A backend restart or reload stops running runs; they are marked as errors.
- Runs are stored as files, not in Postgres. The app's `app2` database is only checked by `/api/health`.
- API (all under `/app2/api` through nginx): `POST /runs` (`{"count": 100, "seed": 42}`), `GET /runs`,
  `GET /runs/{id}`, `POST /runs/{id}/cancel`, `DELETE /runs/{id}`, `GET /runs/{id}/pairs`,
  `GET /runs/{id}/files/{name}`, `GET /runs/{id}/zip`, `GET /config`, `GET /health`.

## Without the web app

`generate.sh` also works on its own (needs Node.js and npm; the first run installs `pngjs` into `core/`):

```sh
apps/app2/generate.sh 100 dataset       # 100 pairs into dataset/, random seed (printed at the end)
apps/app2/generate.sh 100 dataset 42    # reproducible
```

`core/index.html` is a standalone browser preview using the same generator code: open it, enter a seed (or leave
it empty for a random one), and each Generate click shows the next pair, so the k-th click equals
`table_<k-1>.png` and its mask from `generate.sh <N> <folder> <seed>`.

## Layout

```
generate.sh               # entry point: generate.sh <N> <folder> [seed]
core/
├── generate_dataset.js   # writes the N image + mask pairs
├── table_generator.js    # random table layout + rasterization
├── mask_generator.js     # random rectangle masks
├── index.html            # browser preview
└── package.json
backend/app/              # FastAPI: runs generate.sh, serves the results
frontend/src/             # React + MUI UI
output/                   # runs (git-ignored)
```

Hot reload: edits under `frontend/src` and `backend/app` apply at once. `generate.sh` and `core/` are mounted into
the backend and every run starts a fresh process, so edits there apply to the next run. After changing
`core/package.json`, rebuild with `docker compose -f docker-compose.dev.yml up --build -V app2-backend`.
