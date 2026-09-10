import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class RuntimeHardeningTests(unittest.TestCase):
    def test_root_does_not_downgrade_outputs_to_draft_only(self):
        root = read("SKILL.md")
        guide = read("使用指南.md")

        self.assertIn("高质量候选终稿", root)
        self.assertIn("候选终稿", guide)
        self.assertIn("人工核验", root)
        self.assertIn("人工逐项核验", guide)

    def test_runtime_guide_is_not_copied_into_project(self):
        root = read("SKILL.md")

        self.assertIn("不要求复制到 `PROJECT_ROOT`", root)

    def test_literal_code_escaping_is_guarded(self):
        root = read("SKILL.md")

        self.assertIn("普通下划线 `_`", root)
        self.assertIn(r"\_", root)

    def test_matlab_has_canonical_batch_entry(self):
        role = read("references/roles/编程手/SKILL.md")
        spec = read("references/roles/编程手/references/MATLAB规范.md")

        self.assertIn("matlab -batch", role)
        self.assertIn("matlab -batch", spec)
        self.assertIn("Python MATLAB Engine", spec)

    def test_matlab_project_root_layout_is_explicit(self):
        spec = read("references/roles/编程手/references/MATLAB规范.md")

        self.assertIn("`main.m` 直接位于 `PROJECT_ROOT`", spec)
        self.assertIn("不得把入口文件所在目录误当作项目根", spec)

    def test_mac_codex_sandbox_failure_is_not_treated_as_matlab_failure(self):
        spec = read("references/roles/编程手/references/MATLAB规范.md")

        self.assertIn("NEON", spec)
        self.assertIn("执行沙箱问题", spec)


if __name__ == "__main__":
    unittest.main()
