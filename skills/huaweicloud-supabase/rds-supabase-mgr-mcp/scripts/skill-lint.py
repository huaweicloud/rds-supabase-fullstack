#!/usr/bin/env python3
"""Structural lint for the rds-supabase-mgr-mcp skill.

Guards the v0.5.0 scenario-based restructure against regressions:

  1. SKILL.md carries the six scenario sections with expected titles
  2. jargon blacklist (terms banned by the terminology policy) never
     reappears in SKILL.md or any reference file
  3. the server version declared in SKILL.md is not newer than the actual
     mcp_server_rds_supabase_mgr pyproject version
  4. every reference file mentioned in SKILL.md exists on disk, and the
     references directory holds exactly the expected three files

Usage: python skill-lint.py [skill_dir]   (default: this script's parent)
Exit codes: 0 = PASS, 1 = FAIL (missing[] printed as JSON).
"""
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parent.parent.parent
PYPROJECT = REPO_ROOT / "server" / "mcp_server_rds_supabase_mgr" / "pyproject.toml"

SCENARIOS = [
    "场景一：从零创建一个能访问的应用",
    "场景二：使用已经创建好的应用",
    "场景三：按需增强",
    "场景四：日常变更速查",
    "场景五：查询接入信息",
    "场景六：删除应用",
]
JARGON_BLACKLIST = ("台账", "账本", "码道", "未决", "对账")
EXPECTED_REFERENCES = {"scenarios.md", "acceptance.md", "local-requests.md"}
VERSION_RE = re.compile(r"mcp_server_supabase\s*≥\s*(\d+)\.(\d+)\.(\d+)a(\d+)")


def server_version():
    match = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)a(\d+)"',
                      PYPROJECT.read_text(encoding="utf-8"), re.MULTILINE)
    return tuple(int(g) for g in match.groups()) if match else None


def declared_version(text):
    match = VERSION_RE.search(text)
    return tuple(int(g) for g in match.groups()) if match else None


def main():
    missing = []
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    for section in SCENARIOS:
        if f"## {section}" not in skill:
            missing.append(f"SKILL.md missing scenario section: {section}")

    texts = {"SKILL.md": skill}
    refs_dir = SKILL_DIR / "references"
    actual_refs = {p.name for p in refs_dir.glob("*.md")}
    for name in sorted(EXPECTED_REFERENCES - actual_refs):
        missing.append(f"references/{name} missing (expected exactly {sorted(EXPECTED_REFERENCES)})")
    for name in sorted(actual_refs - EXPECTED_REFERENCES):
        missing.append(f"references/{name} unexpected (expected exactly {sorted(EXPECTED_REFERENCES)})")
    for name in sorted(EXPECTED_REFERENCES & actual_refs):
        texts[f"references/{name}"] = (refs_dir / name).read_text(encoding="utf-8")

    for where, text in texts.items():
        for term in JARGON_BLACKLIST:
            if term in text:
                missing.append(f"{where} contains banned jargon: {term}")

    actual = server_version()
    declared = declared_version(skill)
    if actual is None:
        missing.append("cannot parse server pyproject version")
    elif declared is None:
        missing.append("SKILL.md missing 'mcp_server_supabase ≥ x.y.zaN' declaration")
    elif declared > actual:
        missing.append(f"SKILL.md declares server {declared} newer than actual {actual}")

    for name in re.findall(r"\]\((references/[a-z-]+\.md)\)", skill):
        if not (SKILL_DIR / name).is_file():
            missing.append(f"broken reference link: {name}")

    print(json.dumps({"verdict": "PASS" if not missing else "FAIL", "missing": missing},
                     ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
