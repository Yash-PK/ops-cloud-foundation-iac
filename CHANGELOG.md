# Changelog

## Unreleased

- Implemented reusable network, private-compute and state-bootstrap modules,
  with separate root stacks disabled by default.
- Added exact OpenTofu, AWS provider, TFLint and HCL-parser dependency pins,
  public-source provenance and platform checksum review.
- Added native mocked-plan assertions and invalid-input cases, structural
  preflight and blocked live-operation commands.
- Documented the real registry access failure, native lock-migration repair
  and unresolved upstream provider signing-key expiry.
- Added architecture, security boundaries, local demonstration and state
  lifecycle guidance. Formal local controller/clean-clone gates passed; hosted CI
  and release remain pending.
- Completed 41 unit tests, 23 native mock plans, eight accepted policy plans and
  16 rejected unsafe mutations in development checks on 2026-10-24.
- Added recoverable project-venv recreation and pinned Python 3.14.8 / pip 26.2.2
  certificate remediation; CI reads the shared interpreter pin.
