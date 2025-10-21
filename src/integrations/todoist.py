"""
Todoist Integration

Connects to Todoist via MCP server to read and update tasks.

Architecture:
- Claude Code syncs Todoist→cache/todoist_tasks.json via MCP tools
- Python reads from cache file
- This decouples MCP calls from Python execution
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class TodoistIntegration:
    """Integration with Todoist task management system via MCP"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Todoist integration

        Args:
            config: Configuration dict from main config file
        """
        self.config = config
        self.logger = logging.getLogger("TaskManager.Todoist")
        self.enabled = config.get('enabled', True)

        # Cache file path (synced by Claude Code via MCP)
        project_root = Path(__file__).parent.parent.parent
        self.cache_dir = project_root / 'cache'
        self.cache_file = self.cache_dir / 'todoist_tasks.json'

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(exist_ok=True)

        if not self.enabled:
            self.logger.warning("Todoist integration disabled in config")

    def get_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all tasks from Todoist cache

        Claude Code syncs Todoist via MCP to cache/todoist_tasks.json.
        This method reads from that cache.

        Returns:
            List of normalized task dictionaries

        Note: If cache doesn't exist, returns empty list.
              Run `task-manager sync` to refresh cache.
        """
        if not self.enabled:
            return []

        self.logger.info("Reading tasks from Todoist cache...")

        # Check if cache exists
        if not self.cache_file.exists():
            self.logger.warning(
                f"Todoist cache not found: {self.cache_file}\n"
                "Run `task-manager sync` to populate cache from Todoist"
            )
            return []

        try:
            # Read cache file
            with open(self.cache_file, 'r') as f:
                raw_tasks = json.load(f)

            self.logger.info(f"Loaded {len(raw_tasks)} tasks from cache")

            # Parse into normalized format
            return self._parse_todoist_tasks(raw_tasks)

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Todoist cache: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error reading Todoist cache: {e}")
            return []

    def mark_complete(self, task_id: str) -> bool:
        """
        Mark task as complete in Todoist

        Note: This method writes a completion request to cache/todoist_completions.json.
        Claude Code should monitor this file and execute completions via MCP.

        Architecture:
        1. Python writes completion request to cache file
        2. Claude Code monitors file (or user runs sync command)
        3. Claude Code calls mcp__todoist__close_tasks
        4. Cache is updated to reflect completion

        Args:
            task_id: Todoist task ID (without 'todoist_' prefix)

        Returns:
            True if request written successfully, False otherwise
        """
        if not self.enabled:
            return False

        # Remove 'todoist_' prefix if present
        if task_id.startswith('todoist_'):
            task_id = task_id.replace('todoist_', '')

        self.logger.info(f"Marking Todoist task {task_id} complete...")

        try:
            # Load existing completion requests
            completions_file = self.cache_dir / 'todoist_completions.json'
            completions = []

            if completions_file.exists():
                with open(completions_file, 'r') as f:
                    completions = json.load(f)

            # Add new completion request
            completions.append({
                'task_id': task_id,
                'requested_at': datetime.now().isoformat(),
                'status': 'pending'
            })

            # Write back to file
            with open(completions_file, 'w') as f:
                json.dump(completions, f, indent=2)

            self.logger.info(
                f"✅ Completion request queued for task {task_id}\n"
                f"Run `task-manager sync` or ask Claude Code to process completions"
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to queue completion: {e}")
            return False

    def _parse_todoist_tasks(self, raw_tasks: List[Dict]) -> List[Dict[str, Any]]:
        """
        Parse Todoist tasks into standard format

        Mapping:
        - Todoist priority 4 (urgent) → P1
        - Todoist priority 3 (high) → P2
        - Todoist priority 2 (medium) → P3
        - Todoist priority 1 (normal) → P4

        Args:
            raw_tasks: Raw task data from Todoist API/MCP

        Returns:
            List of normalized task dictionaries
        """
        parsed_tasks = []

        # Todoist to our priority mapping
        priority_map = {
            4: 'P1',  # urgent
            3: 'P2',  # high
            2: 'P3',  # medium
            1: 'P4'   # normal (default)
        }

        for task in raw_tasks:
            # Skip completed tasks
            if task.get('is_completed', False):
                continue

            # Extract title
            title = task.get('content', '').strip()
            if not title:
                continue

            # Map priority
            todoist_priority = task.get('priority', 1)
            priority = priority_map.get(todoist_priority, 'P4')

            # Extract due date
            due_date = None
            due_info = task.get('due')
            if due_info:
                # Try datetime first, then date
                if due_info.get('datetime'):
                    try:
                        due_date = datetime.fromisoformat(due_info['datetime'].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass
                elif due_info.get('date'):
                    try:
                        due_date = datetime.strptime(due_info['date'], '%Y-%m-%d')
                    except (ValueError, AttributeError):
                        pass

            # Extract energy/attention from labels
            # Look for labels like 'energy-low', 'attention-high', etc.
            labels = task.get('labels', [])
            energy = self._extract_level_from_labels(labels, 'energy')
            attention = self._extract_level_from_labels(labels, 'attention')

            # Generate task dict
            parsed_task = {
                'id': f"todoist_{task['id']}",
                'title': title,
                'priority': priority,
                'energy': energy,
                'attention': attention,
                'due_date': due_date,
                'source_systems': ['todoist'],
                'metadata': {
                    'todoist_id': task['id'],
                    'todoist_project_id': task.get('project_id'),
                    'todoist_url': task.get('url'),
                    'description': task.get('description', ''),
                    'labels': labels
                }
            }

            parsed_tasks.append(parsed_task)

        self.logger.info(f"Parsed {len(parsed_tasks)} Todoist tasks")
        return parsed_tasks

    def _extract_level_from_labels(self, labels: List[str], category: str) -> str:
        """
        Extract energy/attention level from Todoist labels

        Looks for labels like:
        - 'energy-low', 'energy-medium', 'energy-high'
        - 'attention-low', 'attention-medium', 'attention-high'

        Args:
            labels: List of label strings
            category: 'energy' or 'attention'

        Returns:
            'low', 'medium', or 'high' (defaults to 'medium')
        """
        pattern = f'{category}-(low|medium|high)'

        for label in labels:
            match = re.search(pattern, label.lower())
            if match:
                return match.group(1)

        # Default to medium
        return 'medium'
