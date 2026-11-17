# synthetic-data-manager

Several webapps behind one nginx (HTTPS on 443) sharing one PostgreSQL container. Each webapp is a React (Vite)
frontend plus a FastAPI backend, each on its own port, each with its own database. Everything hot reloads.

```
browser ── https://host:443 ──► nginx ─┬─ /                        landing page (nginx/html)
                                       ├─ /claudeGenData/api/*     ► claudegendata-backend:8101     (/api/*) ─┐
                                       ├─ /claudeGenData/*         ► claudegendata-frontend:5101             ├─► db:5432  database claudeGenData
                                       ├─ /randomHtmlTables/api/*  ► randomhtmltables-backend:8102  (/api/*) ─┤
                                       └─ /randomHtmlTables/*      ► randomhtmltables-frontend:5102          └─► db:5432  database randomHtmlTables
```

| App | What it is |
| --- | --- |
| [claudeGenData](apps/claudeGenData/README.md) | Claude Code chat GUI plus the Biz Doc generator (synthetic Japanese business documents as PDF + labels) |
| [randomHtmlTables](apps/randomHtmlTables/README.md) | Random synthetic table images, each with a random-rectangle inpainting mask, for LaMa training |

## Batch archives (for other systems)

Every finished batch, a claudeGenData **Batch Generation** or a randomHtmlTables run, is also packed with all its data and
labels into one `<unix seconds>.tar.gz` (e.g. `1794898711.tar.gz`). The timestamp is when the batch finished, and
names stay unique: two batches finishing in the same second get consecutive numbers. Each archive unpacks into
`<timestamp>/` with a `manifest.json` that describes the batch and its files. Both apps serve their archives with
the same API:

| Method | Path | |
| --- | --- | --- |
| GET | `/<app>/api/exports?since=<ts>` | Archives, newest first: `name`, `timestamp`, `bytes`, `files`, `md5`, `sha256`. `since` keeps only newer ones, for polling |
| GET | `/<app>/api/exports/<ts>` | The same plus the archive's `manifest` |
| GET | `/<app>/api/exports/<ts>.tar.gz` | The archive |
| DELETE | `/<app>/api/exports/<ts>` | Remove it |

```bash
curl -k https://localhost/randomHtmlTables/api/exports
curl -k -O https://localhost/randomHtmlTables/api/exports/1794898711.tar.gz
```

From another Docker container on the same machine, call the backend directly over plain HTTP
(`http://host.docker.internal:8101/api/exports` or `:8102`) to skip the self-signed certificate. Archives are
written to `apps/claudeGenData/data/exports/` and `apps/randomHtmlTables/output/exports/`; the code is `app/exports.py` (each
app keeps its own copy). The API has no login, like the rest of the stack, so on a server put it behind
authentication.

## Run

```bash
cp .env.example .env     # then set CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY for claudeGenData
docker compose -f docker-compose.dev.yml up --build
```

