# ADR 0001: One engine and a bounded mock-only AWS core

Status: accepted for the local lab core. Date: 2026-10-08.

## Context

The portfolio needs executable IaC evidence, while cloud resource creation,
authenticated plans and billable services are not authorized. A handwritten
JSON fixture alone would not test HCL evaluation or AWS provider schemas. A
cloud emulator would still not establish AWS compatibility.

## Decision

Use pinned OpenTofu 1.13.1 with the real AWS 6.68.0 provider schema and native
`mock_provider` plan tests. Split network, private compute and state bootstrap
into reusable local modules and two disabled-by-default roots. Use TFLint's
bundled language rules and bounded project policies; do not add overlapping
scanners or account-aware lint plugins without a specific tested purpose.

Parse every supported source/test file before native execution. Require mock
providers, explicit plan mode and disabled refresh; reject execution hooks,
alternate configuration formats, remote modules and provider/credential
overrides. Construct a minimal subprocess environment. Keep live operations
blocked in the task interface and make its limitations explicit.

Use the explicit HashiCorp provider registry after the native default-registry
discovery failed in this environment. Preserve both registries' checksum
provenance. Native initialization repairs the unused lock migration entry; do
not edit hashes to force a passing install. Record the expired upstream signing
key as an unresolved limitation while retaining native verification.

## Consequences

The core is usable without a cloud account and tests real configuration. It
can demonstrate deterministic networking, security settings, IAM/state design
and invalid-input rejection. It cannot claim service reachability, effective
permissions, state recovery or any cloud deployment. A direct tool invocation
or malicious source lies outside the wrapper's safety contract; this is not a
security sandbox for arbitrary contributions.

Separate state bootstrap makes the initialization dependency visible and keeps
environments' future keys distinct. The local demo does not solve remote-state
operations by generating example coordinates. An actual deployment needs a
reviewed account, image, roles, short-lived identity, costs and recovery plan,
followed by independent cloud evidence and explicit authorization.

Terraform compatibility, alternative engines, cloud emulators and external AWS
lint plugins remain unclaimed. Reconsider this decision only when a bounded
extension can be authorized and validated, not to enlarge tool coverage.
