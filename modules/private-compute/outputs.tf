output "instance_id" {
  description = "Instance ID or null when disabled."
  value       = try(aws_instance.this[0].id, null)
}

output "policy_contract" {
  description = "Security-relevant resource configuration; cloud boot and reachability remain unverified."
  value = {
    resource_count = length(aws_security_group.health) + length(aws_iam_role.instance) + length(aws_iam_instance_profile.this) + length(aws_instance.this)
    instances = [for instance in aws_instance.this : {
      ami_id                      = instance.ami
      associate_public_ip_address = instance.associate_public_ip_address
      metadata_options            = instance.metadata_options
      root_block_device           = instance.root_block_device
      tags                        = instance.tags
      volume_tags                 = instance.volume_tags
      user_data_replace_on_change = instance.user_data_replace_on_change
    }]
    ingress      = flatten([for group in aws_security_group.health : [for rule in group.ingress : { cidr_blocks = rule.cidr_blocks, from_port = rule.from_port, to_port = rule.to_port, protocol = rule.protocol }]])
    egress_count = sum(concat([0], [for group in aws_security_group.health : length(group.egress)]))
    role_trust   = [for role in aws_iam_role.instance : jsondecode(role.assume_role_policy)]
    user_data    = var.enabled ? file("${path.module}/templates/cloud-init.yaml") : null
  }
}
