# Git PR Helper MCP

A Python MCP server for safe, reviewable Git branch, commit, push, and pull
request workflows.

Most Git automation jumps straight to action. This server is deliberately
two-phase:

1. Inspect the repository.
2. Propose a concrete plan.
3. Execute only after explicit confirmation.

That makes it useful as a small Model Context Protocol learning project and as a
practical assistant for local development.

## What It Does

- Inspects local Git repositories without changing them.
- Builds a reviewable branch, stage, commit, push, and pull request plan.
- Executes a proposed plan only when `confirm=true`.
- Uses GitHub CLI for PR creation when requested.
- Keeps v1 plans in memory, so stale plans disappear when the server restarts.

## Safety Model

`inspect_repo`, `propose_pr_plan`, and `show_plan` are read-only.

`execute_plan` can mutate a repository, but it has guardrails:

- It does nothing unless `confirm=true`.
- It executes only a previously generated plan.
- It refuses to run if the Git index already has staged changes.
- Push and PR creation can be disabled with `push=false` and `create_pr=false`.

This is still local Git automation. Review plans before execution.

## Tools

### `inspect_repo`

Inspect a local Git repository.

```json
{
  "path": "/path/to/repo"
}
```

Returns current branch, default branch, remote URL, changed files, diff stat,
name-status output, and upstream ahead/behind information.

### `propose_pr_plan`

Build a reviewable plan without changing the repository.

```json
{
  "path": "/path/to/repo",
  "branch_name": "feat/add-config-overrides",
  "commit_message": "Add configurable model overrides",
  "pr_title": "Add configurable model overrides",
  "base_branch": "main",
  "files_to_stage": ["configs/default.yaml"],
  "push": true,
  "create_pr": true
}
```

All fields except `path` are optional. If branch name, commit message, PR title,
base branch, or files are omitted, the server infers conservative defaults from
the current Git state.

### `show_plan`

Return a previously proposed plan by `plan_id`.

```json
{
  "plan_id": "PLAN_ID_FROM_PROPOSE_PR_PLAN"
}
```

### `execute_plan`

Run a proposed plan.

```json
{
  "plan_id": "PLAN_ID_FROM_PROPOSE_PR_PLAN",
  "confirm": true
}
```

If `confirm=false`, the tool returns guidance and does nothing.

## Example Workflow

Ask your MCP client:

```text
Use git-pr-helper to inspect /path/to/repo
```

Then:

```text
Use git-pr-helper to propose a PR plan for /path/to/repo with push=false and create_pr=false
```

Review the returned branch name, files, commit message, and steps. To execute a
local-only branch and commit:

```text
Use git-pr-helper to execute plan PLAN_ID with confirm=true
```

For a full GitHub workflow, propose the plan with `push=true` and
`create_pr=true`.

## Install For Local Development

```bash
git clone https://github.com/miharcan/git-pr-helper-mcp.git
cd git-pr-helper-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
git-pr-helper-mcp
```

The server uses MCP stdio transport by default.

## VS Code MCP Config

Add this to your VS Code MCP user configuration:

```json
{
  "servers": {
    "git-pr-helper": {
      "command": "/path/to/git-pr-helper-mcp/.venv/bin/git-pr-helper-mcp",
      "args": []
    }
  }
}
```

Restart the server from `MCP: List Servers` after code changes.

## Other MCP Clients

Some clients use the `mcpServers` key:

```json
{
  "mcpServers": {
    "git-pr-helper": {
      "command": "/path/to/git-pr-helper-mcp/.venv/bin/git-pr-helper-mcp",
      "args": []
    }
  }
}
```

## GitHub Pull Requests

PR creation uses GitHub CLI:

```bash
gh auth status
```

If `gh` is not installed or authenticated, use `create_pr=false` and create the
PR manually after the branch is pushed.

## Development

```bash
source .venv/bin/activate
pytest -q
ruff check .
```

CI runs the same checks on Python 3.10 through 3.13.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Limitations

- Plans are stored in memory for v1.
- PR creation currently depends on GitHub CLI.
- The server does not run tests for the target repository before committing.
- The server does not yet persist audit logs of executed plans.
