"""
IEP Assistant prompt templates
"""

from pathlib import Path

# Load the IEP prompt template
template_dir = Path(__file__).parent
with open(template_dir / "iep_prompt.md", "r", encoding="utf-8") as f:
    IEP_PROMPT_TEMPLATE = f.read()

__all__ = ["IEP_PROMPT_TEMPLATE"]
