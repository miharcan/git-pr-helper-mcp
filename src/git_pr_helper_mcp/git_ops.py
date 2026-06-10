from __future__ import annotations

import subprocess
from pathlib import Path


class GitCommandError(RuntimeError):
    def __init__(self, command: list[str], cwd: Path, stderr: str):
        message = f"Command failed in {cwd}: {' '.join(command)}\n{stderr.strip()}"
        super().__init__(message)
        self.command = command
        self.cwd = cwd
        self.stderr = stderr


def run(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise GitCommandError(command=command, cwd=cwd, stderr=completed.stderr)
    return completed.stdout.strip()


def resolve_repo(path: str) -> Path:
    repo = Path(path).expanduser().resolve()
    if not repo.exists():
        raise ValueError(f"Path does not exist: {repo}")
    root = run(["git", "rev-parse", "--show-toplevel"], repo)
    return Path(root).resolve()


def current_branch(repo: Path) -> str:
    return run(["git", "branch", "--show-current"], repo)


def default_branch(repo: Path) -> str:
    candidates = [
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "--short"],
        ["git", "config", "--get", "init.defaultBranch"],
    ]
    for command in candidates:
        try:
            value = run(command, repo)
        except GitCommandError:
            continue
        if value:
            return value.removeprefix("origin/")
    for branch in ("main", "master"):
        try:
            run(["git", "rev-parse", "--verify", branch], repo)
            return branch
        except GitCommandError:
            pass
    return "main"


def remote_url(repo: Path, remote: str = "origin") -> str | None:
    try:
        return run(["git", "remote", "get-url", remote], repo)
    except GitCommandError:
        return None


def porcelain_status(repo: Path) -> list[str]:
    output = run(["git", "status", "--porcelain=v1"], repo)
    return [line for line in output.splitlines() if line]


def changed_files(repo: Path) -> list[str]:
    output = run(["git", "status", "--porcelain=v1"], repo)
    files: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        path = line[2:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def short_diff_stat(repo: Path) -> str:
    return run(["git", "diff", "--stat"], repo)


def diff_stat_for_paths(repo: Path, paths: list[str]) -> str:
    if not paths:
        return ""
    return run(["git", "diff", "--stat", "--", *paths], repo)


def staged_diff_stat(repo: Path) -> str:
    return run(["git", "diff", "--cached", "--stat"], repo)


def diff_name_status(repo: Path) -> list[str]:
    output = run(["git", "diff", "--name-status"], repo)
    cached = run(["git", "diff", "--cached", "--name-status"], repo)
    untracked = [line[2:].strip() for line in porcelain_status(repo) if line.startswith("?? ")]
    lines = [line for line in output.splitlines() + cached.splitlines() if line]
    lines.extend(f"A\t{path}" for path in untracked)
    return sorted(set(lines))


def ahead_behind(repo: Path, branch: str) -> dict[str, int | str | None]:
    upstream = None
    try:
        upstream = run(["git", "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"], repo)
    except GitCommandError:
        return {"upstream": None, "ahead": 0, "behind": 0}
    counts = run(["git", "rev-list", "--left-right", "--count", f"{upstream}...HEAD"], repo)
    behind, ahead = [int(value) for value in counts.split()]
    return {"upstream": upstream, "ahead": ahead, "behind": behind}


def ensure_clean_index(repo: Path) -> None:
    if run(["git", "diff", "--cached", "--name-only"], repo):
        raise ValueError("Index already has staged changes. Commit or unstage them before executing a plan.")


def is_ancestor(repo: Path, base: str, branch: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, branch],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0
