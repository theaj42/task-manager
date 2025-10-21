"""
Integration modules for external task systems
"""

from .todoist import TodoistIntegration
from .obsidian import ObsidianIntegration

__all__ = ['TodoistIntegration', 'ObsidianIntegration']
