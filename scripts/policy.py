"""Bounded policies over actual native mock-plan resource changes, never AWS proof."""

import copy
import ipaddress
import json
import re


class PolicyError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PolicyError(message)


def one(value):
    require(isinstance(value, list) and len(value) == 1, "Expected exactly one security block")
    return value[0]


def document(value):
    try:
        doc = json.loads(value)
    except (ValueError, TypeError) as error:
        raise PolicyError("Invalid IAM JSON document") from error
    require(isinstance(doc, dict), "IAM policy must be an object")
    require(doc.get("Version") == "2012-10-17", "Unsupported IAM policy version")
    statements = doc.get("Statement")
    require(isinstance(statements, list) and bool(statements), "Missing IAM statements")
    require(all(isinstance(item, dict) for item in statements), "Invalid IAM statement shape")
    return statements


def role_arn(value):
    return (
        isinstance(value, str)
        and re.fullmatch(r"arn:aws:iam::\d{12}:role/[A-Za-z0-9+=,.@_-]+", value) is not None
    )


def policies_for_state(items, variables):
    bucket = variables["bucket_name"]
    bucket_arn = "arn:aws:s3:::" + bucket
    key = variables["environment"] + "/foundation/terraform.tfstate"
    state_arn = bucket_arn + "/" + key
    lock_arn = state_arn + ".tflock"
    kms = one(items["aws_kms_key"])
    kms_arn = kms["arn"]
    require(
        re.fullmatch(r"arn:aws:kms:[a-z0-9-]+:\d{12}:key/[a-z0-9-]+", kms_arn) is not None,
        "Encryption key must be an exact KMS ARN",
    )
    require(
        kms.get("enable_key_rotation") is True and kms.get("deletion_window_in_days") == 30,
        "KMS rotation/deletion window",
    )
    require(
        kms.get("bypass_policy_lockout_safety_check") in (None, False),
        "KMS lockout safety must remain enabled",
    )
    key_statements = document(kms["policy"])
    require(len(key_statements) == 2, "Unexpected key policy statements")
    crypto = {"kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"}
    admins = {
        "kms:DescribeKey",
        "kms:GetKeyPolicy",
        "kms:PutKeyPolicy",
        "kms:EnableKeyRotation",
        "kms:GetKeyRotationStatus",
        "kms:ListResourceTags",
        "kms:TagResource",
        "kms:UntagResource",
        "kms:ScheduleKeyDeletion",
        "kms:CancelKeyDeletion",
        "kms:UpdateKeyDescription",
    }
    condition = {
        "StringEquals": {
            "kms:ViaService": "s3." + variables["region"] + ".amazonaws.com",
            "kms:EncryptionContext:aws:s3:arn": bucket_arn,
        }
    }
    for statement, role, actions in zip(
        key_statements,
        [variables["key_admin_role_name"], variables["state_operator_role_name"]],
        [admins, crypto],
        strict=True,
    ):
        expected = "arn:aws:iam::" + variables["account_id"] + ":role/" + role
        require(
            role_arn(expected) and statement.get("Principal") == {"AWS": expected},
            "Key policy requires the exact named role",
        )
        require(
            statement.get("Effect") == "Allow"
            and set(statement.get("Action", [])) == actions
            and statement.get("Resource") == "*",
            "Key-local IAM permissions exceeded",
        )
        require(
            set(statement) <= {"Sid", "Effect", "Principal", "Action", "Resource", "Condition"},
            "Unexpected IAM key policy element",
        )
    require(
        key_statements[1].get("Condition") == condition,
        "Key use must be limited to this S3 bucket",
    )
    operator = document(one(items["aws_iam_role_policy"])["policy"])
    require(len(operator) == 4, "Unexpected operator statements")
    expected = [
        (
            {"s3:ListBucket"},
            bucket_arn,
            {"StringEquals": {"s3:prefix": [key, key + ".tflock"]}},
        ),
        ({"s3:GetObject", "s3:PutObject"}, state_arn, None),
        ({"s3:GetObject", "s3:PutObject", "s3:DeleteObject"}, lock_arn, None),
        (crypto, kms_arn, condition),
    ]
    for statement, (actions, resource, conditions) in zip(operator, expected, strict=True):
        require(
            set(statement) <= {"Sid", "Effect", "Action", "Resource", "Condition"},
            "Unexpected operator IAM element",
        )
        require(
            statement.get("Effect") == "Allow" and set(statement.get("Action", [])) == actions,
            "Operator action scope exceeded",
        )
        require(
            statement.get("Resource") == resource and statement.get("Condition") == conditions,
            "Operator resource/condition scope exceeded",
        )
    policy = document(one(items["aws_s3_bucket_policy"])["policy"])
    require(len(policy) == 3, "TLS and exact KMS upload denies required")
    by_sid = {statement.get("Sid"): statement for statement in policy}
    require(
        set(by_sid)
        == {
            "DenyInsecureTransport",
            "DenyIncorrectEncryptionAlgorithm",
            "DenyIncorrectEncryptionKey",
        },
        "Unexpected bucket policy scope",
    )
    deny = by_sid["DenyInsecureTransport"]
    require(
        deny.get("Effect") == "Deny"
        and deny.get("Principal") == "*"
        and deny.get("Action") == "s3:*",
        "TLS deny policy required",
    )
    require(
        deny.get("Resource") == [bucket_arn, bucket_arn + "/*"]
        and deny.get("Condition") == {"Bool": {"aws:SecureTransport": "false"}},
        "TLS deny must cover only this bucket",
    )
    require(
        set(deny) <= {"Sid", "Effect", "Principal", "Action", "Resource", "Condition"},
        "Unexpected TLS deny condition",
    )
    for sid, header, value in [
        ("DenyIncorrectEncryptionAlgorithm", "s3:x-amz-server-side-encryption", "aws:kms"),
        (
            "DenyIncorrectEncryptionKey",
            "s3:x-amz-server-side-encryption-aws-kms-key-id",
            kms_arn,
        ),
    ]:
        statement = by_sid[sid]
        require(
            set(statement) == {"Sid", "Effect", "Principal", "Action", "Resource", "Condition"},
            "Unexpected encryption policy element",
        )
        require(
            statement["Effect"] == "Deny"
            and statement["Principal"] == "*"
            and statement["Action"] == "s3:PutObject"
            and statement["Resource"] == bucket_arn + "/*",
            "Exact encryption deny scope required",
        )
        require(
            statement["Condition"] == {"StringNotEquals": {header: value}},
            "Encryption headers must select the exact key/algorithm",
        )
    require(
        one(items["aws_s3_bucket"]).get("force_destroy") is False,
        "State bucket cannot force-delete data",
    )
    block = one(items["aws_s3_bucket_public_access_block"])
    require(
        all(
            block.get(k) is True
            for k in [
                "block_public_acls",
                "block_public_policy",
                "ignore_public_acls",
                "restrict_public_buckets",
            ]
        ),
        "All public-access protections required",
    )
    require(
        one(one(items["aws_s3_bucket_ownership_controls"])["rule"]).get("object_ownership")
        == "BucketOwnerEnforced",
        "ACLs must be disabled",
    )
    require(
        one(one(items["aws_s3_bucket_versioning"])["versioning_configuration"]).get("status")
        == "Enabled",
        "State versioning required",
    )
    rule = one(one(items["aws_s3_bucket_server_side_encryption_configuration"])["rule"])
    encryption = one(rule["apply_server_side_encryption_by_default"])
    require(
        encryption.get("sse_algorithm") == "aws:kms"
        and encryption.get("kms_master_key_id") == kms_arn,
        "Exact KMS encryption required",
    )
    require(
        rule.get("bucket_key_enabled") is True
        and rule.get("blocked_encryption_types") == ["SSE-C"],
        "Bucket key and SSE-C block required",
    )


