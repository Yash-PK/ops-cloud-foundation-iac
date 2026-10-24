# Network module

`enabled` defaults to `false`. Enabled configuration creates one VPC, two
private subnets, two private route tables and two associations. `vpc_cidr` must
be canonical RFC1918 IPv4 with prefix /16–/24; adding two subnet bits derives
four non-overlapping ranges. The first two are private, in two explicit AZs.
There is no AZ lookup, NAT, IPv6, public address assignment or private default
route.

The separately disabled `enable_public_edge` option uses the remaining two
subnet ranges, one Internet Gateway and two edge route tables/associations.
Only those edge tables receive an IPv4 default route. No workload uses them.

Required inputs: `name_prefix`, `availability_zones` and ownership `tags`.
Optional inputs: `enabled`, `vpc_cidr`, `enable_public_edge`. Outputs expose the
VPC ID, ordered private subnet IDs and resource-derived `policy_contract`.
The foundation root tests both network profiles with `mock_provider "aws"`.
No connectivity, region availability or cloud deployment is verified.
