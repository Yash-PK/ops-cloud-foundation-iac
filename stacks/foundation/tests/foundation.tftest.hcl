# Synthetic fixtures only. No provider API, AMI lookup, apply or refresh occurs.
mock_provider "aws" {
  mock_resource "aws_vpc" {
    defaults = { id = "vpc-00000000000000000" }
  }
  mock_resource "aws_subnet" {
    defaults = { id = "subnet-00000000000000000" }
  }
  mock_resource "aws_security_group" {
    defaults = { id = "sg-00000000000000000" }
  }
}

run "disabled_by_default" {
  command = plan
  plan_options { refresh = false }
  assert {
    condition     = output.resource_count == 0
    error_message = "Default configuration must contain zero managed resources."
  }
}

run "edge_cannot_bypass_disabled_stack" {
  command = plan
  plan_options { refresh = false }
  variables { enable_public_edge = true }
  assert {
    condition     = output.resource_count == 0
    error_message = "Selecting an edge profile must not bypass the disabled stack."
  }
}

run "private_foundation" {
  command = plan
  plan_options { refresh = false }
  variables {
    enable = true
    ami_id = "ami-00000000000000000" # Synthetic, not a usable image recommendation.
  }
  assert {
    condition     = output.resource_count == 11 && output.policy_contract.network.resource_count == 7 && output.policy_contract.private_compute.resource_count == 4
    error_message = "Private fixture must contain seven network and four compute/IAM resources."
  }
  assert {
    condition     = output.policy_contract.network.private_subnet_cidrs == ["10.42.0.0/18", "10.42.64.0/18"] && output.policy_contract.network.private_azs == ["us-east-1a", "us-east-1b"]
    error_message = "Subnets must be deterministic, non-overlapping and in the two explicit AZs."
  }
  assert {
    condition     = alltrue([for enabled in output.policy_contract.network.private_public_ips : !enabled]) && output.policy_contract.network.internet_gateways == 0 && alltrue([for count in output.policy_contract.network.private_route_counts : count == 0])
    error_message = "Private network must have no public addresses, IGW or managed routes."
  }
  assert {
    condition     = !output.policy_contract.private_compute.instances[0].associate_public_ip_address && output.policy_contract.private_compute.egress_count == 0
    error_message = "Compute must have no public IP or outbound security-group rules."
  }
  assert {
    condition     = output.policy_contract.private_compute.instances[0].metadata_options[0].http_tokens == "required" && output.policy_contract.private_compute.instances[0].metadata_options[0].http_put_response_hop_limit == 1 && output.policy_contract.private_compute.instances[0].metadata_options[0].instance_metadata_tags == "disabled"
    error_message = "Require IMDSv2, one response hop and no metadata tags."
  }
  assert {
    condition     = output.policy_contract.private_compute.instances[0].root_block_device[0].encrypted && output.policy_contract.private_compute.instances[0].root_block_device[0].volume_type == "gp3" && output.policy_contract.private_compute.instances[0].root_block_device[0].volume_size == 8
    error_message = "The root disk must be encrypted gp3 with bounded size."
  }
  assert {
    condition     = length(output.policy_contract.private_compute.ingress) == 1 && output.policy_contract.private_compute.ingress[0].cidr_blocks == tolist(["10.42.0.0/16"]) && output.policy_contract.private_compute.ingress[0].from_port == 8080 && output.policy_contract.private_compute.ingress[0].to_port == 8080 && output.policy_contract.private_compute.ingress[0].protocol == "tcp"
    error_message = "Only the private VPC CIDR may reach the reserved TCP health port."
  }
  assert {
    condition     = output.policy_contract.private_compute.role_trust[0].Statement[0].Principal.Service == "ec2.amazonaws.com" && output.policy_contract.private_compute.role_trust[0].Statement[0].Action == "sts:AssumeRole"
    error_message = "Only EC2 may assume the empty-permission instance role."
  }
  assert {
    condition     = strcontains(output.policy_contract.private_compute.user_data, "127.0.0.1") && strcontains(output.policy_contract.private_compute.user_data, "DynamicUser=yes") && !strcontains(output.policy_contract.private_compute.user_data, "apt-get") && !strcontains(output.policy_contract.private_compute.user_data, "curl ")
    error_message = "The deterministic health fixture must bind loopback and require no downloads."
  }
  assert {
    condition = alltrue([for labels in [output.policy_contract.network.tags[0], output.policy_contract.private_compute.instances[0].tags, output.policy_contract.private_compute.instances[0].volume_tags] :
      labels.Owner == "reference-lab" && labels.Environment == "lab" && labels.Project == "ops-cloud-foundation-iac" && labels.ManagedBy == "OpenTofu"
    ])
    error_message = "Required ownership tags must reach both compute and its disk."
  }
}

