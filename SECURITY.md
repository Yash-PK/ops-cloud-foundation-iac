# Security model

This repository is a local AWS configuration and mock-test lab. Cloud resource
creation, authenticated plans, billable services, public exposure and host
configuration changes are outside its authorization. Do not add credentials to
make a test pass. No compliance or production-hardening certification is claimed.

## Trust boundary

The supported entry point is the Make/task interface. `scripts/guard.py` parses
the supported HCL files and rejects alternate/shadowing source formats,
unreviewed filesystem functions, remote modules, provisioners, connection hooks,
unsupported providers, override inputs and nonlocal backend configuration.
Each native test must declare the mocked AWS provider, use `command = plan`
and disable refresh. These are checked before native execution.

`scripts/iac.py` constructs a minimal subprocess environment instead of passing
through the caller's environment. It uses an empty project-local home, empty
AWS configuration/credential files and disabled metadata credential lookup.
Download operations allow the pinned public provider registry; other operations
use an unreachable proxy as an additional precaution. The proxy is not a
kernel-enforced network boundary. A malicious tool or edited source can bypass
these measures. Do not run untrusted changes with credentials or privileged
self-hosted CI runners. Review code and negative tests before execution.

The direct `tofu` executable can perform live operations. Its presence in a
project directory is not an authorization mechanism. The task interface blocks
live `plan`, `apply`, `destroy`, integration and teardown requests; bypassing
that interface is outside the supported workflow.

## Infrastructure configuration limits

Private compute has no public IP or SSH key, no configured security-group egress
rules, an encrypted root disk and required IMDSv2. The instance role has only
the EC2 trust relationship and no workload IAM grants. These settings are
inspected in mocked plans. Effective routing, reserved AWS service access,
metadata behavior and IAM permissions have not been tested in AWS.

The health service binds loopback and is configured for a restricted dynamic
systemd user. No EC2 image or boot was exercised. Package patching, OS baseline,
central logging, operator access and recovery would require a separate design.

The state bucket configuration blocks public access, disables ACL ownership,
enables versioning, defaults to SSE-KMS and denies non-TLS requests. The named
operator receives only the configured state/lock paths and scoped KMS use.
SSE-C is blocked, but the core does not enforce exclusive use of the default
KMS key against every possible explicit encryption-header override. Existing
role policies, permissions boundaries, organizational controls and key-policy
lockout behavior are not validated by mocks. Version recovery requires separate
permissions; versioning alone is not a tested backup.

`prevent_destroy` protects resources only while the relevant configuration is
present and used by the engine. It does not stop direct cloud-console deletion,
key deletion by another principal or an authorized configuration change.

## Dependencies and findings

Exact tool archives, Python wheels and provider locks are reviewed and pinned.
Checksums are verified; standalone tool signing/attestation verification was not
independently performed. Native provider installation warns that upstream key
`34365D9472D7468F` is expired. The current engine accepts this with a warning;
the repository does not suppress verification. This is an unresolved upstream
signing-key limitation, not a finding marked fixed by successful installation.
See [dependency audit](docs/dependency-audit.json) and
[provenance notes](docs/dependencies.md) for sources and dates.

No secret-scan success is claimed until the formal report records scans of
working/staged files and the full outgoing history. `.gitignore` is not a
security gate. Do not commit tokens, passwords, private keys, real cloud inputs,
state, plan binaries, raw sensitive plan JSON, credentials or private logs.
Synthetic test fixtures still need review before publishing.

## Reporting

Report nonsensitive reproducible defects through a repository issue once the
repository is published. Do not put a secret or exploitable private environment
detail in a public issue. For sensitive findings, use GitHub's private reporting
option only if the repository exposes it; otherwise request a private contact
without including the finding. No private reporting feature is claimed enabled.

Include affected revision, bounded reproduction, expected boundary and observed
result. Stop the relevant gate, preserve redacted evidence and add a regression
before calling a fix complete. If a credential is exposed, its owner must revoke
or rotate it through the issuing system; a Git deletion does not revoke it.