def policies_for_foundation(items, variables, resources):
    vpc = ipaddress.ip_network(variables["vpc_cidr"])
    private = [
        ipaddress.ip_network(x) for x in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    ]
    require(any(vpc.subnet_of(network) for network in private), "VPC must be RFC1918")
    require(one(items["aws_vpc"]).get("cidr_block") == str(vpc), "VPC CIDR mismatch")
    subnets = [ipaddress.ip_network(x["cidr_block"]) for x in items["aws_subnet"]]
    require(all(s.subnet_of(vpc) for s in subnets), "Subnet outside VPC")
    require(
        all(not a.overlaps(b) for i, a in enumerate(subnets) for b in subnets[i + 1 :]),
        "Overlapping subnets",
    )
    require(
        all(s.get("map_public_ip_on_launch") is False for s in items["aws_subnet"]),
        "Automatic public IP prohibited",
    )
    route_tables = [resource for resource in resources if resource["type"] == "aws_route_table"]
    private_addresses = {f'module.network.aws_route_table.private["{i}"]' for i in range(2)}
    edge_addresses = {f'module.network.aws_route_table.edge["{i}"]' for i in range(2)}
    require(
        {resource["address"] for resource in route_tables}
        == private_addresses | (edge_addresses if variables["enable_public_edge"] else set()),
        "Only classified private/edge route tables are supported",
    )
    for resource in route_tables:
        after = resource["change"]["after"]
        if resource["address"] in private_addresses:
            require(
                after.get("route") == [] and after.get("tags", {}).get("Tier") == "private",
                "Private route table must stay isolated",
            )
        else:
            route = one(after.get("route"))
            require(
                route.get("cidr_block") == "0.0.0.0/0"
                and route.get("gateway_id") == one(items["aws_internet_gateway"])["id"]
                and after.get("tags", {}).get("Tier") == "edge",
                "Edge route must use only the managed Internet Gateway",
            )
    instance = one(items["aws_instance"])
    require(
        instance.get("associate_public_ip_address") is False, "Public instance IP prohibited"
    )
    require(instance.get("instance_type") == "t3.micro", "Bounded compute instance type")
    require(
        one(instance["metadata_options"]).get("http_tokens") == "required", "IMDSv2 required"
    )
    require(
        one(instance["metadata_options"]).get("http_put_response_hop_limit") == 1,
        "Metadata hop limit required",
    )
    disk = one(instance["root_block_device"])
    require(
        disk.get("encrypted") is True
        and disk.get("volume_type") == "gp3"
        and disk.get("volume_size") == 8,
        "Encrypted bounded gp3 root required",
    )
    group = one(items["aws_security_group"])
    require(group.get("egress") == [], "No outbound security-group access")
    ingress = one(group.get("ingress"))
    require(
        ingress.get("cidr_blocks") == [str(vpc)]
        and ingress.get("from_port") == ingress.get("to_port") == 8080
        and ingress.get("protocol") == "tcp",
        "Ingress must be exact VPC health port",
    )
    require(
        all(
            not ingress.get(k)
            for k in ["ipv6_cidr_blocks", "security_groups", "prefix_list_ids", "self"]
        ),
        "Additional ingress sources prohibited",
    )
    role = one(items["aws_iam_role"])
    profile = one(items["aws_iam_instance_profile"])
    require(
        not role.get("inline_policy") and not role.get("managed_policy_arns"),
        "Workload role must have no API permissions",
    )
    require(
        profile.get("role") == role.get("name")
        and instance.get("iam_instance_profile") == profile.get("name")
        and instance.get("vpc_security_group_ids") == [group.get("id")],
        "Compute must use exactly the managed profile, role and security group",
    )
    trust = one(document(role["assume_role_policy"]))
    require(set(trust) <= {"Sid", "Effect", "Principal", "Action"}, "Unexpected trust element")
    require(
        trust.get("Effect") == "Allow"
        and trust.get("Principal") == {"Service": "ec2.amazonaws.com"}
        and trust.get("Action") == "sts:AssumeRole",
        "Only EC2 may assume instance role",
    )


