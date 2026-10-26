# Importable web steps

Import [steps.lms](steps.lms) locally or from its raw GitHub URL. Importing defines functions and performs no work. Pass `{run_id, domain, live, profile}`; run IDs are lowercase hexadecimal and the only live profile is `lmaws`. The helpers return a status summary and retain raw provider identifiers in ignored private state.

| Function | Action | Access |
|---|---|---|
| `web_bucket(o, site_dir)` | Private tagged origin, public-access block, five site assets | Write with lmaws |
| `web_distribution(o)` | Tagged CloudFront distribution and OAC; use prepared certificate if present; wait Deployed | Write with lmaws |
| `web_certificate(o)` | ACM certificate, scoped validation CNAME, wait issuance; attach to an existing distribution when present | Write with lmaws |
| `web_site_dns(o)` | Create the exact site alias and wait INSYNC | Write with lmaws |
| `web_compute(o, settings)` | Tagged spot nano, 8 GiB disk, caller `/32`, user data | Write with lmaws |
| `web_app_dns(o)` | Exact app A record and wait INSYNC | Write with lmaws |
| `web_https(o)` | Enable HTTPS redirection after HTTP tests | Write with lmaws |
| `web_invalidate(o)` | Invalidate only this run's distribution | Write with lmaws |

Use `live:false` for a credential-free preview. Use the driver for failure recovery across the complete lifecycle: `lmctl lmaws/web_stack.lms all --offline`. The driver batches provisioning steps into one host process to avoid repeated JVM startup. Each native step also attempts reverse cleanup when it fails. `down <run-id>` remains available for interruption recovery.

For the quickest complete run, prepare the certificate before creating the distribution. This configures the validated alias at creation and avoids a second initial CloudFront deployment wait.
