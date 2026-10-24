variable "enabled" {
  description = "Create resources only when explicitly enabled. Repository tasks permit mocked plans only."
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
  validation {
    condition = length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2 && alltrue([
      for az in var.availability_zones : can(regex("^[a-z]{2}-[a-z]+-[1-9][a-z]$", az))
    ]) && try(length(distinct([for az in var.availability_zones : substr(az, 0, length(az) - 1)])) == 1, false)
    error_message = "Provide exactly two distinct standard availability-zone names in one region."
  }
}

variable "enable_public_edge" {
  description = "Optional isolated edge subnets and Internet Gateway; never adds a route to private route tables."
  type        = bool
  default     = false
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
