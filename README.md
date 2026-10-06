# Deutsche Bahn MCP Server (local training fork)

A [Model Context Protocol](https://modelcontextprotocol.io) server that wraps four public Deutsche Bahn APIs (station master data, timetables, elevator/escalator status, parking) as 13 MCP tools, 7 prompts and 5 resources. An MCP client such as Kiro or Claude Desktop launches it, and the LLM can then answer questions like "Which elevators at Frankfurt Hbf are out of order right now?" with live data.

This is a fork of [PaulvonBerg/db-mcp-server](https://github.com/PaulvonBerg/db-mcp-server), adapted for **local use in the "Agentic AI" training class**: it runs on the current MCP Python SDK (2.x), starts over stdio directly from your MCP client with a single `uv run` command, and has pinned dependencies so it works the same on every laptop. The upstream Cloud Run deployment is still possible but not needed here (see [What changed compared to upstream](#what-changed-compared-to-upstream)).

## Table of contents

1. [Prerequisites](#prerequisites)
2. [Step 1: Get DB API credentials](#step-1-get-db-api-credentials)
3. [Step 2: Configure the server](#step-2-configure-the-server)
4. [Step 3a: Run it from an MCP client (recommended, stdio)](#step-3a-run-it-from-an-mcp-client-recommended-stdio)
5. [Step 3b: Run it as an HTTP server (optional)](#step-3b-run-it-as-an-http-server-optional)
6. [Step 4: Verify](#step-4-verify)
7. [Tool, prompt and resource reference](#tool-prompt-and-resource-reference)
8. [Known quirks and gotchas for the exercises](#known-quirks-and-gotchas-for-the-exercises)
9. [Troubleshooting](#troubleshooting)
10. [What changed compared to upstream](#what-changed-compared-to-upstream)
11. [Configuration reference](#configuration-reference)
12. [Deploying as a remote server (optional, upstream)](#deploying-as-a-remote-server-optional-upstream)
13. [Project layout](#project-layout)
14. [License and credits](#license-and-credits)

## Prerequisites

- **Python 3.11 or newer.** You do not have to install it yourself: `uv` downloads a matching interpreter on first run if none is found.
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)**, the Python package and project manager. On macOS: `brew install uv`, or on any platform the official installer:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
  Check with `uv --version` (0.11 was used here; any recent release works).
- **A DB API Marketplace account** at <https://developers.deutschebahn.com> (free). See Step 1.
- **An MCP client**, e.g. [Kiro](https://kiro.dev) or Claude Desktop, to actually talk to the server. `curl` and `python3` are enough for the smoke tests.
- `git` to clone this repository.

Clone the repository and note its absolute path; you will need it in the client configuration:

```bash
git clone <this-repo-url> db-mcp-server
cd db-mcp-server
pwd            # -> /ABSOLUTE/PATH/TO/db-mcp-server, used below
```

## Step 1: Get DB API credentials

The server talks to the DB API Marketplace with two values: a **Client ID** and an **API Key (secret)**. Both belong to an *application* that you create in the portal, and every API you want to call has to be *subscribed* for that application. Missing subscriptions are the most common reason the tools fail, so do not skip the second half.

1. Register / log in at <https://developers.deutschebahn.com>.
2. Create an application ("Anwendung") in your account area. The portal shows you two values for it:
   - **Client ID** -> goes into `DB_API_KEY`
   - **API Key / Client Secret** -> goes into `DB_API_SECRET`

   (Yes, the names are confusing: the variable called `DB_API_KEY` holds the *Client ID*, and `DB_API_SECRET` holds the thing the portal calls *API Key*.)
3. Subscribe the application to these **four** products (catalogue -> product -> "Abonnieren" / subscribe -> pick your application and the plan):

   | Product in the portal | Plan | Used by |
   |---|---|---|
   | **StaDa - Station Data** | Free4All | `get_station_by_name`, `get_stations_by_position`, `search_szentralen`, `get_szentralen_by_location`, resources |
   | **Timetables** | Free | `get_planned_timetable`, `get_recent_timetable_changes`, `get_full_timetable_changes` |
   | **FaSta - Station Facilities Status** | Free4All | `find_facilities`, `get_facilities_by_station` |
   | **Parking Information // DB Bahnpark** (marked *deprecated*) | Testzugang | `get_parking_by_station`, `search_parking_facilities`, `get_parking_prognoses` |

   The Parking subscription stays in state *Anstehende Genehmigung* (pending approval) but works anyway.

**How a missing subscription shows up:** the tool result reads `Error executing tool get_station_by_name: External API error (HTTP 403)` and the raw API answer behind it is `{"httpCode":"403","httpMessage":"Forbidden","moreInformation":"Not registered to plan"}`. The credentials were *accepted* (otherwise you would get HTTP 401), the application just has no plan for that API. Go back to the portal and subscribe.

## Step 2: Configure the server

```bash
cd /ABSOLUTE/PATH/TO/db-mcp-server
cp .env.example .env
```

Open `.env` in an editor and fill in the two required values:

| Key in `.env` | Value from the portal |
|---|---|
| `DB_API_KEY` | the application's **Client ID** |
| `DB_API_SECRET` | the application's **API Key / Secret** |
| `GCP_PROJECT_ID` | leave empty for local use (Cloud Run only) |
| `CUSTOM_DOMAIN` | leave empty for local use (Cloud Run only) |

`.env` is listed in `.gitignore`, so your credentials cannot end up in a commit. Verify:

```bash
git check-ignore .env      # prints ".env" when the file is ignored
```

`config.py` loads `.env` from the repository directory itself, so the server finds it no matter which working directory the MCP client starts it from.

## Step 3a: Run it from an MCP client (recommended, stdio)

MCP clients can start a server themselves and talk to it over stdin/stdout ("stdio transport"). The entry point for that is `stdio_main.py`. With `uv run`, the first launch creates `.venv/`, installs the pinned dependencies from `pyproject.toml` / `uv.lock`, and starts the server; later launches start immediately.

### Kiro

Add this to `.kiro/settings/mcp.json` in your workspace (or to `~/.kiro/settings/mcp.json` for all workspaces). Replace the path with the output of `pwd` from the clone:

```json
{
  "mcpServers": {
    "deutschebahn": {
      "command": "uv",
      "args": ["run", "--directory", "/ABSOLUTE/PATH/TO/db-mcp-server", "stdio_main.py"],
      "disabled": false
    }
  }
}
```

Notes:

- Use the **absolute path** of your clone. `--directory` makes `uv` change into the repo before running, so the relative `stdio_main.py` and the `.env` file are found.
- If the client reports `uv: command not found` or `spawn uv ENOENT`, it does not see your shell's `PATH`. Put the full path into `"command"`: run `which uv` in a terminal (typically `/Users/<you>/.local/bin/uv` or `/opt/homebrew/bin/uv`) and use that string.
- The **first launch takes a while** (uv resolves and installs ~10 packages, and may download Python). Kiro shows the server as connecting; give it a minute before you suspect an error.
- The server logs at DEBUG level to stderr; the client shows that in its MCP log view. Lots of log lines are normal.
- The same `command` / `args` snippet works for **Claude Desktop** (`claude_desktop_config.json`, under `"mcpServers"`) and any other stdio MCP client.

### Without uv (plain venv)

If you prefer a classic virtual environment, create it once with the pinned `requirements.txt` and point the client at the venv's interpreter:

```bash
cd /ABSOLUTE/PATH/TO/db-mcp-server
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

```json
"deutschebahn": {
  "command": "/ABSOLUTE/PATH/TO/db-mcp-server/.venv/bin/python",
  "args": ["/ABSOLUTE/PATH/TO/db-mcp-server/stdio_main.py"],
  "disabled": false
}
```

Note the pinned versions in `requirements.txt`: an unpinned `pip install mcp` would give you SDK 2.x, which is what this fork needs, but the upstream code was written for 1.x and breaks on it (see [Troubleshooting](#troubleshooting)).

## Step 3b: Run it as an HTTP server (optional)

`main.py` is the upstream entry point: a FastAPI app with the MCP endpoint at `/mcp` (Streamable HTTP transport) and a health check at `/health`. It is useful if you want to watch the server in its own terminal, connect several clients to one process, or test with `curl`.

```bash
uv run --directory /ABSOLUTE/PATH/TO/db-mcp-server main.py
# or on another port:
PORT=8081 uv run --directory /ABSOLUTE/PATH/TO/db-mcp-server main.py
```

The server binds `0.0.0.0` on port `8080` by default (`PORT` env var overrides it). Kiro entry for a running HTTP server:

```json
"deutschebahn-http": {
  "url": "http://127.0.0.1:8081/mcp",
  "type": "http",
  "disabled": false
}
```

Two things to know:

- Use `127.0.0.1`, not `localhost`. The server listens on IPv4 only, and on many machines `localhost` resolves to the IPv6 `::1` first, which makes the client's first connection attempt fail.
- Port 8080 is popular. Docker Desktop, Jenkins and many dev servers sit on it; if you see `[Errno 48] address already in use`, pick another port with `PORT=8081`.

The rate limiter (60 requests/minute, 1000/hour per client IP) and the security headers from upstream are only active in this HTTP mode. In stdio mode there is no network listener at all.

## Step 4: Verify

### Stdio smoke test (no client needed)

This pipes a minimal MCP handshake into the server and lists its tools. `sleep 3` keeps stdin open long enough for the answers to arrive. Expected output: a line starting with `13 tools:`.

```bash
(printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'; sleep 3) \
| uv run --directory /ABSOLUTE/PATH/TO/db-mcp-server stdio_main.py 2>/dev/null \
| python3 -c 'import sys,json; [print(len(m["result"]["tools"]), "tools:", *sorted(t["name"] for t in m["result"]["tools"])) for m in map(json.loads, sys.stdin) if m.get("id")==2]'
```

```
13 tools: find_facilities get_facilities_by_station get_full_timetable_changes get_parking_by_station get_parking_prognoses get_planned_timetable get_recent_timetable_changes get_station_by_name get_stations_by_position get_szentralen_by_location ping search_parking_facilities search_szentralen
```

Drop the `2>/dev/null` to see the server log if nothing comes back. (For the plain-venv variant, replace the `uv run ...` line with `/ABSOLUTE/PATH/TO/db-mcp-server/.venv/bin/python /ABSOLUTE/PATH/TO/db-mcp-server/stdio_main.py`.)

### HTTP mode

With `PORT=8081 uv run --directory /ABSOLUTE/PATH/TO/db-mcp-server main.py` running in another terminal:

```bash
curl -s http://127.0.0.1:8081/health
# {"status":"healthy","service":"Deutsche Bahn MCP Server"}
```

Opening `/mcp` in a browser gives `406 Not Acceptable`; that is expected, the MCP endpoint wants JSON-RPC POSTs with `Accept: application/json, text/event-stream`.

### First prompts in your client

Once the server shows up as connected in Kiro (or Claude Desktop), try:

- *"Find the station Frankfurt Hauptbahnhof"* -> `get_station_by_name`. Expect `Frankfurt (Main) Hbf`, station number **1866**, EVA numbers **8000105** and 8098105. If the agent searches for the literal string `Frankfurt Hauptbahnhof` it gets zero results and should retry with `Frankfurt*` or `Frankfurt (Main) Hbf`; see the quirks section.
- *"Which elevators at Frankfurt Hbf are out of order right now?"* -> `find_facilities(station_number=1866, type="ELEVATOR", state="INACTIVE")`. An empty list is a legitimate answer (all working).
- *"Show me the planned departures from Frankfurt Hbf (EVA 8000105) today at 14:00"* -> `get_planned_timetable("8000105", "<today as YYMMDD>", "14")`. Expect several dozen stops.
- *"Are there delays at Frankfurt Hbf right now?"* -> `get_recent_timetable_changes("8000105")` / `get_full_timetable_changes("8000105")`.
- *"What parking is there at Frankfurt (Main) Hbf?"* -> `search_parking_facilities`.

Then watch the tool calls the agent makes and compare with the reference below.

## Tool, prompt and resource reference

### Tools (13)

| Tool | Purpose | Key parameters | DB API |
|---|---|---|---|
| `ping()` | Liveness check, returns `{}` | none | none |
| `get_station_by_name(name, limit=10)` | Search station master data by (official) name or wildcard pattern. Returns name, station `number`, `evaNumbers`, category, services, accessibility flags. | `name` (see quirks), `limit` <= 50 | StaDa |
| `get_stations_by_position(latitude, longitude, radius=2.0, limit=10)` | Stations around a coordinate, with distance (km). Pre-filters by federal state. | `radius` in km | StaDa |
| `get_planned_timetable(eva_number, date, hour)` | Scheduled arrivals/departures for one hour slice. Returns `{station, eva, stops, note?}`. | `date` = `YYMMDD`, `hour` = `HH` (24h) | Timetables `/plan` |
| `get_recent_timetable_changes(eva_number)` | Changes (delays, cancellations, platform changes) from the last 2 minutes. Same result shape. | EVA number as string | Timetables `/rchg` |
| `get_full_timetable_changes(eva_number)` | All currently known changes for the station. Same result shape. | EVA number as string | Timetables `/fchg` |
| `get_parking_by_station(stop_place_id)` | Parking facilities at a station by ID (accepts EVA number, StaDa number, RIL100 code or DHID). | `stop_place_id`, e.g. `"8000105"`, `"1866"`, `"FF"` | Parking |
| `search_parking_facilities(station_name, with_passenger_relevance=True)` | Parking facilities by station name (API-side `stationName` filter). | official name, e.g. `Frankfurt (Main) Hbf` | Parking |
| `get_parking_prognoses(facility_id, datetime)` | Occupancy forecast up to 2 h ahead for one facility. | `facility_id` from the two tools above, `datetime` ISO 8601 (`2025-07-24T14:30:00`) | Parking |
| `find_facilities(station_number, type=None, state=None, equipment_number=None)` | Elevators / escalators at a station with optional filters. | `type` `ELEVATOR` or `ESCALATOR`; `state` `ACTIVE`, `INACTIVE`, `UNKNOWN` | FaSta |
| `get_facilities_by_station(station_number)` | Station overview incl. all facilities with description, state and coordinates. | StaDa station number (e.g. 1866) | FaSta |
| `get_szentralen_by_location(latitude, longitude, radius=10000)` | DB mobility service centres (S-Zentralen) near a coordinate. | `radius` in **metres** | StaDa |
| `search_szentralen(limit=50, offset=0)` | Paginated list of all S-Zentralen. | `limit`, `offset` | StaDa |

Identifier cheat sheet: StaDa `number` (e.g. `1866`) is what FaSta wants as `station_number`; the `evaNumbers[].number` (e.g. `8000105`) is what the Timetables tools want as `eva_number`. `get_station_by_name` returns both.

Errors from the DB API are raised as MCP tool errors (`isError: true`) with a short message such as `External API error (HTTP 403)`, `Invalid parameter: ...` or `External service temporarily unavailable`, so the LLM sees what went wrong.

### Prompts (7)

| Prompt | Arguments |
|---|---|
| `accessibility_check` | `start_station`, `end_station` |
| `parking_prognosis` | `station_name`, `datetime` |
| `recent_timetable_changes` | `station_name` |
| `planned_timetable_window` | `station_name`, `date`, `start_time`, `end_time` |
| `station_services` | `station_name` |
| `nearby_stations` | `latitude`, `longitude`, `radius=2.0` |
| `current_disruptions` | `station_name` |

Each prompt returns a user message that instructs the model which tools to chain (defined in `prompts/travel_prompts.py`).

### Resources (5)

| URI | Content |
|---|---|
| `file://reference/station-categories` | What StaDa station categories 1-7 mean |
| `file://reference/train-types` | ICE, IC, RE, RB, S, ... explained |
| `file://stations/major-hubs` | Category 1/2 hubs, fetched live from StaDa |
| `file://services/accessibility-guide` | Accessibility services at DB stations |
| `file://status/current-disruptions` | Live summary of known timetable changes at six major hubs (Frankfurt, Berlin, München, Hamburg, Köln, Hannover) via Timetables `/fchg` |

### Example questions

- Station search: *"Find all train stations in Munich"*, *"What stations are within 5 km of 52.52, 13.405?"*
- Real-time: *"Are there any delays at Frankfurt Hauptbahnhof right now?"*, *"Show me the departures at Frankfurt Hbf today at 3 PM"*
- Accessibility: *"Is barrier-free travel from Frankfurt to Köln possible right now?"*, *"Which escalators at Köln Hbf are out of order?"*
- Parking: *"What parking is available at Frankfurt (Main) Hbf tomorrow at 10 AM?"*
- Planning: *"What are the major railway hubs in Bavaria?"* (uses the `major-hubs` resource plus StaDa)

## Known quirks and gotchas for the exercises

These are properties of the DB APIs, not bugs in the server. They are good material for observing how an agent copes with imperfect tools.

- **StaDa name search is literal.** The `searchstring` parameter matches the official station name and supports `*` wildcards; there is no fuzzy matching. `Berlin Hbf` -> *no result*. `Berlin Hauptbahnhof` or `Berlin*` -> works. `Frankfurt Hbf` and `Frankfurt Hauptbahnhof` -> *no result*; `Frankfurt (Main) Hbf`, `Frankfurt*` or `*Frankfurt*Hbf*` -> works. Watch whether your agent retries with a wildcard on its own.
- **The Timetables `/plan` endpoint only serves the current day.** For any other date the DB API answers HTTP 404 with an empty body. `get_planned_timetable` turns that into `{"stops": [], "note": "...returned 404 for this date/hour..."}` instead of an opaque error (upstream behaviour), so the agent learns *why* and can pick today's date. For hours with no trains (or stations without plan data) you get `stops: []` plus a note as well.
- **Date and hour format**: `date` is `YYMMDD` (`date +%y%m%d` in a shell), `hour` is two digits `HH`. LLMs like to pass `2026-10-06` or `14:00`; the DB API answers those with the same HTTP 404 as a wrong date, so you get `stops: []` plus the 404 note. If an agent keeps getting that note for "today", check the format it used.
- **Best demo station: Frankfurt (Main) Hbf**, StaDa number `1866`, EVA `8000105`. It has plan data, live changes, facilities and parking. **Berlin Hauptbahnhof** (StaDa `1071`, EVA `8011160`) frequently returns an empty `<timetable/>` for plan and changes, which looks like a broken tool if you do not know this.
- **Tool results are prompt text.** The timetable tools always return the same shape `{station, eva, stops, note?}`; `note` is only present when `stops` is empty and explains the likely reason. Compare this with the upstream behaviour (bare `None`, which the SDK reported as "Error executing tool ...") to see why well-formed empty results matter for agents.
- **Parking identifiers**: `get_parking_prognoses` needs the facility `id` from `get_parking_by_station` / `search_parking_facilities`; only facilities with `hasPrognosis: true` have forecasts.
- **FaSta `state` filter**: `INACTIVE` means out of order. An empty list for `state="INACTIVE"` is good news, not a failure.
- **Rate limiting (HTTP mode only)**: 60 requests/minute and 1000/hour per client IP on `/mcp`. Agents that loop over many stations will hit it. Stdio mode has no limiter; the DB API itself has quotas on the free plans.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'McpError' from 'mcp'` or `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` | You are running the **upstream** 1.x code against MCP SDK 2.x, or this fork against an SDK 1.x you installed manually. | Use this fork via `uv run --directory ... stdio_main.py` (pinned `mcp==2.3.0`), or `pip install -r requirements.txt` into a fresh venv. Do not `pip install mcp` unpinned. |
| Tool result `External API error (HTTP 403)`; server log shows `"Not registered to plan"` | Credentials are valid but the application is not subscribed to that API's plan. | Subscribe to StaDa, Timetables, FaSta and Parking in the DB portal (Step 1). Each API needs its own subscription. |
| Tool result `External API error (HTTP 401)` or `API credentials are not configured` | Wrong or empty `DB_API_KEY` / `DB_API_SECRET`. | Re-check `.env` (Client ID -> `DB_API_KEY`, API Key -> `DB_API_SECRET`). Restart the server after editing. |
| `[Errno 48] address already in use` (`Errno 98` on Linux) when starting `main.py` | Something else (often Docker Desktop) listens on 8080. | `PORT=8081 uv run --directory ... main.py` and use `http://127.0.0.1:8081/mcp` in the client. |
| MCP client says `uv: command not found` / `spawn uv ENOENT` | The client process does not have your shell `PATH`. | Put the absolute path from `which uv` into `"command"`. |
| Client shows the server as "connecting" for a long time on first start | uv is creating `.venv` and installing dependencies. | Wait, or run the stdio smoke test once in a terminal so the venv exists before the client starts it. |
| Timetable tool returns `stops: []` with a `note` | No data for that station/date/hour: wrong date format, not today's date, or a station without plan data. | Read the note. Use `YYMMDD` and today's date; try Frankfurt Hbf `8000105`. |
| `get_station_by_name` returns `[]` | Literal search, no fuzzy matching. | Use the official name (`Frankfurt (Main) Hbf`) or a wildcard (`Frankfurt*`). |
| `Invalid host header` in HTTP mode | `TrustedHostMiddleware` only allows `localhost` and `127.0.0.1` (plus `CUSTOM_DOMAIN`). | Connect via `127.0.0.1`, or set `CUSTOM_DOMAIN`. |
| HTTP client cannot connect to `http://localhost:8081/mcp` | `localhost` resolved to IPv6 `::1`; the server listens on IPv4. | Use `http://127.0.0.1:8081/mcp`. |
| Lots of DEBUG log lines in the client's MCP log | `mcp_server.py` configures `logging.basicConfig(level=DEBUG)` to stderr. | Normal. Lower the level in `mcp_server.py` if it bothers you. |

## What changed compared to upstream

This clone diverges from `PaulvonBerg/db-mcp-server@74852f7` in the following ways (`git status --short` / `git diff --stat` in the repo show the exact files):

| # | Change | Why | Files |
|---|---|---|---|
| 1 | **Ported to MCP Python SDK 2.x** (`mcp==2.3.0`): `mcp.server.fastmcp.FastMCP` -> `mcp.server.mcpserver.MCPServer`, `McpError` -> `MCPError`; `utils.tool_error_handler` now raises `mcp.server.mcpserver.exceptions.ToolError`, so a failing tool reaches the LLM as an `isError` result with a readable message instead of crashing the request. | Upstream targets SDK 1.x; the renamed modules raise `ImportError` on 2.x. `McpError(str)` was also wrong on 1.x (it expected an `ErrorData`). | `server_instance.py`, `mcp_server.py`, `utils.py` |
| 2 | **`main.py` honours the `PORT` env var** (default 8080). | The README already documented `PORT`, the code ignored it. Needed because 8080 is often taken. | `main.py` |
| 3 | **New `stdio_main.py`**: `mcp.run(transport="stdio")`. | Lets MCP clients start the server themselves (`command`/`args`), no separate HTTP process. `main.py` (Streamable HTTP at `/mcp`, `/health`) is unchanged in behaviour. | `stdio_main.py` (new) |
| 4 | **New `pyproject.toml` + `uv.lock` with pinned dependencies** and `[tool.uv] package = false`; `requirements.txt` pinned to the same versions (`mcp==2.3.0`, `httpx==0.28.1`, `xmltodict==1.0.4`, `pydantic==2.13.5`, `python-dotenv==1.2.4`, `fastapi==0.142.2`, `uvicorn[standard]==0.54.0`, `google-cloud-secret-manager==2.31.0`, `Authlib==1.8.0`). | `uv run --directory <repo> stdio_main.py` creates the venv and installs everything on first run. Teaching point: upstream's unpinned `mcp` silently pulled in 2.x and broke the 1.x code the day the SDK released a new major version. Pin what you ship. `package = false` because the repo is a flat set of modules, not an installable package. | `pyproject.toml`, `uv.lock` (new), `requirements.txt` |
| 5 | **Well-formed empty timetable results.** New `_normalize_timetable` helper; all three timetable tools return `{station, eva, stops, note?}`, handle `<timetable/>`, empty bodies and missing stops gracefully, and a single stop is normalised to a one-element list. `get_planned_timetable` maps the upstream HTTP 404 for non-current dates to the same shape with an explanatory note. `fetch_from_db_api` returns `{}` for an empty XML body instead of logging a parse error. | Upstream returned `None` for empty responses, which the SDK's output validation turned into an opaque "Error executing tool ...". Tool results are prompt text for the LLM: an empty result without explanation makes agents conclude the tool is broken. | `tools/timetable_tools.py`, `utils.py` |
| 6 | **Cloud Run deployment files removed.** `Dockerfile` and `.gcloudignore` are gone. `auth_server.py` (a placeholder, OAuth is not active) and the Secret Manager branch in `config.py` are untouched because `main.py` imports them. | This fork is for local use from an MCP client; the container deployment is documented upstream (see below). | `Dockerfile`, `.gcloudignore` (deleted) |

## Configuration reference

All settings come from environment variables; locally they are read from `.env` next to `config.py`.

| Variable | Required | Meaning |
|---|---|---|
| `DB_API_KEY` | yes | DB API Marketplace **Client ID** of your application |
| `DB_API_SECRET` | yes | DB API Marketplace **API Key / Secret** of your application |
| `PORT` | no | Listen port for `main.py` (HTTP mode). Default `8080`. |
| `GCP_PROJECT_ID` | no | Google Cloud project; only used when running on Cloud Run (`K_SERVICE` set), where secrets come from Secret Manager instead of `.env`. |
| `CUSTOM_DOMAIN` | no | Extra allowed host / CORS origin for a deployed HTTP instance. |
| `CLOUD_RUN_URL` | no | Backend URL of a Cloud Run service, added to the allowed hosts. |

Logging is configured in `mcp_server.py` (DEBUG to stderr); there is no `LOG_LEVEL` switch in the code.

## Deploying as a remote server (optional, upstream)

The upstream project was built to run on **Google Cloud Run** behind HTTPS, with credentials in Secret Manager and an (unfinished) OAuth 2.1 layer. This fork removed the `Dockerfile` and `.gcloudignore`, but the HTTP server in `main.py` still has everything a remote deployment needs:

- `config.py`: when `K_SERVICE` is set (Cloud Run), `DB_API_KEY` / `DB_API_SECRET` are read from Secret Manager secrets of the same name in `GCP_PROJECT_ID`.
- `main.py`: `TrustedHostMiddleware`, CORS (incl. `https://claude.ai`), security headers and the in-memory rate limiter from `rate_limiter.py`; `CUSTOM_DOMAIN` / `CLOUD_RUN_URL` extend the allowed hosts.
- `auth_server.py`: placeholder router; OAuth is **not** enforced.
- Clients connect to `https://<your-host>/mcp` with an HTTP MCP entry, or via `npx -y mcp-remote <url> --transport http-only` for clients without native HTTP support.

If you want to containerize it, the upstream `Dockerfile` is three lines (`python:3.11-slim`, `pip install -r requirements.txt`, `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}`) and the step-by-step `gcloud run deploy` / `gcloud secrets create` instructions are in the [upstream README](https://github.com/PaulvonBerg/db-mcp-server#readme). Use this fork's pinned `requirements.txt` when building, otherwise the image gets whatever `mcp` version is current.

## Project layout

```
db-mcp-server/
├── stdio_main.py             # stdio entry point for MCP clients (new in this fork)
├── main.py                   # FastAPI + Streamable HTTP entry point (/mcp, /health), honours PORT
├── mcp_server.py             # logging setup, imports/registers tools, resources, prompts
├── server_instance.py        # the shared MCPServer instance ("deutschebahn_mcp_server")
├── config.py                 # loads .env, API base URLs, Secret Manager branch for Cloud Run
├── utils.py                  # fetch_from_db_api (httpx + xmltodict), validation, tool_error_handler
├── models.py                 # Pydantic models (StaDaStation, Facility, ParkingFacility, ...)
├── rate_limiter.py           # in-memory sliding-window limiter (HTTP mode only)
├── auth_server.py            # OAuth placeholder (not active)
├── tools/
│   ├── station_tools.py      # ping, get_station_by_name, get_stations_by_position
│   ├── timetable_tools.py    # get_planned_timetable, get_recent_/get_full_timetable_changes
│   ├── parking_tools.py      # get_parking_by_station, search_parking_facilities, get_parking_prognoses
│   └── facility_tools.py     # find_facilities, get_facilities_by_station, S-Zentralen tools
├── resources/travel_resources.py   # the 5 file:// reference resources
├── prompts/travel_prompts.py       # the 7 prompts
├── OpenAPI definitions/      # DB API specs (StaDa, Timetables, FaSta, Parking, CallaBike)
├── pyproject.toml, uv.lock   # pinned dependencies for `uv run` (new in this fork)
├── requirements.txt          # same pins for plain pip installs
└── .env.example              # template for .env (copy, then fill in DB_API_KEY / DB_API_SECRET)
```

## License and credits

This project is licensed under the **Creative Commons Attribution 4.0 International License (CC BY 4.0)**, see [LICENSE](LICENSE). It is based on the Deutsche Bahn MCP Server by **Paul von Berg**, <https://github.com/PaulvonBerg/db-mcp-server>; if you reuse this code or its ideas, please keep that attribution:

```
Based on Deutsche Bahn MCP Server by Paul von Berg
https://github.com/PaulvonBerg/db-mcp-server
```

Data attribution: the underlying APIs and data are provided by **Deutsche Bahn AG** via the [DB API Marketplace](https://developers.deutschebahn.com/). StaDa, Timetables and FaSta data are CC BY 4.0; Parking Information data is licensed under "Datenlizenz Deutschland – Namensnennung – Version 2.0" (dl-de/by-2-0), may not be modified in content, and requires the attribution *"Parking Information Daten der DB BahnPark – API über den DB API Marketplace"*. Users must comply with the DB API terms of service. This software is not affiliated with Deutsche Bahn AG.

Thanks to Deutsche Bahn for the public APIs, to Anthropic for the Model Context Protocol, and to the MCP Python SDK team. See [CONTRIBUTING.md](CONTRIBUTING.md) for upstream's contribution guidelines.
