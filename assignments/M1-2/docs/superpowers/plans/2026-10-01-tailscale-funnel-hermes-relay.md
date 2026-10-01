# Tailscale Funnel Hermes Relay Implementation Plan

> **For agentic workers:** Execute each task in order. Keep checkboxes current and preserve unrelated working-tree changes.

**Goal:** Let the deployed AI Secretary API reach the Hermes API on this PC through a token-protected, loopback-only relay exposed by Tailscale Funnel.

**Architecture:** A separate local FastAPI process listens only on `127.0.0.1` and forwards two exact API operations to Hermes. It validates the incoming Bearer relay token, replaces it with the local Hermes API key, and rejects every other operation. The existing Render AI provider uses the Funnel HTTPS origin and relay token.

**Tech Stack:** Python 3.11+, FastAPI, httpx, python-dotenv, pytest, Tailscale Funnel.

**Spec:** `docs/superpowers/specs/2026-10-01-tailscale-funnel-hermes-relay-design.md`

## Global Constraints

- Bind the relay to `127.0.0.1` only.
- Allow only `GET /v1/toolsets` and `POST /v1/chat/completions` with no query string.
- Keep the relay token separate from the local Hermes API key.
- Limit request bodies to 1 MiB and the upstream timeout to 120 seconds.
- Never log or return credentials, request bodies, response bodies, or upstream exception text.
- Do not enable Funnel until the relay passes local verification.
- Preserve unrelated working-tree changes and local secret files.

---

## File map

- `server/app/core/config.py`: expose optional `HERMES_RELAY_TOKEN` without making it required by the regular AI service.
- `server/app/hermes_relay.py`: provide the separately constructed relay FastAPI application and strict proxy contract.
- `server/scripts/run_hermes_relay.py`: load the project's ignored `.env` and bind the relay to loopback on port 8766 (8765 is occupied by an unrelated process).
- `server/tests/test_hermes_relay.py`: verify security, route allowlist, forwarding, size limits, and failure handling with a mocked upstream.
- `.env.example`: document the optional local relay token and distinguish it from the Hermes key.
- `docs/deployment.md`: replace the stale Cloudflare comparison with the selected Tailscale path, configuration, operation, and verification instructions.
- `task.md`: record T08.02's relay/Funnel prerequisites and leave remote verification incomplete until Render has made a successful request.

## Task 1: Add relay configuration and isolated ASGI application

**Files:**
- Modify: `server/app/core/config.py`
- Create: `server/app/hermes_relay.py`
- Test: `server/tests/test_hermes_relay.py`

**Interfaces:**
- `create_relay_app(settings, upstream_client=None) -> FastAPI`
- `settings.get("HERMES_RELAY_TOKEN")` is optional for the normal AI Secretary API and required only by the relay.
- Relay credentials are incoming `Authorization: Bearer <relay token>` and outgoing `Authorization: Bearer <local Hermes API key>`.

- [x] **Step 1: Write tests for relay configuration and authentication.**

Test missing relay token returns a generic 503 at app creation or startup; a missing/wrong Bearer token returns 401 and does not call the mocked upstream; a valid token can call the mocked allowed route. Use synthetic `relay-test-token` and `hermes-test-key` values only.

- [x] **Step 2: Run the focused test to confirm it fails.**

Run from `assignments/M1-2/server`: `..\.venv\Scripts\python.exe -m pytest tests/test_hermes_relay.py -q`

Expected: the initial imports fail because `app.hermes_relay` does not exist.

- [x] **Step 3: Add optional relay token configuration and app factory.**

Extend the settings value names with `HERMES_RELAY_TOKEN` without adding it to the required `ai` or `firebase` groups. Create the relay app with injected settings and an optional `httpx.AsyncClient`. Validate the incoming Bearer token with `hmac.compare_digest`; fail closed if relay token or local `OPENAI_API_KEY` is missing. Use the fixed local Hermes URL `http://127.0.0.1:8642/v1`; bind host/port only in the launcher, not in the app factory.

- [x] **Step 4: Run the focused tests.**

Run: `..\.venv\Scripts\python.exe -m pytest tests/test_hermes_relay.py -q`

Expected: authentication tests pass, and the regular `/health` missing-settings contract remains unchanged.

## Task 2: Enforce the narrow forwarding contract

**Files:**
- Modify: `server/app/hermes_relay.py`
- Test: `server/tests/test_hermes_relay.py`

