# Part A host contract

The driver expects these additional `Cloud` methods from lmaws. All return `Row`,
and the host must apply the web-stack guards before any provider request:

* `web_stack(string run_id, string domain, string statepath) -> Web` — open a persistent run-owned session. Raw IDs remain private in the native state file.
* `Web.step(string operation, string json_args) -> Row` — execute `bucket`, `distribution`, `dns_site`, `compute`, `dns_app`, `certificate`, or `https`.
* `Web.status() -> Rows` — return masked state and timing.
* `Web.down() -> Row` — print/apply the reverse deletion plan and independently verify `leftover_count == 0`.

`Web` should use lmaws' `WebCompute` adapter for the persistent spot nano
node. It receives only validated VPC/subnet/AMI/CIDR arguments, tags the
instance, root volume, ENI, spot request, and security group at creation, and
stores raw identifiers only in the native state file. It must never reuse the
auto-closing `SpotRun` session.

The methods must be available in the DSL schema and work with the existing
`aws.example(...)` context. `status.lms` uses the account-level
`Cloud.find_prefix("lmaws-")` separately when a run state is unavailable.
Live provider calls still require `LMAWS_LIVE=1` and `AWS_PROFILE=lmaws`.
