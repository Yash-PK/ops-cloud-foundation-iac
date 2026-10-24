"""Repository checks: provider identities, source boundary, documents and artifacts."""

import re
import subprocess

from guard import PROVIDER, parse, preflight, require
from project import ROOT, STACKS

REQUIRED = [
    "README.md",
    "AGENTS.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "LICENSE",
    "NOTICE.md",
    "docs/acceptance.md",
    "docs/dependencies.md",
]
PROVIDER_SHA256 = {
    "f292ad91c97ac7354a04a698f346c2a0c3866d9170ca45dda6a6bfab71180be0",
    "b2511842cb6b23036c72babbaf12b4984835bb2824f938882330b51c68bdaecd",
    "abd449fbf38cf828b8b17bc8540752733dd861160504a45b411e72e1792c758c",
}


def locks():
    contents = []
    for stack in STACKS:
        path = ROOT / "stacks" / stack / ".terraform.lock.hcl"
        providers = parse(path).get("provider")
        require(
            isinstance(providers, list)
            and len(providers) == 1
            and set(providers[0]) == {PROVIDER},
            "Lock must contain only the selected provider identity",
        )
        locked = providers[0][PROVIDER]
        require(
            locked.get("version") == "6.68.0" and locked.get("constraints") == "6.68.0",
            "Exact provider lock required",
        )
        hashes = locked.get("hashes", [])
        require(
            {"zh:" + value for value in PROVIDER_SHA256} <= set(hashes),
            "Missing verified supported-platform archive hashes",
        )
        require(
            len([value for value in hashes if value.startswith("h1:")]) == 3,
            "Three native platform content hashes required",
        )
        contents.append(path.read_bytes())
    require(contents[0] == contents[1], "Provider locks must match across roots")


def main():
    preflight()
    locks()
    for name in REQUIRED:
        require((ROOT / name).is_file(), "Missing required document: " + name)
    names = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    for name in set(names) - {""}:
        path = ROOT / name
        require(not path.is_symlink(), "Outgoing symlink prohibited")
        require(
            not any(
                part in {".venv", ".tools", ".runtime", ".terraform", "__pycache__"}
                for part in path.relative_to(ROOT).parts
            ),
            "Generated cache in outgoing files",
        )
        require(
            not re.search(r"(\.tfstate(?:\..*)?|\.tfplan|\.plan|\.pem|\.key|\.env)$", name),
            "Sensitive/generated artifact in outgoing files",
        )
        if path.suffix == ".md":
            text = path.read_text()
            for target in re.findall(r"\[[^\]]+\]\(([^\s)]+)\)", text):
                if target.startswith(("https://", "http://", "mailto:", "#")):
                    continue
                local = (path.parent / target.split("#")[0]).resolve()
                require(
                    local.is_relative_to(ROOT) and local.exists(),
                    f"Broken local link in {name}: {target}",
                )
    print("Structural guard, provider locks, document links and artifact boundaries: PASS")


if __name__ == "__main__":
    main()
