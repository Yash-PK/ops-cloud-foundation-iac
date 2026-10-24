resource "aws_security_group" "health" {
  count       = var.enabled ? 1 : 0
  name        = "${var.name_prefix}-health"
  description = "Scoped private health port; no outbound connections"
  vpc_id      = var.vpc_id

  ingress {
    description = "Reserved private health access; the fixture currently binds loopback only"
    protocol    = "tcp"
    from_port   = 8080
    to_port     = 8080
    cidr_blocks = [var.vpc_cidr]
  }
  egress = []
  tags   = merge(var.tags, { Name = "${var.name_prefix}-health" })
}

resource "aws_iam_role" "instance" {
  count = var.enabled ? 1 : 0
  name  = "${var.name_prefix}-instance"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
  # No workload API access is needed by the offline health fixture.
  # There are intentionally no managed-policy attachments or inline policies.
  tags = merge(var.tags, { Name = "${var.name_prefix}-instance" })
}

resource "aws_iam_instance_profile" "this" {
  count = var.enabled ? 1 : 0
  name  = "${var.name_prefix}-instance"
  role  = aws_iam_role.instance[0].name
  tags  = merge(var.tags, { Name = "${var.name_prefix}-instance" })
}

resource "aws_instance" "this" {
  count                       = var.enabled ? 1 : 0
  ami                         = var.ami_id
  instance_type               = "t3.micro"
  subnet_id                   = var.subnet_id
  associate_public_ip_address = false
  vpc_security_group_ids      = [aws_security_group.health[0].id]
  iam_instance_profile        = aws_iam_instance_profile.this[0].name
  monitoring                  = false
  user_data                   = file("${path.module}/templates/cloud-init.yaml")
  user_data_replace_on_change = true

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }
  root_block_device {
    encrypted             = true
    volume_type           = "gp3"
    volume_size           = 8
    delete_on_termination = true
  }
  credit_specification {
    cpu_credits = "standard"
  }
  tags        = merge(var.tags, { Name = "${var.name_prefix}-health" })
  volume_tags = merge(var.tags, { Name = "${var.name_prefix}-health-root" })
}
