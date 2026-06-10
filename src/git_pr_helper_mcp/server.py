from __future__ import annotations

import shutil
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import git_ops
from .models import ExecutionResult, PullRequestPlan, RepoInspection
from .planner import get_plan, inspect_repo as build_inspection, propose_plan

mcp = FastMCP("git-pr-helper-mcp")


@mcp.tool()
def inspect_repo(path: str = ".") -> RepoInspection:
    """Inspect a local Git repository without changing it."""
    return build_inspection(path)


@mcp.tool()
def propose_pr_plan(
    path: str = ".",
    branch_name: str | None = None,
    commit_message: str | None = None,
    pr_title: str | None = None,
    base_branch: str | None = None,
    files_to_stage: list[str] | None = None,
    push: bool = True,
    create_pr: bool = True,
) -> PullRequestPlan:
    """Create a reviewable plan for branch, stage, commit, push, and PR creation."""
    return propose_plan(
        path=path,
        branch_name=branch_name,
        commit_message=commit_message,
        pr_title=pr_title,
        base_branch=base_branch,
        files_to_stage=files_to_stage,
        push=push,
        create_pr=create_pr,
    )


@mcp.tool()
def show_plan(plan_id: str) -> PullRequestPlan:
    """Return a previously proposed plan."""
    return get_plan(plan_id)


@mcp.tool()
def execute_plan(plan_id: str, confirm: bool = False) -> ExecutionResult:
    """Execute a proposed plan only after confirm is true."""
    plan = get_plan(plan_id)
    if not confirm:
        return ExecutionResult(
            plan_id=plan_id,
            executed=False,
            outputs=["Plan was not executed because confirm=false."],
            next_steps=["Review the plan, then call execute_plan with confirm=true."],
        )

    repo = Path(plan.repo_path)
    git_ops.ensure_clean_index(repo)
    outputs: list[str] = []

    if plan.new_branch:
        outputs.append(git_ops.run(["git", "switch", "-c", plan.new_branch], repo))

    outputs.append(git_ops.run(["git", "add", *plan.files_to_stage], repo))
    outputs.append(git_ops.run(["git", "commit", "-m", plan.commit_message], repo))

    active_branch = plan.new_branch or git_ops.current_branch(repo)
    if plan.push:
        outputs.append(git_ops.run(["git", "push", "-u", "origin", active_branch], repo))

    if plan.create_pr:
        if not shutil.which("gh"):
            raise ValueError("GitHub CLI is not installed, so the pull request cannot be created.")
        outputs.append(
            git_ops.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--base",
                    plan.base_branch,
                    "--head",
                    active_branch,
                    "--title",
                    plan.pr_title,
                    "--body",
                    plan.pr_body,
                ],
                repo,
            )
        )

    return ExecutionResult(
        plan_id=plan_id,
        executed=True,
        outputs=[output for output in outputs if output],
        next_steps=["Review the created commit, pushed branch, and pull request."],
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
