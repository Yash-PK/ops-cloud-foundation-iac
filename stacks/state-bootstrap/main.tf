locals {
  tags = {
    Owner       = var.owner
    Environment = var.environment
    Project     = var.project
    ManagedBy   = "OpenTofu"
  }
}

provider "aws" {
  region = var.region
}

module "state_bootstrap" {
  source                   = "../../modules/state-bootstrap"
  enabled                  = var.enable
  name_prefix              = var.name_prefix
  bucket_name              = var.bucket_name
  account_id               = var.account_id
  key_admin_role_name      = var.key_admin_role_name
  state_operator_role_name = var.state_operator_role_name
  environment              = var.environment
  region                   = var.region
  tags                     = local.tags
}
