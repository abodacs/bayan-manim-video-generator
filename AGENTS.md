# Agent instructions

## Pull requests

When a task requires a pull request, use the GitHub CLI REST API rather than a
browser workflow or `gh pr create`:

1. Confirm the current branch and target repository:

   ```bash
   git branch --show-current
   gh repo view --json nameWithOwner,defaultBranchRef
   ```

2. Commit only the files belonging to the task, then push the feature branch:

   ```bash
   git push --set-upstream origin <branch>
   ```

3. Create the pull request through the pulls endpoint:

   ```bash
   gh api repos/<owner>/<repo>/pulls \
     --method POST \
     -f title="<title>" \
     -f head="<branch>" \
     -f base="main" \
     -f body="<summary and validation>"
   ```

Use the repository’s default branch as `base`, include a concise summary and
validation notes in the body, and report the returned pull-request URL.
