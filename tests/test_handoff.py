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
        encoding="utf-8",
        errors="replace",
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


    def test_init_creates_idle_active_work(self) -> None:
        self._init_project()

        active = json.loads(
            (
                self.project
                / ".handoff"
                / "ACTIVE_WORK.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            active["status"],
            "IDLE",
        )

        self.assertIsNone(
            active["active"]
        )

        self.assertIsNone(
            active["last_completed"]
        )

    def test_begin_work_records_write_ahead_state(self) -> None:
        self._init_project()

        result = self._handoff(
            "begin-work",
            "--project-root",
            str(self.project),
            "--stage",
            "M1",
            "--objective",
            "完成问题一模型设计",
            "--atomic-unit",
            "比较候选模型并冻结主模型",
            "--next-action",
            "读取数据特征并完成模型适配性比较",
            "--input",
            "题目.pdf",
            "--expected-output",
            "题目分析报告.md",
            "--actor",
            "member-a",
        )

        self.assertEqual(
            result.returncode,
            0,
        )

        active = json.loads(
            (
                self.project
                / ".handoff"
                / "ACTIVE_WORK.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            active["status"],
            "IN_PROGRESS",
        )

        work = active["active"]

        self.assertEqual(
            work["stage"],
            "M1",
        )

        self.assertEqual(
            work["atomic_unit"],
            "比较候选模型并冻结主模型",
        )

        self.assertEqual(
            work["next_action"],
            "读取数据特征并完成模型适配性比较",
        )

        self.assertEqual(
            work["checkpoint_count"],
            0,
        )

    def test_begin_work_refuses_to_overwrite_in_progress(self) -> None:
        self._init_project()

        args = (
            "begin-work",
            "--project-root",
            str(self.project),
            "--stage",
            "M1",
            "--objective",
            "测试目标",
            "--atomic-unit",
            "测试原子单元",
            "--next-action",
            "继续测试",
        )

        self._handoff(
            *args
        )

        denied = self._handoff(
            *args,
            check=False,
        )

        self.assertEqual(
            denied.returncode,
            2,
        )

        self.assertIn(
            "拒绝覆盖",
            denied.stderr,
        )

    def test_checkpoint_updates_resume_point(self) -> None:
        self._init_project()

        self._handoff(
            "begin-work",
            "--project-root",
            str(self.project),
            "--stage",
            "P2",
            "--objective",
            "实现问题一求解",
            "--atomic-unit",
            "完成核心求解器",
            "--next-action",
            "编写 solver.py",
        )

        solver = (
            self.project / "solver.py"
        )

        solver.write_text(
            "print('partial')\n",
            encoding="utf-8",
        )

        result = self._handoff(
            "checkpoint",
            "--project-root",
            str(self.project),
            "--next-action",
            "运行最小样例并核对边界条件",
            "--note",
            "求解器主体已写完",
            "--touch",
            "solver.py",
        )

        self.assertEqual(
            result.returncode,
            0,
        )

        active = json.loads(
            (
                self.project
                / ".handoff"
                / "ACTIVE_WORK.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        work = active["active"]

        self.assertEqual(
            work["checkpoint_count"],
            1,
        )

        self.assertEqual(
            work["next_action"],
            "运行最小样例并核对边界条件",
        )

        self.assertEqual(
            work["last_checkpoint"]["note"],
            "求解器主体已写完",
        )

        touched = {
            item["path"]: item
            for item in work["touched_files"]
        }

        self.assertIn(
            "solver.py",
            touched,
        )

        self.assertTrue(
            touched["solver.py"]["exists"],
        )

        self.assertIn(
            "sha256",
            touched["solver.py"],
        )

    def test_checkpoint_requires_active_work(self) -> None:
        self._init_project()

        result = self._handoff(
            "checkpoint",
            "--project-root",
            str(self.project),
            "--next-action",
            "无",
            check=False,
        )

        self.assertEqual(
            result.returncode,
            2,
        )

        self.assertIn(
            "没有 IN_PROGRESS 工作",
            result.stderr,
        )

    def test_finish_work_returns_idle_and_preserves_last_completed(self) -> None:
        self._init_project()

        self._handoff(
            "begin-work",
            "--project-root",
            str(self.project),
            "--stage",
            "W2",
            "--objective",
            "核对摘要",
            "--atomic-unit",
            "核对摘要关键数字",
            "--next-action",
            "逐项比对摘要与结果表",
        )

        result = self._handoff(
            "finish-work",
            "--project-root",
            str(self.project),
            "--summary",
            "摘要关键数字核对完成",
            "--next-action",
            "检查结论章节与摘要一致性",
            "--actor",
            "member-b",
        )

        self.assertEqual(
            result.returncode,
            0,
        )

        active = json.loads(
            (
                self.project
                / ".handoff"
                / "ACTIVE_WORK.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            active["status"],
            "IDLE",
        )

        self.assertIsNone(
            active["active"]
        )

        completed = active[
            "last_completed"
        ]

        self.assertEqual(
            completed["summary"],
            "摘要关键数字核对完成",
        )

        self.assertEqual(
            completed["next_action_after"],
            "检查结论章节与摘要一致性",
        )

    def test_check_reports_in_progress_recovery_state(self) -> None:
        self._init_project()

        self._handoff(
            "begin-work",
            "--project-root",
            str(self.project),
            "--stage",
            "M1",
            "--objective",
            "问题一建模",
            "--atomic-unit",
            "建立候选模型比较",
            "--next-action",
            "继续完成适配性比较",
        )

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
            "[RECOVER]",
            result.stdout,
        )

        self.assertIn(
            "上一工作单元可能被中断",
            result.stdout,
        )

        self.assertIn(
            "继续完成适配性比较",
            result.stdout,
        )

    def test_strict_check_allows_dirty_tree_during_active_work(self) -> None:
        self._init_project()

        self._handoff(
            "begin-work",
            "--project-root",
            str(self.project),
            "--stage",
            "P2",
            "--objective",
            "代码实现",
            "--atomic-unit",
            "实现核心函数",
            "--next-action",
            "继续实现",
        )

        (
            self.project / "partial.py"
        ).write_text(
            "x = 1\n",
            encoding="utf-8",
        )

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
            "保留这些修改并从恢复点继续",
            result.stdout,
        )

        self.assertNotIn(
            "接力检查：FAIL",
            result.stdout,
        )


    def test_strict_check_recovers_finished_work_before_git_checkpoint(self) -> None:
        self._init_project()

        self._handoff(
            "begin-work",
            "--project-root",
            str(self.project),
            "--stage",
            "M1",
            "--objective",
            "完成候选模型比较",
            "--atomic-unit",
            "冻结问题一主模型",
            "--next-action",
            "完成模型比较",
        )

        (
            self.project
            / "model-choice.md"
        ).write_text(
            "最终选择模型 B。\n",
            encoding="utf-8",
        )

        self._handoff(
            "finish-work",
            "--project-root",
            str(self.project),
            "--summary",
            "问题一主模型已冻结为模型 B",
            "--next-action",
            "更新题目分析报告并建立 Git checkpoint",
            "--touch",
            "model-choice.md",
        )

        current_task = (
            self.project
            / "CURRENT_TASK.md"
        )

        with current_task.open(
            "a",
            encoding="utf-8",
        ) as f:
            f.write(
                "\n收尾更新：主模型已经冻结。\n"
            )

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
            "已 finish-work",
            result.stdout,
        )

        self.assertIn(
            "问题一主模型已冻结为模型 B",
            result.stdout,
        )

        self.assertIn(
            "更新题目分析报告并建立 Git checkpoint",
            result.stdout,
        )


    def test_new_work_requires_previous_finished_work_to_be_persisted(self) -> None:
        self._init_project()

        self._handoff(
            "begin-work",
            "--project-root",
            str(self.project),
            "--stage",
            "M1",
            "--objective",
            "完成第一个原子任务",
            "--atomic-unit",
            "冻结模型选择",
            "--next-action",
            "完成模型选择",
        )

        (
            self.project
            / "model.md"
        ).write_text(
            "模型 B。\n",
            encoding="utf-8",
        )

        self._handoff(
            "finish-work",
            "--project-root",
            str(self.project),
            "--summary",
            "模型选择已完成",
            "--next-action",
            "开始参数确定",
            "--touch",
            "model.md",
        )

        denied = self._handoff(
            "begin-work",
            "--project-root",
            str(self.project),
            "--stage",
            "M1",
            "--objective",
            "确定参数",
            "--atomic-unit",
            "确定核心参数",
            "--next-action",
            "读取数据并估计参数",
            check=False,
        )

        self.assertEqual(
            denied.returncode,
            2,
        )

        self.assertIn(
            "尚未完成持久化收尾",
            denied.stderr,
        )

        self._commit_all(
            self.project,
            "persist completed atomic work",
        )

        accepted = self._handoff(
            "begin-work",
            "--project-root",
            str(self.project),
            "--stage",
            "M1",
            "--objective",
            "确定参数",
            "--atomic-unit",
            "确定核心参数",
            "--next-action",
            "读取数据并估计参数",
        )

        self.assertEqual(
            accepted.returncode,
            0,
        )



    def test_skill_lock_does_not_store_install_location(self) -> None:
        self._init_project()

        lock_path = (
            self.project
            / ".handoff"
            / "SKILL.lock"
        )

        lock = json.loads(
            lock_path.read_text(
                encoding="utf-8"
            )
        )

        self.assertNotIn(
            "skill_path_template",
            lock,
        )

        serialized = json.dumps(
            lock,
            ensure_ascii=False,
        )

        self.assertNotIn(
            str(self.skill),
            serialized,
        )


    def test_unknown_lock_metadata_does_not_change_identity(self) -> None:
        self._init_project()

        lock_path = (
            self.project
            / ".handoff"
            / "SKILL.lock"
        )

        lock = json.loads(
            lock_path.read_text(
                encoding="utf-8"
            )
        )

        lock["extra_metadata"] = {
            "note": "ignored by identity check",
        }

        lock_path.write_text(
            json.dumps(
                lock,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        self._commit_all(
            self.project,
            "add unrelated lock metadata",
        )

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
            "SKILL.lock 与本机 Skill 完全一致",
            result.stdout,
        )


    def test_relocated_skill_with_same_commit_is_accepted(self) -> None:
        self._init_project()

        relocated = (
            self.base
            / "另一个 Skill 位置"
            / "math-modeling-skill"
        )

        relocated.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        run(
            "git",
            "clone",
            "-q",
            str(self.skill),
            str(relocated),
        )

        result = self._handoff(
            "check",
            "--skill-root",
            str(relocated),
            "--project-root",
            str(self.project),
            "--strict",
        )

        self.assertEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            "SKILL.lock 与本机 Skill 完全一致",
            result.stdout,
        )


    def test_unicode_and_space_paths_are_supported(self) -> None:
        project = (
            self.base
            / "比赛项目 胡耀宇"
        )

        self._init_git(
            project
        )

        initialized = self._handoff(
            "init",
            "--skill-root",
            str(self.skill),
            "--project-root",
            str(project),
            "--contest",
            "cumcm",
            "--year",
            "2026",
        )

        self.assertEqual(
            initialized.returncode,
            0,
        )

        self._commit_all(
            project,
            "initialize unicode project",
        )

        self._handoff(
            "begin-work",
            "--project-root",
            str(project),
            "--stage",
            "M1",
            "--objective",
            "验证中文路径",
            "--atomic-unit",
            "记录中文文件",
            "--next-action",
            "继续中文路径恢复测试",
        )

        record = (
            project
            / "阶段 记录.md"
        )

        record.write_text(
            "中文路径测试\n",
            encoding="utf-8",
        )

        checkpoint = self._handoff(
            "checkpoint",
            "--project-root",
            str(project),
            "--next-action",
            "从中文文件继续",
            "--touch",
            "阶段 记录.md",
        )

        self.assertEqual(
            checkpoint.returncode,
            0,
        )

        checked = self._handoff(
            "check",
            "--skill-root",
            str(self.skill),
            "--project-root",
            str(project),
            "--strict",
        )

        self.assertEqual(
            checked.returncode,
            0,
        )

        self.assertIn(
            "[RECOVER]",
            checked.stdout,
        )

        self.assertIn(
            "从中文文件继续",
            checked.stdout,
        )



class PreemptionProtocolDocumentationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.agents = (
            REPO_ROOT
            / "tools"
            / "handoff"
            / "templates"
            / "AGENTS.md"
        ).read_text(encoding="utf-8")

        cls.current_task = (
            REPO_ROOT
            / "tools"
            / "handoff"
            / "templates"
            / "CURRENT_TASK.md"
        ).read_text(encoding="utf-8")

        cls.handoff_template = (
            REPO_ROOT
            / "tools"
            / "handoff"
            / "templates"
            / "HANDOFF.md"
        ).read_text(encoding="utf-8")

        cls.skill = (
            REPO_ROOT
            / "tools"
            / "handoff"
            / "SKILL.md"
        ).read_text(encoding="utf-8")

        cls.protocol = (
            REPO_ROOT
            / "references"
            / "跨账号接力协议.md"
        ).read_text(encoding="utf-8")

        cls.root_skill = (
            REPO_ROOT
            / "SKILL.md"
        ).read_text(encoding="utf-8")

        cls.handoff_source = (
            REPO_ROOT
            / "tools"
            / "handoff"
            / "scripts"
            / "handoff.py"
        ).read_text(encoding="utf-8")

        cls.handoff_template = (
            REPO_ROOT
            / "tools"
            / "handoff"
            / "templates"
            / "HANDOFF.md"
        ).read_text(encoding="utf-8")

    def test_expensive_work_requires_write_ahead_record(self) -> None:
        self.assertIn(
            "`begin-work` 成功之后再开始昂贵推理",
            self.agents,
        )

        self.assertIn(
            "必须 begin-work 的工作",
            self.agents,
        )

    def test_atomic_units_must_not_cover_entire_major_gate(self) -> None:
        for phrase in (
            "整个 M1",
            "整个 P2",
            "整篇论文",
            "整个 W2",
        ):
            self.assertIn(
                phrase,
                self.agents,
            )

    def test_recovery_prioritizes_active_work(self) -> None:
        self.assertIn(
            ".handoff/ACTIVE_WORK.json",
            self.agents,
        )

        self.assertIn(
            "不得重新执行 `begin-work`",
            self.agents,
        )

        self.assertIn(
            "保留现有 working tree",
            self.agents,
        )

    def test_current_task_defers_immediate_resume_to_active_work(self) -> None:
        self.assertIn(
            "即时权威恢复点",
            self.current_task,
        )

        self.assertIn(
            "优先执行其中的 `next_action`",
            self.current_task,
        )

    def test_planned_handoff_handles_in_progress_work(self) -> None:
        self.assertIn(
            "若当前工作能安全完成，执行 `finish-work`",
            self.agents,
        )

        self.assertIn(
            "至少执行一次 `checkpoint`",
            self.agents,
        )

    def test_handoff_skill_exposes_preemption_commands(self) -> None:
        for command in (
            "begin-work",
            "checkpoint",
            "finish-work",
        ):
            self.assertIn(
                command,
                self.skill,
            )

    def test_protocol_preserves_five_gate_semantics(self) -> None:
        self.assertIn(
            "它不是新的 Gate",
            self.protocol,
        )

        self.assertIn(
            "M1/P1/P2/W1/W2",
            self.protocol,
        )

    def test_handoff_template_checks_active_work_first(self) -> None:
        self.assertIn(
            "ACTIVE_WORK",
            self.handoff_template,
        )

        self.assertIn(
            "直接恢复该原子工作",
            self.handoff_template,
        )




    def test_runtime_does_not_require_fixed_skill_location(self) -> None:
        runtime_documents = (
            self.root_skill,
            self.skill,
            self.agents,
            self.protocol,
        )

        forbidden = (
            "$HOME/MathModelingWorkspace/"
            "skills/math-modeling-skill"
        )

        for document in runtime_documents:
            self.assertNotIn(
                forbidden,
                document,
            )

        self.assertNotIn(
            "skill_path_template",
            self.handoff_source,
        )

        self.assertIn(
            "<SKILL_ROOT>/SKILL.md",
            self.agents,
        )


    def test_handoff_template_avoids_duplicate_skill_identity(self) -> None:
        self.assertNotIn(
            "Skill 版本：",
            self.handoff_template,
        )

        self.assertNotIn(
            "Skill Commit：",
            self.handoff_template,
        )




if __name__ == "__main__":
    unittest.main()
