#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

GATES = ("M1", "P1", "P2", "W1", "W2")

STATUSES = (
    "NOT_STARTED",
    "PENDING",
    "PASS",
    "FAIL",
    "BLOCKED",
    "STALE",
)

TEMPLATE_FILES = (
    "AGENTS.md",
    "CURRENT_TASK.md",
    "DECISIONS.md",
    "HANDOFF.md",
    "AI使用日志.md",
)

LOCK_REL = Path(".handoff") / "SKILL.lock"
STATE_REL = Path(".handoff") / "GATE_STATE.json"
EVIDENCE_DIR_REL = Path(".handoff") / "gate-evidence"


class HandoffError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_git(
    root: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise HandoffError(
            "未找到 git 命令，请先安装并配置 Git。"
        ) from exc

    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise HandoffError(
            f"Git 命令失败：git {' '.join(args)}\n{detail}"
        )

    return result


def git_head(root: Path) -> str:
    return run_git(
        root,
        "rev-parse",
        "HEAD",
    ).stdout.strip()


def git_toplevel(root: Path) -> Path:
    output = run_git(
        root,
        "rev-parse",
        "--show-toplevel",
    ).stdout.strip()

    return Path(output).resolve()


def git_status_porcelain(root: Path) -> str:
    return run_git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ).stdout


def git_file_clean(root: Path, rel: str) -> bool:
    result = run_git(
        root,
        "status",
        "--porcelain=v1",
        "--",
        rel,
    )

    return result.stdout.strip() == ""


def git_file_tracked(root: Path, rel: str) -> bool:
    result = run_git(
        root,
        "ls-files",
        "--error-unmatch",
        "--",
        rel,
        check=False,
    )

    return result.returncode == 0


def git_commit_exists(root: Path, commit: str) -> bool:
    result = run_git(
        root,
        "cat-file",
        "-e",
        f"{commit}^{{commit}}",
        check=False,
    )

    return result.returncode == 0


def git_is_ancestor(
    root: Path,
    ancestor: str,
    descendant: str = "HEAD",
) -> bool:
    result = run_git(
        root,
        "merge-base",
        "--is-ancestor",
        ancestor,
        descendant,
        check=False,
    )

    return result.returncode == 0


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)

    except FileNotFoundError as exc:
        raise HandoffError(
            f"缺少文件：{path}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise HandoffError(
            f"JSON 无法解析：{path}\n{exc}"
        ) from exc

    if not isinstance(data, dict):
        raise HandoffError(
            f"JSON 顶层必须是对象：{path}"
        )

    return data