**Interfaces:**
- The relay forwards only `GET /v1/toolsets` and `POST /v1/chat/completions` to Hermes.
- Upstream calls use the fixed `http://127.0.0.1:8642` origin, the configured local Hermes API key, and a timeout no greater than 120 seconds. Do not derive this origin from Render's `AI_PROVIDER_BASE_URL`.

- [x] **Step 1: Add failing tests for route and request restrictions.**

Test `GET /v1/models`, unknown paths, `PUT /v1/toolsets`, and either allowed path with a query string. Test a body larger than 1 MiB. Each rejected request must leave the mock upstream call list empty.

- [x] **Step 2: Run the focused tests and inspect the rejection results.**

Run: `..\.venv\Scripts\python.exe -m pytest tests/test_hermes_relay.py -q`

Expected: inspect the allowlist and size-limit results; no rejected request reaches the upstream mock.

- [x] **Step 3: Implement exact allowlisting and bounded forwarding.**

Reject unsupported method/path/query before any upstream request. Stream and count incoming body bytes, returning 413 beyond 1 MiB. Forward only JSON content to the fixed loopback Hermes origin; discard caller authorization and hop-by-hop headers, then set the local Hermes Bearer key. Use an async HTTP client with a maximum 120-second timeout. Do not follow redirects. Return only the upstream status and JSON body with a safe content type; map connection errors to generic 502 and timeouts to generic 504 without logging exception text.

- [x] **Step 4: Verify allowed forwarding and rejection cases.**

Run: `..\.venv\Scripts\python.exe -m pytest tests/test_hermes_relay.py -q`

Expected: valid requests reach only the expected upstream URL with the local Hermes key; every rejected request makes zero upstream calls.

## Task 3: Add launcher, environment guidance, and deployment runbook

**Files:**
- Create: `server/scripts/run_hermes_relay.py`
- Modify: `.env.example`
- Modify: `docs/deployment.md`
- Modify: `task.md`
- Test: `server/tests/test_hermes_relay.py`

**Interfaces:**
- Launch command from `assignments/M1-2`: `..\.venv\Scripts\python.exe server/scripts/run_hermes_relay.py`
- Local relay URL: `http://127.0.0.1:8766`; Funnel must target port `8766`, never Hermes port `8642`.
- Render uses `AI_PROVIDER_BASE_URL=https://<assigned-funnel-host>/v1` and `OPENAI_API_KEY=<relay-token>`.

- [x] **Step 1: Add launcher tests and startup instructions.**

Test that launcher settings select loopback host `127.0.0.1`, relay port `8766`, local Hermes URL, and configured timeout. Tracked examples must contain no actual secrets or assigned Funnel hostname.

- [x] **Step 2: Implement the loopback launcher and update configuration docs.**

Load the ignored project `.env` with `load_settings()`, create the relay app, and run Uvicorn at `127.0.0.1:8766`. Add an empty `HERMES_RELAY_TOKEN=` entry and comments explaining that local `.env` keeps the Hermes key while Render's `OPENAI_API_KEY` holds the relay token. Document relay startup, Funnel activation after local checks, Render variables, PC-online limitation, and shutdown. Update T08.02 without marking remote validation complete.

- [x] **Step 3: Run all server tests and static checks.**

Run from `assignments/M1-2/server`: `..\.venv\Scripts\python.exe -m pytest tests -q` and `..\.venv\Scripts\python.exe -m compileall -q app scripts`.

Expected: all existing and relay tests pass; compileall exits 0.

- [x] **Step 4: Verify local relay against Hermes without enabling Funnel.**

Start the relay locally and call `GET http://127.0.0.1:8766/v1/toolsets` with the relay Bearer token. Confirm disabled toolsets. Then make one short synthetic text completion through `POST /v1/chat/completions`; confirm nonempty response, `finish_reason=stop`, and no credentials or prompts in logs. Stop the relay. Do not run `tailscale funnel` in this task.

Expected: local requests succeed through the relay; unauthorized requests and disallowed routes fail; `tailscale funnel status` still reports Funnel inactive.

## Execution note

- Task 1 used a test-first check: the initial focused run failed because `app.hermes_relay` did not exist; the completed module then passed the focused tests.
- The route guard and launcher were implemented before all corresponding rejection/launcher tests were added. Those tests subsequently passed, but their sequence did not demonstrate a red state first.
- Port 8765 was already occupied by an unrelated Python process, which was left running. The relay therefore uses port 8766; the relay process itself was stopped after live local verification.

## Completion boundary

This plan completes local relay implementation and validation only. Enabling Funnel publishes a new public HTTPS endpoint and remains a separate user-confirmed action. Remote verification requires a real request from the deployed Render service and must remain unchecked until that request succeeds.
