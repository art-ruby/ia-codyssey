# Tailscale Funnel Hermes Relay Design

## Goal

Allow the Render-hosted AI Secretary API to reach this PC's Hermes API while the PC and Tailscale are online, without exposing Hermes' own port or API key to the public internet.

## Context

- Hermes listens on this PC at `http://127.0.0.1:8642/v1`.
- The existing AI provider calls `GET /toolsets` and `POST /chat/completions` relative to `AI_PROVIDER_BASE_URL`, authenticating with a Bearer key.
- Render cannot reach this PC's loopback address.
- Tailscale Funnel is the selected external path. Its HTTPS endpoint is publicly reachable, so the relay must authenticate every request and expose only the routes the provider needs.
- Tailscale is installed and the device is online. Funnel has not been enabled.

## Chosen architecture

```text
Render FastAPI
  -- HTTPS + Bearer relay token --> Tailscale Funnel public URL
    --> loopback-only Hermes relay on this PC
      -- HTTP + Hermes API key --> Hermes at 127.0.0.1:8642
```

The relay is a separate local process bound only to `127.0.0.1`. Funnel targets that process, never Hermes directly. On the public hop, the existing `OPENAI_API_KEY` setting contains the relay token. The relay validates that Bearer value and replaces it with the separately stored local Hermes API key before forwarding. Neither credential is logged or returned.

## Relay contract

Allow only these exact operations:

- `GET /v1/toolsets`
- `POST /v1/chat/completions`

Reject every other method, path, and query string. Do not provide a generic proxy, path forwarding, redirects, or access to Hermes' other endpoints. Do not pass caller-supplied authorization or hop-by-hop headers upstream; construct the upstream request with the local Hermes key. Forward only the JSON request body and the minimum content headers needed by Hermes.

The relay must:

- compare the relay token using a constant-time comparison;
- reject missing or invalid authorization before contacting Hermes;
- bind to `127.0.0.1` only;
- limit request bodies to 1 MiB;
- use the configured AI timeout, capped at 120 seconds;
- return a generic, non-secret error when Hermes is unavailable;
- avoid logging request bodies, authorization values, response bodies, or upstream exception text.

## Configuration and secret handling

- Keep the local Hermes API key only on this PC in an ignored environment file.
- Store a separate, randomly generated relay token on this PC and in Render's server environment. On Render, set `OPENAI_API_KEY` to this relay token and `AI_PROVIDER_BASE_URL` to the Funnel HTTPS origin plus `/v1`.
- Keep the local relay's upstream Hermes key distinct from the relay token.
- Put only empty variable names and non-secret examples in tracked templates. Never put the Funnel hostname or either credential in browser configuration.
- Do not change the existing local Hermes setup or overwrite unrelated working-tree changes.

## Enablement and operational boundaries

- Implement and test the relay before enabling Funnel.
- Verify locally that valid relay credentials reach only the two allowed Hermes operations, and that invalid credentials and all other routes are rejected.
- Start Funnel only after local checks pass. Funnel exposes the relay's HTTPS endpoint publicly; access to the AI routes still requires the relay token.
- PC shutdown, Hermes shutdown, or Tailscale disconnection makes remote AI unavailable. No automatic fallback to another provider is added.
- Do not mark remote connectivity verified until a request has traveled from the deployed Render service through Funnel to Hermes and returned successfully.

## Error behavior

- Missing or invalid relay token: HTTP 401, generic response.
- Unsupported method/path/query: HTTP 404 or 405 without forwarding.
- Oversized request body: HTTP 413.
- Hermes connection or timeout failure: HTTP 502 or 504 with a generic response.
- Valid upstream responses preserve their status and JSON content needed by the OpenAI-compatible client; sensitive headers are not copied.

## Verification

Automated tests must cover allowed operations, invalid/missing token, route and method rejection, query rejection, request size enforcement, upstream key replacement, timeout/failure handling, and secret-free errors/logging. A local smoke test must confirm the existing Hermes toolset check and a text completion through the relay. After Funnel is enabled, verify HTTPS reachability, then verify the complete Render-to-Hermes path; local-only success is not remote verification.

## Out of scope

- Making the Hermes API port itself public.
- General-purpose reverse proxying or exposing `/v1/models`, administrative APIs, or arbitrary URLs.
- Keeping the service available when this PC is off.
- Adding a second AI provider, retry-based failover, or browser-to-Hermes access.
- Automatically enabling Funnel before the relay is implemented and verified.
