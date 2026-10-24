# All identities and names below are synthetic mock fixtures, not existing AWS resources.
mock_provider "aws" {
  mock_resource "aws_kms_key" {
    defaults = {
      arn = "arn:aws:kms:us-east-1:000000000000:key/00000000-0000-0000-0000-000000000000"
    }
  }
  mock_resource "aws_s3_bucket" {
    defaults = { id = "mock-foundation-state-000000000000" }
  }
}

run "disabled_by_default" {
  command = plan
  plan_options { refresh = false }
  assert {
    condition     = output.resource_count == 0 && output.backend_configuration == null
    error_message = "Default configuration must contain zero resources and no remote backend coordinates."
  }
}

run "secure_lab_state" {
  command = plan
  plan_options { refresh = false }
  variables {
    enable                   = true
    bucket_name              = "mock-foundation-state-000000000000"
    account_id               = "000000000000"
    key_admin_role_name      = "mock-state-admin"
    state_operator_role_name = "mock-state-operator"
  }
  assert {
    condition     = output.resource_count == 8 && !output.policy_contract.force_destroy[0] && output.policy_contract.ownership[0] == "BucketOwnerEnforced"
    error_message = "The state fixture must create eight resources and retain nonempty private buckets."
  }
  assert {
    condition     = alltrue(values(output.policy_contract.public_access_blocks[0])) && output.policy_contract.versioning[0] == "Enabled"
    error_message = "Block every form of S3 public access and enable versioning."
  }
  assert {
    condition     = output.policy_contract.encryption[0].algorithm == "aws:kms" && output.policy_contract.encryption[0].kms_key_id == output.backend_configuration.kms_key_id && output.policy_contract.encryption[0].bucket_key_enabled && contains(output.policy_contract.encryption[0].blocked_encryption_types, "SSE-C") && output.policy_contract.kms_keys[0].enable_key_rotation && output.policy_contract.kms_keys[0].deletion_window_in_days == 30
    error_message = "State must use SSE-KMS, rotation, blocked SSE-C and a 30-day deletion window."
  }
  assert {
    condition     = output.backend_configuration.use_lockfile && output.backend_configuration.encrypt && output.backend_configuration.key == "lab/foundation/terraform.tfstate" && output.policy_contract.lock_key == "lab/foundation/terraform.tfstate.tflock"
    error_message = "Use environment-scoped native S3 locks beside encrypted state."
  }
  assert {
    condition     = output.policy_contract.bucket_policies[0].Statement[0].Effect == "Deny" && output.policy_contract.bucket_policies[0].Statement[0].Condition.Bool["aws:SecureTransport"] == "false" && output.policy_contract.bucket_policies[0].Statement[0].Principal == "*"
    error_message = "Bucket policy must deny insecure transport for every principal."
  }
  assert {
    condition     = output.policy_contract.bucket_policies[0].Statement[1].Effect == "Deny" && output.policy_contract.bucket_policies[0].Statement[1].Principal == "*" && output.policy_contract.bucket_policies[0].Statement[1].Action == "s3:PutObject" && output.policy_contract.bucket_policies[0].Statement[1].Resource == "arn:aws:s3:::mock-foundation-state-000000000000/*" && output.policy_contract.bucket_policies[0].Statement[1].Condition.StringNotEquals["s3:x-amz-server-side-encryption"] == "aws:kms"
    error_message = "Uploads must explicitly use SSE-KMS; bucket defaults alone can be overridden."
  }
  assert {
    condition     = output.policy_contract.bucket_policies[0].Statement[2].Effect == "Deny" && output.policy_contract.bucket_policies[0].Statement[2].Principal == "*" && output.policy_contract.bucket_policies[0].Statement[2].Action == "s3:PutObject" && output.policy_contract.bucket_policies[0].Statement[2].Resource == "arn:aws:s3:::mock-foundation-state-000000000000/*" && output.policy_contract.bucket_policies[0].Statement[2].Condition.StringNotEquals["s3:x-amz-server-side-encryption-aws-kms-key-id"] == output.backend_configuration.kms_key_id
    error_message = "Uploads must explicitly name this state key ARN; an alternate or absent key must be denied."
  }
  assert {
    condition     = output.policy_contract.operator_policies[0].Statement[0].Condition.StringEquals["s3:prefix"] == ["lab/foundation/terraform.tfstate", "lab/foundation/terraform.tfstate.tflock"] && output.policy_contract.operator_policies[0].Statement[1].Resource == "arn:aws:s3:::mock-foundation-state-000000000000/lab/foundation/terraform.tfstate" && output.policy_contract.operator_policies[0].Statement[2].Resource == "arn:aws:s3:::mock-foundation-state-000000000000/lab/foundation/terraform.tfstate.tflock"
    error_message = "S3 permissions must target only this environment's state and lock keys."
  }
  assert {
    condition     = alltrue(flatten([for statement in output.policy_contract.operator_policies[0].Statement : [for action in statement.Action : !strcontains(action, "*")]])) && alltrue([for statement in output.policy_contract.operator_policies[0].Statement : !strcontains(statement.Resource, "*")])
    error_message = "Identity policy must contain no wildcard actions or resources."
  }
  assert {
    condition     = !contains(output.policy_contract.operator_policies[0].Statement[1].Action, "s3:DeleteObject") && contains(output.policy_contract.operator_policies[0].Statement[2].Action, "s3:DeleteObject")
    error_message = "The operator may remove its lock, but must not delete state objects."
  }
  assert {
    condition     = output.policy_contract.operator_policies[0].Statement[3].Resource == "arn:aws:kms:us-east-1:000000000000:key/00000000-0000-0000-0000-000000000000" && output.policy_contract.operator_policies[0].Statement[3].Condition.StringEquals["kms:ViaService"] == "s3.us-east-1.amazonaws.com" && output.policy_contract.operator_policies[0].Statement[3].Condition.StringEquals["kms:EncryptionContext:aws:s3:arn"] == "arn:aws:s3:::mock-foundation-state-000000000000"
    error_message = "KMS identity permission must use this exact key through this S3 bucket."
  }
  assert {
    condition     = output.policy_contract.kms_keys[0].policy.Statement[0].Principal.AWS == "arn:aws:iam::000000000000:role/mock-state-admin" && output.policy_contract.kms_keys[0].policy.Statement[1].Principal.AWS == "arn:aws:iam::000000000000:role/mock-state-operator"
    error_message = "KMS policies must name explicit administrator and operator roles."
  }
  assert {
    condition     = output.policy_contract.kms_keys[0].policy.Statement[1].Condition.StringEquals["kms:ViaService"] == "s3.us-east-1.amazonaws.com" && output.policy_contract.kms_keys[0].policy.Statement[1].Condition.StringEquals["kms:EncryptionContext:aws:s3:arn"] == "arn:aws:s3:::mock-foundation-state-000000000000" && alltrue(flatten([for statement in output.policy_contract.kms_keys[0].policy.Statement : [for action in statement.Action : !strcontains(action, "*")]]))
    error_message = "The direct key-policy grant must retain S3/bucket restrictions and enumerate actions."
  }
  assert {
    condition     = output.policy_contract.tags[0].Owner == "reference-lab" && output.policy_contract.tags[0].Environment == "lab" && output.policy_contract.tags[0].Project == "ops-cloud-foundation-iac" && output.policy_contract.tags[0].ManagedBy == "OpenTofu"
    error_message = "State storage must carry all ownership tags."
  }
}

