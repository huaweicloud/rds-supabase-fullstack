#!/usr/bin/env python3
"""Structural lint for the rds-supabase-web-build skill itself.

Guards against the class of accidents where a renumbering or contract edit
lands in one file but not the others. Checks, against a single expected
pipeline:

  1. SKILL.md step headers: eight sequential 步骤一–步骤八 blocks, each with
     the expected stage name and breakpoint enum value
  2. workflow-stages.md: eight matching step sections
  3. project-state.md: the step enum line lists all enum values in order
  4. webapp-gate.py: the STAGES list matches the same pipeline
  5. every reference file mentioned in SKILL.md exists on disk

Usage: python skill-lint.py [skill_dir]   (default: this script's parent)
Exit codes: 0 = PASS, 1 = FAIL (missing[] printed as JSON).
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

STEPS = [
    ("步骤一", "环境检查与配置", "environment_ready"),
    ("步骤二", "需求澄清", "requirements_confirmed"),
    ("步骤三", "资源准备", "instance_ready"),
    ("步骤四", "数据面接入", "mcp_connected"),
    ("步骤五", "后端生成部署", "backend_deployed"),
    ("步骤六", "前端生成", "frontend_built"),
    ("步骤七", "构建与托管", "hosting_published"),
    ("步骤八", "端到端上线", "launched"),
]
SKILL_HEADER = re.compile(r"^### (步骤[一二三四五六七八]) · (.+?) → 断点 `([a-z_]+)`", re.MULTILINE)
PLAYBOOK_HEADER = re.compile(r"^## (步骤[一二三四五六七八]) · (.+?)$", re.MULTILINE)
REF_LINK = re.compile(r"(references/[A-Za-z0-9_-]+\.md|scripts/[A-Za-z0-9_-]+\.py|assets/[A-Za-z0-9_.-]+)")


def load_gate_stages(skill_dir, missing):
    gate = skill_dir / "scripts" / "webapp-gate.py"
    if not gate.is_file():
        missing.append("scripts/webapp-gate.py not found")
        return []
    spec = importlib.util.spec_from_file_location("webapp_gate", gate)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - report, don't crash the lint
        missing.append(f"webapp-gate.py failed to import: {exc}")
        return []
    return list(module.STAGES)


def lint(skill_dir):
    missing = []
    skill = (skill_dir / "SKILL.md")
    playbook = skill_dir / "references" / "workflow-stages.md"
    state = skill_dir / "references" / "project-state.md"
    for path in (skill, playbook, state):
        if not path.is_file():
            missing.append(f"{path.relative_to(skill_dir)} not found")
    if missing:
        return missing
    text, wf_text, state_text = skill.read_text(encoding="utf-8"), \
        playbook.read_text(encoding="utf-8"), state.read_text(encoding="utf-8")

    headers = SKILL_HEADER.findall(text)
    if len(headers) != len(STEPS):
        missing.append(f"SKILL.md has {len(headers)} step headers with breakpoints, expected {len(STEPS)}")
    for (number, name, enum), (want_number, want_name, want_enum) in zip(headers, STEPS):
        if (number, name, enum) != (want_number, want_name, want_enum):
            missing.append(f"SKILL.md step header mismatch: got '{number} · {name} → {enum}', "
                           f"expected '{want_number} · {want_name} → {want_enum}'")

    sections = PLAYBOOK_HEADER.findall(wf_text)
    for (number, name), (want_number, want_name, _) in zip(sections, STEPS):
        if (number, name) != (want_number, want_name):
            missing.append(f"workflow-stages.md section mismatch: got '{number} · {name}', "
                           f"expected '{want_number} · {want_name}'")
    if len(sections) != len(STEPS):
        missing.append(f"workflow-stages.md has {len(sections)} step sections, expected {len(STEPS)}")

    enum_line = next((line for line in state_text.splitlines() if "步骤枚举" in line), "")
    for _, _, want_enum in STEPS + [("x", "x", "decommissioned")]:
        if f"`{want_enum}`" not in enum_line:
            missing.append(f"project-state.md step enum line is missing `{want_enum}`")
    positions = [enum_line.find(f"`{want_enum}`") for _, _, want_enum in STEPS]
    if any(p == -1 for p in positions) or positions != sorted(positions):
        missing.append("project-state.md step enum order does not match the pipeline order")

    gate_stages = load_gate_stages(skill_dir, missing)
    expected = [want_enum for _, _, want_enum in STEPS] + ["decommissioned"]
    if gate_stages and gate_stages != expected:
        missing.append(f"webapp-gate.py STAGES {gate_stages} != expected {expected}")

    reference_section = text.split("## 参考文档", 1)
    reference_body = reference_section[1] if len(reference_section) > 1 else ""
    for ref in sorted(set(REF_LINK.findall(reference_body))):
        if not (skill_dir / ref).exists():
            missing.append(f"SKILL.md references missing file: {ref}")
    return missing


def main():
    skill_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    missing = lint(skill_dir)
    print(json.dumps({"verdict": "PASS" if not missing else "FAIL", "missing": missing},
                     ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
