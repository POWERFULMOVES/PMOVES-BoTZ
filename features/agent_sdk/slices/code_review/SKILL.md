# Code Review Skill

**Slice:** `slices/code_review/`
**Type:** Security Analysis

## Purpose

Security-focused code review with OWASP Top 10 coverage. Use this skill when:
- Code changes need security review before merge
- Vulnerability scanning is required
- Security audit documentation is needed

## Quick Start

```python
from features.agent_sdk.slices.code_review import (
    CodeReviewService,
    FindingCategory,
    ReviewTask,
)

service = CodeReviewService()
task = ReviewTask(
    paths=["src/api/", "src/auth/"],
    focus_areas=[FindingCategory.INJECTION, FindingCategory.AUTH],
)
result = await service.execute(task)

for finding in result.findings:
    print(f"[{finding.severity.value}] {finding.title} at {finding.file_path}:{finding.line_number}")
```

## API Reference

### CodeReviewService

| Method | Description | Returns |
|--------|-------------|---------|
| `execute(task)` | Execute security review | `ReviewResult` |

### Severity Levels

| Level | Description | Action Required |
|-------|-------------|-----------------|
| CRITICAL | Immediate exploitation risk | Block merge |
| HIGH | Significant vulnerability | Fix before merge |
| MEDIUM | Moderate risk | Fix soon |
| LOW | Minor issue | Fix when convenient |
| INFO | Informational | No action |

### Finding Categories (OWASP-aligned)

- **INJECTION**: SQL, XSS, Command injection (A03:2021)
- **AUTH**: Authentication/authorization issues (A07:2021)
- **SECRETS**: Exposed credentials (A02:2021)
- **VALIDATION**: Input validation (A03:2021)
- **CRYPTO**: Weak cryptography (A02:2021)
- **CONFIG**: Security misconfig (A05:2021)
- **DEPENDENCY**: Vulnerable dependencies (A06:2021)

## Pattern-Based Detection

The service uses regex patterns for common vulnerabilities:

| Pattern | Severity | Description |
|---------|----------|-------------|
| `eval()` | CRITICAL | Code injection |
| `shell=True` | HIGH | Command injection |
| Hardcoded secrets | HIGH | Credential exposure |
| `md5()` | MEDIUM | Weak hashing |

## Risk Score Calculation

- CRITICAL: +10 points
- HIGH: +5 points
- MEDIUM: +2 points
- LOW: +0.5 points

Score is normalized to 0-10 scale.

## Integration

- **Pre-commit hook**: Block commits with critical findings
- **CI/CD**: Fail builds above risk threshold
- **PR Review**: Auto-comment findings on PRs
