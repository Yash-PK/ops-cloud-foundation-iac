"""Parse trusted lab HCL before allowing the offline-only task interface."""

import re

import hcl2
from project import ROOT, STACKS

OPTIONS = hcl2.SerializationOptions(
    strip_string_quotes=True, explicit_blocks=False, with_comments=False
)
PROVIDER = "registry.terraform.io/hashicorp/aws"
# Includes file reads, existence/listing functions and every file-hash variant.
# A future file-prefixed function requires review instead of silently widening
# the offline expression surface. No test expression needs a filesystem read.
FILESYSTEM_FUNCTION = re.compile(r"\b(?:file[A-Za-z0-9_]*|templatefile)\s*\(")
RESOURCE_TYPES = {
    "aws_vpc",
    "aws_subnet",
    "aws_route_table",
    "aws_route_table_association",
    "aws_internet_gateway",
    "aws_route",
    "aws_security_group",
    "aws_vpc_security_group_ingress_rule",
    "aws_vpc_security_group_egress_rule",
    "aws_instance",
    "aws_iam_role",
    "aws_iam_instance_profile",
    "aws_iam_role_policy",
    "aws_s3_bucket",
    "aws_s3_bucket_public_access_block",
    "aws_s3_bucket_versioning",
    "aws_s3_bucket_server_side_encryption_configuration",
    "aws_s3_bucket_ownership_controls",
    "aws_s3_bucket_policy",
    "aws_kms_key",
    "aws_kms_alias",
}


class GuardError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise GuardError(message)


def parse(path):
    require(path.is_file() and not path.is_symlink(), "HCL must be a regular file")
    require(path.stat().st_size <= 150_000, "HCL file exceeds lab size limit")
    try:
        return hcl2.loads(path.read_text(), serialization_options=OPTIONS)
    except Exception as error:
        raise GuardError("Invalid HCL: " + path.name) from error


def walk(value):
    """Visit mapping entries, expression keys and scalar list members."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            # HCL object keys can themselves contain expressions.
            yield None, key
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield None, item
            yield from walk(item)


def validate_config(value, path, root):
    require(
        set(value)
        <= {
            "terraform",
            "variable",
            "locals",
            "resource",
            "output",
            "provider",
            "module",
            "check",
        },
        "Unsupported configuration block",
    )
    for key, item in walk(value):
        require(
            key not in {"provisioner", "connection", "external", "backend_config"},
            "Execution/connection hooks are forbidden",
        )
        require(
            not (isinstance(item, str) and "provider::" in item),
            "Provider-defined functions are outside this offline contract",
        )
        if isinstance(item, str) and FILESYSTEM_FUNCTION.search(item):
            # Only the reviewed fixed guest cloud-init template may read a source file.
            require(
                item
                in {
                    '${file("${path.module}/templates/cloud-init.yaml")}',
                    '${var.enabled ? file("${path.module}/templates/cloud-init.yaml") : null}',
                },
                "Unreviewed filesystem function in configuration",
            )
    for block in value.get("terraform", []):
        for backend in block.get("backend", []):
            require(
                backend == {"local": {}}, "Only the implicit/empty local backend is permitted"
            )
        for required in block.get("required_providers", []):
            require(set(required) == {"aws"}, "Only the selected AWS schema is allowed")
            require(
                required["aws"].get("source") == PROVIDER
                and re.fullmatch(r"=?\s*6\.68\.0", required["aws"].get("version", ""))
                is not None,
                "Provider must match the audited exact registry/version",
            )
    for provider in value.get("provider", []):
        require(set(provider) == {"aws"}, "Unexpected provider")
        require(
            set(provider["aws"]) <= {"region", "allowed_account_ids", "default_tags"},
            "Provider credential/endpoint settings are forbidden",
        )
    for group in value.get("resource", []):
        require(set(group) <= RESOURCE_TYPES, "Resource outside bounded AWS core")
    for block in value.get("module", []):
        for settings in block.values():
            source = settings.get("source")
            require(
                isinstance(source, str) and source.startswith(("./", "../")),
                "Only local reviewed modules are allowed",
            )
            target = (path.parent / source).resolve()
            require(
                target.is_dir() and target.is_relative_to(root / "modules"),
                "Module outside repository module boundary",
            )
            require(
                ".terraform" not in target.relative_to(root).parts,
                "Module cannot hide source in ignored tool cache",
            )


def validate_test(value):
    require(
        set(value) <= {"mock_provider", "run", "variables"},
        "Tests must use only mock providers and plan runs",
    )
    for _key, item in walk(value):
        if isinstance(item, str):
            require(
                not FILESYSTEM_FUNCTION.search(item), "Test filesystem functions are forbidden"
            )
            require(
                "provider::" not in item,
                "Provider-defined functions are outside this offline contract",
            )
    mocks = value.get("mock_provider", [])
    require(
        len(mocks) == 1 and set(mocks[0]) == {"aws"},
        "Exactly one mocked AWS provider is required",
    )
    require("alias" not in mocks[0]["aws"], "Default AWS provider must be mocked")
    runs = value.get("run", [])
    require(bool(runs), "At least one mock plan run is required")
    names = []
    for group in runs:
        require(isinstance(group, dict) and len(group) == 1, "Invalid run block")
        name, run = next(iter(group.items()))
        require(name not in names, "Duplicate mock test name")
        names.append(name)
        require(run.get("command") == "plan", "Every test must explicitly use command = plan")
        require(
            run.get("plan_options") == [{"refresh": False}],
            "Every plan must disable refresh without target/replace overrides",
        )
        require(
            set(run) <= {"command", "plan_options", "variables", "assert", "expect_failures"},
            "Test provider/module override is forbidden",
        )
        require(
            bool(run.get("assert") or run.get("expect_failures")),
            "Test must assert behavior or an expected validation failure",
        )
    return names


def preflight(root=ROOT):
    root = root.resolve()
    counts = {}
    for directory in (root / "modules", root / "stacks"):
        require(directory.is_dir(), "Missing IaC directory")
        for path in directory.rglob("*"):
            if ".terraform" in path.parts:
                continue
            require(not path.is_symlink(), "Symlink in IaC source")
            if not path.is_file():
                continue
            name = path.name
            require(
                not name.endswith(
                    (
                        ".tofu",
                        ".tofu.json",
                        ".tf.json",
                        ".tftest.json",
                        ".tofutest.hcl",
                        ".tofutest.json",
                    )
                ),
                "Alternate/shadowing source formats are not supported by this guard",
            )
            require(
                not (
                    name.endswith((".tfvars", ".tfvars.json", ".tfstate", ".tfstate.backup"))
                    or name == "override.tf"
                    or name.endswith("_override.tf")
                ),
                "State, variable overrides and override files are forbidden in source stacks",
            )
            if name.endswith(".tf"):
                validate_config(parse(path), path, root)
            elif name.endswith(".tftest.hcl"):
                counts[str(path.relative_to(root))] = validate_test(parse(path))
    for stack in STACKS:
        require(
            any(name.startswith("stacks/" + stack + "/tests/") for name in counts),
            "Missing guarded test suite: " + stack,
        )
    return counts


if __name__ == "__main__":
    result = preflight()
    print(
        f"Offline guard: {sum(map(len, result.values()))} explicit mocked plans; "
        "no live task allowed"
    )
