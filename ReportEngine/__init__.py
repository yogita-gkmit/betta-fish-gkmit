"""
Report Engine
An intelligent report generation AI agent implementation
Generates comprehensive HTML reports based on outputs from three sub-agents and forum logs
"""

from .agent import ReportAgent, create_agent

__version__ = "1.0.0"
__author__ = "Report Engine Team"

__all__ = ["ReportAgent", "create_agent"]
