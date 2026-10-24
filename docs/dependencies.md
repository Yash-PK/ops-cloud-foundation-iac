# Dependency selection and provenance

Originally reviewed on 2026-10-08; interpreter and public advisories rechecked
on 2026-10-24. [The machine-readable audit](dependency-audit.json)
records sources, checksums, publication dates and the limits of verification.
Dependency selection is separate from the repository's execution evidence:
downloading a provider does not demonstrate an AWS deployment.

| Component | Selected version | Reason and support boundary |
| --- | --- | --- |
| OpenTofu | 1.13.1 | Primary IaC engine; current stable patch. The 1.13 series receives security support through August 2027. |
| AWS provider | 6.68.0 | Current stable release in the maintained major version; provider protocol 5.0. |
| TFLint | 0.64.0 | Current stable release; bundled Terraform ruleset 0.15.0, with no separate AWS plugin. |
| python-hcl2 | 8.1.4 | Structural HCL parsing for the local safety boundary; current stable release. |
| Lark / regex | 1.3.1 / 2026.9.29 | Exact compatible transitive parser dependencies. |
| CPython / pip | 3.14.8 / 26.2.2 | Reviewed interpreter update on 2026-10-24; hash-pinned pip certificate remediation precedes package downloads. Local and CI execution must validate this combination. |
| Ruff / Gitleaks | 0.16.10 / 8.30.1 | Python linting and secret scanning, including outgoing history. |
| ShellCheck / shfmt / actionlint | 0.11.0 / 3.14.1 / 1.7.12 | Shell correctness, formatting and workflow checks. |