def write_json_atomic(
    path: Path,
    data: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        path.name + ".tmp"
    )

    with temporary.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )
        f.write("\n")

    os.replace(
        temporary,
        path,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def normalized_rel_path(
    project_root: Path,
    raw: str,
    *,
    must_exist: bool = True,
) -> tuple[Path, str]:
    if not raw or "\x00" in raw:
        raise HandoffError(
            "文件路径为空或包含非法字符。"
        )

    candidate = Path(raw)

    if candidate.is_absolute():
        resolved = candidate.resolve(
            strict=must_exist
        )
    else:
        resolved = (
            project_root / candidate
        ).resolve(
            strict=must_exist
        )

    try:
        relative = resolved.relative_to(
            project_root
        )
    except ValueError as exc:
        raise HandoffError(
            f"路径越出 PROJECT_ROOT，已拒绝：{raw}"
        ) from exc

    if resolved == project_root:
        raise HandoffError(
            f"需要文件路径，不能直接使用 PROJECT_ROOT：{raw}"
        )

    return resolved, relative.as_posix()


def roots_overlap(
    first: Path,
    second: Path,
) -> bool:
    try:
        first.relative_to(second)
        return True
    except ValueError:
        pass

    try:
        second.relative_to(first)
        return True
    except ValueError:
        return False


def require_skill_root(
    skill_root: Path,
) -> tuple[str, str]:
    skill_md = skill_root / "SKILL.md"
    version_file = skill_root / "VERSION"

    templates = (
        skill_root
        / "tools"
        / "handoff"
        / "templates"
    )

    if not skill_md.is_file():
        raise HandoffError(
            f"无效 SKILL_ROOT：缺少 {skill_md}"
        )

    if not version_file.is_file():
        raise HandoffError(
            f"无效 SKILL_ROOT：缺少 {version_file}"
        )

    if not templates.is_dir():
        raise HandoffError(
            f"无效 SKILL_ROOT：缺少模板目录 {templates}"
        )

    version = version_file.read_text(
        encoding="utf-8"
    ).strip()

    if not version:
        raise HandoffError(
            "VERSION 文件为空。"
        )

    top = git_toplevel(
        skill_root
    )

    if top != skill_root:
        raise HandoffError(
            "SKILL_ROOT 必须是 Skill Git 仓库根目录。\n"
            f"给定：{skill_root}\n"
            f"Git 根目录：{top}"
        )

    commit = git_head(
        skill_root
    )

    skill_status = git_status_porcelain(
        skill_root
    )

    if skill_status.strip():
        lines = skill_status.rstrip().splitlines()
        preview = "\n".join(
            f"  {line}"
            for line in lines[:10]
        )

        if len(lines) > 10:
            preview += "\n  ..."

        raise HandoffError(
            "SKILL_ROOT working tree 非 clean，"
            "当前 Git commit 无法唯一代表实际 Skill 内容。\n"
            "请先提交、还原或清理 Skill 修改，再初始化或恢复比赛项目。\n"
            f"{preview}"
        )

    return version, commit


def require_project_root(
    project_root: Path,
) -> str:
    if not project_root.is_dir():
        raise HandoffError(
            f"PROJECT_ROOT 不存在或不是目录：{project_root}"
        )

    top = git_toplevel(
        project_root
    )

    if top != project_root:
        raise HandoffError(
            "PROJECT_ROOT 必须已经是独立的本地 Git 仓库根目录。\n"
            f"给定：{project_root}\n"
            f"Git 根目录：{top}\n"
            "请先在项目目录执行 git init。"
        )

    result = run_git(
        project_root,
        "rev-parse",
        "--verify",
        "HEAD",
        check=False,
    )

    if result.returncode == 0:
        return git_head(
            project_root
        )

    return "UNBORN"


def validate_roots(
    skill_root: Path,
    project_root: Path,
) -> None:
    if roots_overlap(
        skill_root,
        project_root,
    ):
        raise HandoffError(
            "SKILL_ROOT 与 PROJECT_ROOT "
            "不得相同，也不得互相嵌套。\n"
            f"SKILL_ROOT={skill_root}\n"
            f"PROJECT_ROOT={project_root}"
        )


def skill_path_template() -> str:
    return (
        "$HOME/MathModelingWorkspace/"
        "skills/math-modeling-skill"
    )


def initial_gate_state(
    contest: str | None,
    year: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project": {
            "contest": contest or None,
            "year": year or None,
            "initialized_at": now_iso(),
        },
        "gates": {
            gate: {
                "status": "NOT_STARTED"
            }
            for gate in GATES
        },
    }


