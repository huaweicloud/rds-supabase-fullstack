#!/usr/bin/env python3
"""Structural lint for the rds-supabase-mgr-mcp skill.

Guards the v0.5.x scenario-based restructure against regressions:

  1. SKILL.md carries the six scenario sections as exact `## <title>`
     heading lines (line-anchored, not substring-matched)
  2. jargon blacklist (terms banned by the terminology policy) never
     reappears anywhere under SKILL.md or references/ (recursive)
  3. the server version declared in SKILL.md is not newer than the actual
     mcp_server_rds_supabase_mgr pyproject version; stable (0.4.0) and
     pre-release (0.4.0a8) forms both supported, stable sorts newer
  4. every relative markdown link in every skill file resolves on disk,
     and the references directory holds exactly the expected four files

Usage: python skill-lint.py            (checks this script's own skill dir)
Exit codes: 0 = PASS, 1 = FAIL (missing[] printed as JSON).
Enforced by server tests/test_skill_lint.py, which runs this script and
also verifies that it actually bites (jargon and version-drift fixtures).
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
    "场景五：查询接入信息（随时可用，创建场景的最后一步也用它）",
    "场景六：删除应用（干净收尾）",
]
JARGON_BLACKLIST = ("台账", "账本", "码道", "未决", "对账")
EXPECTED_REFERENCES = {"scenarios.md", "acceptance.md", "local-requests.md", "install.md"}
VERSION_RE = re.compile(r"mcp_server_supabase\s*≥\s*(\d+)\.(\d+)\.(\d+)(?:a(\d+))?")
PYPROJECT_RE = re.compile(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)(?:a(\d+))?"', re.MULTILINE)
LINK_RE = re.compile(r"\]\(([^)#\s]+\.md)(?:#[^)\s]*)?\)")


def _version(groups):
    major, minor, patch, alpha = (int(g) if g else None for g in groups)
    # A stable release (no alpha part) sorts after any pre-release of the
    # same x.y.z: 0.4.0 > 0.4.0a8.
    return (major, minor, patch, 0 if alpha is not None else 1, alpha or 0)


def server_version():
    match = PYPROJECT_RE.search(PYPROJECT.read_text(encoding="utf-8"))
    return _version(match.groups()) if match else None


def declared_version(text):
    match = VERSION_RE.search(text)
    return _version(match.groups()) if match else None


def main():
    missing = []
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    for section in SCENARIOS:
        if not re.search(rf"^## {re.escape(section)}\s*$", skill, re.MULTILINE):
            missing.append(f"SKILL.md missing scenario heading line: '## {section}'")

    texts = {"SKILL.md": skill}
    refs_dir = SKILL_DIR / "references"
    actual_refs = {p.name for p in refs_dir.rglob("*.md")}
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
        missing.append("SKILL.md missing 'mcp_server_supabase ≥ x.y.z[aN]' declaration")
    elif declared > actual:
        missing.append(f"SKILL.md declares server {declared} newer than actual {actual}")

    for where, text in texts.items():
        base = (SKILL_DIR / where).parent
        for target in LINK_RE.findall(text):
            if not target.startswith(("http://", "https://", "mailto:")) and not (base / target).is_file():
                missing.append(f"broken markdown link in {where}: {target}")

    print(json.dumps({"verdict": "PASS" if not missing else "FAIL", "missing": missing},
                     ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
