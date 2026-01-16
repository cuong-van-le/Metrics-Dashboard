# GitHub Workflows

This directory contains GitHub Actions workflows for CI/CD, security, and code quality.

## Workflow Overview

### Tests (`tests.yml`)

- Runs unit tests on Python 3.10, 3.11, and 3.12
- No AWS credentials required
- Runs on push and pull requests

### Security Scan (`security.yml`)

- **Bandit**: Python security linting (no tokens needed)
- **Safety**: Dependency vulnerability checks (works without API key, but free tier has limited checks)
- **CodeQL**: Static code analysis (uses automatic GITHUB_TOKEN)
- Runs on push, PR, and weekly schedule

### Code Quality (`code-quality.yml`)

- **Ruff**: Fast Python linter
- **Black**: Code formatter
- **isort**: Import sorter
- **MyPy**: Type checker
- **Radon**: Complexity analysis
- All tools run locally, no tokens needed

### Dependency Review (`dependency-review.yml`)

- Reviews dependencies in pull requests
- Uses automatic GITHUB_TOKEN
- Runs on pull requests only

### Release (`release.yml`)

- Creates GitHub releases when version tags are pushed
- Uses automatic GITHUB_TOKEN (no setup needed)
- Runs tests before creating release
- Generates changelog automatically

## Permissions

Workflows have minimal required permissions:

- Most workflows: `contents: read` (default)
- CodeQL: `security-events: write` (for security alerts)
- Release: `contents: write` (to create releases)

All permissions are explicitly set in workflow files for security best practices.
