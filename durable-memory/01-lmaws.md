# Part A: lmaws implementation

The `lmaws/` driver uses a persistent native `Cloud.web_stack(run, domain, statepath)` session. `Web.step` executes bucket, CloudFront, ACM, Route 53, and EC2 phases while raw identifiers remain in a private `.lmweblab-local/lmaws-web-state-<run>.json` file. `Web.status` exports a masked singleton row; `Web.down` performs reverse teardown and verifies zero owned leftovers.

Offline mode uses the lmaws demo transport and lmcurl mock fixtures. `all` runs phase-one HTTP checks before optional `--phase2` HTTPS redirect checks. Live mode sets `AWS_PROFILE=lmaws`, `us-east-1`, `LMAWS_LIVE=1`, and the `$0.10` cap. The only permitted names are `lmaws-site-<run>`, `lmaws-app-<run>`, and related run-tagged resources with `lmaws_test=<run>`.

EC2 discovery selects a public default subnet through lmaws inventory and resolves the Amazon Linux 2023 arm64 AMI through the public SSM parameter. The caller `/32` is detected through lmcurl. The node is a t3.nano/t4g.nano one-time spot instance with an encrypted 8 GiB gp3 root, IMDSv2, a nine-minute self-shutdown, and TCP/80 restricted to that `/32`.

Verification gate: `mvn -q -DskipTests package` in lmaws and `lmctl lmaws/web_stack.lms all --offline` in this repository. Live results are intentionally not recorded in public files.
