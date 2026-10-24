# Local demonstration and design walkthrough

This demonstration uses real OpenTofu evaluation with synthetic AWS provider
responses. It does not create a container, VM, emulator or cloud resource.
Run from a standalone repository checkout after the pinned interpreter exists.

```sh
make bootstrap
make doctor
make demo
```

The demo must run the native mock tests and bounded plan policies, then verify
that a live apply request is blocked. Read its actual output; there is no canned
success transcript. At the initial development checkpoint, 23 native test runs
passed; the formal validation report must establish the final count/revision.

## Explain a valid configuration

Open `stacks/foundation/tests/foundation.tftest.hcl`. The
`disabled_by_default` case requires zero resources. `private_foundation` enables
only synthetic input and checks eleven configured resources: seven networking
and four compute/IAM resources. Its two derived private subnet ranges are
`10.42.0.0/18` and `10.42.64.0/18`; no AWS lookup chooses these values.

Follow `module.network` into `modules/network/main.tf` to show `cidrsubnet`,
explicit AZs and private route tables. Then follow compute into its resource
attributes and cloud-init template. Explain why an encrypted disk and IMDSv2 are
configuration assertions here, while EC2 boot and effective IAM remain unproven.
The health process binds loopback, so no browser endpoint is produced locally.

Show the optional edge test: Internet Gateway routes appear only in two separate
edge subnets. The private compute address/routing settings remain private. A
mocked route assertion is not a packet-level reachability test.

## Show failure and recovery

Run the same checked source through:

```sh
make test
make validate
```

Native expected-failure cases exercise invalid public/noncanonical CIDRs,
duplicate/mixed-region zones, invalid identifiers and environment labels. A
passing expected-failure case means that the intended validation rejected the
bad input. Guard/policy negative cases exercise the execution and configuration
boundaries; the valid equivalents must also pass.

To expose the live-operation boundary directly:

```sh
.venv/bin/python scripts/iac.py apply
```

Expected behavior is exit 3 and a blocked-operation message before any native
apply. This command changes no source or infrastructure, so recovery is simply
to use the supported demo again. A nonzero Make wrapper status may differ from
the underlying Python exit code. Do not supply credentials or bypass the wrapper
to make the intentionally unsupported operation succeed.

For an actual broken dependency or test, preserve the failure, make a reviewed
fix, rerun the same gate and record both outcomes. Follow the
[local runbook](runbooks/local-checks.md). The registry-access and unused-lock
entry failures are real examples; the expired signing-key warning remains open.

## Explain state and IAM

Open `stacks/state-bootstrap/tests/state-bootstrap.tftest.hcl` and
`modules/state-bootstrap/main.tf`. Show private-bucket controls, KMS settings,
the separate lab/dev keys and the operator's state-versus-lock permissions.
Explain why an IAM wildcard in a KMS key policy means the attached key, while
an identity-policy wildcard would broaden access. A wildcard principal in a
TLS Deny is not a public access grant.

The output proposes backend coordinates, but the actual root backend is local.
Explain the bootstrap dependency, locking failure modes, recovery-role gap and
why versioning alone proves no restore. These tradeoffs are documented in
[architecture](architecture.md) and the [state runbook](runbooks/state-lifecycle.md).

## Interview discussion

- Why native mock tests: they evaluate real module expressions and schemas
  cheaply; they cannot prove AWS service behavior or effective authorization.
- Why an exact registry address and lock: two distributors can publish different
  archives for one version; provenance and checksums must identify the chosen one.
- Why an empty-permission instance role: the health fixture needs no AWS API
  access, so attaching broad service policies would add unnecessary authority.
- Why no default egress path: the fixture requires no downloads; operating a
  patched reachable service would need a separately designed image/access path.
- Why separate state bootstrap: its storage must exist before another stack can
  use it; state migration and recoverability need their own operational evidence.

These explanations point to implemented code and explicit limits. They do not
substitute for professional operations experience or a real cloud deployment.
