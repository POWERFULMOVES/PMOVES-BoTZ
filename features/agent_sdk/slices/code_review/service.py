"""
Code Review Slice - Service Layer.

Security-focused code analysis with OWASP Top 10 coverage:
- Injection vulnerabilities (SQL, XSS, Command)
- Authentication/authorization issues
- Secrets and credentials exposure
- Input validation problems
"""

import inspect
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .models import (
    FindingCategory,
    ReviewResult,
    ReviewTask,
    SecurityFinding,
    Severity,
)

logger = logging.getLogger(__name__)


# Pattern-based security checks
SECURITY_PATTERNS = {
    FindingCategory.INJECTION: [
        (r'f".*{.*}.*".*execute', Severity.CRITICAL, "Potential SQL injection via f-string"),
        (r'\.format\(.*\).*execute', Severity.CRITICAL, "Potential SQL injection via format"),
        (r'subprocess\..*shell\s*=\s*True', Severity.HIGH, "Shell injection risk with shell=True"),
        (r'eval\s*\(', Severity.CRITICAL, "Dangerous eval() usage"),
        (r'exec\s*\(', Severity.CRITICAL, "Dangerous exec() usage"),
        (r'os\.system\s*\(', Severity.HIGH, "OS command execution"),
    ],
    FindingCategory.SECRETS: [
        (r'password\s*=\s*["\'][^"\']+["\']', Severity.HIGH, "Hardcoded password"),
        (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', Severity.HIGH, "Hardcoded API key"),
        (r'secret\s*=\s*["\'][^"\']+["\']', Severity.HIGH, "Hardcoded secret"),
        (r'-----BEGIN.*PRIVATE KEY-----', Severity.CRITICAL, "Exposed private key"),
    ],
    FindingCategory.VALIDATION: [
        (r'\.get\([^)]+\)\s*$', Severity.LOW, "Missing default value in dict.get()"),
        (r'int\(request\.', Severity.MEDIUM, "Unvalidated integer conversion from request"),
    ],
    FindingCategory.CRYPTO: [
        (r'md5\s*\(', Severity.MEDIUM, "Weak MD5 hash usage"),
        (r'sha1\s*\(', Severity.LOW, "Weak SHA1 hash usage"),
        (r'DES\s*\(', Severity.HIGH, "Weak DES encryption"),
    ],
}


class CodeReviewService:
    """
    Code Review Service - Security-focused code analysis.

    This service encapsulates all code review logic in a single vertical slice.

    Usage:
        service = CodeReviewService()
        task = ReviewTask(paths=["src/"], focus_areas=[FindingCategory.INJECTION])
        result = await service.execute(task)
        print(f"Found {result.critical_count} critical issues")
    """

    def __init__(self, file_reader: Optional[Callable[[str], Union[str, Any]]] = None):
        """
        Initialize Code Review Service.

        Args:
            file_reader: Optional sync or async function to read files (default: sync read).
                         If async, will be awaited automatically.
        """
        self.file_reader = file_reader or self._default_file_reader

    def _default_file_reader(self, path: str) -> str:
        """Default sync file reader."""
        try:
            return Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Failed to read file {path}: {e}")
            return ""

    async def execute(self, task: ReviewTask) -> ReviewResult:
        """
        Execute a code review task.

        Args:
            task: Review task specification

        Returns:
            ReviewResult with findings and risk score
        """
        start_time = time.time()
        all_findings: List[SecurityFinding] = []
        files_reviewed = 0

        logger.info(f"Starting code review task {task.id} for {len(task.paths)} paths")

        for path in task.paths:
            files = self._collect_files(path, task.max_files - files_reviewed)
            for file_path in files:
                if files_reviewed >= task.max_files:
                    break

                try:
                    # Support both sync and async file readers
                    content = self.file_reader(file_path)
                    if inspect.isawaitable(content):
                        content = await content
                    if not content:
                        logger.debug(f"Skipping empty or unreadable file: {file_path}")
                        continue
                    findings = self._analyze_file(file_path, content, task.focus_areas)
                    all_findings.extend(findings)
                    files_reviewed += 1
                except Exception as e:
                    logger.warning(f"Error analyzing {file_path}: {e}")

        # Calculate risk score
        risk_score = self._calculate_risk_score(all_findings)

        # Generate summary
        summary = self._generate_summary(all_findings, files_reviewed)

        duration_ms = int((time.time() - start_time) * 1000)

        result = ReviewResult(
            task_id=task.id,
            findings=all_findings,
            files_reviewed=files_reviewed,
            summary=summary,
            risk_score=risk_score,
            duration_ms=duration_ms,
        )

        logger.info(f"Code review {task.id} completed: {len(all_findings)} findings, risk score {risk_score:.1f}")
        return result

    def _collect_files(self, path: str, max_files: int) -> List[str]:
        """Collect files from path for review."""
        p = Path(path)
        files = []

        # Supported extensions
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs"}

        if p.is_file():
            if p.suffix in extensions:
                files.append(str(p))
        elif p.is_dir():
            for ext in extensions:
                for f in p.rglob(f"*{ext}"):
                    if len(files) >= max_files:
                        break
                    # Skip common non-source directories
                    if any(part in f.parts for part in ["node_modules", "__pycache__", ".git", "venv"]):
                        continue
                    files.append(str(f))

        return files[:max_files]

    def _analyze_file(
        self,
        file_path: str,
        content: str,
        focus_areas: List[FindingCategory],
    ) -> List[SecurityFinding]:
        """Analyze a single file for security issues."""
        findings = []

        # Determine which patterns to check
        categories_to_check = focus_areas if focus_areas else list(SECURITY_PATTERNS.keys())

        for category in categories_to_check:
            patterns = SECURITY_PATTERNS.get(category, [])
            for pattern, severity, description in patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_number = content[:match.start()].count("\n") + 1
                    findings.append(SecurityFinding(
                        severity=severity,
                        category=category,
                        title=description,
                        description=f"Pattern matched: {pattern}",
                        file_path=file_path,
                        line_number=line_number,
                        code_snippet=match.group(0)[:100],
                        recommendation=f"Review and fix {category.value} issue",
                    ))

        return findings

    def _calculate_risk_score(self, findings: List[SecurityFinding]) -> float:
        """Calculate overall risk score (0-10)."""
        if not findings:
            return 0.0

        severity_weights = {
            Severity.CRITICAL: 10.0,
            Severity.HIGH: 5.0,
            Severity.MEDIUM: 2.0,
            Severity.LOW: 0.5,
            Severity.INFO: 0.1,
        }

        total_weight = sum(severity_weights[f.severity] for f in findings)
        # Normalize to 0-10 scale (cap at 10)
        return min(10.0, total_weight / 2)

    def _generate_summary(self, findings: List[SecurityFinding], files_reviewed: int) -> str:
        """Generate human-readable summary."""
        if not findings:
            return f"No security issues found in {files_reviewed} files reviewed."

        critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in findings if f.severity == Severity.HIGH)
        medium = sum(1 for f in findings if f.severity == Severity.MEDIUM)
        low = sum(1 for f in findings if f.severity == Severity.LOW)

        parts = []
        if critical:
            parts.append(f"{critical} critical")
        if high:
            parts.append(f"{high} high")
        if medium:
            parts.append(f"{medium} medium")
        if low:
            parts.append(f"{low} low")

        return f"Found {', '.join(parts)} severity issues in {files_reviewed} files."
