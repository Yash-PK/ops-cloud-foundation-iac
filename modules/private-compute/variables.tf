variable "enabled" {
  description = "Create resources only when explicitly enabled; repository execution remains mock-only."
  type        = bool
  default     = false
}

variable "name_prefix" {
  description = "Lowercase resource-name prefix, 3 to 32 characters."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}[a-z0-9]$", var.name_prefix))
    error_message = "Use 3-32 lowercase letters, digits or hyphens; begin with a letter and end with a letter or digit."
  }
}

variable "ami_id" {
  description = "Explicit reviewed x86_64 Linux AMI with Python 3, cloud-init and systemd preinstalled. Null while disabled; mock AMIs are fixtures only."
  type        = string
  default     = null
  validation {
    condition     = !var.enabled || can(regex("^ami-[0-9a-f]{17}$", var.ami_id))
    error_message = "An explicitly selected long-format AMI ID is required when enabled. No AMI is discovered."
  }
}

variable "vpc_id" {
  description = "VPC ID supplied by the network module."
  type        = string
  default     = null
  validation {
    condition     = !var.enabled || can(regex("^vpc-([0-9a-f]{8}|[0-9a-f]{17})$", var.vpc_id))
    error_message = "Enabled compute requires an explicit VPC ID."
  }
}

variable "subnet_id" {
  description = "Private subnet ID supplied by the network module."
  type        = string
  default     = null
  validation {
    condition     = !var.enabled || can(regex("^subnet-([0-9a-f]{8}|[0-9a-f]{17})$", var.subnet_id))
    error_message = "Enabled compute requires an explicit private subnet ID."
  }
}

variable "vpc_cidr" {
  description = "Canonical RFC1918 VPC CIDR; the only allowed source range for the health port."
  type        = string
  validation {
    condition = can(cidrnetmask(var.vpc_cidr)) && try(
      tonumber(split("/", var.vpc_cidr)[1]) >= 16 &&
      tonumber(split("/", var.vpc_cidr)[1]) <= 24 &&
      cidrhost(var.vpc_cidr, 0) == split("/", var.vpc_cidr)[0] &&
      can(regex("^(10\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.|192\\.168\\.)", cidrhost(var.vpc_cidr, 0))),
      false
    )
    error_message = "The health source must be the canonical private RFC1918 VPC CIDR with prefix /16 through /24."
  }
}

variable "tags" {
  description = "Required ownership labels."
  type        = map(string)
  validation {
    condition = alltrue([
      for key in ["Owner", "Environment", "Project", "ManagedBy"] : try(length(trimspace(var.tags[key])) > 0, false)
    ]) && try(contains(["lab", "dev"], var.tags["Environment"]) && var.tags["ManagedBy"] == "OpenTofu", false)
    error_message = "Tags must include nonempty Owner, Project, Environment (lab/dev) and ManagedBy (OpenTofu)."
  }
}