def cmd_init(
    args: argparse.Namespace,
) -> int:
    skill_root = Path(
        args.skill_root
    ).expanduser().resolve()

    project_root = Path(
        args.project_root
    ).expanduser().resolve()

    validate_roots(
        skill_root,
        project_root,
    )

    version, skill_commit = require_skill_root(
        skill_root
    )

    project_head = require_project_root(
        project_root
    )

    template_root = (
        skill_root
        / "tools"
        / "handoff"
        / "templates"
    )

    targets = [
        project_root / name
        for name in TEMPLATE_FILES
    ]

    targets += [
        project_root / LOCK_REL,
        project_root / STATE_REL,
    ]

    existing = [
        path
        for path in targets
        if path.exists()
    ]

    if existing:
        listing = "\n".join(
            f"- {path.relative_to(project_root)}"
            for path in existing
        )

        raise HandoffError(
            "检测到已有接力状态文件。"
            "为避免覆盖项目历史，init 已停止。\n"
            f"{listing}\n"
            "如确需重新初始化，请先人工备份并移走这些文件。"
        )

    for name in TEMPLATE_FILES:
        source = template_root / name

        if not source.is_file():
            raise HandoffError(
                f"缺少模板：{source}"
            )

    handoff_dir = (
        project_root / ".handoff"
    )

    evidence_dir = (
        project_root / EVIDENCE_DIR_REL
    )

    if handoff_dir.exists():
        raise HandoffError(
            "PROJECT_ROOT 中已经存在 .handoff/。"
            "为避免覆盖历史，init 已停止。"
        )

    handoff_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    evidence_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    # Git 不保存空目录。用占位文件确保跨机器恢复后该目录仍然存在。
    (
        evidence_dir / ".gitkeep"
    ).write_text(
        "",
        encoding="utf-8",
    )

    copied: list[Path] = []

    try:
        for name in TEMPLATE_FILES:
            source = template_root / name
            destination = project_root / name

            shutil.copy2(
                source,
                destination,
            )

            copied.append(
                destination
            )

        skill_lock = {
            "schema_version": SCHEMA_VERSION,
            "upstream_version": version,
            "skill_commit": skill_commit,
            "skill_path_template": skill_path_template(),
            "created_at": now_iso(),
        }

        write_json_atomic(
            project_root / LOCK_REL,
            skill_lock,
        )

        state = initial_gate_state(
            args.contest,
            args.year,
        )

        state["project"][
            "initial_git_head"
        ] = project_head

        write_json_atomic(
            project_root / STATE_REL,
            state,
        )

    except Exception:
        for path in reversed(copied):
            try:
                path.unlink()
            except OSError:
                pass

        shutil.rmtree(
            handoff_dir,
            ignore_errors=True,
        )

        raise

    print(
        "接力状态初始化完成。"
    )

    print(
        f"PROJECT_ROOT: {project_root}"
    )

    print(
        f"Skill VERSION: {version}"
    )

    print(
        f"Skill commit: {skill_commit}"
    )

    print(
        f"Project Git HEAD: {project_head}"
    )

    print(
        "已创建："
    )

    for name in TEMPLATE_FILES:
        print(
            f"  - {name}"
        )

    print(
        f"  - {LOCK_REL.as_posix()}"
    )

    print(
        f"  - {STATE_REL.as_posix()}"
    )

    print(
        f"  - {EVIDENCE_DIR_REL.as_posix()}/"
    )

    print(
        "\n下一步：人工检查模板后执行 git add/commit，"
        "建立项目初始化 checkpoint。"
    )

    return 0


def validate_gate_state_shape(
    state: dict[str, Any],
) -> list[str]:
    issues: list[str] = []

    if state.get(
        "schema_version"
    ) != SCHEMA_VERSION:
        issues.append(
            "GATE_STATE schema_version="
            f"{state.get('schema_version')!r}，"
            f"期望 {SCHEMA_VERSION}"
        )

    gates = state.get(
        "gates"
    )

    if not isinstance(
        gates,
        dict,
    ):
        issues.append(
            "GATE_STATE 缺少 gates 对象"
        )
        return issues

    for gate in GATES:
        entry = gates.get(
            gate
        )

        if not isinstance(
            entry,
            dict,
        ):
            issues.append(
                f"缺少门禁状态：{gate}"
            )
            continue

        status = entry.get(
            "status"
        )

        if status not in STATUSES:
            issues.append(
                f"{gate} 状态非法：{status!r}"
            )

    return issues


def print_check_line(
    kind: str,
    message: str,
) -> None:
    print(
        f"[{kind}] {message}"
    )


