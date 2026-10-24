locals {
  private_subnets = var.enabled ? {
    for index, zone in var.availability_zones : tostring(index) => {
      zone = zone
      cidr = cidrsubnet(var.vpc_cidr, 2, index)
    }
  } : {}
  edge_subnets = var.enabled && var.enable_public_edge ? {
    for index, zone in var.availability_zones : tostring(index) => {
      zone = zone
      cidr = cidrsubnet(var.vpc_cidr, 2, index + 2)
    }
  } : {}
}

resource "aws_vpc" "this" {
  count                = var.enabled ? 1 : 0
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(var.tags, { Name = "${var.name_prefix}-vpc" })
}

resource "aws_subnet" "private" {
  for_each                = local.private_subnets
  vpc_id                  = aws_vpc.this[0].id
  cidr_block              = each.value.cidr
  availability_zone       = each.value.zone
  map_public_ip_on_launch = false
  tags                    = merge(var.tags, { Name = "${var.name_prefix}-private-${each.key}", Tier = "private" })
}

resource "aws_route_table" "private" {
  for_each = local.private_subnets
  vpc_id   = aws_vpc.this[0].id
  # Explicitly manage no routes beyond the AWS implicit local VPC route.
  route = []
  tags  = merge(var.tags, { Name = "${var.name_prefix}-private-${each.key}", Tier = "private" })
}

resource "aws_route_table_association" "private" {
  for_each       = local.private_subnets
  subnet_id      = aws_subnet.private[each.key].id
  route_table_id = aws_route_table.private[each.key].id
}

resource "aws_internet_gateway" "edge" {
  count  = var.enabled && var.enable_public_edge ? 1 : 0
  vpc_id = aws_vpc.this[0].id
  tags   = merge(var.tags, { Name = "${var.name_prefix}-edge", Tier = "edge" })
}

resource "aws_subnet" "edge" {
  for_each                = local.edge_subnets
  vpc_id                  = aws_vpc.this[0].id
  cidr_block              = each.value.cidr
  availability_zone       = each.value.zone
  map_public_ip_on_launch = false
  tags                    = merge(var.tags, { Name = "${var.name_prefix}-edge-${each.key}", Tier = "edge" })
}

resource "aws_route_table" "edge" {
  for_each = local.edge_subnets
  vpc_id   = aws_vpc.this[0].id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.edge[0].id
  }
  tags = merge(var.tags, { Name = "${var.name_prefix}-edge-${each.key}", Tier = "edge" })
}

resource "aws_route_table_association" "edge" {
  for_each       = local.edge_subnets
  subnet_id      = aws_subnet.edge[each.key].id
  route_table_id = aws_route_table.edge[each.key].id
}
