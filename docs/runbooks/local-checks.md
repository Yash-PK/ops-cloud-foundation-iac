# Runbook: local checks and dependency failures

Scope: this repository's tools, source, native mock tests and ignored caches.
No AWS credentials or resources are involved. Keep the failed revision and
redacted command output before changing anything.

## Normal check sequence

From the repository root, run the README commands:

```sh
make bootstrap
make doctor
make lint
make test
make validate
make demo
make security
```

Run sequentially on small machines. Initial package downloads require public
HTTPS access. A provider download is not a cloud API call or a deployed-resource
test. When making a release, also run the clean-clone and evidence targets after
the source revision is committed and stable; follow [validation](../validation.md).

## Diagnose without weakening checks

| Symptom | Interpretation and recovery |
| --- | --- |
| Python version rejected | Use the pinned ordinary CPython 3.14.8; set `BOOTSTRAP_PYTHON` when its command is not `python3.14`. Review and revalidate interpreter updates rather than bypassing the version gate. |
| Missing wheel or hash mismatch | Stop bootstrap; compare exact official metadata with the reviewed lock and investigate corruption/version drift |
| Provider discovery timeout or HTTP 403 | Package-registry access failed; inspect the requested registry identity and network response; do not disable TLS |
| Lock contains an unused OpenTofu registry identity | Review the documented native migration behavior and regenerate/prune through the native engine, then inspect the diff |
| Expired provider signing-key warning | Preserve it; the current engine warns while future engines may reject; require official key/release remediation before claiming resolution |
| Guard rejects HCL | Inspect the rejected block/format; keep mock-only plans and reviewed local sources rather than bypassing preflight |
| Native test fails or skips | Inspect the private test output, reproduce the exact test, fix configuration or a justified assertion error and rerun the same suite |
| Policy rejects a plan | Inspect the resource and violated invariant; keep the unsafe fixture only in its bounded negative test |
| Secret scan reports a finding | Stop publication, classify the finding without echoing sensitive values, remediate source/history and rotate any exposed credential through its issuer |

The observed initial registry failure and lock repair are recorded in
[dependencies](../dependencies.md). The selected provider is explicitly
`registry.terraform.io/hashicorp/aws`. Switching registry is a reviewed supply
chain change because archive hashes differ, even for the same version.

For an intentional, reviewed dependency update, the existing wrapper exposes:

```sh
.venv/bin/python scripts/iac.py init --update-lock
```

This performs registry downloads only and does not change a remote backend.
The pinned OpenTofu release can add a synthetic predecessor-registry lock entry.
After the update, inspect both `.terraform.lock.hcl` files. If the unused entry
appears, a native initialization with the reviewed unchanged HCL prunes it;
this maintenance path must be reviewed before returning to read-only locks.
Do not manually paste hashes or treat a validation failure as an allowed skip.
The routine quickstart uses committed locks in read-only mode.

Native test output is written under `.runtime/mock-output/` with restricted
permissions. It contains synthetic configurations in this core, but inspect and
redact it before sharing. Real plans/state can contain sensitive values even
when terminal output marks an input sensitive. Public evidence should retain
the assertion outcome, revision and command status without copying raw secrets.

## Cleanup and recovery verification

After a fix, rerun the failed command and then its relevant local gates. Record
both failure and recovery; do not overwrite an earlier failed report with a
fabricated success. Source changes invalidate previous implementation evidence.

`make clean` reports retained project-local caches and performs no broad
deletion. No cloud teardown is required for mock tests. If a temporary clone
exists, its creator may remove only that inventoried, owned temporary directory.
Never delete an unfamiliar state file, change the host clock to bypass key
expiry, modify global tool installations or run blanket cache/prune commands.
