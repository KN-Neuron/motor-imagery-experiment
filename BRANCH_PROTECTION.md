# Branch Protection Setup Instructions

To enforce code quality and ensure all CI checks pass before merging, follow these steps to set up branch protection rules in your GitHub repository:

## Setting up Branch Protection Rules

1. Navigate to your GitHub repository
2. Go to the "Settings" tab
3. Click on "Branches" in the left sidebar
4. Under "Branch protection rules", click "Add rule"
5. Enter "main" as the branch name pattern (or your primary branch)
6. Select the following options:
   - [x] Require pull request reviews before merging
     - Set "Required number of approvals" to at least 1 (or your preferred number)
   - [x] Require status checks to pass before merging
     - Check "Require branches to be up to date before merging"
     - In "Status checks that are required", you should see the following checks from the workflows we created:
       - `test (3.13)` - This is from the python-ci.yml workflow
       - `pre-commit` - This is from the pre-commit.yml workflow
   - [x] Require conversation resolution before merging
7. Click "Create"

## Required Status Checks

The following status checks will be enforced:
- `test (3.13)`: Runs formatting, linting, type checking, and tests
- `pre-commit`: Runs pre-commit hooks including formatting and additional checks
- If you set up security scanning, that would also appear as `security-scan`

## Recommended Additional Settings

For even better code quality enforcement:
- Consider requiring multiple reviewers for critical repositories
- Set up "Restrict who can push to matching branches" for extra security
- Consider setting up code owners for different parts of the codebase
