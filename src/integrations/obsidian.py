"""
Obsidian Integration

Reads and updates tasks in Obsidian vault via direct file access.
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class ObsidianIntegration:
    """Integration with Obsidian vault for task management"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Obsidian integration

        Args:
            config: Configuration dict from main config file
        """
        self.config = config
        self.logger = logging.getLogger("TaskManager.Obsidian")

        # Expand paths
        self.vault_path = Path(config['vault_path']).expanduser()
        self.task_database = self.vault_path / config['task_database']
        self.daily_notes_path = self.vault_path / config['daily_notes_path']

        # Verify paths exist
        if not self.vault_path.exists():
            self.logger.warning(f"Obsidian vault not found: {self.vault_path}")
        if not self.task_database.exists():
            self.logger.warning(f"Task database not found: {self.task_database}")

    def get_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all tasks from Obsidian task database

        Returns:
            List of task dictionaries from Obsidian

        TODO: Implement in Increment 2
        - Read task_database.md file
        - Parse markdown tasks with tags
        - Extract priority, energy, attention, due date
        - Return in standard format
        """
        if not self.task_database.exists():
            return []

        self.logger.info("Fetching tasks from Obsidian task database...")

        # TODO: Implement file parsing
        # tasks = self._parse_task_database()
        # return tasks

        return []

    def get_daily_note_tasks(self, date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get tasks from specific daily note

        Args:
            date: Date of daily note (default: today)

        Returns:
            List of task dictionaries from daily note

        TODO: Implement in Increment 3
        - Read daily note for specified date
        - Parse "Action Items" or morning pages analysis section
        - Extract tasks
        """
        if date is None:
            date = datetime.now()

        daily_note = self._get_daily_note_path(date)
        if not daily_note.exists():
            self.logger.warning(f"Daily note not found: {daily_note}")
            return []

        self.logger.info(f"Fetching tasks from daily note: {daily_note.name}")

        # TODO: Implement daily note parsing
        return []

    def get_current_capacity(self, date: Optional[datetime] = None) -> Dict[str, str]:
        """
        Read energy/attention from daily note "How I'm Feeling" section

        Args:
            date: Date of daily note (default: today)

        Returns:
            Dict with 'energy' and 'attention' keys

        TODO: Implement in Increment 3
        - Read daily note
        - Find "How I'm Feeling" section
        - Parse energy and attention tags (#energy/medium, #attention/high)
        """
        if date is None:
            date = datetime.now()

        daily_note = self._get_daily_note_path(date)
        if not daily_note.exists():
            return {"energy": "medium", "attention": "medium"}

        self.logger.info(f"Reading capacity from: {daily_note.name}")

        # TODO: Implement capacity parsing
        # content = daily_note.read_text()
        # return self._parse_capacity(content)

        return {"energy": "medium", "attention": "medium"}

    def mark_complete(self, task_text: str) -> bool:
        """
        Mark task as complete in Obsidian task database

        Args:
            task_text: Text of task to mark complete

        Returns:
            True if successful, False otherwise

        TODO: Implement in Increment 8
        - Find task in task_database.md
        - Change [ ] to [x]
        - Optionally move to archive section
        - Write file back
        """
        if not self.task_database.exists():
            return False

        self.logger.info(f"Marking Obsidian task complete: {task_text[:50]}...")

        # TODO: Implement task completion
        return False

    def _get_daily_note_path(self, date: datetime) -> Path:
        """Get path to daily note for specified date"""
        date_str = date.strftime(self.config['daily_note_format'])
        return self.daily_notes_path / f"{date_str}.md"

    def _parse_task_database(self) -> List[Dict[str, Any]]:
        """
        Parse task database markdown file

        Returns:
            List of parsed tasks

        TODO: Implement markdown parsing
        - Read file line by line
        - Identify task lines (- [ ] pattern)
        - Extract tags (#P1, #energy/high, etc.)
        - Parse metadata (Attention Tax, due dates)
        """
        return []

    def _parse_capacity(self, content: str) -> Dict[str, str]:
        """
        Parse energy/attention from daily note content

        Args:
            content: Full text of daily note

        Returns:
            Dict with energy and attention levels

        Example:
            - Current Energy Level: #energy/high
            - Focus Capacity: #attention/medium

        TODO: Implement regex parsing
        """
        capacity = {"energy": "medium", "attention": "medium"}

        # TODO: Add regex patterns to extract tags
        # energy_match = re.search(r'#energy/(high|medium|low)', content)
        # attention_match = re.search(r'#attention/(high|medium|low)', content)

        return capacity
