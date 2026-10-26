# lmweblab with lmaws

This directory is the lmscript + lmaws implementation of the integration stack. It uses the `lmaws-<run-id>` namespace and the `lmaws_test=<run-id>` tag. Offline runs use deterministic fixtures and cost `$0.0000`; live runs require the single `lmaws` profile and a real `LMWEBLAB_DOMAIN`.

Run the complete offline lifecycle:

```sh
lmctl https://raw.githubusercontent.com/lmctl-ai/lmweblab/main/lmaws/web_stack.lms all
```

For a live run, set `AWS_PROFILE=lmaws`, `LMWEBLAB_DOMAIN` to the delegated domain, and `LMWEBLAB_LIVE=1`. The driver tests static CloudFront content and dynamic EC2 content through lmcurl, and always attempts teardown after a failed test. `down <run-id>` is independently safe and verifies zero owned leftovers through lmaws.

The lmaws host owns the cloud operations and applies guards for the prefix, exact run tag, us-east-1, t3.nano/t4g.nano, 8 GiB disks, and caller `/32`. Phase 2 adds ACM DNS validation and redirects viewers to HTTPS.

`status` reads provider resources without acquiring the lifecycle state lock, so it remains usable during CloudFront propagation. `lmaws/recipes/steps.lms` is an import-only library of individual guarded provisioning steps; see its recipes index.
