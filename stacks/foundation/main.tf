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

module "network" {
  source             = "../../modules/network"
  enabled            = var.enable
  name_prefix        = var.name_prefix
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  enable_public_edge = var.enable_public_edge
  tags               = local.tags
}

module "private_compute" {
  source      = "../../modules/private-compute"
  enabled     = var.enable
  name_prefix = var.name_prefix
  ami_id      = var.ami_id
  vpc_id      = module.network.vpc_id
  subnet_id   = try(module.network.private_subnet_ids[0], null)
  vpc_cidr    = var.vpc_cidr
  tags        = local.tags
}
