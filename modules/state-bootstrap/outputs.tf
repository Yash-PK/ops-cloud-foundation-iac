output "backend_configuration" {
  description = "Future reviewed backend coordinates only. Current root backend stays local; emitting this does not migrate state."
  value = var.enabled ? {
    bucket       = aws_s3_bucket.state[0].bucket
    key          = local.state_key
    region       = var.region
    encrypt      = true
    kms_key_id   = aws_kms_key.state[0].arn
    use_lockfile = true
  } : null
}

output "policy_contract" {
  description = "Security-relevant resource configuration exposed for native mock assertions."
  value = {
    resource_count = length(aws_kms_key.state) + length(aws_s3_bucket.state) + length(aws_s3_bucket_public_access_block.state) + length(aws_s3_bucket_ownership_controls.state) + length(aws_s3_bucket_versioning.state) + length(aws_s3_bucket_server_side_encryption_configuration.state) + length(aws_s3_bucket_policy.state) + length(aws_iam_role_policy.state_operator)
    state_key      = local.state_key
    lock_key       = local.lock_key
    bucket_names   = [for bucket in aws_s3_bucket.state : bucket.bucket]
    force_destroy  = [for bucket in aws_s3_bucket.state : bucket.force_destroy]
    public_access_blocks = [for block in aws_s3_bucket_public_access_block.state : {
      block_public_acls       = block.block_public_acls
      block_public_policy     = block.block_public_policy
      ignore_public_acls      = block.ignore_public_acls
      restrict_public_buckets = block.restrict_public_buckets
    }]
    ownership  = [for ownership in aws_s3_bucket_ownership_controls.state : one(ownership.rule).object_ownership]
    versioning = [for versioning in aws_s3_bucket_versioning.state : one(versioning.versioning_configuration).status]
    encryption = [for encryption in aws_s3_bucket_server_side_encryption_configuration.state : {
      algorithm                = one(one(encryption.rule).apply_server_side_encryption_by_default).sse_algorithm
      kms_key_id               = one(one(encryption.rule).apply_server_side_encryption_by_default).kms_master_key_id
      bucket_key_enabled       = one(encryption.rule).bucket_key_enabled
      blocked_encryption_types = one(encryption.rule).blocked_encryption_types
    }]
    kms_keys = [for key in aws_kms_key.state : {
      enable_key_rotation     = key.enable_key_rotation
      deletion_window_in_days = key.deletion_window_in_days
      policy                  = jsondecode(key.policy)
    }]
    bucket_policies   = [for policy in aws_s3_bucket_policy.state : jsondecode(policy.policy)]
    operator_policies = [for policy in aws_iam_role_policy.state_operator : jsondecode(policy.policy)]
    tags              = [for bucket in aws_s3_bucket.state : bucket.tags]
  }
}
