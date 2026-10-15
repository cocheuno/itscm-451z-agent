"""Errors a tool may raise. The registry turns each into an audit entry before letting it propagate."""
from __future__ import annotations


class ToolError(RuntimeError):
    """The tool could not do what was asked: the target does not exist, an argument names something unknown."""


class ApprovalRefused(ToolError):
    """A write was attempted with an approval that is missing, for different arguments, or already used."""