def check_pass_gate(
    project_root: Path,
    gate: str,
    entry: dict[str, Any],
) -> list[str]:
    problems: list[str] = []

    commit = entry.get(
        "validated_project_commit"
    )

    if (
        not isinstance(commit, str)
        or not commit
    ):
        problems.append(
            "缺少 validated_project_commit"
        )

    elif not git_commit_exists(
        project_root,
        commit,
    ):
        problems.append(
            "验收 commit 不存在于当前 Git 历史："
            f"{commit}"
        )

    elif not git_is_ancestor(
        project_root,
        commit,
    ):
        problems.append(
            "当前 HEAD 不再包含验收 commit："
            f"{commit}"
        )

    evidence = entry.get(
        "evidence"
    )

    if not isinstance(
        evidence,
        dict,
    ):
        problems.append(
            "缺少 evidence 记录"
        )

    else:
        path_raw = evidence.get(
            "path"
        )

        expected_hash = evidence.get(
            "sha256"
        )

        if (
            not isinstance(path_raw, str)
            or not path_raw
        ):
            problems.append(
                "evidence.path 缺失"
            )

        elif (
            not isinstance(expected_hash, str)
            or not expected_hash
        ):
            problems.append(
                "evidence.sha256 缺失"
            )

        else:
            try:
                evidence_path, relative = (
                    normalized_rel_path(
                        project_root,
                        path_raw,
                    )
                )

                actual_hash = sha256_file(
                    evidence_path
                )

                if actual_hash != expected_hash:
                    problems.append(
                        f"evidence 已变化：{relative}"
                    )

            except (
                HandoffError,
                FileNotFoundError,
            ):
                problems.append(
                    "evidence 不存在或路径无效："
                    f"{path_raw}"
                )

    artifacts = entry.get(
        "artifacts"
    )

    if (
        not isinstance(artifacts, list)
        or not artifacts
    ):
        problems.append(
            "PASS 状态缺少 artifacts"
        )

    else:
        for item in artifacts:
            if not isinstance(
                item,
                dict,
            ):
                problems.append(
                    "artifacts 中存在非法条目"
                )
                continue

            raw = item.get(
                "path"
            )

            expected_hash = item.get(
                "sha256"
            )

            if (
                not isinstance(raw, str)
                or not raw
            ):
                problems.append(
                    "artifact.path 缺失"
                )
                continue

            if (
                not isinstance(expected_hash, str)
                or not expected_hash
            ):
                problems.append(
                    f"artifact.sha256 缺失：{raw}"
                )
                continue

            try:
                path, relative = (
                    normalized_rel_path(
                        project_root,
                        raw,
                    )
                )

                actual_hash = sha256_file(
                    path
                )

                if actual_hash != expected_hash:
                    problems.append(
                        f"artifact 已变化：{relative}"
                    )

            except (
                HandoffError,
                FileNotFoundError,
            ):
                problems.append(
                    "artifact 不存在或路径无效："
                    f"{raw}"
                )

    return problems


