# Cloud foundation continuation

This is the sole active engineering project after the first four completed cores.
Read docs/acceptance.md before implementation. Keep this sibling repository
outside the portfolio hub. Build lab/reference engineering, not production or
employment claims. Use the existing Git identity and preserve prior evidence.

Primary engine: OpenTofu; choose a maintained pinned release after official
support/release/advisory review. Claim Terraform compatibility only if tested.
Architecture: bounded AWS network, private compute/IAM and state-bootstrap
modules; synthetic mock tests plus static policy checks. Keep optional costly
profiles in the roadmap until separately implemented and tested.

Cloud resource creation, real authenticated plans, billable services, container
publishing and host/global changes are unauthorized. Do not inspect cloud or Git
credential files, environment variables, histories or unrelated home content.
No cloud apply/destroy, credential discovery, real account identity lookup or
public service exposure. Bootstrap tools only into ignored repository paths.
The task interface must refuse live operations; mock providers are never cloud
proof. Test controls accepting safe and rejecting unsafe inputs. Exclude state,
plan binaries/JSON with sensitive values, credentials and generated caches.

Commands will be documented in Makefile. Required gates: pinned bootstrap,
format/validate/lint, real OpenTofu mocked plans, policy/unit negative tests,
clean-clone quickstart, staged/working/full-history secret scans and exact outgoing
review. Record revision, environment, versions, exit codes and honest omissions.
Only publish the new public Yash-PK/ops-cloud-foundation-iac repository after
local gates; verify exact-head hosted CI before release. No force-push or adoption
of a remote collision. Update the hub and save exact next work at boundaries.
