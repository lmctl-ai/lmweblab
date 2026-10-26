# Verification and current limits

The Part A live run passed HTTP and HTTPS using only profile `lmaws` in us-east-1. Numeric evidence is in [lmaws-summary.json](../evidence/lmaws-summary.json); phase timings and costs are in [the results table](../compare/RESULTS.md). A separate native host process checked seven attempt namespaces and found zero active leftovers. Raw identifiers, URLs, request data and receipts stay under ignored `.lmweblab-local/`.

The successful estimate is $0.00107766; the complete campaign estimate is $0.00513459. These are price-table estimates with request/transfer bounds and timed resource charges, not billing queries. The public pictures are synthetic.

`bash test.sh` runs in a fresh temporary directory with fake cloud transport, both HTTP contract phases, import-only recipe composition, image checks and the actual Python user-data handler on loopback through lmcurl. The lmaws host additionally tests its SDK serialization against loopback endpoints and the native executable, including ownership/cost refusals.

Live verification is Linux-only. macOS and Windows use fake-transport/build checks. The operator supplies an existing public hosted zone and the `lmaws` profile grant; the scripts do not change IAM, credentials or profile files. The nano has a bounded lifetime; use `down` to recover interrupted resource lifecycles from the private state.
