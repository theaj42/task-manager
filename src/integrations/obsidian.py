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
        """
        if not self.task_database.exists():
            self.logger.warning(f"Task database not found: {self.task_database}")
            return []

        self.logger.info("Fetching tasks from Obsidian task database...")

        try:
            tasks = self._parse_task_database()
            self.logger.info(f"Found {len(tasks)} tasks in Obsidian database")
            return tasks
        except Exception as e:
            self.logger.error(f"Error parsing task database: {e}")
            return []

    def get_daily_note_tasks(self, date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get tasks from specific daily note

        Args:
            date: Date of daily note (default: today)

        Returns:
            List of task dictionaries from daily note
        """
        if date is None:
            date = datetime.now()

        daily_note = self._get_daily_note_path(date)
        if not daily_note.exists():
            self.logger.warning(f"Daily note not found: {daily_note}")
            return []

        self.logger.info(f"Fetching tasks from daily note: {daily_note.name}")

        try:
            content = daily_note.read_text()
            tasks = self._parse_daily_note_action_items(content)
            self.logger.info(f"Found {len(tasks)} tasks in daily note")
            return tasks
        except Exception as e:
            self.logger.error(f"Error parsing daily note tasks: {e}")
            return []

    def _parse_daily_note_action_items(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse action items from daily note Morning Pages Analysis section

        Args:
            content: Full daily note text

        Returns:
            List of task dictionaries
        """
        tasks = []

        # Find the "Action Items" section
        action_items_match = re.search(r'####\s+Action Items\s*\n(.*?)(?=\n####|\n###|\Z)', content, re.DOTALL)
        if not action_items_match:
            return tasks

        action_items_section = action_items_match.group(1)
        lines = action_items_section.split('\n')

        for i, line in enumerate(lines):
            # Match uncompleted tasks
            task_match = re.match(r'^- \[ \] (.+)$', line)
            if not task_match:
                continue

            task_text = task_match.group(1).strip()

            # Remove all tags to get clean title
            title = re.sub(r'#[\w/:\-()]+', '', task_text).strip()

            # Generate unique ID
            task_id = f"daily_{hash(title) % 1000000:06d}"

            task = {
                'id': task_id,
                'title': title,
                'priority': 'P2',  # Default priority for daily note tasks
                'energy': 'medium',
                'attention': 'medium',
                'due_date': None,
                'source_systems': ['daily_note'],
                'metadata': {
                    'raw_line': task_text,
                    'source': 'action_items'
                }
            }

            tasks.append(task)

        return tasks

    def get_current_capacity(self, date: Optional[datetime] = None) -> Dict[str, str]:
        """
        Read energy/attention from daily note "How I'm Feeling" section

        Args:
            date: Date of daily note (default: today)

        Returns:
            Dict with 'energy' and 'attention' keys
        """
        if date is None:
            date = datetime.now()

        daily_note = self._get_daily_note_path(date)
        if not daily_note.exists():
            self.logger.warning(f"Daily note not found: {daily_note}")
            return {"energy": "medium", "attention": "medium"}

        self.logger.info(f"Reading capacity from: {daily_note.name}")

        try:
            content = daily_note.read_text()
            return self._parse_capacity(content)
        except Exception as e:
            self.logger.error(f"Error parsing capacity: {e}")
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
            List of parsed tasks with normalized structure
        """
        tasks = []
        content = self.task_database.read_text()
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Match uncompleted tasks: - [ ] Task text
            task_match = re.match(r'^- \[ \] (.+)$', line)
            if not task_match:
                continue

            task_text = task_match.group(1)

            # Extract tags using regex
            priority = self._extract_tag(task_text, r'#(P[1-4])', default='P3')
            energy = self._extract_tag(task_text, r'#energy/(high|medium|low)', default='medium')
            attention = self._extract_tag(task_text, r'#attention/(high|medium|low)', default='medium')
            context = self._extract_tag(task_text, r'#context/(\w+)', default='personal')

            # Extract due date
            due_date = self._extract_due_date(task_text)

            # Remove all tags to get clean title
            title = re.sub(r'#[\w/:\-()]+', '', task_text).strip()

            # Generate unique ID (hash of title)
            task_id = f"obs_{hash(title) % 1000000:06d}"

            task = {
                'id': task_id,
                'title': title,
                'priority': priority,
                'energy': energy,
                'attention': attention,
                'context': context,
                'due_date': due_date,
                'source_systems': ['obsidian'],
                'metadata': {
                    'raw_line': task_text,
                    'line_number': i + 1
                }
            }

            tasks.append(task)

        return tasks

    def _extract_tag(self, text: str, pattern: str, default: str = None) -> Optional[str]:
        """Extract a tag value using regex pattern"""
        match = re.search(pattern, text)
        return match.group(1) if match else default

    def _extract_due_date(self, text: str) -> Optional[datetime]:
        """Extract due date from #due(YYYY-MM-DD) or #due(YYYY-MM-DDTHH:mm) format"""
        due_match = re.search(r'#due\(([^\)]+)\)', text)
        if not due_match:
            return None

        date_str = due_match.group(1)
        try:
            # Try datetime format first
            if 'T' in date_str:
                return datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            else:
                return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            self.logger.warning(f"Failed to parse due date: {date_str}")
            return None

    def _parse_capacity(self, content: str) -> Dict[str, str]:
        """
        Parse energy/attention from daily note content

        Args:
            content: Full text of daily note

        Returns:
            Dict with energy and attention levels

        Looks for patterns like:
            - Current Energy Level: #energy/high
            - Focus Capacity: #attention/medium

        Ignores template lines with "or" (e.g. #energy/high or #energy/medium or #energy/low)
        """
        capacity = {"energy": "medium", "attention": "medium"}

        # Find "How I'm Feeling" section
        feeling_section = re.search(r'###\s+How I\'m Feeling\s*\n(.*?)(?=\n###|\n##|\Z)', content, re.DOTALL)
        if not feeling_section:
            self.logger.info("No 'How I'm Feeling' section found, using defaults")
            return capacity

        section_text = feeling_section.group(1)

        # Extract energy level (only if not template with "or")
        energy_line_match = re.search(r'Current Energy Level:(.+?)$', section_text, re.MULTILINE)
        if energy_line_match:
            energy_line = energy_line_match.group(1)
            # If it contains "or", it's a template
            if ' or ' not in energy_line:
                energy_match = re.search(r'#energy/(high|medium|low)', energy_line)
                if energy_match:
                    capacity['energy'] = energy_match.group(1)

        # Extract attention level (only if not template with "or")
        attention_line_match = re.search(r'Focus Capacity:(.+?)$', section_text, re.MULTILINE)
        if attention_line_match:
            attention_line = attention_line_match.group(1)
            # If it contains "or", it's a template
            if ' or ' not in attention_line:
                attention_match = re.search(r'#attention/(high|medium|low)', attention_line)
                if attention_match:
                    capacity['attention'] = attention_match.group(1)

        if capacity['energy'] == 'medium' and capacity['attention'] == 'medium':
            self.logger.info("Template detected (not filled in), using default capacity: medium/medium")
        else:
            self.logger.info(f"Parsed capacity: energy={capacity['energy']}, attention={capacity['attention']}")

        return capacity
