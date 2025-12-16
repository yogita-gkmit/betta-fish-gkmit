"""
Report Engine Prompts Module
Defines system prompts used in various stages of report generation
"""

from .prompts import (
    SYSTEM_PROMPT_TEMPLATE_SELECTION,
    SYSTEM_PROMPT_HTML_GENERATION,
    output_schema_template_selection,
    input_schema_html_generation
)

__all__ = [
    "SYSTEM_PROMPT_TEMPLATE_SELECTION",
    "SYSTEM_PROMPT_HTML_GENERATION", 
    "output_schema_template_selection",
    "input_schema_html_generation"
]
