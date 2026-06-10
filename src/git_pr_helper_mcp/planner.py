from __future__ import annotations

import re
import uuid
from pathlib import Path

from . import git_ops
from .models import PlanStep, PullRequestPlan, RepoInspection


PLAN_STORE: dict[str, PullRequestPlan] = {}


def inspect_repo(path: str) -> RepoInspection:
    repo = git_ops.resolve_repo(path)
    branch = git_ops.current_branch(repo)
    tracking = git_ops.ahead_behind(repo, branch) if branch else {"upstream": None, "ahead": 0, "behind": 0}
    return RepoInspection(
        repo_path=str(repo),
        current_branch=branch,
        default_branch=git_ops.default_branch(repo),
        remote_url=git_ops.remote_url(repo),
        status=git_ops.porcelain_status(repo),
        changed_files=git_ops.changed_files(repo),
        diff_stat=git_ops.short_diff_stat(repo),
        name_status=git_ops.diff_name_status(repo),
        upstream=tracking["upstream"],
        ahead=int(tracking["ahead"]),
        behind=int(tracking["behind"]),
    )


def _slug(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return value[:48] or "update"


def _infer_summary(files: list[str]) -> str:
    if not files:
        return "Update project files"
    top_dirs = sorted({Path(file).parts[0] for file in files if Path(file).parts})
    if len(files) == 1:
        return f"Update {files[0]}"
    if len(top_dirs) == 1:
        return f"Update {top_dirs[0]} files"
    if len(top_dirs) <= 3:
        return f"Update {', '.join(top_dirs)} files"
    return f"Update {len(files)} files"


def _pr_body(summary: str, files: list[str], diff_stat: str) -> str:
    file_lines = "\n".join(f"- `{file}`" for file in files)
    stat = diff_stat or "No diff stat available for the selected files."
    return (
        "## Summary\n"
        f"- {summary}\n\n"
        "## Changed files\n"
        f"{file_lines or '- No changed files detected.'}\n\n"
        "## Validation\n"
        "- Not run by git-pr-helper-mcp.\n\n"
        "## Diff stat\n"
        "```text\n"
        f"{stat}\n"
        "```"
    )


def propose_plan(
    path: str,
    branch_name: str | None = None,
    commit_message: str | None = None,
    pr_title: str | None = None,
    base_branch: str | None = None,
    files_to_stage: list[str] | None = None,
    push: bool = True,
    create_pr: bool = True,
) -> PullRequestPlan:
    inspection = inspect_repo(path)
    if not inspection.changed_files:
        raise ValueError("No changed files found. Make a local change before proposing a PR plan.")

    selected_files = files_to_stage or inspection.changed_files
    missing = sorted(set(selected_files) - set(inspection.changed_files))
    if missing:
        raise ValueError(f"Selected files are not currently changed: {missing}")

    summary = _infer_summary(selected_files)
    selected_diff_stat = git_ops.diff_stat_for_paths(Path(inspection.repo_path), selected_files)
    commit = commit_message or summary
    title = pr_title or summary
    base = base_branch or inspection.default_branch
    new_branch = branch_name or f"feat/{_slug(title)}"
    current = inspection.current_branch
    needs_branch = current != new_branch

    steps: list[PlanStep] = []
    order = 1
    if needs_branch:
        steps.append(
            PlanStep(
                order=order,
                action="create_branch",
                command=["git", "switch", "-c", new_branch],
                description=f"Create and switch to branch `{new_branch}` from `{current}`.",
            )
        )
        order += 1

    steps.append(
        PlanStep(
            order=order,
            action="stage_files",
            command=["git", "add", *selected_files],
            description=f"Stage {len(selected_files)} changed file(s).",
        )
    )
    order += 1
    steps.append(
        PlanStep(
            order=order,
            action="commit",
            command=["git", "commit", "-m", commit],
            description=f"Create commit `{commit}`.",
        )
    )
    order += 1
    if push:
        steps.append(
            PlanStep(
                order=order,
                action="push",
                command=["git", "push", "-u", "origin", new_branch],
                description=f"Push `{new_branch}` to origin.",
            )
        )
        order += 1
    if create_pr:
        steps.append(
            PlanStep(
                order=order,
                action="create_pr",
                command=[
                    "gh",
                    "pr",
                    "create",
                    "--base",
                    base,
                    "--head",
                    new_branch,
                    "--title",
                    title,
                    "--body",
                    "<generated body>",
                ],
                description=f"Open a pull request from `{new_branch}` into `{base}`.",
            )
        )

    plan = PullRequestPlan(
        plan_id=uuid.uuid4().hex,
        repo_path=inspection.repo_path,
        base_branch=base,
        working_branch=current,
        new_branch=new_branch if needs_branch else None,
        files_to_stage=selected_files,
        commit_message=commit,
        pr_title=title,
        pr_body=_pr_body(summary, selected_files, selected_diff_stat),
        push=push,
        create_pr=create_pr,
        steps=steps,
        notes=[
            "Review this plan before calling execute_plan.",
            "execute_plan refuses to run if the Git index already has staged changes.",
        ],
    )
    PLAN_STORE[plan.plan_id] = plan
    return plan


def get_plan(plan_id: str) -> PullRequestPlan:
    try:
        return PLAN_STORE[plan_id]
    except KeyError as exc:
        raise ValueError(f"Unknown plan id: {plan_id}") from exc
