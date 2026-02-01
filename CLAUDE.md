# Claude Code Project Notes

## Branching Workflow

1. Always start from an updated `main` branch
2. Create a new branch named `minor/na/<feature_name>` where `feature_name` is a brief description joined by underscores (e.g., `minor/na/add_moderation_queue`)
3. When ready, push the branch to the remote and open a PR against `main`

## Python / Django

Always use the project virtualenv when running Python or Django commands:

```
.venv/bin/python manage.py <command>
```
