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

## Automatic Tokens

All workflows use GitHub's automatic `GITHUB_TOKEN` which is:
- Automatically provided by GitHub Actions
- No setup or configuration required
- Has appropriate permissions based on workflow needs
- Automatically scoped to the repository

## Optional Enhancements

### Safety API Key (Optional)
The Safety check works without an API key, but with limited checks. For full vulnerability database access:
1. Get a free API key from [safetycli.com](https://safetycli.com)
2. Add it as a repository secret named `SAFETY_API_KEY`
3. Update the security workflow to use it:

```yaml
- name: Run Safety check
  run: |
    safety check --key ${{ secrets.SAFETY_API_KEY }} || true
```

### CodeQL Setup (One-time)
CodeQL will work automatically, but you may want to:
1. Enable CodeQL in repository settings (Settings → Code security and analysis)
2. This enables additional features like security alerts

### Dependabot
Dependabot is configured in `.github/dependabot.yml` and works automatically. No tokens needed.

## Permissions

Workflows have minimal required permissions:
- Most workflows: `contents: read` (default)
- CodeQL: `security-events: write` (for security alerts)
- Release: `contents: write` (to create releases)

All permissions are explicitly set in workflow files for security best practices.
