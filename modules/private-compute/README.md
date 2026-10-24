# Private compute module

`enabled` defaults to `false`. Enabled configuration creates one `t3.micro`,
one security group, an EC2-only trust role and its instance profile. No IAM
permissions are attached because the fixture makes no AWS API calls. There is
no SSH key, public address, outbound security-group rule or package download.
The root disk is encrypted gp3; metadata requires IMDSv2 and one response hop.
CPU credits use standard mode, without surplus-credit charges.

Required inputs: `name_prefix`, `vpc_cidr` and ownership `tags`. Enabled use
also requires an explicit `ami_id`, `vpc_id` and private `subnet_id`. A separately
reviewed x86_64 Linux image must already include cloud-init, systemd and Python 3
at `/usr/bin/python3`. No usable AMI is selected by this repository.

The deterministic cloud-init writes a Python standard-library `/healthz`
fixture and a restricted, dynamically unprivileged systemd service. It binds
only `127.0.0.1:8080`. The security group reserves TCP 8080 from the private VPC
CIDR, but the current fixture is deliberately not reachable from another host.
Tags cover the instance and its volume. `policy_contract` exposes configured
security fields for mock assertions; the template is not proof of a boot test.
