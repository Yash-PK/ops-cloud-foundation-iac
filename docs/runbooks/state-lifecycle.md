# Runbook: state design, migration and recovery boundaries

This is an operational design for a future separately authorized AWS profile.
Its procedures have not been exercised against AWS. The current task interface
blocks live plans, applies, imports, backend migration and destructive actions.
There is no existing cloud bucket or state to recover.

## Ownership and initial bootstrap

The foundation and state-bootstrap roots have separate local backends. The
state module emits future S3 coordinates; output is not a backend connection.
Before any real deployment, establish the target account, region, existing
administrator/operator roles, short-lived identity, reviewed AMI, cost approval
and explicit resource inventory. A 12-digit fixture value is not verified
account ownership. An account check would require separate authorization.

The S3 bucket and KMS key must exist before the foundation can use them. The
bootstrap stack therefore needs its own protected initial state and backup,
separate from the foundation state. Its key policy requires the intended key
administrator to remain authorized; no key-policy lockout bypass is configured.
The module does not create or verify existing role trust and identity policies.

## Environment state and locking

The proposed keys are `lab/foundation/terraform.tfstate` and
`dev/foundation/terraform.tfstate`, each with an adjacent `.tflock` object.
Use separate reviewed working directories/backend configurations for future
environments. Merely changing a variable in one already initialized working
directory does not safely select a different backend.

The proposed S3 backend uses native lockfiles, not a DynamoDB table. The operator
may read/write state and read/write/delete its lock; ordinary state-object
deletion is absent. Those privileges do not cover arbitrary workspaces or
historical version restoration. Real concurrent lock acquisition, conditional
S3 writes and failure recovery require integration tests. See the official
[OpenTofu S3 backend documentation](https://opentofu.org/docs/language/settings/backends/s3/).

If a future lock appears stale, first identify its owner and the active process.
Verify no writer remains and preserve lock/state metadata. Never force-unlock
only because a command is taking too long. A force unlock or manual object
deletion needs a reviewed target and explicit destructive-operation authority.

## Migration and provider identity

For a future local-to-S3 migration, freeze writers, back up the source state to
approved encrypted storage, review backend coordinates and KMS access, then
perform an explicitly authorized native migration. Verify state lineage,
serial/resource inventory and the remote object version afterward, and test
concurrent locking before resuming changes. Keep a recovery copy until the
migration has been independently checked. No automatic migration is part of
this repository's current quickstart.

The dependency-lock registry repair described in
[dependency provenance](../dependencies.md) is unrelated to migrating live
infrastructure state. A later change of provider identity in actual state is a
separate operation requiring its own plan and backup; do not infer that editing
an HCL source address alone safely migrates state.

## Drift and imports

The current mock profile disables refresh, so it cannot detect real cloud drift.
A future authorized drift check needs read permissions, protected output and an
explicit account/region/resource scope. Review any proposed changes before an
apply; a refresh-only result still reads real resources and may reveal secrets.

Import is not resource creation, but it changes management state. Before a
future import, establish that the resource is owned by the intended lab, is not
already managed by another stack and matches the reviewed configuration. Back
up state and verify a subsequent no-surprise plan. Neither import nor drift
reconciliation is demonstrated by the current native mock tests.

## Recovery and destruction

Versioning preserves historical S3 objects; it is not a verified application
backup. For a future recovery exercise, restore a selected state version into
an isolated destination first. Check lineage, serial, resource addresses and
the difference from current cloud reality before replacing active state. State
recovery cannot recreate deleted application data. Measure actual recovery
time and data loss only when an authorized exercise runs.

The named operator lacks historical-version recovery permissions; any recovery
role and object-version access must be separately reviewed. KMS key deletion
can make retained ciphertext unusable, so retention and key lifecycle must be
designed together. The 30-day key-deletion window is a configuration choice, not
a tested recovery guarantee.

Both key and bucket use `prevent_destroy`; the bucket also disables forced
emptying. These guards do not prevent out-of-band deletion. A future teardown
must preserve required state/backups, enumerate only owned resources and obtain
explicit destructive confirmation. No current task bypasses these guards or
destroys cloud resources.
