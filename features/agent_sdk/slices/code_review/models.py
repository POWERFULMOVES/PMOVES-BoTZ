"""
Code Review Slice - Data Models.

Defines data structures for security-focused code review.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class Severity(Enum):
    """Security finding severity levels."""
    CRITICAL = "critical"  # Immediate exploitation risk
    HIGH = "high"          # Significant vulnerability
    MEDIUM = "medium"      # Moderate risk
    LOW = "low"            # Minor issue
    INFO = "info"          # Informational


class FindingCategory(Enum):
    """Categories of security findings."""
    INJECTION = "injection"           # SQL, XSS, Command injection
    AUTH = "authentication"           # Auth/authz issues
    SECRETS = "secrets"               # Exposed credentials
    VALIDATION = "validation"         # Input validation
    CRYPTO = "cryptography"           # Weak cryptography
    CONFIG = "configuration"          # Security misconfig
    DEPENDENCY = "dependency"         # Vulnerable dependencies
    LOGIC = "logic"                   # Business logic flaws
    OTHER = "other"


@dataclass
class SecurityFinding:
    """A security finding from code review."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    severity: Severity = Severity.MEDIUM
    category: FindingCategory = FindingCategory.OTHER
    title: str = ""
    description: str = ""
    file_path: str = ""
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: str = ""
    cwe_id: Optional[str] = None  # Common Weakness Enumeration
    owasp_category: Optional[str] = None  # OWASP Top 10

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
            "cwe_id": self.cwe_id,
            "owasp_category": self.owasp_category,
        }


@dataclass
class ReviewTask:
    """A code review task specification."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    paths: List[str] = field(default_factory=list)  # Files/directories to review
    focus_areas: List[FindingCategory] = field(default_factory=list)
    include_dependencies: bool = True
    max_files: int = 50
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "paths": self.paths,
            "focus_areas": [f.value for f in self.focus_areas],
            "include_dependencies": self.include_dependencies,
            "max_files": self.max_files,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class ReviewResult:
    """Result of a code review task."""
    task_id: str
    findings: List[SecurityFinding] = field(default_factory=list)
    files_reviewed: int = 0
    summary: str = ""
    risk_score: float = 0.0  # 0-10 scale
    completed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    duration_ms: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "findings": [f.to_dict() for f in self.findings],
            "files_reviewed": self.files_reviewed,
            "summary": self.summary,
            "risk_score": self.risk_score,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }
