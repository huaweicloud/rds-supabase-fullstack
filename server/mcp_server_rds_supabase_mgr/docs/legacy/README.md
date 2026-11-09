# Legacy: Windows offline-bundle delivery workflow

These documents record the pre-integration delivery workflow of the
control-plane MCP (personal-branch Windows x64 offline ZIP + PowerShell
installer), retained for workstation reproduction and joint-debugging
history. They are not the primary installation path.

Main path: the repository-standard cross-platform uvx template — see
[USER_GUIDE.md](../USER_GUIDE.md) and the server README ("Configure and
run"). The bundle installer remains at `../../scripts/install-development.ps1`
(it expects an extracted bundle containing `requirements-development.txt`
and `wheels/`, which are not part of this repository).

Contents:

- WORKSTATION.md — workstation integration guide (bundle flow)
- WORKSTATION_0.3.8a1_RESULTS.md — 0.3.8a1 workstation results
- NEXT_WORKSTATION_PROMPT.md — joint-debug execution prompt
- RELEASE_0.3.8a1.md / RELEASE_0.3.8a2.md — bundle release notes
- COMPATIBILITY.md — Windows compatibility matrix and checklist