def cmd_check(
    args: argparse.Namespace,
) -> int:
    skill_root = Path(
        args.skill_root
    ).expanduser().resolve()

    project_root = Path(
        args.project_root
    ).expanduser().resolve()

    validate_roots(
        skill_root,
        project_root,
    )

    hard_errors: list[str] = []
    strict_issues: list[str] = []

    try:
        version, skill_commit = (
            require_skill_root(
                skill_root
            )
        )

        print_check_line(
            "PASS",
            f"Skill 可读取：VERSION {version}",
        )

    except HandoffError as exc:
        print_check_line(
            "FAIL",
            str(exc),
        )
        return 2

    try:
        project_head = (
            require_project_root(
                project_root
            )
        )

        print_check_line(
            "PASS",
            f"项目 Git 仓库：HEAD {project_head}",
        )

    except HandoffError as exc:
        print_check_line(
            "FAIL",
            str(exc),
        )
        return 2

    required = [
        project_root / name
        for name in TEMPLATE_FILES
    ]

    required += [
        project_root / LOCK_REL,
        project_root / STATE_REL,
    ]

    missing = [
        path
        for path in required
        if not path.is_file()
    ]

    if missing:
        for path in missing:
            hard_errors.append(
                "缺少接力文件："
                f"{path.relative_to(project_root)}"
            )
    else:
        print_check_line(
            "PASS",
            "接力状态文件齐全",
        )

    if not (
        project_root / EVIDENCE_DIR_REL
    ).is_dir():
        hard_errors.append(
            "缺少目录："
            f"{EVIDENCE_DIR_REL.as_posix()}"
        )
    else:
        print_check_line(
            "PASS",
            "存在 "
            f"{EVIDENCE_DIR_REL.as_posix()}/",
        )

    if hard_errors:
        for item in hard_errors:
            print_check_line(
                "FAIL",
                item,
            )

        return 2

    try:
        lock = load_json(
            project_root / LOCK_REL
        )

    except HandoffError as exc:
        print_check_line(
            "FAIL",
            str(exc),
        )
        return 2

    if lock.get(
        "schema_version"
    ) != SCHEMA_VERSION:
        hard_errors.append(
            "SKILL.lock schema_version="
            f"{lock.get('schema_version')!r}，"
            f"期望 {SCHEMA_VERSION}"
        )

    locked_version = lock.get(
        "upstream_version"
    )

    locked_commit = lock.get(
        "skill_commit"
    )

    if locked_version != version:
        hard_errors.append(
            "Skill VERSION 不匹配："
            f"项目要求 {locked_version!r}，"
            f"本机为 {version!r}"
        )

    if locked_commit != skill_commit:
        hard_errors.append(
            "Skill commit 不匹配："
            f"项目要求 {locked_commit!r}，"
            f"本机为 {skill_commit!r}"
        )

    if hard_errors:
        for item in hard_errors:
            print_check_line(
                "FAIL",
                item,
            )
    else:
        print_check_line(
            "PASS",
            "SKILL.lock 与本机 Skill 完全一致",
        )

    try:
        state = load_json(
            project_root / STATE_REL
        )

    except HandoffError as exc:
        print_check_line(
            "FAIL",
            str(exc),
        )
        return 2

    shape_issues = (
        validate_gate_state_shape(
            state
        )
    )

    if shape_issues:
        for item in shape_issues:
            hard_errors.append(
                item
            )

            print_check_line(
                "FAIL",
                item,
            )

    else:
        print_check_line(
            "PASS",
            "GATE_STATE.json 结构有效",
        )

    status_text = git_status_porcelain(
        project_root
    )

    if status_text.strip():
        strict_issues.append(
            "项目 working tree 非 clean"
        )

        print_check_line(
            "WARN",
            "项目 working tree 非 clean",
        )

        lines = (
            status_text
            .rstrip()
            .splitlines()
        )

        for line in lines[:20]:
            print(
                f"       {line}"
            )

        if len(lines) > 20:
            print(
                "       ..."
            )

    else:
        print_check_line(
            "PASS",
            "项目 working tree clean",
        )

    gates = state.get(
        "gates",
        {},
    )

    print(
        "\n门禁状态："
    )

    for gate in GATES:
        entry = gates.get(
            gate,
            {},
        )

        status = entry.get(
            "status",
            "INVALID",
        )

        if status == "PASS":
            problems = check_pass_gate(
                project_root,
                gate,
                entry,
            )

            if problems:
                strict_issues.append(
                    f"{gate} 检测到状态漂移"
                )

                print_check_line(
                    "STALE",
                    f"{gate}: 记录为 PASS，"
                    "但当前证据不再一致",
                )

                for problem in problems:
                    print(
                        f"       - {problem}"
                    )

            else:
                print_check_line(
                    "PASS",
                    f"{gate}: PASS / VALID",
                )

        elif status == "STALE":
            strict_issues.append(
                f"{gate} 当前已标记为 STALE"
            )

            print_check_line(
                "STALE",
                f"{gate}: STALE",
            )

        else:
            print_check_line(
                "INFO",
                f"{gate}: {status}",
            )

    if hard_errors:
        print(
            "\n接力检查：FAIL"
            "（存在结构或 Skill 锁错误）"
        )

        return 2

    if strict_issues:
        if args.strict:
            print(
                "\n接力检查：FAIL"
                "（--strict 下存在未解决状态）"
            )

            for item in strict_issues:
                print(
                    f"  - {item}"
                )

            return 1

        print(
            "\n接力检查：WARN"
        )

        for item in strict_issues:
            print(
                f"  - {item}"
            )

        return 0

    print(
        "\n接力检查：PASS"
    )

    return 0


def require_gate_state(
    project_root: Path,
) -> dict[str, Any]:
    state = load_json(
        project_root / STATE_REL
    )

    issues = validate_gate_state_shape(
        state
    )

    if issues:
        raise HandoffError(
            "GATE_STATE.json 无效：\n"
            + "\n".join(
                f"- {item}"
                for item in issues
            )
        )

    return state


def require_clean_tracked_file(
    project_root: Path,
    raw: str,
) -> tuple[Path, str]:
    path, relative = normalized_rel_path(
        project_root,
        raw,
    )

    if not path.is_file():
        raise HandoffError(
            f"不是普通文件：{relative}"
        )

    if not git_file_tracked(
        project_root,
        relative,
    ):
        raise HandoffError(
            f"文件尚未纳入项目 Git：{relative}"
        )

    if not git_file_clean(
        project_root,
        relative,
    ):
        raise HandoffError(
            "文件存在未提交修改，"
            "不能作为已验收快照："
            f"{relative}"
        )

    return path, relative


def require_gate_evidence_path(
    relative: str,
) -> None:
    prefix = (
        EVIDENCE_DIR_REL
        .as_posix()
        .rstrip("/")
        + "/"
    )

    if not relative.startswith(
        prefix
    ):
        raise HandoffError(
            "门禁 evidence 必须保存在 "
            f"{EVIDENCE_DIR_REL.as_posix()}/ 下："
            f"{relative}"
        )


