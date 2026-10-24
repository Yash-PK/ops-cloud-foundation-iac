# Contributing

Read [AGENTS.md](AGENTS.md), [acceptance](docs/acceptance.md) and
[SECURITY.md](SECURITY.md) before changing the project. Keep work bounded and
claim only what executable evidence supports. No AWS credentials, account
lookups or real cloud operations belong in the default workflow.

Use the pinned Python interpreter and `make bootstrap`, then run `make lint`,
`make test`, `make validate` and `make security`. Test the README sequence from a
clean temporary clone before publishing. Do not use global package installs,
delete unrelated caches or modify host configuration to satisfy a check.

Place reusable resources in `modules/`, explicit root composition in `stacks/`
and native tests beside the roots. Keep enabled defaults false. New test cases
must use the default mocked AWS provider, explicit plan mode and disabled
refresh. Do not introduce remote modules, real data sources, execution hooks,
credential inputs or a remote backend as a shortcut. Extend guard/policy tests
for any justified new capability, including a meaningful rejection case.

Mock assertions should inspect resource-derived behavior and native plans, not
only handwritten copies of expected configuration. Preserve expected failures:
a test that rejects an unsafe input is useful only if the safe equivalent also
passes. Never change missing checks or skips into successful evidence.

Dependency updates require official release/support/advisory review, exact
archive/wheel hashes and native provider lock generation. Review registry
identity and the complete lock diff. OpenTofu can add an unused registry shim
entry during a provider lock update; follow the documented native-init repair.
Do not synthesize hashes, disable signature checks or hide the expired-key
warning. Revalidate each supported platform claimed by a release.

Document the reason for meaningful architecture changes in a decision record.
Update the README, module docs, runbooks, changelog and validation status with
the final behavior. Record the code revision tested separately from later
documentation commits. Include exact commands, exit codes and redacted evidence;
do not manufacture screenshots, output or cloud results.

Before publication, review the exact outgoing files, license/attribution,
generated artifacts, source diff and secret scans. Only new authorized public
repositories may be created; collisions require investigation. No force push,
remote deletion, account-setting changes or container publishing is authorized.
Hosted CI and versioned releases must wait for their actual gates.

A pull request should explain the concrete problem, changed behavior, affected
boundary and validation. Separate proposed production improvements from
implemented behavior. Real deployment, identity federation, broader IAM,
additional services and alternative engines need separate acceptance and
authorization; they cannot inherit success from the mock core.
