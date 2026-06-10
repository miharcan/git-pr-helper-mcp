from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from git_pr_helper_mcp.planner import inspect_repo, propose_plan


def run(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    run(["git", "init", "-b", "main"], tmp_path)
    run(["git", "config", "user.email", "test@example.com"], tmp_path)
    run(["git", "config", "user.name", "Test User"], tmp_path)
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    run(["git", "add", "README.md"], tmp_path)
    run(["git", "commit", "-m", "Initial commit"], tmp_path)
    return tmp_path


def test_inspect_repo_reports_changed_files(repo: Path) -> None:
    (repo / "README.md").write_text("# Demo\n\nChanged.\n", encoding="utf-8")

    inspection = inspect_repo(str(repo))

    assert inspection.current_branch == "main"
    assert inspection.changed_files == ["README.md"]
    assert "README.md" in inspection.diff_stat


def test_propose_plan_infers_branch_and_commit(repo: Path) -> None:
    (repo / "src.py").write_text("print('hello')\n", encoding="utf-8")

    plan = propose_plan(str(repo), create_pr=False, push=False)

    assert plan.new_branch == "feat/update-src-py"
    assert plan.files_to_stage == ["src.py"]
    assert plan.commit_message == "Update src.py"
    assert [step.action for step in plan.steps] == ["create_branch", "stage_files", "commit"]


def test_propose_plan_rejects_missing_selected_file(repo: Path) -> None:
    (repo / "README.md").write_text("# Demo\n\nChanged.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not currently changed"):
        propose_plan(str(repo), files_to_stage=["missing.py"])


def test_pr_body_only_lists_selected_files(repo: Path) -> None:
    (repo / "README.md").write_text("# Demo\n\nChanged.\n", encoding="utf-8")
    (repo / "notes.txt").write_text("scratch\n", encoding="utf-8")

    plan = propose_plan(str(repo), files_to_stage=["README.md"], push=False, create_pr=False)

    assert "`README.md`" in plan.pr_body
    assert "`notes.txt`" not in plan.pr_body
