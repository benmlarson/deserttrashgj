# Claude Code Project Notes

## Branching Workflow

**Before writing any code for a new feature or change**, always complete steps 1–2 first:

1. Fetch and checkout the latest `main` branch (`git fetch origin main && git checkout main && git pull origin main`)
2. Create a new branch named `minor/na/<feature_name>` where `feature_name` is a brief description joined by underscores (e.g., `minor/na/add_moderation_queue`)
3. Implement the changes on this branch
4. When ready, push the branch to the remote and open a PR against `main`

## Python / Django

Always use the project virtualenv when running Python or Django commands:

```
.venv/bin/python manage.py <command>
```
