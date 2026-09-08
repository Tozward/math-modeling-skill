from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

HANDOFF = (
    REPO_ROOT
    / "tools"
    / "handoff"
    / "scripts"
    / "handoff.py"
)

TEMPLATES = (
    "AGENTS.md",
    "CURRENT_TASK.md",
    "DECISIONS.md",
    "HANDOFF.md",
    "AI使用日志.md",
)


def run(
    *args: str,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if check and result.returncode != 0:
        raise AssertionError(
            f"命令失败：{' '.join(args)}\n"
            f"exit={result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return result


def git(
    root: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return run(
        "git",
        "-C",
        str(root),
        *args,
        check=check,
    )


class HandoffCLITest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

        self.skill = self.base / "skill"
        self.project = self.base / "project"

        self._create_fake_skill()
        self._create_project()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _init_git(self, root: Path) -> None:
        root.mkdir(
            parents=True,
            exist_ok=True,
        )

        git(root, "init", "-q")
        git(
            root,
            "config",
            "user.name",
            "Handoff Test",
        )
        git(
            root,
            "config",
            "user.email",
            "handoff-test@example.invalid",
        )

    def _commit_all(
        self,
        root: Path,
        message: str,
    ) -> str:
        git(root, "add", ".")
        git(
            root,
            "commit",
            "-q",
            "-m",
            message,
        )

        return git(
            root,
            "rev-parse",
            "HEAD",
        ).stdout.strip()

    def _create_fake_skill(self) -> None:
        self._init_git(
            self.skill
        )

        (
            self.skill / "SKILL.md"
        ).write_text(
            "# Test Skill\n",
            encoding="utf-8",
        )

        (
            self.skill / "VERSION"
        ).write_text(
            "1.3.0\n",
            encoding="utf-8",
        )

        template_root = (
            self.skill
            / "tools"
            / "handoff"
            / "templates"
        )

        template_root.mkdir(
            parents=True,
        )

        for name in TEMPLATES:
            (
                template_root / name
            ).write_text(
                f"# {name}\n",
                encoding="utf-8",
            )

        self.skill_commit = self._commit_all(
            self.skill,
            "create fake skill",
        )

    def _create_project(self) -> None:
        self._init_git(
            self.project
        )

    def _handoff(
        self,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return run(
            sys.executable,
            str(HANDOFF),
            *args,
            check=check,
        )

    def _init_project(self) -> None:
        result = self._handoff(
            "init",
            "--skill-root",
            str(self.skill),
            "--project-root",
            str(self.project),
            "--contest",
            "cumcm",
            "--year",
            "2026",
        )

        self.assertEqual(
            result.returncode,
            0,
        )

        self._commit_all(
            self.project,
            "initialize project",
        )

    def _write_m1_artifacts(self) -> None:
        (
            self.project
            / "题目分析报告.md"
        ).write_text(
            "# 题目分析报告\n测试\n",
            encoding="utf-8",
        )

        (
            self.project
            / "术语表格.md"
        ).write_text(
            "# 术语表格\n测试\n",
            encoding="utf-8",
        )

        evidence = (
            self.project
            / ".handoff"
            / "gate-evidence"
            / "M1.md"
        )

        evidence.write_text(
            "# M1\n状态：PASS\n",
            encoding="utf-8",
        )

    def _record_m1_pass(
        self,
        *,
        revalidated: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        args = [
            "record-gate",
            "--project-root",
            str(self.project),
            "--gate",
            "M1",
            "--status",
            "PASS",
            "--evidence",
            ".handoff/gate-evidence/M1.md",
            "--artifact",
            "题目分析报告.md",
            "--artifact",
            "术语表格.md",
        ]

        if revalidated:
            args.append(
                "--revalidated"
            )

        return self._handoff(
            *args
        )

    def test_init_creates_expected_state(self) -> None:
        self._init_project()

        for name in TEMPLATES:
            self.assertTrue(
                (
                    self.project / name
                ).is_file()
            )

        self.assertTrue(
            (
                self.project
                / ".handoff"
                / "gate-evidence"
                / ".gitkeep"
            ).is_file()
        )

        lock = json.loads(
            (
                self.project
                / ".handoff"
                / "SKILL.lock"
            ).read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            lock["upstream_version"],
            "1.3.0",
        )

        self.assertEqual(
            lock["skill_commit"],
            self.skill_commit,
        )

        state = json.loads(
            (
                self.project
                / ".handoff"
                / "GATE_STATE.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            state["project"]["contest"],
            "cumcm",
        )

        self.assertEqual(
            state["project"]["year"],
            "2026",
        )

        for gate in (
            "M1",
            "P1",
            "P2",
            "W1",
            "W2",
        ):
            self.assertEqual(
                state["gates"][gate]["status"],
                "NOT_STARTED",
            )

    def test_init_refuses_overwrite(self) -> None:
        self._init_project()

        result = self._handoff(
            "init",
            "--skill-root",
            str(self.skill),
            "--project-root",
            str(self.project),
            check=False,
        )

        self.assertEqual(
            result.returncode,
            2,
        )

        self.assertIn(
            "已有接力状态文件",
            result.stderr,
        )

    def test_clean_project_passes_strict_check(self) -> None:
        self._init_project()

        result = self._handoff(
            "check",
            "--skill-root",
            str(self.skill),
            "--project-root",
            str(self.project),
            "--strict",
        )

        self.assertEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            "接力检查：PASS",
            result.stdout,
        )

    def test_pass_and_artifact_drift(self) -> None:
        self._init_project()
        self._write_m1_artifacts()

        validated_commit = self._commit_all(
            self.project,
            "M1 validated artifacts",
        )

        self._record_m1_pass()

        state = json.loads(
            (
                self.project
                / ".handoff"
                / "GATE_STATE.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            state["gates"]["M1"][
                "validated_project_commit"
            ],
            validated_commit,
        )

        self._commit_all(
            self.project,
            "record M1 state",
        )

        valid = self._handoff(
            "check",
            "--skill-root",
            str(self.skill),
            "--project-root",
            str(self.project),
            "--strict",
        )

        self.assertIn(
            "M1: PASS / VALID",
            valid.stdout,
        )

        with (
            self.project
            / "题目分析报告.md"
        ).open(
            "a",
            encoding="utf-8",
        ) as f:
            f.write(
                "未经复验的修改\n"
            )

        drift = self._handoff(
            "check",
            "--skill-root",
            str(self.skill),
            "--project-root",
            str(self.project),
            "--strict",
            check=False,
        )

        self.assertEqual(
            drift.returncode,
            1,
        )

        self.assertIn(
            "artifact 已变化：题目分析报告.md",
            drift.stdout,
        )

        state_after = json.loads(
            (
                self.project
                / ".handoff"
                / "GATE_STATE.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            state_after["gates"]["M1"]["status"],
            "PASS",
        )

    def test_pass_requires_clean_project(self) -> None:
        self._init_project()
        self._write_m1_artifacts()

        self._commit_all(
            self.project,
            "M1 artifacts",
        )

        (
            self.project / "extra.txt"
        ).write_text(
            "uncommitted\n",
            encoding="utf-8",
        )

        result = self._handoff(
            "record-gate",
            "--project-root",
            str(self.project),
            "--gate",
            "M1",
            "--status",
            "PASS",
            "--evidence",
            ".handoff/gate-evidence/M1.md",
            "--artifact",
            "题目分析报告.md",
            check=False,
        )

        self.assertEqual(
            result.returncode,
            2,
        )

        self.assertIn(
            "working tree 必须 clean",
            result.stderr,
        )

    def test_revalidated_flag_is_required(self) -> None:
        self._init_project()
        self._write_m1_artifacts()

        self._commit_all(
            self.project,
            "M1 artifacts",
        )

        self._record_m1_pass()

        self._commit_all(
            self.project,
            "record M1 pass",
        )

        self._handoff(
            "invalidate",
            "--project-root",
            str(self.project),
            "--gate",
            "M1",
            "--reason",
            "测试失效",
        )

        (
            self.project
            / ".handoff"
            / "gate-evidence"
            / "M1.md"
        ).write_text(
            "# M1\n重新验收：PASS\n",
            encoding="utf-8",
        )

        self._commit_all(
            self.project,
            "M1 revalidated artifacts",
        )

        denied = self._handoff(
            "record-gate",
            "--project-root",
            str(self.project),
            "--gate",
            "M1",
            "--status",
            "PASS",
            "--evidence",
            ".handoff/gate-evidence/M1.md",
            "--artifact",
            "题目分析报告.md",
            check=False,
        )

        self.assertEqual(
            denied.returncode,
            2,
        )

        self.assertIn(
            "--revalidated",
            denied.stderr,
        )

        accepted = self._record_m1_pass(
            revalidated=True,
        )

        self.assertEqual(
            accepted.returncode,
            0,
        )

    def test_skill_commit_mismatch_is_rejected(self) -> None:
        self._init_project()

        (
            self.skill / "SKILL.md"
        ).write_text(
            "# Test Skill\nchanged\n",
            encoding="utf-8",
        )

        self._commit_all(
            self.skill,
            "change skill",
        )

        result = self._handoff(
            "check",
            "--skill-root",
            str(self.skill),
            "--project-root",
            str(self.project),
            "--strict",
            check=False,
        )

        self.assertEqual(
            result.returncode,
            2,
        )

        self.assertIn(
            "Skill commit 不匹配",
            result.stdout,
        )

    def test_dirty_skill_is_rejected(self) -> None:
        (
            self.skill / "SKILL.md"
        ).write_text(
            "# dirty skill\n",
            encoding="utf-8",
        )

        result = self._handoff(
            "init",
            "--skill-root",
            str(self.skill),
            "--project-root",
            str(self.project),
            check=False,
        )

        self.assertEqual(
            result.returncode,
            2,
        )

        self.assertIn(
            "SKILL_ROOT working tree 非 clean",
            result.stderr,
        )

    def test_artifact_cannot_escape_project_root(self) -> None:
        self._init_project()
        self._write_m1_artifacts()

        outside = (
            self.base / "outside.md"
        )

        outside.write_text(
            "outside\n",
            encoding="utf-8",
        )

        self._commit_all(
            self.project,
            "M1 artifacts",
        )

        result = self._handoff(
            "record-gate",
            "--project-root",
            str(self.project),
            "--gate",
            "M1",
            "--status",
            "PASS",
            "--evidence",
            ".handoff/gate-evidence/M1.md",
            "--artifact",
            str(outside),
            check=False,
        )

        self.assertEqual(
            result.returncode,
            2,
        )

        self.assertIn(
            "路径越出 PROJECT_ROOT",
            result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
