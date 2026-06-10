from __future__ import annotations

from pydantic import BaseModel, Field


class RepoInspection(BaseModel):
    repo_path: str
    current_branch: str
    default_branch: str
    remote_url: str | None
    status: list[str]
    changed_files: list[str]
    diff_stat: str
    name_status: list[str]
    upstream: str | None
    ahead: int
    behind: int


class PlanStep(BaseModel):
    order: int
    action: str
    command: list[str] = Field(default_factory=list)
    description: str
    mutates_repo: bool = True


class PullRequestPlan(BaseModel):
    plan_id: str
    repo_path: str
    base_branch: str
    working_branch: str
    new_branch: str | None
    files_to_stage: list[str]
    commit_message: str
    pr_title: str
    pr_body: str
    push: bool
    create_pr: bool
    steps: list[PlanStep]
    notes: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    plan_id: str
    executed: bool
    outputs: list[str]
    next_steps: list[str]