def check_plan(plan, stack):
    """Reject unknown/partial shapes and policies beyond this lab's bounded scope."""
    try:
        require(isinstance(plan, dict), "Plan must be a JSON object")
        require(stack in {"foundation", "state-bootstrap"}, "Unknown stack profile")
        require(plan.get("format_version") == "1.2", "Unreviewed plan JSON format")
        require(isinstance(plan.get("variables"), dict), "Invalid plan variables")
        variables = {key: value["value"] for key, value in plan["variables"].items()}
        enabled = variables["enable"]
        require(type(enabled) is bool, "Unknown enable flag")
        resources = plan.get("resource_changes", [])
        if not enabled:
            require(resources == [], "Disabled stack must contain no resource changes")
            return {"resources": 0, "profile": stack}
        expected = {
            "foundation": {
                "aws_vpc": 1,
                "aws_subnet": 2,
                "aws_route_table": 2,
                "aws_route_table_association": 2,
                "aws_instance": 1,
                "aws_security_group": 1,
                "aws_iam_role": 1,
                "aws_iam_instance_profile": 1,
            },
            "state-bootstrap": dict.fromkeys(
                [
                    "aws_s3_bucket",
                    "aws_s3_bucket_public_access_block",
                    "aws_s3_bucket_ownership_controls",
                    "aws_s3_bucket_versioning",
                    "aws_s3_bucket_server_side_encryption_configuration",
                    "aws_s3_bucket_policy",
                    "aws_kms_key",
                    "aws_iam_role_policy",
                ],
                1,
            ),
        }[stack]
        if stack == "foundation" and variables["enable_public_edge"]:
            expected.update(
                aws_subnet=4,
                aws_route_table=4,
                aws_route_table_association=4,
                aws_internet_gateway=1,
            )
        items = {}
        for resource in resources:
            require(
                resource.get("mode") == "managed"
                and resource.get("provider_name") == "registry.terraform.io/hashicorp/aws",
                "Unreviewed provider or resource mode",
            )
            require(
                resource["change"].get("actions") == ["create"],
                "Only mock creation plans are in scope",
            )
            after = resource["change"]["after"]
            require(isinstance(after, dict), "Missing planned values")
            items.setdefault(resource["type"], []).append(after)
            if "tags" in after:
                tags = after["tags"]
                require(
                    isinstance(tags, dict)
                    and all(
                        tags.get(key) == value
                        for key, value in {
                            "Environment": variables["environment"],
                            "Owner": variables["owner"],
                            "Project": variables["project"],
                            "ManagedBy": "OpenTofu",
                        }.items()
                    ),
                    "Required ownership tags missing",
                )
        require(
            {key: len(value) for key, value in items.items()} == expected,
            "Unexpected or missing resource types/counts",
        )
        if stack == "foundation":
            policies_for_foundation(items, variables, resources)
        else:
            policies_for_state(items, variables)
        return {"resources": len(resources), "profile": stack}
    except (KeyError, TypeError, IndexError, ValueError) as error:
        if isinstance(error, PolicyError):
            raise
        raise PolicyError("Malformed or incomplete mock plan") from error