OpenTofu's [1.13 release announcement](https://opentofu.org/blog/opentofu-1-13-0/)
specifies the security-support window and requires macOS 13 or newer. Its
[platform policy](https://opentofu.org/docs/language/v1-compatibility-promises/)
includes Apple Silicon macOS and Linux AMD64/ARM64. The
[1.13.1 patch](https://github.com/opentofu/opentofu/releases/tag/v1.13.1)
fixes ephemeral-value behavior. Experimental language features are unnecessary
for this project's core. Terraform engine compatibility remains unverified.

The AWS provider's [release](https://github.com/hashicorp/terraform-provider-aws/releases/tag/v6.68.0)
and live registry metadata identify 6.68.0. Upstream normally puts fixes and
features in the newest major version; security backports are exceptional, as
described in its [support FAQ](https://hashicorp.github.io/terraform-provider-aws/faq/).
Pinning prevents silent upgrades; it does not remove the need to review future
security fixes and provider schema changes.

## Locks and archive verification

`tools-iac.lock.json` pins official ZIP URLs, SHA-256 values and exact members
for Darwin ARM64, Linux AMD64 and Linux ARM64. All six OpenTofu/TFLint archives
were downloaded into memory during this review. Their byte hashes matched both
the published checksum files and GitHub's release-asset digests; archive member
names were inspected. OpenTofu ZIPs include `LICENSE`; TFLint ZIPs contain only
the executable. The audit records this distinction.

`tools.lock.json` holds the other executable pins. Their selected asset digests
were rechecked against official release metadata on the same date. The
repository bootstrap must verify downloaded bytes before execution and install
only into ignored project paths. Archive checksums establish integrity relative
to these trusted metadata sources. This review did **not** independently verify
GPG signatures, Sigstore certificates or GitHub artifact attestations for those
tool archives. Native provider verification is described separately below. TFLint's
[verification guidance](https://github.com/terraform-linters/tflint/blob/v0.64.0/README.md#verification)
describes attestation verification; it must not be reported as executed here.

The selected provider address is explicitly
`registry.terraform.io/hashicorp/aws`, pinned to `6.68.0`. The initial default
OpenTofu registry discovery request timed out in the native tool; a direct HTTPS
probe returned HTTP 403 with `error code: 1010`. The official HashiCorp discovery
endpoint responded with HTTP 200. This observed acquisition failure remains part
of development history, not a passing installation.

Both registries publish AWS 6.68.0, but the OpenTofu rebuild and HashiCorp archive
bytes differ. The audit retains both metadata sets and their own published
checksums; only HashiCorp's registry is selected. Do not mix archive hashes or
provider identities. The engine remains OpenTofu; using this provider registry
makes no Terraform-engine compatibility claim. Generate actual
`.terraform.lock.hcl` files with OpenTofu. Normal initialization verifies the
reviewed lock first and requires its bytes to remain unchanged afterward. Native
`-lockfile=readonly` rejects the 1.13.1 predecessor-registry migration shim even
with the correct explicit provider identity; the wrapper's unchanged-lock check
retains reproducibility while native package checksum verification remains active.
No TLS or checksum verification is disabled.

The first native multi-platform lock update also exposed OpenTofu's predecessor
registry migration behavior: it added a `registry.opentofu.org/hashicorp/aws`
entry beside the explicitly selected HashiCorp provider. Subsequent validation
failed because that extra identity had no cached package. The
[1.13.1 migration code](https://github.com/opentofu/opentofu/blob/v1.13.1/internal/command/meta_dependencies.go)
explains the synthetic entry and why it cannot inherit archive hashes. A
subsequent native `tofu init -backend=false` pruned the unused entry. Both
resulting stack lockfiles contain only `registry.terraform.io/hashicorp/aws`,
three native `h1:` platform hashes and the upstream `zh:` archive hashes. No
hashes were fabricated or manually substituted. This was a dependency-lock
repair, not infrastructure state migration. Recheck lock diffs after future
multi-platform lock updates.

Native provider installation completed with a warning that HashiCorp signing
key `34365D9472D7468F` is expired and that future OpenTofu versions will fail
this condition. The current engine's
[signature verifier](https://github.com/opentofu/opentofu/blob/v1.13.1/internal/getproviders/package_authentication.go)
can accept expired keys with a warning. The repository did not disable
verification or add an expiry override; the warning remains an unresolved
upstream trust/maintenance limitation. Successful checksum and native signature
handling do not establish a currently valid signing-key lifetime. An updated
official key or reviewed release is needed before claiming this issue resolved;
do not work around a future rejection by suppressing checks. The original
registry and lock failures remain development failures, even though later native
initialization and schema validation succeeded.

`requirements.lock` pins all parser dependencies and hashes five downloaded,
verified wheels. The supported lock profile is ordinary CPython 3.14 on macOS
ARM64 and glibc Linux AMD64/ARM64. It excludes source builds, musl and free-threaded
Python. `requirements-dev.lock` adds pinned Ruff. Install with
`--require-hashes --only-binary=:all:`; a missing compatible wheel must fail.

The [python-hcl2 release metadata](https://pypi.org/project/python-hcl2/8.1.4/)
allows Python 3.8 and newer, but its
[tagged CI matrix](https://github.com/amplify-education/python-hcl2/blob/v8.1.4/.github/workflows/pr_check.yml)
stops at 3.13. Therefore Python 3.14 is a repository-tested combination only
after its own tests pass, not an upstream certification. The parser's
[serialization defaults](https://github.com/amplify-education/python-hcl2/blob/v8.1.4/docs/01_getting_started.md)
preserve quotes and block markers; safety checks must handle these deliberately.
Parsing is not full OpenTofu semantic evaluation or a sandbox.

## Interpreter continuation review — 2026-10-24

The previously recorded Homebrew 3.14.7 interpreter was removed during a host
upgrade, leaving the existing project virtual environment unable to start.
The installed ordinary CPython 3.14.8 is now explicitly pinned, rather than
accepting arbitrary interpreter versions. Its [official release notes](https://www.python.org/downloads/release/python-3148/)
describe the September security fixes. Python 3.14.9 is newer; its
[October security advisory](https://www.python.org/downloads/release/python-3149/)
provides an explicit pip 26.2.2 hash-pinned mitigation for existing installations.
Bootstrap applies that exact wheel before installing dependencies. This project
does not install or change a system interpreter or the host certificate store.
The interpreter pin is shared by doctor and CI, and fresh local/clean-clone/CI
evidence is required for this revised combination. Earlier development results
remain associated with 3.14.7.

## Lint scope and advisories

TFLint 0.64.0 embeds Terraform ruleset 0.15.0, verified in its
[tagged dependency manifest](https://github.com/terraform-linters/tflint/blob/v0.64.0/go.mod).
Use the bundled recommended rules for language checks. The optional AWS
ruleset was reviewed but is not installed: provider schema validation and
project-specific negative policy tests are the bounded core. No account-based
TFLint deep checking is authorized. Upstream's
[security policy](https://github.com/terraform-linters/tflint/blob/v0.64.0/SECURITY.md)
supports only the latest TFLint version.

OpenTofu's public advisory feed contained ten entries. Version 1.13.1 is above
the fixed releases listed for all of them. Examples include malicious Git URL
file reads, unsafe provider-cache symlinks and resource exhaustion while
installing dependencies. Exact advisory identifiers, affected ranges and fixed
versions are in the audit, linked to the
[upstream advisory feed](https://github.com/opentofu/opentofu/security/advisories).
Keep remote sources pinned and treat source code and downloaded packages as
untrusted input even on a patched engine.

At review time, the queried public advisory feeds for the AWS provider,
OpenTofu's provider build, TFLint and the three Python parser packages returned
no entries; their selected PyPI versions also reported no vulnerability
records. This is a dated, limited observation, not a complete transitive
vulnerability assessment. Recheck releases and advisories before updating pins
or declaring a future release. Preserve failures and rerun the local gates and
clean-clone check after changes.

## Third-party attribution

The repository's original work uses MIT. Downloaded dependencies retain their
own licenses; the MIT file does not relicense them.

| Dependency | Upstream license reference |
| --- | --- |
| OpenTofu | [MPL-2.0](https://github.com/opentofu/opentofu/blob/v1.13.1/LICENSE) |
| AWS provider | [MPL-2.0](https://github.com/hashicorp/terraform-provider-aws/blob/v6.68.0/LICENSE) |
| TFLint executable | [MPL-2.0 AND BUSL-1.1](https://github.com/terraform-linters/tflint/blob/v0.64.0/README.md#license); embedded Terraform code adds BUSL terms |
| Bundled Terraform ruleset | [MPL-2.0](https://github.com/terraform-linters/tflint-ruleset-terraform/blob/v0.15.0/LICENSE) |
| python-hcl2 / Lark | [MIT](https://github.com/amplify-education/python-hcl2/blob/v8.1.4/LICENSE) / [MIT](https://github.com/lark-parser/lark/blob/1.3.1/LICENSE) |
| regex | [Apache-2.0 AND CNRI-Python](https://pypi.org/project/regex/2026.9.29/) |
| Ruff | [MIT](https://github.com/astral-sh/ruff/blob/0.16.10/LICENSE) |
| Gitleaks | [MIT](https://github.com/gitleaks/gitleaks/blob/v8.30.1/LICENSE) |
| ShellCheck | [GPL-3.0](https://github.com/koalaman/shellcheck/blob/v0.11.0/LICENSE) |
| shfmt | [BSD-3-Clause](https://github.com/mvdan/sh/blob/v3.14.1/LICENSE) |
| actionlint | [MIT](https://github.com/rhysd/actionlint/blob/v1.7.12/LICENSE.txt) |

Preserve bundled license files when extracting tools. The locks identify
downloads; executables and provider caches stay out of Git. Initial bootstrap
and provider installation need public package-network access. Subsequent local
checks still do not constitute a fully air-gapped build unless all required
artifacts are cached and that mode is independently tested. No dependency
verification here contacted an AWS account or provisioned a resource.
