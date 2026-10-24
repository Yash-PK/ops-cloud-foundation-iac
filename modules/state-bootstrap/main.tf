locals {
  state_key    = "${var.environment}/foundation/terraform.tfstate"
  lock_key     = "${local.state_key}.tflock"
  bucket_arn   = var.enabled ? "arn:aws:s3:::${var.bucket_name}" : null
  admin_arn    = var.enabled ? "arn:aws:iam::${var.account_id}:role/${var.key_admin_role_name}" : null
  operator_arn = var.enabled ? "arn:aws:iam::${var.account_id}:role/${var.state_operator_role_name}" : null
  s3_kms_condition = var.enabled ? {
    StringEquals = {
      "kms:ViaService"                   = "s3.${var.region}.amazonaws.com"
      "kms:EncryptionContext:aws:s3:arn" = local.bucket_arn
    }
  } : null
}

resource "aws_kms_key" "state" {
  count                   = var.enabled ? 1 : 0
  description             = "State encryption for ${var.name_prefix} ${var.environment}"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "NamedKeyAdministrator"
        Effect    = "Allow"
        Principal = { AWS = local.admin_arn }
        Action = [
          "kms:DescribeKey", "kms:GetKeyPolicy", "kms:PutKeyPolicy",
          "kms:EnableKeyRotation", "kms:GetKeyRotationStatus",
          "kms:ListResourceTags", "kms:TagResource", "kms:UntagResource",
          "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion", "kms:UpdateKeyDescription"
        ]
        # In a KMS key policy '*' means this attached key, not every account key.
        Resource = "*"
      },
      {
        Sid       = "StateOperatorThroughThisBucket"
        Effect    = "Allow"
        Principal = { AWS = local.operator_arn }
        Action    = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"]
        Resource  = "*"
        Condition = local.s3_kms_condition
      }
    ]
  })
  tags = merge(var.tags, { Name = "${var.name_prefix}-${var.environment}-state" })
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket" "state" {
  count         = var.enabled ? 1 : 0
  bucket        = var.bucket_name
  force_destroy = false
  tags          = merge(var.tags, { Name = "${var.name_prefix}-${var.environment}-state" })
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  count                   = var.enabled ? 1 : 0
  bucket                  = aws_s3_bucket.state[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "state" {
  count  = var.enabled ? 1 : 0
  bucket = aws_s3_bucket.state[0].id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "state" {
  count  = var.enabled ? 1 : 0
  bucket = aws_s3_bucket.state[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  count  = var.enabled ? 1 : 0
  bucket = aws_s3_bucket.state[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.state[0].arn
    }
    bucket_key_enabled       = true
    blocked_encryption_types = ["SSE-C"]
  }
}

resource "aws_s3_bucket_policy" "state" {
  count  = var.enabled ? 1 : 0
  bucket = aws_s3_bucket.state[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [local.bucket_arn, "${local.bucket_arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "DenyIncorrectEncryptionAlgorithm"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${local.bucket_arn}/*"
        Condition = { StringNotEquals = { "s3:x-amz-server-side-encryption" = "aws:kms" } }
      },
      {
        Sid       = "DenyIncorrectEncryptionKey"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${local.bucket_arn}/*"
        Condition = { StringNotEquals = { "s3:x-amz-server-side-encryption-aws-kms-key-id" = aws_kms_key.state[0].arn } }
      }
    ]
  })
  depends_on = [aws_s3_bucket_public_access_block.state]
}

resource "aws_iam_role_policy" "state_operator" {
  count = var.enabled ? 1 : 0
  name  = "${var.name_prefix}-${var.environment}-state"
  role  = var.state_operator_role_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "ListOnlyEnvironmentKeys"
        Effect    = "Allow"
        Action    = ["s3:ListBucket"]
        Resource  = local.bucket_arn
        Condition = { StringEquals = { "s3:prefix" = [local.state_key, local.lock_key] } }
      },
      {
        Sid      = "ReadWriteEnvironmentState"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${local.bucket_arn}/${local.state_key}"
      },
      {
        Sid      = "NativeS3StateLock"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${local.bucket_arn}/${local.lock_key}"
      },
      {
        Sid       = "UseStateEncryptionKeyThroughS3"
        Effect    = "Allow"
        Action    = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"]
        Resource  = aws_kms_key.state[0].arn
        Condition = local.s3_kms_condition
      }
    ]
  })
}