run "dev_has_distinct_keys" {
  command = plan
  plan_options { refresh = false }
  variables {
    enable                   = true
    bucket_name              = "mock-foundation-state-000000000000"
    account_id               = "000000000000"
    key_admin_role_name      = "mock-state-admin"
    state_operator_role_name = "mock-state-operator"
    environment              = "dev"
  }
  assert {
    condition     = output.backend_configuration.key == "dev/foundation/terraform.tfstate" && output.policy_contract.lock_key == "dev/foundation/terraform.tfstate.tflock" && output.policy_contract.operator_policies[0].Statement[1].Resource == "arn:aws:s3:::mock-foundation-state-000000000000/dev/foundation/terraform.tfstate"
    error_message = "Dev must never share lab's state or lock key."
  }
}

run "reject_account" {
  command = plan
  plan_options { refresh = false }
  variables {
    enable                   = true
    bucket_name              = "mock-foundation-state-000000000000"
    account_id               = "not-an-account"
    key_admin_role_name      = "mock-state-admin"
    state_operator_role_name = "mock-state-operator"
  }
  expect_failures = [var.account_id]
}

run "reject_bucket_name" {
  command = plan
  plan_options { refresh = false }
  variables {
    enable                   = true
    bucket_name              = "Public Bad Bucket!"
    account_id               = "000000000000"
    key_admin_role_name      = "mock-state-admin"
    state_operator_role_name = "mock-state-operator"
  }
  expect_failures = [var.bucket_name]
}

run "reject_wildcard_role" {
  command = plan
  plan_options { refresh = false }
  variables {
    enable                   = true
    bucket_name              = "mock-foundation-state-000000000000"
    account_id               = "000000000000"
    key_admin_role_name      = "mock-state-admin"
    state_operator_role_name = "*"
  }
  expect_failures = [var.state_operator_role_name]
}

run "reject_environment" {
  command = plan
  plan_options { refresh = false }
  variables { environment = "prod" }
  expect_failures = [var.environment]
}
