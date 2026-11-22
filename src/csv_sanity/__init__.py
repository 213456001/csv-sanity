"""Streaming CSV validation with no runtime dependencies."""

from .validator import Issue, Report, validate

__all__ = ["Issue", "Report", "validate"]
__version__ = "0.1.0"
