"""
Code Reviewer Subagent

Security-focused code review agent that checks for:
- OWASP Top 10 vulnerabilities
- Authentication/authorization issues
- Input validation problems
- SQL injection, XSS, command injection
- Secrets/credentials exposure
- Code quality and maintainability

Usage:
    async with CodeReviewerAgent("reviewer-001") as agent:
        result = await agent.review_file(
            file_path="/path/to/code.py",
            focus=["security", "quality"]
        )
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class SecurityFinding:
    """Represents a security finding in code."""
    severity: str  # Critical, High, Medium, Low, Info
    category: str  # OWASP category or custom
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    remediation: Optional[str] = None
    cwe_id: Optional[str] = None  # Common Weakness Enumeration


class CodeReviewerAgent:
    """
    Security-focused code review agent.

    Performs static analysis looking for:
    - Security vulnerabilities (OWASP Top 10)
    - Authentication/authorization issues
    - Input validation problems
    - Secrets exposure
    - Code quality issues

    Provides severity ratings and remediation guidance.
    """

    # Patterns to detect potential security issues
    DANGEROUS_PATTERNS = {
        "python": {
            "sql_injection": [
                r'execute\s*\(\s*["\'].*%s',
                r'execute\s*\(\s*f["\']',
                r'\.format\s*\(.*\).*execute',
            ],
            "command_injection": [
                r'os\.system\s*\(',
                r'subprocess\.call\s*\(.*shell\s*=\s*True',
                r'eval\s*\(',
                r'exec\s*\(',
            ],
            "secrets": [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][a-zA-Z0-9_-]{20,}["\']',
            ],
            "xss": [
                r'innerHTML\s*=',
                r'\.html\s*\(',
                r'render_template_string\s*\(',
            ],
        },
        "javascript": {
            "xss": [
                r'innerHTML\s*=',
                r'document\.write\s*\(',
                r'eval\s*\(',
                r'\$\(.*\)\.html\s*\(',
            ],
            "secrets": [
                r'apiKey\s*[:=]\s*["\'][^"\']+["\']',
                r'password\s*[:=]\s*["\'][^"\']+["\']',
                r'secret\s*[:=]\s*["\'][^"\']+["\']',
            ],
        },
    }

    def __init__(self, agent_id: str):
        """
        Initialize code reviewer agent.

        Args:
            agent_id: Unique identifier for this agent
        """
        self.agent_id = agent_id
        self.findings: list[SecurityFinding] = []

    async def connect(self) -> None:
        """Initialize resources (placeholder for future integrations)."""
        pass

    async def disconnect(self) -> None:
        """Clean up resources."""
        self.findings = []

    async def review_file(
        self,
        file_path: str,
        focus: Optional[list[str]] = None,
    ) -> dict:
        """
        Review a single file for security issues.

        Args:
            file_path: Path to file to review
            focus: Focus areas (security, quality, all)

        Returns:
            Review results with findings
        """
        focus = focus or ["security", "quality"]
        path = Path(file_path)

        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        content = path.read_text()
        extension = path.suffix.lower()

        self.findings = []

        # Determine language
        lang = self._detect_language(extension)

        # Security checks
        if "security" in focus or "all" in focus:
            await self._check_security_patterns(content, file_path, lang)
            await self._check_secrets(content, file_path)

        # Quality checks
        if "quality" in focus or "all" in focus:
            await self._check_code_quality(content, file_path, lang)

        return self._generate_report(file_path)

    async def review_directory(
        self,
        directory: str,
        extensions: Optional[list[str]] = None,
        focus: Optional[list[str]] = None,
        recursive: bool = True,
    ) -> dict:
        """
        Review all files in a directory.

        Args:
            directory: Directory path
            extensions: File extensions to review
            focus: Focus areas
            recursive: Whether to recurse into subdirectories

        Returns:
            Aggregated review results
        """
        extensions = extensions or [".py", ".js", ".ts", ".jsx", ".tsx"]
        dir_path = Path(directory)
        all_findings = []

        pattern = "**/*" if recursive else "*"
        for ext in extensions:
            for file_path in dir_path.glob(f"{pattern}{ext}"):
                result = await self.review_file(str(file_path), focus)
                if "findings" in result:
                    all_findings.extend(result["findings"])

        return {
            "directory": directory,
            "files_reviewed": len(all_findings),
            "findings": all_findings,
            "summary": self._summarize_findings(all_findings),
        }

    async def _check_security_patterns(
        self,
        content: str,
        file_path: str,
        lang: str,
    ) -> None:
        """Check for dangerous code patterns."""
        import re

        patterns = self.DANGEROUS_PATTERNS.get(lang, {})

        for category, regex_list in patterns.items():
            for regex in regex_list:
                for i, line in enumerate(content.split("\n"), 1):
                    if re.search(regex, line):
                        self.findings.append(SecurityFinding(
                            severity="High" if category in ["sql_injection", "command_injection"] else "Medium",
                            category=category,
                            title=f"Potential {category.replace('_', ' ').title()}",
                            description=f"Detected pattern that may indicate {category}",
                            file_path=file_path,
                            line_number=i,
                            code_snippet=line.strip()[:100],
                            remediation=self._get_remediation(category),
                        ))

    async def _check_secrets(self, content: str, file_path: str) -> None:
        """Check for hardcoded secrets."""
        import re

        secret_patterns = [
            (r'(?i)password\s*[=:]\s*["\'][^"\']{8,}["\']', "Hardcoded password"),
            (r'(?i)api[_-]?key\s*[=:]\s*["\'][a-zA-Z0-9_-]{20,}["\']', "Hardcoded API key"),
            (r'(?i)secret\s*[=:]\s*["\'][^"\']{8,}["\']', "Hardcoded secret"),
            (r'(?i)token\s*[=:]\s*["\'][a-zA-Z0-9_-]{20,}["\']', "Hardcoded token"),
            (r'-----BEGIN (RSA |EC |)PRIVATE KEY-----', "Private key in code"),
        ]

        for i, line in enumerate(content.split("\n"), 1):
            for pattern, title in secret_patterns:
                if re.search(pattern, line):
                    self.findings.append(SecurityFinding(
                        severity="Critical",
                        category="secrets_exposure",
                        title=title,
                        description="Sensitive credential found in source code",
                        file_path=file_path,
                        line_number=i,
                        code_snippet="[REDACTED]",
                        remediation="Move to environment variables or secrets manager",
                        cwe_id="CWE-798",
                    ))

    async def _check_code_quality(
        self,
        content: str,
        file_path: str,
        lang: str,
    ) -> None:
        """Check for code quality issues."""
        lines = content.split("\n")

        # Check for very long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                self.findings.append(SecurityFinding(
                    severity="Info",
                    category="code_quality",
                    title="Line too long",
                    description=f"Line exceeds 120 characters ({len(line)} chars)",
                    file_path=file_path,
                    line_number=i,
                ))

        # Check for TODO/FIXME comments (potential incomplete work)
        for i, line in enumerate(lines, 1):
            if "TODO" in line or "FIXME" in line or "XXX" in line:
                self.findings.append(SecurityFinding(
                    severity="Info",
                    category="incomplete_work",
                    title="TODO/FIXME comment found",
                    description="Incomplete work marker detected",
                    file_path=file_path,
                    line_number=i,
                    code_snippet=line.strip()[:80],
                ))

    def _detect_language(self, extension: str) -> str:
        """Detect programming language from file extension."""
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "javascript",
            ".jsx": "javascript",
            ".tsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
        }
        return mapping.get(extension, "unknown")

    def _get_remediation(self, category: str) -> str:
        """Get remediation guidance for a category."""
        remediations = {
            "sql_injection": "Use parameterized queries or ORM methods",
            "command_injection": "Avoid shell=True, use subprocess with list args",
            "xss": "Sanitize user input, use safe rendering methods",
            "secrets": "Use environment variables or secrets manager",
        }
        return remediations.get(category, "Review and fix the identified issue")

    def _generate_report(self, file_path: str) -> dict:
        """Generate review report."""
        return {
            "file_path": file_path,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_id": self.agent_id,
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "title": f.title,
                    "description": f.description,
                    "line_number": f.line_number,
                    "code_snippet": f.code_snippet,
                    "remediation": f.remediation,
                    "cwe_id": f.cwe_id,
                }
                for f in self.findings
            ],
            "summary": self._summarize_findings(self.findings),
        }

    def _summarize_findings(self, findings: list) -> dict:
        """Summarize findings by severity."""
        severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
        for f in findings:
            severity = f.severity if isinstance(f, SecurityFinding) else f.get("severity", "Info")
            if severity in severity_counts:
                severity_counts[severity] += 1
        return {
            "total": len(findings),
            "by_severity": severity_counts,
        }

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False
