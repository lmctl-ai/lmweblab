# lmweblab

![lmweblab stack](images/lmaws_architecture.png)

`lmweblab` is a pictures-first integration test for the same tagged web stack implemented with lmaws and lmcloud. The lmaws driver provisions a private S3 site, CloudFront, Route 53 records, and a disposable tagged nano web server; lmcurl performs the HTTP assertions and p95 load check.

| Picture | Runnable example |
| --- | --- |
| ![stack architecture](images/lmaws_architecture.png) | `lmctl https://raw.githubusercontent.com/lmctl-ai/lmweblab/main/lmaws/report.lms` |
| ![shared banner](shared/site/banner.png) | `lmctl https://raw.githubusercontent.com/lmctl-ai/lmweblab/main/shared/site/render_banner.lms` |
| ![lmcloud architecture](images/lmcloud_architecture.png) | `lmctl https://raw.githubusercontent.com/lmctl-ai/lmweblab/main/lmcloud/all.lms` |

Offline runs are the local gate and cost `$0.00`. They use synthetic fixtures and always execute teardown. Live runs require `AWS_PROFILE=lmaws`, `LMWEBLAB_DOMAIN`, and `LMWEBLAB_LIVE=1`; names use `lmaws-site-<run>` and `lmaws-app-<run>`, and all resources carry `lmaws_test=<run>`. The default cap is `$0.10` with a `$0.25` hard ceiling. Never use an administrator profile.

```sh
lmctl lmaws/web_stack.lms all --offline
lmctl lmaws/web_stack.lms all --offline --phase2
```

The dynamic app serves escaped query echo, request counters, timestamps, hostname, and `/api/info`. Teardown is available separately as `lmctl lmaws/down.lms <run-id>` and verifies the owned state before deletion.
