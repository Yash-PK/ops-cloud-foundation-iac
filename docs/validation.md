# Validation and evidence status

Status on 2026-10-24: development checks pass; a clean committed source revision
has not yet completed the formal local release gate in this report. Publication,
exact-revision hosted CI and versioned release are pending. No success badge or
cloud-deployed designation is warranted.

| Profile | Current evidence | Status |
| --- | --- | --- |
| Tool/package provenance | Official metadata, six IaC tool archive hashes and five parser wheel hashes checked; JSON audit retained | Statically validated dependency metadata |
| Provider setup | Native installation and multi-platform locks generated; original registry/lock failures preserved in dependency notes | Development execution; signing-key expiry remains open |
| Native schema validation | Both roots passed with zero warnings on 2026-10-24 | Development execution; formal revision-bound report pending |
| Native mocked plans | 23 runs passed; eight policy plans accepted, 16 unsafe mutations rejected | Development execution; formal report pending |
| Unit tests and lint | 41 unit tests, Ruff, HCL formatting, TFLint, ShellCheck, shfmt and actionlint passed | Development execution on macOS ARM64 / Python 3.14.8 |
| Security/clean-clone gates | Reviewed implementation ready for committed-source scans and fresh clone | Pending required gates |
| GitHub repository/CI/release | No verified publication or run attached here | Pending |
| Real authenticated plan/apply | Not run; prohibited by task scope | Cloud deployment not authorized |
| EC2 boot, effective IAM, connectivity, S3 locking/recovery | Not run | Unverified integration |

Development tool output was observed during execution but the early registry and
lock-repair command streams were not retained as standalone log files. The
[dependency audit](dependency-audit.json) identifies this provenance instead of
presenting reconstructed output as a recording. Current native lockfiles were
independently inspected, and their hashes are recorded in that audit.

## Required release evidence

After the implementation is committed and stable, execute the README quickstart
from an isolated temporary clone and produce the local record through the task
interface. The report must contain the actual tested Git revision, source/pin
fingerprint, timestamps, OS/architecture, interpreter/tool versions, commands,
exit codes and assertion counts. Source changes require new evidence. A later
documentation-only commit must identify the original tested revision rather than
pretend it was the revision that ran.

The local gate requires bootstrap/doctor, formatting/lint, unit/negative tests,
native schema validation, all native mock runs, policy acceptance/rejection,
demo, secret scans and the clean-clone result. Missing required checks, skipped
tests, development-mode reports, stale fingerprints and failed commands cannot
be treated as successful proof. Publication requires an exact outgoing review
in addition to these checks. Hosted CI must be inspected for the exact pushed
revision; pending CI is not release success.

Native mock plans and their raw JSON remain in ignored restricted runtime paths.
Public evidence should summarize their results and preserve redacted failure
context, not upload unrestricted logs or future real state/plan artifacts.
Dependency hashes prove artifact selection/integrity, not application behavior.

## Known failure history and open limitations

1. OpenTofu registry discovery timed out; an HTTPS probe returned HTTP 403.
   The explicit HashiCorp registry was selected after verifying its own release
   checksums. This failure was not reclassified as a successful default install.
2. A native multi-platform lock update added an unused OpenTofu registry entry.
   Validation could not find that package. Native initialization removed the
   unused entry while preserving the selected provider's hashes; later schema
   validation and development mock tests passed.
3. Native provider verification warned that the upstream signing key is expired.
   This remains unresolved. No repository verification check was disabled.
4. The old virtual environment could not start after its Homebrew Python 3.14.7
   framework disappeared. Bootstrap now preserves the old environment in an
   ignored backup and recreates it using pinned 3.14.8 with pip 26.2.2 remediation.
   Native `venv --upgrade` alone did not repair the copied macOS launcher.
   Regression coverage checks preservation and failed-remediation propagation.

There is no complete transitive vulnerability scan, independent standalone-tool
signature verification, Linux ARM64 runtime result, real cloud compatibility
proof or Terraform-engine test implied by these records. The final evidence
must list the exact platforms that actually ran. See [SECURITY.md](../SECURITY.md)
and [dependencies](dependencies.md) for scope and remediation boundaries.