def negative_controls(plan, stack):
    """Mutate a real accepted mock plan in memory; every unsafe change must fail."""
    check_plan(plan, stack)
    require(bool(plan.get("resource_changes")), "Mutations require an enabled accepted plan")
    cases = (
        [
            (
                "public_instance",
                "aws_instance",
                lambda x: x.update(associate_public_ip_address=True),
            ),
            (
                "unencrypted_disk",
                "aws_instance",
                lambda x: x["root_block_device"][0].update(encrypted=False),
            ),
            (
                "open_ingress",
                "aws_security_group",
                lambda x: x["ingress"][0].update(cidr_blocks=["0.0.0.0/0"]),
            ),
            (
                "metadata_v1",
                "aws_instance",
                lambda x: x["metadata_options"][0].update(http_tokens="optional"),
            ),
            (
                "privileged_role",
                "aws_iam_role",
                lambda x: x.update(
                    managed_policy_arns=["arn:aws:iam::aws:policy/AdministratorAccess"]
                ),
            ),
            (
                "foreign_profile",
                "aws_instance",
                lambda x: x.update(iam_instance_profile="unreviewed-profile"),
            ),
            (
                "foreign_security_group",
                "aws_instance",
                lambda x: x.update(vpc_security_group_ids=["sg-11111111111111111"]),
            ),
            (
                "private_default_route",
                "aws_route_table",
                lambda x: x.update(
                    route=[{"cidr_block": "0.0.0.0/0", "gateway_id": "unreviewed-gateway"}]
                ),
            ),
        ]
        if stack == "foundation"
        else [
            (
                "public_state",
                "aws_s3_bucket_public_access_block",
                lambda x: x.update(block_public_policy=False),
            ),
            (
                "unencrypted_state",
                "aws_s3_bucket_server_side_encryption_configuration",
                lambda x: x["rule"][0]["apply_server_side_encryption_by_default"][0].update(
                    sse_algorithm="AES256"
                ),
            ),
            (
                "broad_iam",
                "aws_iam_role_policy",
                lambda x: x.update(
                    policy=json.dumps(
                        {
                            "Version": "2012-10-17",
                            "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
                        }
                    )
                ),
            ),
            ("state_force_delete", "aws_s3_bucket", lambda x: x.update(force_destroy=True)),
            (
                "missing_encryption_denies",
                "aws_s3_bucket_policy",
                lambda x: x.update(
                    policy=json.dumps(
                        {"Version": "2012-10-17", "Statement": [document(x["policy"])[0]]}
                    )
                ),
            ),
            (
                "wrong_kms_key",
                "aws_s3_bucket_server_side_encryption_configuration",
                lambda x: x["rule"][0]["apply_server_side_encryption_by_default"][0].update(
                    kms_master_key_id="arn:aws:kms:us-east-1:000000000000:key/11111111-1111-1111-1111-111111111111"
                ),
            ),
            (
                "suspended_versioning",
                "aws_s3_bucket_versioning",
                lambda x: x["versioning_configuration"][0].update(status="Suspended"),
            ),
            ("no_kms_rotation", "aws_kms_key", lambda x: x.update(enable_key_rotation=False)),
        ]
    )
    results = []
    for name, kind, mutation in cases:
        changed = copy.deepcopy(plan)
        target = next(x for x in changed["resource_changes"] if x["type"] == kind)
        mutation(target["change"]["after"])
        try:
            check_plan(changed, stack)
        except PolicyError as error:
            results.append({"name": name, "rejected": True, "reason": str(error)})
        else:
            raise PolicyError("Negative policy control accepted: " + name)
    return results
