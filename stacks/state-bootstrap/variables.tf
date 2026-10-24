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

variable "bucket_name" {
  description = "Explicit globally unique bucket name, supplied only for a separately reviewed deployment; no bucket is discovered."
  type        = string
  default     = null
  validation {
    condition = !var.enable || (can(regex("^[a-z][a-z0-9-]{1,61}[a-z0-9]$", var.bucket_name)) &&
    !can(regex("^(xn--|sthree-|amzn-s3-demo-)|(-s3alias|--ol-s3|\\.mrap|--x-s3|--table-s3)$", var.bucket_name)))
    error_message = "When enabled supply a 3-63 character lowercase S3 bucket name without dots or reserved prefixes/suffixes."
  }
}

variable "account_id" {
  description = "Explicit target account ID; no caller-identity query. Test values are synthetic fixtures."
  type        = string
  default     = null
  validation {
    condition     = !var.enable || can(regex("^[0-9]{12}$", var.account_id))
    error_message = "An explicit 12-digit account ID is required when enabled."
  }
}

variable "key_admin_role_name" {
  description = "Existing IAM role name responsible for the key lifecycle; no wildcard or path."
  type        = string
  default     = null
  validation {
    condition     = !var.enable || can(regex("^[A-Za-z0-9_+=,.@-]{1,64}$", var.key_admin_role_name))
    error_message = "Supply an explicit existing IAM key-administrator role name when enabled."
  }
}

variable "state_operator_role_name" {
  description = "Existing IAM role name receiving a policy limited to this environment's state and lock."
  type        = string
  default     = null
  validation {
    condition     = !var.enable || can(regex("^[A-Za-z0-9_+=,.@-]{1,64}$", var.state_operator_role_name))
    error_message = "Supply an explicit existing IAM state-operator role name when enabled."
  }
}
