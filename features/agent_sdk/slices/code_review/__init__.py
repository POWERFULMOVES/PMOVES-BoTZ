"""
Code Review Slice - Security-focused code analysis.

This vertical slice encapsulates all code review functionality:
- api.py: Review task endpoints
- service.py: Security analysis logic
- models.py: Review data structures
- SKILL.md: Agent context for code review

Use: from slices.code_review import CodeReviewService
"""

from .service import CodeReviewService
from .models import ReviewTask, ReviewResult, SecurityFinding, Severity
from .. import register_slice

# Register this slice
register_slice("code_review")(CodeReviewService)

__all__ = [
    "CodeReviewService",
    "ReviewTask",
    "ReviewResult",
    "SecurityFinding",
    "Severity",
]
