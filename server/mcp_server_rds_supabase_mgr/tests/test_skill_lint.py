import shutil,subprocess,sys,tempfile,unittest
from pathlib import Path

SKILL=Path(__file__).resolve().parents[3]/'skills'/'huaweicloud-supabase'/'rds-supabase-mgr-mcp'


def _run(skill_dir):
    return subprocess.run([sys.executable,str(Path(skill_dir)/'scripts'/'skill-lint.py')],capture_output=True,text=True)


def _fake_repo_with_skill(tmp):
    root=Path(tmp);(root/'server'/'mcp_server_rds_supabase_mgr').mkdir(parents=True)
    (root/'server'/'mcp_server_rds_supabase_mgr'/'pyproject.toml').write_text('version = "0.4.0a8"\n')
    broken=root/'skills'/'huaweicloud-supabase'/'rds-supabase-mgr-mcp'
    shutil.copytree(SKILL,broken)
    return broken


class SkillLintTests(unittest.TestCase):
    def test_lint_passes_on_current_skill(self):
        result=_run(SKILL)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_lint_catches_jargon_regression(self):
        with tempfile.TemporaryDirectory(prefix='skill-lint-') as tmp:
            broken=_fake_repo_with_skill(tmp)
            target=broken/'references'/'scenarios.md'
            target.write_text(target.read_text(encoding='utf-8')+' 台账',encoding='utf-8')
            result=_run(broken)
            self.assertEqual(result.returncode,1)
            self.assertIn('banned jargon',result.stdout)

    def test_lint_rejects_version_drift(self):
        with tempfile.TemporaryDirectory(prefix='skill-lint-') as tmp:
            broken=_fake_repo_with_skill(tmp)
            skill_md=broken/'SKILL.md'
            skill_md.write_text(skill_md.read_text(encoding='utf-8').replace('≥ 0.4.0a8','≥ 9.9.9a9'),encoding='utf-8')
            result=_run(broken)
            self.assertEqual(result.returncode,1)
            self.assertIn('newer than actual',result.stdout)
