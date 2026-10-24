variable "enable" {
  description = "Disabled by default. Only mocked plans may enable resources in this repository."
  type        = bool
  default     = false
}

variable "name_prefix" {
  description = "Lowercase resource-name prefix, 3 to 32 characters."
  type        = string
  default     = "foundation-lab"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}[a-z0-9]$", var.name_prefix))
    error_message = "Use 3-32 lowercase letters, digits or hyphens; begin with a letter and end with a letter or digit."
  }
}

variable "owner" {
  description = "Owner tag for all taggable resources."
  type        = string
  default     = "reference-lab"
  validation {
    condition     = length(trimspace(var.owner)) > 0 && length(var.owner) <= 64
    error_message = "Owner must be a nonempty label of at most 64 characters."
  }
}

variable "project" {
  description = "Project tag for all taggable resources."
  type        = string
  default     = "ops-cloud-foundation-iac"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,62}[a-z0-9]$", var.project))
    error_message = "Project must be a 3-64 character lowercase project label."
  }
}

variable "environment" {
  description = "Each environment uses its own state and .tflock key."
  type        = string
  default     = "lab"
  validation {
    condition     = contains(["lab", "dev"], var.environment)
    error_message = "Environment must be lab or dev."
  }
}

variable "region" {
  description = "Explicit AWS commercial-partition region; no region lookup."
  type        = string
  default     = "us-east-1"
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[1-9]$", var.region)) && !startswith(var.region, "cn-")
    error_message = "Use a standard commercial-partition region name."
  }
}

variable "vpc_cidr" {
  description = "Canonical RFC1918 IPv4 network with prefix /16 through /24. Four non-overlapping subnets are derived."
  type        = string
  default     = "10.42.0.0/16"
  validation {
    condition = can(cidrnetmask(var.vpc_cidr)) && try(
      tonumber(split("/", var.vpc_cidr)[1]) >= 16 &&
      tonumber(split("/", var.vpc_cidr)[1]) <= 24 &&
      cidrhost(var.vpc_cidr, 0) == split("/", var.vpc_cidr)[0] &&
      can(regex("^(10\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.|192\\.168\\.)", cidrhost(var.vpc_cidr, 0))),
      false
    )
    error_message = "Use a canonical private IPv4 RFC1918 CIDR with prefix /16 through /24."
  }
}

variable "availability_zones" {
  description = "Exactly two explicit distinct standard availability-zone names; no discovery API is used."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
  validation {
    condition = length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2 && alltrue([
      for az in var.availability_zones : can(regex("^[a-z]{2}-[a-z]+-[1-9][a-z]$", az)) && startswith(az, var.region)
    ])
    error_message = "Provide exactly two distinct standard availability-zone names."
  }
}

variable "enable_public_edge" {
  description = "Optional isolated edge subnets and Internet Gateway; never adds a route to private route tables."
  type        = bool
  default     = false
}

variable "ami_id" {
  description = "Explicit reviewed x86_64 Linux AMI with Python 3, cloud-init and systemd preinstalled. Null while disabled; mock AMIs are fixtures only."
  type        = string
  default     = null
  validation {
    condition     = !var.enable || can(regex("^ami-[0-9a-f]{17}$", var.ami_id))
    error_message = "An explicitly selected long-format AMI ID is required when enabled. No AMI is discovered."
  }
}
