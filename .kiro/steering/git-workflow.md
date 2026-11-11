---
inclusion: always
---

# Git Workflow — Cartoon Animation Studio

## Branch and PR Convention

**Default base branch:** `develop`

All feature branches and stage branches must PR into `develop`, NOT `main`.

```
feature/stage-X-X-description  →  PR into develop
fix/description                 →  PR into develop
develop                         →  PR into main  (releases only)
```

## Rules for Every Stage

1. Push completed previous stage work to its branch
2. Create PR targeting `develop` (not `main`)
3. Create new branch for next stage from `develop` (after PR merges) or from latest tip if parallel
4. Implement next stage on that branch
5. Commit and push
6. Create PR targeting `develop`
7. Wait for human review

## Branch Naming

- `feature/stage-4-2-description`
- `feature/stage-5-description`
- `fix/brief-description`

## Commit Message Convention

```
stage-X.X: brief summary

- Detail 1
- Detail 2
```

or for fixes:
```
fix: brief description of what was fixed
```

## PR Checks (GitHub Actions)

CI runs on push to `develop`, `feature/**`, `fix/**`.
PR checks run on PRs targeting `develop` and `main`.

Do NOT raise PRs directly to `main` for feature work.
Only `develop` → `main` merges are permitted for releases.

## Repository

- Remote: https://github.com/kotlinandfluttertutorial-lab/Cartoon-Animation-Studio.git
- Default branch: `develop`
- Release branch: `main`
