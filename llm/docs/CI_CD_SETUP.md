# CI/CD Setup Guide - Intelia Expert LLM

## Overview

This document describes the CI/CD pipelines configured for the Intelia Expert LLM project to ensure code quality, security, and reliability.

## Table of Contents

1. [Workflows Overview](#workflows-overview)
2. [Quality Checks Workflow](#quality-checks-workflow)
3. [Security Audit Workflow](#security-audit-workflow)
4. [Local Development](#local-development)
5. [GitHub Configuration](#github-configuration)
6. [Troubleshooting](#troubleshooting)

---

## Workflows Overview

### 1. Quality Checks (`.github/workflows/quality-checks.yml`)

**Trigger:** On every push/PR to `main` or `develop` branches
**Duration:** ~5-10 minutes
**Purpose:** Ensure code quality and prevent regressions

**Checks performed:**
- ✅ **Ruff** - Python linting (PEP 8, security patterns)
- ✅ **Black** - Code formatting verification
- ✅ **Bandit** - Security vulnerability scanning (blocks on HIGH severity)
- ℹ️ **Pyright** - Type checking (informational only)
- ℹ️ **pip-audit** - CVE vulnerability check (informational)

**Exit criteria:**
- MUST pass: Ruff, Black, Bandit (no HIGH severity)
- CAN fail: Pyright, pip-audit (warnings only)

---

### 2. Security Audit (`.github/workflows/security-audit.yml`)

**Trigger:** Monthly (1st of each month at 9:00 AM UTC) + manual
**Duration:** ~15-20 minutes
**Purpose:** Comprehensive security assessment

**Checks performed:**
- 🔒 **Bandit** - Full security scan (all severity levels)
- 🔒 **pip-audit** - Known CVE vulnerabilities in dependencies
- 🔒 **Safety** - Dependency security database check
- 🔒 **Semgrep** - Static Application Security Testing (SAST)
- 🔒 **Secret scanning** - Hardcoded credentials detection

**Automated actions:**
- Creates GitHub issue if HIGH severity found
- Uploads detailed reports as artifacts (90-day retention)
- (Optional) Slack notification on failure

---

## Quality Checks Workflow

### When It Runs

```yaml
on:
  push:
    branches: [ main, develop ]
    paths:
      - 'llm/**/*.py'
      - 'rag/**/*.py'
      - 'llm/requirements.txt'
```

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`
- Only when Python files or dependencies change

### What Happens

#### Step 1: Ruff Linting
```bash
ruff check . --output-format=github
```

**Checks for:**
- PEP 8 style violations
- Security issues (bare excepts, hardcoded secrets)
- Code smells (unused variables, imports)
- Anti-patterns (boolean comparisons)

**Status:** ❌ **BLOCKS merge** if errors found

---

#### Step 2: Black Formatting
```bash
black --check --diff .
```

**Checks for:**
- Consistent code formatting
- Line length (default 88 chars)
- String quotes, imports, spacing

**Status:** ❌ **BLOCKS merge** if not formatted

**Fix locally:**
```bash
cd llm
black .
```

---

#### Step 3: Bandit Security Scan
```bash
bandit -r . -f json --exclude './tests/*,./scripts/*'
```

**Checks for:**
- SQL injection vulnerabilities
- Command injection risks
- Insecure cryptography (MD5, weak ciphers)
- Hardcoded passwords/tokens
- Unsafe YAML/pickle usage

**Status:** ❌ **BLOCKS merge** if HIGH severity found

---

#### Step 4: Pyright Type Checking
```bash
pyright --outputjson > pyright_report.json
```

**Checks for:**
- Type hint coverage
- Type mismatches
- Missing return types
- Incorrect function signatures

**Status:** ℹ️ **INFORMATIONAL** (does not block merge)

**Rationale:** Type hints are being added gradually (578 errors currently)

---

#### Step 5: pip-audit CVE Check
```bash
pip-audit --format json
```

**Checks for:**
- Known CVE vulnerabilities in dependencies
- Outdated packages with security patches

**Status:** ℹ️ **INFORMATIONAL** (does not block merge)

**Rationale:** Some CVEs may be false positives or require major version upgrades

---

### PR Comments

The workflow automatically comments on PRs with a summary:

```markdown
## 🔍 Code Quality Report

### ✅ All critical checks passed!

**Checks performed:**
- ✓ Ruff linting
- ✓ Black formatting
- ✓ Bandit security scan (no HIGH severity issues)
- ℹ️ Pyright type checking (informational)
- ℹ️ pip-audit CVE check (informational)
```

---

## Security Audit Workflow

### When It Runs

**Scheduled:**
```yaml
on:
  schedule:
    - cron: '0 9 1 * *'  # 1st of every month at 9:00 AM UTC
```

**Manual trigger:**
```bash
# Go to GitHub Actions → Security Audit → Run workflow
```

### What It Does

#### 1. Comprehensive Bandit Scan
```bash
bandit -r . -f json -o bandit_full_report.json -ll
```

**Includes:**
- All severity levels (HIGH, MEDIUM, LOW)
- All file types (including tests, scripts)
- Detailed issue descriptions

---

#### 2. Full Dependency Audit
```bash
pip-audit --format json --output pip_audit_full.json
safety check --json --output safety_report.json
```

**Checks:**
- **pip-audit**: Official Python Security Database
- **Safety**: PyUp.io vulnerability database
- Cross-references multiple sources

---

#### 3. SAST with Semgrep
```bash
semgrep --config=auto --json --output=semgrep_report.json .
```

**Detects:**
- SQL injection patterns
- XSS vulnerabilities
- Path traversal risks
- Insecure deserialization
- OWASP Top 10 issues

---

#### 4. Secret Scanning
```bash
grep -r "api[_-]key.*=.*['\"]" --include="*.py" .
grep -r "password.*=.*['\"]" --include="*.py" .
grep -r "token.*=.*['\"]" --include="*.py" .
```

**Looks for:**
- Hardcoded API keys
- Hardcoded passwords
- OAuth tokens
- AWS credentials

---

### Automated Issue Creation

If HIGH severity issues are found:

```yaml
Title: Security Audit: 3 HIGH severity issue(s) found
Labels: security, high-priority
```

**Issue body includes:**
- Number of HIGH severity issues
- Link to workflow run with detailed reports
- Recommended next steps

---

### Report Artifacts

All reports are uploaded as artifacts (90-day retention):

```
security-audit-reports-{run_number}/
├── bandit_full_report.json
├── bandit_full_report.txt
├── pip_audit_full.json
├── pip_audit_full.md
├── safety_report.json
├── safety_report.txt
├── semgrep_report.json
└── semgrep_report.txt
```

**Download:** GitHub Actions → Workflow Run → Artifacts

---

## Local Development

### Running Quality Checks Locally

Before pushing code, run the same checks locally:

```bash
cd llm

# Full quality check suite
bash run_quality_checks.sh

# Individual checks
ruff check .                    # Linting
black --check .                 # Formatting
bandit -r . -ll                 # Security
pyright                         # Type checking
pip-audit                       # CVE check
```

---

### Auto-fix Common Issues

```bash
# Auto-fix Ruff errors
ruff check . --fix

# Auto-format with Black
black .

# Fix import order
ruff check . --select I --fix
```

---

### Pre-commit Hook (Optional)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
cd llm

echo "Running pre-commit quality checks..."

ruff check . || {
    echo "❌ Ruff linting failed"
    exit 1
}

black --check . || {
    echo "❌ Black formatting failed. Run: black ."
    exit 1
}

echo "✅ Pre-commit checks passed!"
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## GitHub Configuration

### Required Setup

#### 1. Enable GitHub Actions

**Settings → Actions → General:**
- ✅ Allow all actions and reusable workflows
- ✅ Read and write permissions
- ✅ Allow GitHub Actions to create and approve pull requests

---

#### 2. Branch Protection Rules

**Settings → Branches → Add rule:**

**Branch name pattern:** `main`

**Protect matching branches:**
- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
  - ✅ `quality-checks / Quality & Linting`
- ✅ Require branches to be up to date before merging
- ✅ Do not allow bypassing the above settings

**Result:** Cannot merge to `main` if quality checks fail

---

#### 3. Optional: Slack Notifications

**Add Slack webhook:**

1. Create Slack Incoming Webhook: https://api.slack.com/messaging/webhooks
2. Add GitHub secret: `Settings → Secrets → Actions → New repository secret`
   - Name: `SLACK_WEBHOOK_URL`
   - Value: `https://hooks.slack.com/services/...`

3. Uncomment in `security-audit.yml`:
```yaml
- name: Notify on Slack
  if: failure()
  run: |
    curl -X POST -H 'Content-type: application/json' \
      --data '{"text":"Security Audit Failed"}' \
      ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Troubleshooting

### Issue: Workflow fails on "Install dependencies"

**Error:**
```
ERROR: Could not find a version that satisfies the requirement X
```

**Solution:**
1. Verify `requirements.txt` is valid
2. Check Python version compatibility (workflow uses 3.11)
3. Update workflow to use correct Python version

---

### Issue: Bandit reports HIGH severity

**Error:**
```
Issue: [B303:blacklist] Use of insecure MD2, MD4, MD5, or SHA1 hash function
```

**Solution:**
1. Review Bandit report in workflow artifacts
2. If legitimate use (e.g., cache keys), add `# nosec` comment:
   ```python
   hash_obj = hashlib.md5(data.encode(), usedforsecurity=False)  # nosec
   ```
3. If security issue, fix the code

---

### Issue: Black formatting fails

**Error:**
```
would reformat file.py
```

**Solution:**
```bash
cd llm
black .
git add .
git commit -m "chore: Auto-format with Black"
```

---

### Issue: Ruff errors on import order

**Error:**
```
I001 Import block is un-sorted or un-formatted
```

**Solution:**
```bash
cd llm
ruff check . --select I --fix
```

---

### Issue: Workflow doesn't trigger

**Checklist:**
- ✅ Workflow file is in `.github/workflows/`
- ✅ File has `.yml` or `.yaml` extension
- ✅ Valid YAML syntax (use yamllint)
- ✅ Branch name matches trigger condition
- ✅ File path matches `paths` filter
- ✅ GitHub Actions enabled in repository settings

---

## Quality Metrics

### Current Status (2025-10-09)

| Check | Status | Count |
|-------|--------|-------|
| Ruff errors | ✅ Pass | 0 |
| Black formatting | ✅ Pass | 0 issues |
| Bandit HIGH | ✅ Pass | 0 |
| Bandit MEDIUM | ⚠️ Info | ~10 |
| Bandit LOW | ⚠️ Info | ~30 |
| Pyright errors | ⚠️ Info | 578 |
| CVE vulnerabilities | ✅ Pass | 0 |

---

### Quality Goals (6 months)

| Metric | Current | Target |
|--------|---------|--------|
| Ruff errors | 0 | 0 (maintain) |
| Bandit HIGH | 0 | 0 (maintain) |
| Bandit MEDIUM | ~10 | <5 |
| Pyright errors | 578 | <300 (50% reduction) |
| Type hint coverage | ~30% | 70% |

---

## Additional Resources

### Documentation
- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
- [Black Code Style](https://black.readthedocs.io/)
- [Bandit Security Checks](https://bandit.readthedocs.io/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)

### Tools
- [Ruff Playground](https://play.ruff.rs/) - Test linting rules online
- [YAML Validator](https://www.yamllint.com/) - Validate workflow syntax
- [Semgrep Registry](https://semgrep.dev/explore) - Browse security rules

---

## Maintenance

### Monthly Tasks
- ✅ Review security audit reports (automated)
- ✅ Update dependencies with security patches
- ✅ Triage automated security issues

### Quarterly Tasks
- ✅ Review and update Bandit baseline
- ✅ Assess type hint coverage progress
- ✅ Update workflow versions (actions/checkout, etc.)

### Annual Tasks
- ✅ Comprehensive security audit with external tools
- ✅ Review branch protection rules
- ✅ Update quality goals and metrics

---

## Contact

For questions or issues with CI/CD:
- Create GitHub issue with label `ci-cd`
- Contact DevOps team
- Review workflow logs in GitHub Actions tab

---

**Last Updated:** 2025-10-09
**Version:** 1.0
**Maintainer:** Intelia DevOps Team