claudeGenData needs Claude credentials (see [its README](apps/claudeGenData/README.md#setup)); everything else has
defaults.

| What           | URL                                   |
| -------------- | ------------------------------------- |
| Landing page   | https://localhost/                    |
| claudeGenData  | https://localhost/claudeGenData/      |
| claudeGenData API docs | https://localhost/claudeGenData/api/docs |
| randomHtmlTables | https://localhost/randomHtmlTables/  |
| randomHtmlTables API docs | https://localhost/randomHtmlTables/api/docs       |
| Postgres       | localhost:5432 (postgres/postgres; claudeGenData/claudeGenData → db claudeGenData; randomHtmlTables/randomHtmlTables → db randomHtmlTables) |
| pgweb (optional, see below) | http://localhost:8081, or https://localhost/pgweb/ with `PGWEB_VIA_HTTPS=true` |

http://localhost redirects to HTTPS. Locally the certificate is self-signed (generated into `nginx/certs/` on first
`up`), so the browser warns once. For a trusted local cert, create one with
[mkcert](https://github.com/FiloSottile/mkcert) as `nginx/certs/fullchain.pem` and `nginx/certs/privkey.pem`.

For debugging, each service is also published on 127.0.0.1 only: frontends at http://localhost:5101/claudeGenData/ and
http://localhost:5102/randomHtmlTables/ (Vite proxies their API the same way nginx does), backends at :8101 and :8102.

## Database browser (pgweb, optional)

[pgweb](https://github.com/sosedoff/pgweb) lives in its own compose file and project (`synthetic-data-manager-pgweb`)
that joins the main stack's network (`synthetic-data-manager`), so it can be started and stopped without touching the apps:

```bash
docker compose -f docker-compose.dev.yml up -d       # main stack first (it creates the network)
docker compose -f docker-compose.pgweb.yml up -d     # http://localhost:8081
docker compose -f docker-compose.pgweb.yml down      # stop pgweb only
```

It connects as the Postgres superuser to `postgres`; pick `claudeGenData`/`randomHtmlTables` from its database menu. A small nginx
(`tools/pgweb/`) sits in front of it and adds `custom/json-viewer.js` (pretty-printed JSON in the cell popup). Port
8081 is bound to 127.0.0.1 because pgweb has no login; on a server, reach it with an SSH tunnel (`ssh -L 8081:localhost:8081`).

To also open it from the main site at https://localhost/pgweb/, set `PGWEB_VIA_HTTPS=true` in `.env` and restart
pgweb (`docker compose -f docker-compose.pgweb.yml up -d`). Port 443 listens on all interfaces, so anyone who can
reach this machine gets superuser access to the database: unless it's only your laptop, also set `PGWEB_AUTH_USER` /
`PGWEB_AUTH_PASS` (HTTP basic auth, applies to both ports). With the setting off, /pgweb/ returns 404; with pgweb
stopped, 503.

Stop pgweb before `docker compose -f docker-compose.dev.yml down`, otherwise the network can't be removed while
pgweb is still attached.

## How it works

- **Routing is by path.** Each app owns a prefix (`/randomHtmlTables/`). Vite runs with `base: "/randomHtmlTables/"`, so its pages,
  assets and HMR websocket all live under it and nginx passes them through unchanged. Requests to `/randomHtmlTables/api/*`
  have the prefix stripped and go to the backend as `/api/*`. Config: `nginx/conf.d/default.conf` (TLS, headers,
  websocket upgrade) and one file per app in `nginx/apps/`.
- **Frontend code must not hard-code `/`.** Build URLs from `import.meta.env.BASE_URL` (see `src/api.js`). If you
  add React Router, use `<BrowserRouter basename={import.meta.env.BASE_URL}>`.
- **Backends** keep all routes under `/api`. `ROOT_PATH=/randomHtmlTables` only tells FastAPI its public prefix so
  `/randomHtmlTables/api/docs` loads the right `openapi.json`. Uvicorn trusts nginx's `X-Forwarded-*` headers.
- **One Postgres, one database per app.** `db-init` runs `db/create-databases.sh` on every `up`: for each
  `name:password` in `APP_DATABASES` it creates a login role and a database it owns (skipping existing ones) and
  revokes `CONNECT` from everyone else, so randomHtmlTables's credentials can't open claudeGenData's database. Tables are created by
  each backend on startup.
- nginx resolves the app containers per request (Docker DNS), so it starts even if an app is down and keeps
  working after an app container restarts.
- **Database names are case-sensitive.** `claudeGenData` is a quoted mixed-case identifier in Postgres: connect with
  that exact spelling (`psql -d claudeGenData` works; in SQL, write `"claudeGenData"`).

## Add a webapp (e.g. app3)

A new app is a copy of the minimal template app (a Vite + FastAPI items list, kept in git history as the original
`apps/app2` in commit f8f2f98) plus four small config edits: compose services, a database, an nginx route and a
landing page entry. The example uses `app3` with frontend port **5103** and backend port **8103**. Pick ports that
no other app uses. Run the commands from the repo root.

### 1. Copy the code

```bash
mkdir -p apps/app3 && git archive f8f2f98 apps/app2 | tar -x --strip-components=2 -C apps/app3
grep -rlE 'app2|App 2|5102|8102' apps/app3 | xargs perl -pi -e 's/app2/app3/g; s/App 2/App 3/g; s/5102/5103/g; s/8102/8103/g'
```

That renames the app in the frontend (`package.json` name, page `<title>`, heading in `src/App.jsx`) and the
fallback base path and ports in `frontend/vite.config.js`. Docker Compose sets the actual values (step 2).

- **Frontend** (`apps/app3/frontend`): build every URL from `import.meta.env.BASE_URL`, as `src/api.js` does. Never start a path with `/`.
- **Backend** (`apps/app3/backend`): needs no edits. `APP_NAME`, `ROOT_PATH`, `PORT` and `DATABASE_URL` come
  from compose. Keep its routes under `/api`. Tables in `app/models.py` are created on startup, in app3's own
  database.

### 2. Add the services to `docker-compose.dev.yml`

Add these two services next to the `randomHtmlTables` ones (randomHtmlTables's backend has extra generator settings; app3 needs only these):

```yaml
  # ---------------------------------------------------------------- app3
  app3-backend:
    build:
      context: ./apps/app3/backend
      dockerfile: Dockerfile.dev
    environment:
      <<: *backend-env
      PORT: "8103"
      APP_NAME: app3
      ROOT_PATH: /app3
      DATABASE_URL: postgresql+psycopg://app3:${APP3_DB_PASSWORD:-app3}@db:5432/app3
    ports:
      - "127.0.0.1:8103:8103"
    volumes:
      - ./apps/app3/backend:/app
    depends_on:
      db-init:
        condition: service_completed_successfully

  app3-frontend:
    build:
      context: ./apps/app3/frontend
      dockerfile: Dockerfile.dev
    environment:
      <<: *frontend-env
      PORT: "5103"
      BASE_PATH: /app3/
      API_PROXY_TARGET: http://app3-backend:8103
    ports:
      - "127.0.0.1:5103:5103"
    volumes:
      - ./apps/app3/frontend:/app
      - /app/node_modules
    depends_on:
      - app3-backend
```

### 3. Give it a database

In the same file, add a line to `APP_DATABASES` under `db-init`:

```yaml
      APP_DATABASES: >-
        claudeGenData:${CLAUDEGENDATA_DB_PASSWORD:-claudeGenData}
        randomHtmlTables:${RANDOMHTMLTABLES_DB_PASSWORD:-randomHtmlTables}
        app3:${APP3_DB_PASSWORD:-app3}
```

Add `APP3_DB_PASSWORD=app3` to `.env.example` (and to `.env` if you have one). On a server, use a strong password.
`db-init` creates the `app3` role and database on the next `up`, without touching existing data.

### 4. Route it in nginx

```bash
git show f8f2f98:nginx/apps/app2.conf | sed -e 's/app2/app3/g' -e 's/5102/5103/g' -e 's/8102/8103/g' > nginx/apps/app3.conf
```

This sends `/app3/api/*` to `app3-backend:8103` with the `/app3` prefix removed, and everything else under `/app3/`
to `app3-frontend:5103`.

### 5. Add it to the landing page

In `nginx/html/index.html`, add an entry to `APPS`. It gets a card with frontend and backend checks and a Go button:

```js
const APPS = [
  { name: "claudeGenData", path: "/claudeGenData/", kind: "webapp" },
  { name: "randomHtmlTables", path: "/randomHtmlTables/", kind: "webapp" },
  { name: "App 3", path: "/app3/", kind: "webapp" },
  { name: "pgweb", path: "/pgweb/", kind: "pgweb" },
];
```

### 6. Start it

```bash
docker compose -f docker-compose.dev.yml up --build -d          # builds app3, db-init creates its database
docker compose -f docker-compose.dev.yml exec nginx nginx -s reload   # nginx only reads apps/*.conf when it (re)loads
```

The rest of the stack keeps running, and no database reset is needed.

### 7. Check it

- https://localhost/: the App 3 card shows **OK** for Frontend and Backend. **Go** opens it.
- https://localhost/app3/api/health returns `{"status": "ok", "app": "app3", "database": "app3", ...}`.
- https://localhost/app3/api/docs: the FastAPI docs.
- Direct, for debugging: http://localhost:5103/app3/ (frontend) and http://localhost:8103/api/health (backend).
- pgweb: `app3` appears in its database menu.

If the card shows 502 or 504, look at `docker compose -f docker-compose.dev.yml logs app3-frontend app3-backend`.
If `/app3/` returns the landing page or a 404, nginx hasn't been reloaded (step 6).

Optionally, add app3 to the diagram and the URL table at the top of this README.

## On a server

- Point DNS at the server and put real certificates at `nginx/certs/fullchain.pem` and `privkey.pem` (e.g. copy
  or mount Let's Encrypt's `live/<domain>/` files). Reload with `docker compose exec nginx nginx -s reload`.
- Set strong `POSTGRES_PASSWORD` and `APPn_DB_PASSWORD` values in `.env` before the first start.
- This is a **dev** stack (Vite dev server, uvicorn `--reload`). For production, build the frontends
  (`vite build`) and serve `dist/` from nginx, and run uvicorn without `--reload`.

## Development

Edit `apps/<app>/frontend/src` (Vite HMR, through nginx too) or `apps/<app>/backend/app` (uvicorn `--reload`).

After changing dependencies (`package.json` or `requirements.txt`), rebuild with a fresh `node_modules` volume:

```bash
docker compose -f docker-compose.dev.yml up --build -V
```

Reset all databases: `docker compose -f docker-compose.dev.yml down -v`
