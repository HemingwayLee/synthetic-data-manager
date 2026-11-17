# claudeGenData

An Ollama-style chat GUI for Claude Code. React + MUI frontend, FastAPI backend, PostgreSQL. Runs as one of the
synthetic-data-manager webapps, served at https://localhost/claudeGenData/ (see the repo root README).

The backend drives Claude Code through the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview),
so each chat is a real Claude Code session: it can read and edit files, run commands, and search the web
inside `./workspace`.

## Setup

From the repo root:

```bash
cp .env.example .env
claude setup-token            # Pro/Max plan: paste the printed token into CLAUDE_CODE_OAUTH_TOKEN in .env
docker compose -f docker-compose.dev.yml up --build
```

Credentials, set one in the repo root's `.env`:

- **`CLAUDE_CODE_OAUTH_TOKEN`**: uses your Claude Pro/Max subscription and its usage limits. `claude setup-token`
  creates a one-year token. This is for your own personal use; don't host this app for other people on your
  subscription, and keep the token out of git (`.env` is ignored).
- **`ANTHROPIC_API_KEY`**: pay-as-you-go API billing, with a key from the [Claude Console](https://platform.claude.com/).
  Use this if other people will use the app. Per-reply cost is shown only in this mode.

Which models you can pick depends on your plan; if one isn't available, the error shows in the chat.

| Service  | URL                                                       |
| -------- | --------------------------------------------------------- |
| Chat UI  | https://localhost/claudeGenData/                          |
| API      | https://localhost/claudeGenData/api                       |
| API docs | https://localhost/claudeGenData/api/docs                  |
| Postgres | localhost:5432, database/role `claudeGenData`             |

For debugging: frontend at http://localhost:5101/claudeGenData/, backend at http://localhost:8101/api.

## How it works

- `POST /api/conversations/{id}/messages` runs one Claude Code turn and streams it back as server-sent events
  (text deltas, tool calls, tool results, final cost).
- Chats and messages are stored in Postgres. Each conversation keeps its Claude Code session id, and the next
  message resumes that session, so Claude remembers the conversation. Session transcripts live in the
  `claude-config` Docker volume.
- Claude Code works in `apps/claudeGenData/workspace` (mounted at `/workspace` in the backend container). Files it creates show up there.
- The web UI can't approve tool calls one by one, so tools are pre-approved and anything else is denied
  (`permission_mode="dontAsk"`). The default set is Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch
  and TodoWrite. Override it with `CLAUDE_ALLOWED_TOOLS='["Read","Glob","Grep"]'` on the backend for a read-only
  assistant. Bash runs inside the backend container, not on your machine.
- The Stop button aborts the stream, which stops Claude Code; the partial reply is kept.

## Biz Doc: synthetic Japanese business documents

The **Biz Doc** tab generates fictional 契約書, 請求書, 見積書 and 領収書 as training data.

1. Pick a document type from the Biz Doc menu, choose variations on **Settings** (anything left on
   "random" is picked per document), and click **Generate**.
2. Claude Code writes the document as HTML plus an answer key (parties, amounts, key fields, planted issues);
   the backend renders the HTML to PDF with WeasyPrint and Japanese fonts (IPAex, Noto CJK).
3. **Results** shows progress, the PDF, its labels, and the exact settings used.
4. **Batch Generation** (left panel) queues 2–50 documents with the current Settings; "random" fields are
   picked separately for each one. **Cancel queued** on Results stops documents that haven't started yet.

Each document is saved to `apps/claudeGenData/data/bizdoc/<type>/<id>/` as `document.pdf`, `document.html` and `labels.json`.

When the last document of a batch finishes (done, failed or cancelled), the batch's finished documents are
packed into `data/exports/<unix seconds>.tar.gz`: `<id>/document.pdf`, `<id>/document.html` and `<id>/labels.json`
for each, plus a `manifest.json` with every document's settings and labels and a list of the ones left out. A
batch where nothing succeeded gets no archive. `GET /api/bizdoc/batches/{id}` shows a batch's status and its
archive's timestamp (`export`); see [Batch archives](../../README.md#batch-archives-for-other-systems) for the API.
Single documents (Generate) aren't archived.
Up to 2 documents generate at once (`BIZDOC_CONCURRENCY`); jobs running when the backend restarts (including
a hot reload from editing backend code) are marked failed.

All names are invented. Phone numbers use a 0 right after the area code and registration numbers (T + 13 digits)
have a deliberately wrong check digit, so neither can belong to a real business. Variation options live in
`backend/app/bizdoc/schema.py`; the Settings form is generated from it.

## Tutorial video

`video/` builds a Japanese walkthrough of Biz Doc (macOS `say` narration, burned-in subtitles, MP4) from a script.
See [video/README.md](video/README.md).

## Development

Both apps hot reload: edit files under `frontend/src` (Vite HMR) or `backend/app` (uvicorn `--reload`).
The frontend calls the API via `${import.meta.env.BASE_URL}api` (`/claudeGenData/api`), which nginx (or the Vite
proxy, when opened on port 5101) forwards to the backend as `/api`.

After changing dependencies (`package.json` or `requirements.txt`), rebuild. `-V` gives the frontend a fresh
`node_modules` volume; without it the old one is reused:

```bash
docker compose -f docker-compose.dev.yml up --build -V
```

Reset all databases and Claude sessions: `docker compose -f docker-compose.dev.yml down -v`

## Layout

```
backend/app/
  main.py      REST + streaming chat endpoints
  claude.py    Claude Agent SDK bridge (options, event mapping, model list)
  models.py    Conversation / Message tables
  bizdoc/      document types & variations (schema.py), generation + PDF (generator.py), API (routes.py)
frontend/src/
  App.jsx      top bar, tabs, routes
  api.js       API client + SSE parsing
  pages/       ChatPage, BizDocPage
  bizdoc/      Settings and Results pages
  components/  chat UI pieces
  layout/      shared left/right SplitLayout
workspace/     Claude Code's working directory (chat)
data/          generated business documents
video/         Japanese tutorial video generator (see video/README.md)
```

Tables are created on startup with `Base.metadata.create_all`. Switch to Alembic once the schema needs migrations.
