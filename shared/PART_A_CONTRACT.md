# Shared web stack contract

Part A owns `lmaws/`; Part B owns `lmcloud/`. Both use the single `lmaws` profile, distinct run tags and resource names. Part A uses `lmaws-site-<hex>` and `lmaws-app-<hex>`. Shared assets and tests contain synthetic fixtures only. Live endpoint state stays under ignored `.lmweblab-local/`.

CloudFront requires a valid certificate for every custom alias, including HTTP aliases. Part A validates an ACM certificate before adding the alias, tests HTTP with `allow-all`, then enables the HTTPS redirect in phase 2. The default CloudFront hostname can serve HTTP earlier. A Host-header override is a routing diagnostic, not proof that the custom alias is configured.

The native lmaws extension uses `Cloud.web_stack(run_id, domain, private_state_path)` and explicit `Web.step`, `Web.status`, `Web.down`. Stateful mutation happens only with the run tag and creation proof. HTTP assertions use lmcurl. Local fake-transport tests must pass before live deployment.
