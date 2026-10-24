output "vpc_id" {
  description = "VPC ID or null when disabled."
  value       = try(aws_vpc.this[0].id, null)
}

output "private_subnet_ids" {
  description = "Private subnet IDs in explicit AZ order."
  value       = [for key in sort(keys(aws_subnet.private)) : aws_subnet.private[key].id]
}

output "policy_contract" {
  description = "Security-relevant resource configuration exposed for native mock assertions."
  value = {
    resource_count       = length(aws_vpc.this) + length(aws_subnet.private) + length(aws_route_table.private) + length(aws_route_table_association.private) + length(aws_internet_gateway.edge) + length(aws_subnet.edge) + length(aws_route_table.edge) + length(aws_route_table_association.edge)
    vpc_cidrs            = [for vpc in aws_vpc.this : vpc.cidr_block]
    private_subnet_cidrs = [for subnet in aws_subnet.private : subnet.cidr_block]
    private_azs          = [for subnet in aws_subnet.private : subnet.availability_zone]
    private_public_ips   = [for subnet in aws_subnet.private : subnet.map_public_ip_on_launch]
    private_route_counts = [for table in aws_route_table.private : length(table.route)]
    edge_subnet_cidrs    = [for subnet in aws_subnet.edge : subnet.cidr_block]
    edge_public_ips      = [for subnet in aws_subnet.edge : subnet.map_public_ip_on_launch]
    edge_routes          = flatten([for table in aws_route_table.edge : [for route in table.route : route.cidr_block]])
    internet_gateways    = length(aws_internet_gateway.edge)
    tags                 = [for vpc in aws_vpc.this : vpc.tags]
  }
}
