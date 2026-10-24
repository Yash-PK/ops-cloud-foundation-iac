# Bounded acceptance — defined before implementation

Status on 2026-10-24: bounded implementation and development checks pass;
revision-bound release gates and publication are next. No AWS API call,
authenticated plan, apply or cloud compatibility result is claimed.

- Reusable AWS network module derives non-overlapping private subnets in two
  explicit availability zones, private route tables and a separately disabled
  public-edge/Internet Gateway option. Validate CIDRs, names, tags and AZ inputs.
- Private compute module uses an explicit AMI input, no public IP or SSH key,
  security groups with scoped ingress/egress, encrypted gp3 root disk, IMDSv2,
  tagged resources and a least-privilege instance role. Supply minimal
  deterministic cloud-init/systemd health configuration without embedded secrets.
- Separate state-bootstrap module defines encrypted/versioned private S3 state,
  explicit access/IAM policy, locking design and environment-specific keys.
  Keep all actual state/bootstrap/cloud actions disabled by default and in the
  task interface. Describe backend chicken-and-egg and migration/recovery risks.
- Pin maintained OpenTofu, AWS provider and relevant lint/security tooling;
  commit actual generated dependency lockfiles and official selection evidence.
- Run the real OpenTofu parser/schema validation and mock-provider tests for
  valid and invalid settings. Mock plans must exercise resource configuration,
  not just a parallel handwritten fixture. Check plan policies accepting valid
  input and rejecting public exposure, broad IAM and unencrypted resources.
- Run no authenticated plan or apply, provision no resource and read no cloud
  credentials. Every demonstration states its static/mock nature. A direct
  binary outside the task interface is not claimed to be an enforced sandbox.
- Provide standalone bootstrap/doctor/lint/test/validate/demo/clean tasks,
  meaningful tests/CI, MIT attribution, architecture/ADR/runbooks, security and
  contribution guides, changelog, issue/PR templates and reviewed evidence.
- Verify the documented quickstart from a temporary clone. Scan working/staged
  files and full outgoing history; state/plan/credential artifacts remain ignored.
  Publish only after gates; inspect exact-commit GitHub CI before a release.

Load balancing, databases, managed Kubernetes, DNS, workload object storage,
audit logging, other clouds and real deployment are explicit extensions, not
empty modules or renamed provider files. Terraform compatibility remains
unverified unless separately exercised.