def cmd_record_gate(
    args: argparse.Namespace,
) -> int:
    project_root = Path(
        args.project_root
    ).expanduser().resolve()

    require_project_root(
        project_root
    )

    gate = args.gate
    status = args.status

    state = require_gate_state(
        project_root
    )

    entry = state[
        "gates"
    ][gate]

    previous_status = entry.get(
        "status",
        "NOT_STARTED",
    )

    if (
        status == "PASS"
        and previous_status
        in {
            "FAIL",
            "BLOCKED",
            "STALE",
        }
        and not args.revalidated
    ):
        raise HandoffError(
            f"{gate} 当前状态为 "
            f"{previous_status}。"
            "如已按原门禁完成独立复验，"
            "请显式增加 --revalidated "
            "后再记录 PASS。"
        )

    if status == "PASS":
        if not args.evidence:
            raise HandoffError(
                "记录 PASS 时必须提供 --evidence。"
            )

        if not args.artifact:
            raise HandoffError(
                "记录 PASS 时至少提供一个 --artifact。"
            )

        whole_status = git_status_porcelain(
            project_root
        )

        if whole_status.strip():
            raise HandoffError(
                "record-gate PASS 前项目 working tree "
                "必须 clean。\n"
                "请先把被验收产物与 evidence "
                "提交为 Git checkpoint，"
                "再记录 PASS。"
            )

        (
            evidence_path,
            evidence_relative,
        ) = require_clean_tracked_file(
            project_root,
            args.evidence,
        )

        require_gate_evidence_path(
            evidence_relative
        )

        artifact_records: list[
            dict[str, Any]
        ] = []

        seen: set[str] = set()

        for raw in args.artifact:
            path, relative = (
                require_clean_tracked_file(
                    project_root,
                    raw,
                )
            )

            if relative in seen:
                continue

            seen.add(
                relative
            )

            artifact_records.append(
                {
                    "path": relative,
                    "sha256": sha256_file(path),
                    "size": path.stat().st_size,
                }
            )

        validated_commit = git_head(
            project_root
        )

        state["gates"][gate] = {
            "status": "PASS",
            "recorded_at": now_iso(),
            "validated_project_commit": (
                validated_commit
            ),
            "evidence": {
                "path": evidence_relative,
                "sha256": sha256_file(
                    evidence_path
                ),
                "size": (
                    evidence_path
                    .stat()
                    .st_size
                ),
            },
            "artifacts": artifact_records,
        }

        if args.actor:
            state[
                "gates"
            ][gate][
                "recorded_by"
            ] = args.actor

        if previous_status in {
            "FAIL",
            "BLOCKED",
            "STALE",
        }:
            state[
                "gates"
            ][gate][
                "revalidated_from"
            ] = previous_status

    elif status in {
        "FAIL",
        "BLOCKED",
    }:
        record: dict[str, Any] = {
            "status": status,
            "recorded_at": now_iso(),
            "project_commit": (
                require_project_root(
                    project_root
                )
            ),
        }

        if args.evidence:
            (
                evidence_path,
                evidence_relative,
            ) = normalized_rel_path(
                project_root,
                args.evidence,
            )

            require_gate_evidence_path(
                evidence_relative
            )

            if not evidence_path.is_file():
                raise HandoffError(
                    "evidence 不是普通文件："
                    f"{evidence_relative}"
                )

            record[
                "evidence"
            ] = {
                "path": evidence_relative,
                "sha256": sha256_file(
                    evidence_path
                ),
                "size": (
                    evidence_path
                    .stat()
                    .st_size
                ),
            }

        if args.reason:
            record[
                "reason"
            ] = args.reason

        if args.actor:
            record[
                "recorded_by"
            ] = args.actor

        state[
            "gates"
        ][gate] = record

    elif status == "PENDING":
        state[
            "gates"
        ][gate] = {
            "status": "PENDING",
            "recorded_at": now_iso(),
        }

        if args.reason:
            state[
                "gates"
            ][gate][
                "reason"
            ] = args.reason

    elif status == "STALE":
        raise HandoffError(
            "请使用 invalidate 子命令"
            "将门禁置为 STALE。"
        )

    elif status == "NOT_STARTED":
        raise HandoffError(
            "record-gate 不负责重置为 NOT_STARTED。"
        )

    else:
        raise HandoffError(
            f"不支持的状态：{status}"
        )

    write_json_atomic(
        project_root / STATE_REL,
        state,
    )

    print(
        f"{gate} 已记录为 {status}。"
    )

    if status == "PASS":
        print(
            "validated_project_commit: "
            f"{state['gates'][gate]['validated_project_commit']}"
        )

        print(
            "artifacts: "
            f"{len(state['gates'][gate]['artifacts'])}"
        )

        print(
            "注意：GATE_STATE.json 现已修改，"
            "请单独提交状态记录。"
        )

    return 0


