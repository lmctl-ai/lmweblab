# Shared lmweblab contract

The `site/` directory is the private S3 origin fixture. `site/banner.png` is a synthetic architecture picture rendered by `site/render_banner.lms`; `site/lmweblab_latency.png` is a synthetic p95 chart rendered by `site/render_latency.lms`. They contain no account, host, distribution, or address data.

`userdata/user_data.sh` installs the dynamic Python service on the tagged nano instance. It exposes `/healthz`, `/api/info`, and an HTML page at `/` and `/index.html`. The page shows UTC time, hostname, a monotonic request counter, the run id, and an HTML-escaped query echo. `/api/info` returns the original query value as JSON so clients can assert both safe rendering and data fidelity. `LMWEBLAB_PORT` is supported for local fixtures and defaults to port 80.

The lmcurl contract scripts are in `tests/`:

| script | live input | offline input |
|---|---|---|
| `static_contract.lms` | write CloudFront URL to `.lmweblab-static-url` and custom Route 53 URL to `.lmweblab-static-alias-url` | create `.lmweblab-offline` |
| `dynamic_contract.lms` | write URL to `.lmweblab-dynamic-url` | create `.lmweblab-offline` |
| `load_check.lms` | write URL to `.lmweblab-dynamic-url` | create `.lmweblab-offline` |

Run a script through the lmscript host with `lmctl shared/tests/static_contract.lms` (or use its raw GitHub URL). The driver writes URLs to the corresponding private dot files before invocation. Live mode fails closed when a URL is missing; it never substitutes a mock. Offline mode is explicit and uses only lmcurl’s built-in `/site/*` fixtures. The scripts install `lmcurl` themselves, retry propagation, assert status/content/schema, write a small report under `reports/`, and never invoke an AWS command. A live run must set `AWS_PROFILE=lmaws` in the surrounding stack driver; the contract scripts themselves only perform HTTP.

From the repository root, `bash shared/tests/offline_gate.sh` runs all three scripts in a fresh temporary directory with the explicit offline marker. It is suitable for the local gate and makes no AWS calls.
