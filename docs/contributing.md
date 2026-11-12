# Jira and pull requests

Follow the existing sprint and Jira assignments. Each developer works on a local clone and starts each issue branch from the latest `main` after the foundation merges.

1. Open your assigned Jira issue and check its dependencies and acceptance criteria.
2. Update your local copy and create an issue branch. For example:

   ```sh
   git switch main
   git pull --ff-only
   git switch -c WEZA-36/customer-portal-layout
   ```

3. Work in the relevant folder. Coordinate edits to the workspace lockfile, API contracts and migrations with anyone touching those files.
4. Run the checks in the README. Stage the files for your issue and review `git diff --cached`. Use the issue key in your commit and pull request title.
5. Push your issue branch and open a pull request against `main`. Include the Jira link, test results, and setup or migration steps where relevant. Ask a teammate to review the change.
6. Resolve feedback and follow the team's approval process before merging. Update the Jira issue with the pull request and refresh local `main` before starting the next issue.
