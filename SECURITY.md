# Security

Git PR Helper MCP can mutate local repositories when `execute_plan` is called
with `confirm=true`.

Use the read-only tools first:

- `inspect_repo`
- `propose_pr_plan`
- `show_plan`

Review the generated plan before execution. For safer testing, set:

```json
{
  "push": false,
  "create_pr": false
}
```

This limits execution to local branch creation, staging, and committing.

## Reporting Issues

Please open a GitHub issue with:

- MCP client used
- Python version
- Git version
- Minimal reproduction steps
- Expected and actual behavior