run "optional_edge_stays_separate" {
  command = plan
  plan_options { refresh = false }
  variables {
    enable             = true
    ami_id             = "ami-00000000000000000"
    enable_public_edge = true
  }
  assert {
    condition     = output.resource_count == 18 && output.policy_contract.network.internet_gateways == 1 && output.policy_contract.network.edge_subnet_cidrs == ["10.42.128.0/18", "10.42.192.0/18"] && output.policy_contract.network.edge_routes == ["0.0.0.0/0", "0.0.0.0/0"]
    error_message = "The explicit edge option must create two isolated edge subnets with IGW routes."
  }
  assert {
    condition     = alltrue([for count in output.policy_contract.network.private_route_counts : count == 0]) && alltrue([for enabled in output.policy_contract.network.edge_public_ips : !enabled]) && !output.policy_contract.private_compute.instances[0].associate_public_ip_address
    error_message = "Edge creation must not expose private compute or enable auto public addresses."
  }
}

run "small_private_cidr" {
  command = plan
  plan_options { refresh = false }
  variables {
    enable      = true
    ami_id      = "ami-00000000000000000"
    vpc_cidr    = "192.168.20.0/24"
    environment = "dev"
  }
  assert {
    condition     = output.policy_contract.network.private_subnet_cidrs == ["192.168.20.0/26", "192.168.20.64/26"] && output.policy_contract.network.tags[0].Environment == "dev"
    error_message = "Small private prefixes and dev tags must propagate correctly."
  }
}

run "reject_public_cidr" {
  command = plan
  plan_options { refresh = false }
  variables { vpc_cidr = "0.0.0.0/0" }
  expect_failures = [var.vpc_cidr]
}

run "reject_malformed_cidr" {
  command = plan
  plan_options { refresh = false }
  variables { vpc_cidr = "not-a-network" }
  expect_failures = [var.vpc_cidr]
}

run "reject_host_bits" {
  command = plan
  plan_options { refresh = false }
  variables { vpc_cidr = "10.42.0.1/16" }
  expect_failures = [var.vpc_cidr]
}

run "reject_too_small_cidr" {
  command = plan
  plan_options { refresh = false }
  variables { vpc_cidr = "10.42.0.0/28" }
  expect_failures = [var.vpc_cidr]
}

run "reject_duplicate_azs" {
  command = plan
  plan_options { refresh = false }
  variables { availability_zones = ["us-east-1a", "us-east-1a"] }
  expect_failures = [var.availability_zones]
}

run "reject_mixed_region_azs" {
  command = plan
  plan_options { refresh = false }
  variables { availability_zones = ["us-east-1a", "us-west-2b"] }
  expect_failures = [var.availability_zones]
}

run "reject_name" {
  command = plan
  plan_options { refresh = false }
  variables { name_prefix = "Bad Name!" }
  expect_failures = [var.name_prefix]
}

run "reject_empty_owner" {
  command = plan
  plan_options { refresh = false }
  variables { owner = " " }
  expect_failures = [var.owner]
}

run "reject_environment" {
  command = plan
  plan_options { refresh = false }
  variables { environment = "prod" }
  expect_failures = [var.environment]
}

run "reject_ami" {
  command = plan
  plan_options { refresh = false }
  variables {
    enable = true
    ami_id = "latest"
  }
  expect_failures = [var.ami_id]
}

run "reject_missing_ami" {
  command = plan
  plan_options { refresh = false }
  variables { enable = true }
  expect_failures = [var.ami_id]
}