def cmd_invalidate(
    args: argparse.Namespace,
) -> int:
    project_root = Path(
        args.project_root
    ).expanduser().resolve()

    require_project_root(
        project_root
    )

    state = require_gate_state(
        project_root
    )

    gate = args.gate

    previous = state[
        "gates"
    ][gate]

    if previous.get(
        "status"
    ) == "NOT_STARTED":
        raise HandoffError(
            f"{gate} 尚未开始，"
            "无需标记为 STALE。"
        )

    new_entry = dict(
        previous
    )

    new_entry[
        "status"
    ] = "STALE"

    new_entry[
        "invalidated_at"
    ] = now_iso()

    new_entry[
        "invalidation_reason"
    ] = args.reason

    if args.actor:
        new_entry[
            "invalidated_by"
        ] = args.actor

    state[
        "gates"
    ][gate] = new_entry

    write_json_atomic(
        project_root / STATE_REL,
        state,
    )

    print(
        f"{gate} 已标记为 STALE。"
    )

    print(
        f"原因：{args.reason}"
    )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "数学建模项目跨账号接力状态工具"
            "（纯本地、确定性、不联网）。"
        )
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    p_init = sub.add_parser(
        "init",
        help="初始化项目接力状态",
    )

    p_init.add_argument(
        "--skill-root",
        required=True,
    )

    p_init.add_argument(
        "--project-root",
        required=True,
    )

    p_init.add_argument(
        "--contest",
    )

    p_init.add_argument(
        "--year",
    )

    p_init.set_defaults(
        func=cmd_init
    )

    p_check = sub.add_parser(
        "check",
        help="只读检查接力状态",
    )

    p_check.add_argument(
        "--skill-root",
        required=True,
    )

    p_check.add_argument(
        "--project-root",
        required=True,
    )

    p_check.add_argument(
        "--strict",
        action="store_true",
        help=(
            "working tree 非 clean、"
            "PASS 发生漂移或存在 STALE 时"
            "返回非零退出码"
        ),
    )

    p_check.set_defaults(
        func=cmd_check
    )

    p_record = sub.add_parser(
        "record-gate",
        help="记录一个既有门禁的状态",
    )

    p_record.add_argument(
        "--project-root",
        required=True,
    )

    p_record.add_argument(
        "--gate",
        required=True,
        choices=GATES,
    )

    p_record.add_argument(
        "--status",
        required=True,
        choices=(
            "PENDING",
            "PASS",
            "FAIL",
            "BLOCKED",
        ),
    )

    p_record.add_argument(
        "--evidence",
    )

    p_record.add_argument(
        "--artifact",
        action="append",
        default=[],
        help=(
            "PASS 所保护的项目文件，"
            "可重复提供"
        ),
    )

    p_record.add_argument(
        "--reason",
    )

    p_record.add_argument(
        "--actor",
    )

    p_record.add_argument(
        "--revalidated",
        action="store_true",
        help=(
            "明确声明 FAIL/BLOCKED/STALE "
            "已按原门禁完成独立复验"
        ),
    )

    p_record.set_defaults(
        func=cmd_record_gate
    )

    p_invalidate = sub.add_parser(
        "invalidate",
        help="将一个门禁显式置为 STALE",
    )

    p_invalidate.add_argument(
        "--project-root",
        required=True,
    )

    p_invalidate.add_argument(
        "--gate",
        required=True,
        choices=GATES,
    )

    p_invalidate.add_argument(
        "--reason",
        required=True,
    )

    p_invalidate.add_argument(
        "--actor",
    )

    p_invalidate.set_defaults(
        func=cmd_invalidate
    )

    return parser


def main() -> int:
    parser = build_parser()

    args = parser.parse_args()

    try:
        return int(
            args.func(args)
        )

    except HandoffError as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    except KeyboardInterrupt:
        print(
            "ERROR: 用户中断。",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
