#!/usr/bin/env python3
"""
TaskManager Agent

AI-powered task orchestrator that:
1. Aggregates tasks from Todoist, Obsidian, daily notes
2. Deduplicates tasks across systems
3. Reads current energy/attention from daily note
4. Calculates Attention Tax scores
5. Recommends tasks matching current capacity
6. Marks tasks complete across all systems
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Task:
    """Unified task representation across all systems"""
    id: str
    title: str
    priority: str  # P1, P2, P3, P4
    energy: str  # high, medium, low
    attention: str  # high, medium, low
    due_date: Optional[datetime]
    source_systems: List[str]  # ['todoist', 'obsidian', 'daily_note']
    attention_tax: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Capacity:
    """User's current energy and attention capacity"""
    energy: str  # high, medium, low
    attention: str  # high, medium, low
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class TaskManager:
    """
    Self-contained task management agent

    Follows SelfContainedAgent pattern but simplified for standalone project.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize TaskManager with configuration"""
        self.logger = self._setup_logging()
        self.project_root = self._detect_project_root()
        self.config = self._load_config(config_path)

        # Initialize integrations
        from integrations import ObsidianIntegration, TodoistIntegration

        self._obsidian = ObsidianIntegration(self.config['obsidian'])
        self._todoist = TodoistIntegration(self.config['todoist']) if self.config['todoist']['enabled'] else None

        self.logger.info("✅ TaskManager initialized successfully")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the agent"""
        logger = logging.getLogger("TaskManager")

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - TaskManager - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    def _detect_project_root(self) -> Path:
        """Detect project root directory"""
        current_path = Path(__file__).resolve()

        # Look for project markers
        for parent in current_path.parents:
            if (parent / 'PRD.md').exists() or (parent / 'requirements.txt').exists():
                return parent

        # Fallback
        return Path.cwd()

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if config_path is None:
            config_path = self.project_root / 'config' / 'config.yaml'
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            # Try example config
            example_config = self.project_root / 'config' / 'config.example.yaml'
            if example_config.exists():
                self.logger.warning(
                    f"Config not found at {config_path}. "
                    f"Please copy {example_config} to {config_path} and customize."
                )
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def is_ready(self) -> bool:
        """Check if agent is ready to operate"""
        # TODO: Check all integrations are configured
        return True

    # ==================== Core Methods ====================

    def aggregate_tasks(self) -> List[Task]:
        """
        Aggregate tasks from all sources

        Returns:
            List of Task objects from all systems
        """
        self.logger.info("Aggregating tasks from all sources...")
        tasks = []

        # Get tasks from Obsidian
        tasks.extend(self._get_obsidian_tasks())

        # Get tasks from Todoist (if enabled)
        if self._todoist and self.config['todoist']['enabled']:
            tasks.extend(self._get_todoist_tasks())

        # Get tasks from daily note
        tasks.extend(self._get_daily_note_tasks())

        self.logger.info(f"Found {len(tasks)} total tasks")
        return tasks

    def deduplicate_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Deduplicate tasks using heuristic matching

        Strategy:
        1. Exact title match → merge immediately
        2. Fuzzy match (>80% similar) → merge
        3. For duplicates: merge source_systems, combine metadata

        Args:
            tasks: List of tasks potentially containing duplicates

        Returns:
            List of unique tasks
        """
        from difflib import SequenceMatcher

        if not tasks:
            return []

        self.logger.info(f"Deduplicating {len(tasks)} tasks...")

        # Track unique tasks and duplicates
        unique_tasks = []
        merged_count = 0

        for task in tasks:
            # Check if this task is a duplicate of an existing unique task
            is_duplicate = False

            for unique_task in unique_tasks:
                # Check for exact match (case-insensitive)
                if task.title.lower().strip() == unique_task.title.lower().strip():
                    # Exact match - merge source systems
                    self._merge_duplicate(unique_task, task)
                    is_duplicate = True
                    merged_count += 1
                    self.logger.debug(f"Exact match: '{task.title[:40]}' (merged into existing)")
                    break

                # Check for fuzzy match (80% similarity threshold)
                similarity = SequenceMatcher(
                    None,
                    task.title.lower().strip(),
                    unique_task.title.lower().strip()
                ).ratio()

                if similarity >= 0.80:
                    # High similarity - merge
                    self._merge_duplicate(unique_task, task)
                    is_duplicate = True
                    merged_count += 1
                    self.logger.debug(
                        f"Fuzzy match ({similarity:.2f}): "
                        f"'{task.title[:40]}' ≈ '{unique_task.title[:40]}' (merged)"
                    )
                    break

            # If not a duplicate, add to unique list
            if not is_duplicate:
                unique_tasks.append(task)

        self.logger.info(
            f"Deduplication complete: {len(tasks)} → {len(unique_tasks)} "
            f"({merged_count} duplicates merged)"
        )

        return unique_tasks

    def _merge_duplicate(self, existing: Task, duplicate: Task) -> None:
        """
        Merge a duplicate task into an existing task

        Combines source_systems and metadata. Keeps existing task's primary fields.

        Args:
            existing: The task to merge into (modified in-place)
            duplicate: The duplicate task to merge from
        """
        # Merge source systems (unique values only)
        for source in duplicate.source_systems:
            if source not in existing.source_systems:
                existing.source_systems.append(source)

        # Merge metadata (preserve both)
        if duplicate.metadata:
            if 'merged_from' not in existing.metadata:
                existing.metadata['merged_from'] = []

            existing.metadata['merged_from'].append({
                'title': duplicate.title,
                'sources': duplicate.source_systems,
                'metadata': duplicate.metadata
            })

    def get_current_capacity(self) -> Capacity:
        """
        Read current energy/attention from today's daily note

        Returns:
            Capacity object with energy and attention levels
        """
        self.logger.info("Reading current capacity from daily note...")

        capacity_dict = self._obsidian.get_current_capacity()

        return Capacity(
            energy=capacity_dict['energy'],
            attention=capacity_dict['attention']
        )

    def calculate_attention_tax(self, task: Task) -> float:
        """
        Calculate Attention Tax score using Obsidian formula

        Formula: Priority × Energy Multiplier × Deadline Multiplier

        Args:
            task: Task to calculate score for

        Returns:
            Attention Tax score

        Example:
            P1 task + high energy + has deadline = 5 × 2.0 × 1.5 = 15.0
            P3 task + low energy + no deadline = 3 × 1.0 × 1.0 = 3.0
        """
        config = self.config['attention_tax']

        # Get base priority score
        priority_score = config['priority_base'].get(task.priority, 2)

        # Get energy multiplier
        energy_mult = config['energy_multiplier'].get(task.energy, 1.0)

        # Get deadline multiplier
        deadline_mult = (
            config['deadline_multiplier']['has_deadline']
            if task.due_date
            else config['deadline_multiplier']['no_deadline']
        )

        score = priority_score * energy_mult * deadline_mult

        self.logger.debug(
            f"Attention Tax for '{task.title[:30]}': "
            f"{priority_score} × {energy_mult} × {deadline_mult} = {score}"
        )

        return score

    def recommend_next_actions(
        self,
        capacity: Optional[Capacity] = None,
        max_tasks: Optional[int] = None
    ) -> Dict[str, List[Task]]:
        """
        Recommend tasks with separate critical and capacity-matched sections

        Args:
            capacity: Current energy/attention (if None, will read from daily note)
            max_tasks: Maximum tasks to return in recommended section (default from config)

        Returns:
            Dict with 'critical' and 'recommended' lists:
            - critical: Urgent tasks regardless of capacity (due soon, blockers, P1 deadlines)
            - recommended: Capacity-matched tasks sorted by lowest Attention Tax first
        """
        if capacity is None:
            capacity = self.get_current_capacity()

        if max_tasks is None:
            max_tasks = self.config['recommendations']['max_tasks']

        self.logger.info(
            f"Recommending tasks for capacity: "
            f"energy={capacity.energy}, attention={capacity.attention}"
        )

        # Get all tasks
        all_tasks = self.aggregate_tasks()
        all_tasks = self.deduplicate_tasks(all_tasks)

        # Filter out backlog tasks (deferred for future consideration)
        backlog_count = 0
        filtered_tasks = []
        for task in all_tasks:
            raw_line = task.metadata.get('raw_line', '') if task.metadata else ''
            if '#backlog' not in raw_line:
                filtered_tasks.append(task)
            else:
                backlog_count += 1

        if backlog_count > 0:
            self.logger.info(f"Filtered out {backlog_count} backlog tasks from recommendations")

        all_tasks = filtered_tasks

        # Calculate attention tax for each
        for task in all_tasks:
            task.attention_tax = self.calculate_attention_tax(task)

        # Identify critical tasks (overrides capacity)
        critical_tasks = self._identify_critical_tasks(all_tasks)
        self.logger.info(f"Found {len(critical_tasks)} critical tasks")

        # Filter by capacity match (excluding already-critical tasks)
        non_critical = [t for t in all_tasks if t not in critical_tasks]
        matched_tasks = self._filter_by_capacity(non_critical, capacity)

        self.logger.info(
            f"Filtered to {len(matched_tasks)} tasks matching capacity "
            f"(from {len(non_critical)} non-critical tasks)"
        )

        # Sort by Attention Tax (LOWEST first - easiest wins when tired)
        matched_tasks.sort(key=lambda t: t.attention_tax)

        # Return top N
        min_tasks = self.config['recommendations']['min_tasks']
        recommendations = matched_tasks[:max_tasks]

        # If we don't have enough matches, fill with lowest-tax tasks regardless of capacity
        if len(recommendations) < min_tasks:
            self.logger.info(
                f"Only {len(recommendations)} capacity matches, "
                f"adding low-tax tasks to reach minimum of {min_tasks}"
            )
            non_critical.sort(key=lambda t: t.attention_tax)
            for task in non_critical:
                if task not in recommendations:
                    recommendations.append(task)
                    if len(recommendations) >= min_tasks:
                        break

        self.logger.info(
            f"Returning {len(critical_tasks)} critical + "
            f"{len(recommendations)} recommended tasks"
        )

        return {
            'critical': critical_tasks,
            'recommended': recommendations
        }

    def _filter_by_capacity(self, tasks: List[Task], capacity: Capacity) -> List[Task]:
        """
        Filter tasks to those AT OR BELOW current energy/attention capacity

        Strategy (STRICT):
        - Only show tasks you can actually handle at current capacity
        - Task requirement must be <= your capacity in both dimensions
        - Example: If you're at low/low, only show low/low tasks
        - Example: If you're at medium/high, show low/medium, low/high, medium/medium, medium/high

        Args:
            tasks: List of all tasks
            capacity: Current capacity

        Returns:
            Tasks that are at or below current capacity
        """
        energy_levels = {'low': 0, 'medium': 1, 'high': 2}
        attention_levels = {'low': 0, 'medium': 1, 'high': 2}

        capacity_energy_level = energy_levels[capacity.energy]
        capacity_attention_level = attention_levels[capacity.attention]

        matched = []

        for task in tasks:
            task_energy_level = energy_levels[task.energy]
            task_attention_level = attention_levels[task.attention]

            # STRICT: Task requirements must be <= your capacity
            # Don't show tasks that require MORE than you have
            if (task_energy_level <= capacity_energy_level and
                task_attention_level <= capacity_attention_level):
                matched.append(task)
                self.logger.debug(
                    f"Match: '{task.title[:30]}' "
                    f"(task: {task.energy}/{task.attention}, "
                    f"capacity: {capacity.energy}/{capacity.attention})"
                )

        return matched

    def _identify_critical_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Identify critical/urgent tasks that override capacity filtering

        Criteria for critical:
        - Due within configured days threshold (default: 2 days)
        - P1 tasks with deadlines
        - Contains urgent keywords (urgent, asap, critical, blocker, blocking)
        - Has critical tags (urgency/high, importance/high)

        Args:
            tasks: All tasks to evaluate

        Returns:
            List of critical tasks sorted by due date (soonest first)
        """
        config = self.config['critical_tasks']
        critical = []
        now = datetime.now()

        for task in tasks:
            is_critical = False
            reasons = []

            # Check due date
            if task.due_date:
                days_until_due = (task.due_date - now).days
                if days_until_due <= config['due_within_days']:
                    is_critical = True
                    reasons.append(f"due in {days_until_due} days")

            # Check P1 with deadline
            if (config['p1_with_deadline_critical'] and
                task.priority == 'P1' and
                task.due_date):
                is_critical = True
                reasons.append("P1 with deadline")

            # Check urgent keywords in title
            title_lower = task.title.lower()
            for keyword in config['urgent_keywords']:
                if keyword in title_lower:
                    is_critical = True
                    reasons.append(f"contains '{keyword}'")
                    break

            # Check critical tags in metadata
            if task.metadata and 'raw_line' in task.metadata:
                raw_line = task.metadata['raw_line']
                for tag in config['critical_tags']:
                    if f'#{tag}' in raw_line:
                        is_critical = True
                        reasons.append(f"has #{tag}")
                        break

            if is_critical:
                self.logger.info(
                    f"Critical task: '{task.title[:40]}' - {', '.join(reasons)}"
                )
                critical.append(task)

        # Sort critical tasks by due date (soonest first)
        critical.sort(key=lambda t: (
            t.due_date if t.due_date else datetime.max,
            -t.attention_tax  # Secondary sort by tax if same due date
        ))

        return critical

    def mark_complete(self, task_id: str, systems: Optional[List[str]] = None) -> bool:
        """
        Mark task complete across all relevant systems

        Args:
            task_id: Unique task identifier
            systems: List of systems to update (default: all source systems for that task)

        Returns:
            True if at least one system updated successfully, False otherwise
        """
        self.logger.info(f"Marking task {task_id} complete...")

        # Get all tasks to find this one
        all_tasks = self.aggregate_tasks()

        # Find the task
        target_task = None
        for task in all_tasks:
            if task.id == task_id:
                target_task = task
                break

        if not target_task:
            self.logger.error(f"Task not found: {task_id}")
            return False

        # Determine which systems to update
        if systems is None:
            systems = target_task.source_systems

        self.logger.info(
            f"Marking '{target_task.title[:50]}' complete in: {', '.join(systems)}"
        )

        # Track success
        success_count = 0
        total_count = len(systems)

        # Update each system
        for system in systems:
            if system == 'todoist':
                if self._todoist and self._todoist.mark_complete(task_id):
                    success_count += 1
                    self.logger.info(f"✅ Marked complete in Todoist")
                else:
                    self.logger.warning(f"⚠️  Failed to mark complete in Todoist")

            elif system == 'obsidian':
                if self._obsidian.mark_complete(target_task.title):
                    success_count += 1
                    self.logger.info(f"✅ Marked complete in Obsidian")
                else:
                    self.logger.warning(f"⚠️  Failed to mark complete in Obsidian")

            elif system == 'daily_note':
                # Daily note tasks are transient - just log
                self.logger.info(f"ℹ️  Daily note tasks are transient (no action needed)")
                success_count += 1

            else:
                self.logger.warning(f"Unknown system: {system}")

        # Report results
        if success_count == total_count:
            self.logger.info(f"✅ Task marked complete in all {total_count} systems")
            return True
        elif success_count > 0:
            self.logger.warning(
                f"⚠️  Task marked complete in {success_count}/{total_count} systems"
            )
            return True
        else:
            self.logger.error(f"❌ Failed to mark task complete in any system")
            return False

    def sync_daily_note(self, date: Optional[datetime] = None) -> bool:
        """
        Sync task recommendations to today's daily note

        Inserts/updates a ## Tasks section between ## Planning and ## Notes
        with critical tasks and capacity-matched recommendations.

        Args:
            date: Date of daily note (default: today)

        Returns:
            True if successful, False otherwise
        """
        if date is None:
            date = datetime.now()

        daily_note_path = self._obsidian._get_daily_note_path(date)

        if not daily_note_path.exists():
            self.logger.error(f"Daily note not found: {daily_note_path}")
            return False

        self.logger.info(f"Syncing tasks to daily note: {daily_note_path.name}")

        # Get recommendations
        recommendations = self.recommend_next_actions()
        critical_tasks = recommendations['critical']
        recommended_tasks = recommendations['recommended']

        # Generate markdown section
        tasks_section = self._generate_daily_tasks_markdown(critical_tasks, recommended_tasks)

        # Read current daily note
        content = daily_note_path.read_text()

        # Find position for Tasks section (between Planning and Notes)
        # Check if ## Tasks already exists
        if '\n## Tasks\n' in content or content.startswith('## Tasks\n'):
            # Update existing section
            content = self._update_tasks_section(content, tasks_section)
        else:
            # Insert new section
            content = self._insert_tasks_section(content, tasks_section)

        # Write back to daily note
        daily_note_path.write_text(content)

        self.logger.info(
            f"✅ Synced {len(critical_tasks)} critical + {len(recommended_tasks)} recommended tasks to daily note"
        )

        return True

    def _generate_daily_tasks_markdown(self, critical_tasks: List[Task], recommended_tasks: List[Task]) -> str:
        """
        Generate markdown for the ## Tasks section in daily note

        Args:
            critical_tasks: List of critical tasks
            recommended_tasks: List of recommended tasks

        Returns:
            Markdown string for tasks section
        """
        import urllib.parse

        lines = ["## Tasks", ""]

        # Get vault name from config (for Obsidian URIs)
        vault_path = self._obsidian.vault_path
        vault_name = vault_path.name

        # Critical tasks section
        if critical_tasks:
            lines.append(f"### 🚨 Critical ({len(critical_tasks)})")
            lines.append("")

            for task in critical_tasks:
                # Checkbox
                line = f"- [ ] **{task.title}** #{task.priority} #energy/{task.energy} #attention/{task.attention}"
                lines.append(line)

                # Metadata line
                meta_parts = []
                if task.due_date:
                    days_until = (task.due_date - datetime.now()).days
                    if days_until < 0:
                        meta_parts.append(f"**Due**: {task.due_date.strftime('%Y-%m-%d')} (⚠️ OVERDUE by {abs(days_until)} days)")
                    else:
                        meta_parts.append(f"**Due**: {task.due_date.strftime('%Y-%m-%d')} (in {days_until} days)")

                meta_parts.append(f"**Tax**: {task.attention_tax:.1f}")

                # Source link
                if 'obsidian' in task.source_systems:
                    # Generate Obsidian URI
                    task_db_path = self._obsidian.task_database.relative_to(vault_path)
                    encoded_path = urllib.parse.quote(str(task_db_path))
                    uri = f"obsidian://open?vault={urllib.parse.quote(vault_name)}&file={encoded_path}"
                    meta_parts.append(f"**Source**: [Tasks]({uri})")
                else:
                    source_name = ', '.join(task.source_systems)
                    meta_parts.append(f"**Source**: {source_name}")

                lines.append(f"  - {' | '.join(meta_parts)}")
                lines.append("")

        # Recommended tasks section
        if recommended_tasks:
            lines.append(f"### 📋 Recommended ({len(recommended_tasks)} capacity-matched)")
            lines.append("")

            for task in recommended_tasks:
                # Checkbox
                line = f"- [ ] **{task.title}** #{task.priority} #energy/{task.energy} #attention/{task.attention}"
                lines.append(line)

                # Metadata line
                meta_parts = [f"**Tax**: {task.attention_tax:.1f}"]

                if task.due_date:
                    meta_parts.append(f"**Due**: {task.due_date.strftime('%Y-%m-%d')}")

                # Source link
                if 'obsidian' in task.source_systems:
                    task_db_path = self._obsidian.task_database.relative_to(vault_path)
                    encoded_path = urllib.parse.quote(str(task_db_path))
                    uri = f"obsidian://open?vault={urllib.parse.quote(vault_name)}&file={encoded_path}"
                    meta_parts.append(f"**Source**: [Tasks]({uri})")
                else:
                    source_name = ', '.join(task.source_systems)
                    meta_parts.append(f"**Source**: {source_name}")

                lines.append(f"  - {' | '.join(meta_parts)}")
                lines.append("")

        if not critical_tasks and not recommended_tasks:
            lines.append("*No tasks to recommend at this time.*")
            lines.append("")

        return '\n'.join(lines)

    def _insert_tasks_section(self, content: str, tasks_section: str) -> str:
        """
        Insert ## Tasks section between ## Planning and ## Notes

        Args:
            content: Current daily note content
            tasks_section: Markdown for tasks section

        Returns:
            Updated content
        """
        import re

        # Try to find ## Planning and ## Notes
        # Insert Tasks section between them
        pattern = r'(## Planning.*?)(\n## Notes)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            # Insert between Planning and Notes
            return content[:match.end(1)] + '\n\n' + tasks_section + '\n' + content[match.end(1):]
        else:
            # Fallback: add at end
            self.logger.warning("Could not find ## Planning and ## Notes sections, appending tasks to end")
            return content.rstrip() + '\n\n' + tasks_section + '\n'

    def _update_tasks_section(self, content: str, new_tasks_section: str) -> str:
        """
        Update existing ## Tasks section, preserving checked boxes

        Args:
            content: Current daily note content
            new_tasks_section: New markdown for tasks section

        Returns:
            Updated content with preserved checkboxes
        """
        import re

        # Find the existing ## Tasks section
        pattern = r'## Tasks\n.*?(?=\n## [^T]|\Z)'
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            # No existing section found, insert new one
            return self._insert_tasks_section(content, new_tasks_section)

        # Extract old section
        old_section = match.group(0)

        # Find all checked tasks in old section (preserve completions)
        checked_tasks = set()
        for line in old_section.split('\n'):
            if line.strip().startswith('- [x]'):
                # Extract task title
                task_match = re.match(r'- \[x\] \*\*(.+?)\*\*', line)
                if task_match:
                    checked_tasks.add(task_match.group(1))

        # Update new section to preserve checked boxes
        new_lines = []
        for line in new_tasks_section.split('\n'):
            if line.strip().startswith('- [ ]'):
                # Check if this task was completed
                task_match = re.match(r'- \[ \] \*\*(.+?)\*\*', line)
                if task_match and task_match.group(1) in checked_tasks:
                    # Mark as checked
                    line = line.replace('- [ ]', '- [x]', 1)
            new_lines.append(line)

        updated_section = '\n'.join(new_lines)

        # Replace old section with updated section
        return content[:match.start()] + updated_section + content[match.end():]

    def sync_completions(self, date: Optional[datetime] = None) -> Dict[str, int]:
        """
        Sync checked boxes from daily note to source systems

        Reads the ## Tasks section in daily note, finds all checked boxes,
        and marks corresponding tasks complete in their source systems.

        Args:
            date: Date of daily note (default: today)

        Returns:
            Dict with 'completed' and 'failed' counts
        """
        if date is None:
            date = datetime.now()

        daily_note_path = self._obsidian._get_daily_note_path(date)

        if not daily_note_path.exists():
            self.logger.error(f"Daily note not found: {daily_note_path}")
            return {'completed': 0, 'failed': 0}

        self.logger.info(f"Syncing completions from daily note: {daily_note_path.name}")

        # Read daily note
        content = daily_note_path.read_text()

        # Extract checked tasks from ## Tasks section
        checked_tasks = self._extract_checked_tasks(content)

        if not checked_tasks:
            self.logger.info("No checked tasks found in daily note")
            return {'completed': 0, 'failed': 0}

        self.logger.info(f"Found {len(checked_tasks)} checked tasks")

        # Get all tasks to match against
        all_tasks = self.aggregate_tasks()

        # Match checked tasks to actual task objects and mark complete
        completed = 0
        failed = 0

        for task_title in checked_tasks:
            # Find matching task
            matching_task = None
            for task in all_tasks:
                if task.title.lower().strip() == task_title.lower().strip():
                    matching_task = task
                    break

            if not matching_task:
                self.logger.warning(f"Could not find task: {task_title[:50]}...")
                failed += 1
                continue

            # Mark complete in source systems
            success = self.mark_complete(matching_task.id)
            if success:
                completed += 1
                self.logger.info(f"✅ Marked complete: {task_title[:50]}...")
            else:
                failed += 1
                self.logger.warning(f"❌ Failed to mark complete: {task_title[:50]}...")

        return {'completed': completed, 'failed': failed}

    def _extract_checked_tasks(self, content: str) -> List[str]:
        """
        Extract task titles from checked boxes in ## Tasks section

        Args:
            content: Full daily note content

        Returns:
            List of task titles that are checked
        """
        import re

        # Find the ## Tasks section
        pattern = r'## Tasks\n.*?(?=\n## [^T]|\Z)'
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            return []

        tasks_section = match.group(0)

        # Find all checked tasks: - [x] **Task Title** ...
        checked_tasks = []
        for line in tasks_section.split('\n'):
            if line.strip().startswith('- [x]'):
                # Extract task title
                task_match = re.match(r'- \[x\] \*\*(.+?)\*\*', line)
                if task_match:
                    checked_tasks.append(task_match.group(1))

        return checked_tasks

    def sync_dashboard(self) -> bool:
        """
        Create/update Task Dashboard in Obsidian vault

        Generates a comprehensive task curation dashboard at:
        80 - Tasks/Task Dashboard.md

        Dashboard includes all tasks grouped by priority, with full metadata
        and checkboxes for easy completion/review.

        Returns:
            True if successful, False otherwise
        """
        dashboard_path = self._obsidian.vault_path / "80 - Tasks" / "Task Dashboard.md"

        # Ensure directory exists
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Syncing task dashboard: {dashboard_path}")

        # Get all tasks
        all_tasks = self.aggregate_tasks()
        deduplicated_tasks = self.deduplicate_tasks(all_tasks)

        # Calculate attention tax and stats
        for task in deduplicated_tasks:
            task.attention_tax = self.calculate_attention_tax(task)

        # Generate dashboard markdown
        dashboard_content = self._generate_dashboard_markdown(deduplicated_tasks)

        # Write to file
        dashboard_path.write_text(dashboard_content)

        self.logger.info(f"✅ Dashboard updated with {len(deduplicated_tasks)} tasks")

        return True

    def _generate_dashboard_markdown(self, tasks: List[Task]) -> str:
        """
        Generate markdown for Task Dashboard

        Args:
            tasks: All tasks (deduplicated)

        Returns:
            Markdown string for dashboard
        """
        import urllib.parse

        lines = ["# Task Dashboard", ""]

        # Get vault name from config (for Obsidian URIs)
        vault_path = self._obsidian.vault_path
        vault_name = vault_path.name

        # Stats header
        now = datetime.now()
        critical_tasks = self._identify_critical_tasks(tasks)
        overdue_tasks = [t for t in tasks if t.due_date and t.due_date < now]

        lines.append(f"*Last updated: {now.strftime('%Y-%m-%d %H:%M')}*")
        lines.append(f"*Total: {len(tasks)} tasks | Critical: {len(critical_tasks)} | Overdue: {len(overdue_tasks)}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Group tasks by priority
        by_priority = {
            'P1': [],
            'P2': [],
            'P3': [],
            'P4': []
        }

        for task in tasks:
            priority = task.priority
            if priority in by_priority:
                by_priority[priority].append(task)

        # Generate sections for each priority
        priority_labels = {
            'P1': '🔴 P1 Tasks (Urgent)',
            'P2': '🟡 P2 Tasks (High)',
            'P3': '🟢 P3 Tasks (Normal)',
            'P4': '🔵 P4 Tasks (Low)'
        }

        for priority in ['P1', 'P2', 'P3', 'P4']:
            priority_tasks = by_priority[priority]

            if not priority_tasks:
                continue

            lines.append(f"## {priority_labels[priority]} ({len(priority_tasks)})")
            lines.append("")

            # Group by source within priority
            by_source = {}
            for task in priority_tasks:
                for source in task.source_systems:
                    if source not in by_source:
                        by_source[source] = []
                    by_source[source].append(task)

            # Sort sources
            for source in sorted(by_source.keys()):
                source_tasks = by_source[source]
                lines.append(f"### {source.capitalize()} ({len(source_tasks)} tasks)")
                lines.append("")

                # Sort by attention tax
                source_tasks.sort(key=lambda t: t.attention_tax)

                for task in source_tasks:
                    # Checkbox and title
                    lines.append(f"- [ ] **{task.title}** #energy/{task.energy} #attention/{task.attention}")

                    # Metadata line
                    meta_parts = [f"Tax: {task.attention_tax:.1f}"]

                    if task.due_date:
                        days_until = (task.due_date - now).days
                        if days_until < 0:
                            meta_parts.append(f"Due: {task.due_date.strftime('%Y-%m-%d')} (⚠️ OVERDUE by {abs(days_until)} days)")
                        elif days_until <= 7:
                            meta_parts.append(f"Due: {task.due_date.strftime('%Y-%m-%d')} (in {days_until} days)")
                        else:
                            meta_parts.append(f"Due: {task.due_date.strftime('%Y-%m-%d')}")

                    # Source link (if Obsidian)
                    if 'obsidian' in task.source_systems:
                        task_db_path = self._obsidian.task_database.relative_to(vault_path)
                        encoded_path = urllib.parse.quote(str(task_db_path))
                        uri = f"obsidian://open?vault={urllib.parse.quote(vault_name)}&file={encoded_path}"
                        meta_parts.append(f"[View]({uri})")

                    if len(task.source_systems) > 1:
                        other_sources = [s for s in task.source_systems if s != source]
                        meta_parts.append(f"Also in: {', '.join(other_sources)}")

                    lines.append(f"  - {' | '.join(meta_parts)}")
                    lines.append("")

            lines.append("")

        return '\n'.join(lines)

    def cleanup_stale_tasks(self, stale_threshold_days: Optional[int] = None) -> List[Task]:
        """
        Find stale tasks that may need review

        A task is considered stale if:
        - It has a due date that's more than threshold days overdue
        - This indicates the task was likely forgotten or is no longer relevant

        Args:
            stale_threshold_days: Days overdue to consider stale (default from config)

        Returns:
            List of stale tasks sorted by staleness (oldest first)
        """
        if stale_threshold_days is None:
            stale_threshold_days = self.config.get('cleanup', {}).get('stale_threshold_days', 30)

        self.logger.info(f"Finding tasks overdue by {stale_threshold_days}+ days...")

        # Get all tasks
        all_tasks = self.aggregate_tasks()
        deduplicated_tasks = self.deduplicate_tasks(all_tasks)

        # Find stale tasks
        stale_tasks = []
        now = datetime.now()

        for task in deduplicated_tasks:
            # Only consider tasks with due dates
            if not task.due_date:
                continue

            # Calculate days overdue
            days_overdue = (now - task.due_date).days

            # Flag if overdue by threshold or more
            if days_overdue >= stale_threshold_days:
                task.attention_tax = self.calculate_attention_tax(task)
                task.metadata['days_overdue'] = days_overdue
                stale_tasks.append(task)
                self.logger.info(
                    f"Stale task: '{task.title[:40]}' (overdue by {days_overdue} days)"
                )

        # Sort by days overdue (oldest first)
        stale_tasks.sort(key=lambda t: t.metadata['days_overdue'], reverse=True)

        self.logger.info(f"Found {len(stale_tasks)} stale tasks (overdue by {stale_threshold_days}+ days)")

        return stale_tasks

    # ==================== Integration Methods ====================

    def _get_todoist_tasks(self) -> List[Task]:
        """Get tasks from Todoist via cache"""
        raw_tasks = self._todoist.get_tasks()

        tasks = []
        for raw in raw_tasks:
            task = Task(
                id=raw['id'],
                title=raw['title'],
                priority=raw['priority'],
                energy=raw['energy'],
                attention=raw['attention'],
                due_date=raw['due_date'],
                source_systems=raw['source_systems'],
                metadata=raw['metadata']
            )
            tasks.append(task)

        return tasks

    def _get_obsidian_tasks(self) -> List[Task]:
        """Get tasks from Obsidian task database"""
        raw_tasks = self._obsidian.get_tasks()

        tasks = []
        for raw in raw_tasks:
            task = Task(
                id=raw['id'],
                title=raw['title'],
                priority=raw['priority'],
                energy=raw['energy'],
                attention=raw['attention'],
                due_date=raw['due_date'],
                source_systems=raw['source_systems'],
                metadata=raw['metadata']
            )
            tasks.append(task)

        return tasks

    def _get_daily_note_tasks(self) -> List[Task]:
        """Get tasks from today's daily note action items"""
        raw_tasks = self._obsidian.get_daily_note_tasks()

        tasks = []
        for raw in raw_tasks:
            task = Task(
                id=raw['id'],
                title=raw['title'],
                priority=raw['priority'],
                energy=raw['energy'],
                attention=raw['attention'],
                due_date=raw['due_date'],
                source_systems=raw['source_systems'],
                metadata=raw['metadata']
            )
            tasks.append(task)

        return tasks


# ==================== CLI Interface ====================

def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="TaskManager: AI-powered task orchestrator"
    )
    parser.add_argument(
        'command',
        choices=['recommend', 'list', 'status', 'complete', 'cleanup', 'sync-daily', 'sync-dashboard', 'sync-completions'],
        help='Command to execute'
    )
    parser.add_argument(
        '--task-id',
        help='Task ID (for complete command)'
    )
    parser.add_argument(
        '--max-tasks',
        type=int,
        help='Maximum tasks to return (for recommend command)'
    )
    parser.add_argument(
        '--source',
        choices=['obsidian', 'todoist', 'daily_note', 'all'],
        default='all',
        help='Filter tasks by source (for list command)'
    )
    parser.add_argument(
        '--priority',
        choices=['P1', 'P2', 'P3', 'P4', 'all'],
        default='all',
        help='Filter tasks by priority (for list command)'
    )
    parser.add_argument(
        '--stale-threshold',
        type=int,
        help='Days overdue to consider stale (for cleanup command, default: 30)'
    )
    parser.add_argument(
        '--config',
        help='Path to config file'
    )

    args = parser.parse_args()

    # Initialize agent
    try:
        agent = TaskManager(config_path=args.config)
    except Exception as e:
        print(f"❌ Failed to initialize TaskManager: {e}")
        return 1

    # Execute command
    if args.command == 'recommend':
        result = agent.recommend_next_actions(max_tasks=args.max_tasks)
        critical_tasks = result['critical']
        recommended_tasks = result['recommended']

        # Show critical tasks first (if any)
        if critical_tasks:
            print(f"\n🚨 CRITICAL TASKS ({len(critical_tasks)}):")
            print("=" * 60)
            for i, task in enumerate(critical_tasks, 1):
                print(f"\n{i}. [{task.priority}] {task.title}")
                print(f"   ID: {task.id}")
                print(f"   Attention Tax: {task.attention_tax:.1f}")
                print(f"   Energy: {task.energy}, Attention: {task.attention}")
                if task.due_date:
                    days_until = (task.due_date - datetime.now()).days
                    if days_until < 0:
                        print(f"   Due: {task.due_date.strftime('%Y-%m-%d')} (⚠️  OVERDUE by {abs(days_until)} days)")
                    elif days_until == 0:
                        print(f"   Due: {task.due_date.strftime('%Y-%m-%d')} (⚠️  DUE TODAY)")
                    elif days_until == 1:
                        print(f"   Due: {task.due_date.strftime('%Y-%m-%d')} (DUE TOMORROW)")
                    else:
                        print(f"   Due: {task.due_date.strftime('%Y-%m-%d')} (in {days_until} days)")
                print(f"   Sources: {', '.join(task.source_systems)}")
        else:
            print(f"\n✅ No critical tasks - great!")

        # Show capacity-matched recommendations
        print(f"\n\n📋 RECOMMENDED TASKS ({len(recommended_tasks)}):")
        print("=" * 60)
        print("(Sorted by Attention Tax: lowest first = easiest wins)\n")
        for i, task in enumerate(recommended_tasks, 1):
            print(f"{i}. [{task.priority}] {task.title}")
            print(f"   ID: {task.id}")
            print(f"   Attention Tax: {task.attention_tax:.1f}")
            print(f"   Energy: {task.energy}, Attention: {task.attention}")
            if task.due_date:
                print(f"   Due: {task.due_date.strftime('%Y-%m-%d')}")
            print(f"   Sources: {', '.join(task.source_systems)}")
            print()

    elif args.command == 'list':
        # Get all tasks
        all_tasks = agent.aggregate_tasks()
        deduplicated_tasks = agent.deduplicate_tasks(all_tasks)

        # Apply filters
        filtered_tasks = deduplicated_tasks

        # Filter by source
        if args.source != 'all':
            filtered_tasks = [t for t in filtered_tasks if args.source in t.source_systems]

        # Filter by priority
        if args.priority != 'all':
            filtered_tasks = [t for t in filtered_tasks if t.priority == args.priority]

        # Calculate attention tax for sorting
        for task in filtered_tasks:
            task.attention_tax = agent.calculate_attention_tax(task)

        # Group tasks by source system
        by_source = {}
        for task in filtered_tasks:
            for source in task.source_systems:
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(task)

        # Display results
        filter_desc = []
        if args.source != 'all':
            filter_desc.append(f"source={args.source}")
        if args.priority != 'all':
            filter_desc.append(f"priority={args.priority}")

        filter_str = f" ({', '.join(filter_desc)})" if filter_desc else ""

        print(f"\n📋 ALL TASKS{filter_str}:")
        print("=" * 60)
        print(f"Total: {len(filtered_tasks)} tasks (after deduplication)")
        print(f"Before deduplication: {len(all_tasks)} tasks\n")

        # Show by source
        for source in sorted(by_source.keys()):
            source_tasks = by_source[source]
            print(f"\n{source.upper()} ({len(source_tasks)} tasks):")
            print("-" * 40)

            # Sort by priority then attention tax
            priority_order = {'P1': 0, 'P2': 1, 'P3': 2, 'P4': 3}
            source_tasks.sort(key=lambda t: (priority_order.get(t.priority, 4), t.attention_tax))

            for task in source_tasks:
                print(f"\n  [{task.priority}] {task.title}")
                print(f"  ID: {task.id}")
                print(f"  Attention Tax: {task.attention_tax:.1f} | Energy: {task.energy} | Attention: {task.attention}")
                if task.due_date:
                    days_until = (task.due_date - datetime.now()).days
                    if days_until < 0:
                        print(f"  Due: {task.due_date.strftime('%Y-%m-%d')} (⚠️  OVERDUE by {abs(days_until)} days)")
                    else:
                        print(f"  Due: {task.due_date.strftime('%Y-%m-%d')} (in {days_until} days)")
                if len(task.source_systems) > 1:
                    print(f"  Also in: {', '.join([s for s in task.source_systems if s != source])}")

    elif args.command == 'status':
        # Get all tasks
        all_tasks = agent.aggregate_tasks()
        deduplicated_tasks = agent.deduplicate_tasks(all_tasks)

        # Calculate stats
        for task in deduplicated_tasks:
            task.attention_tax = agent.calculate_attention_tax(task)

        # Get current capacity
        capacity = agent.get_current_capacity()

        # Count by source
        by_source = {}
        for task in deduplicated_tasks:
            for source in task.source_systems:
                by_source[source] = by_source.get(source, 0) + 1

        # Count by priority
        by_priority = {}
        for task in deduplicated_tasks:
            by_priority[task.priority] = by_priority.get(task.priority, 0) + 1

        # Count critical tasks
        critical_tasks = agent._identify_critical_tasks(deduplicated_tasks)

        # Count overdue tasks
        now = datetime.now()
        overdue_tasks = [t for t in deduplicated_tasks if t.due_date and t.due_date < now]

        # Display status
        print(f"\n📊 TASK MANAGER STATUS:")
        print("=" * 60)

        print(f"\n🗂️  TASK INVENTORY:")
        print(f"   Total Tasks (before deduplication): {len(all_tasks)}")
        print(f"   Total Tasks (after deduplication):  {len(deduplicated_tasks)}")
        print(f"   Duplicates Merged: {len(all_tasks) - len(deduplicated_tasks)}")

        print(f"\n📦 BY SOURCE:")
        for source in sorted(by_source.keys()):
            print(f"   {source.capitalize():<15} {by_source[source]:>3} tasks")

        print(f"\n🎯 BY PRIORITY:")
        for priority in ['P1', 'P2', 'P3', 'P4']:
            count = by_priority.get(priority, 0)
            if count > 0:
                print(f"   {priority:<15} {count:>3} tasks")

        print(f"\n⚡ CURRENT CAPACITY:")
        print(f"   Energy:    {capacity.energy.capitalize()}")
        print(f"   Attention: {capacity.attention.capitalize()}")
        print(f"   (Read from today's daily note at {capacity.timestamp.strftime('%H:%M')})")

        print(f"\n🚨 CRITICAL ALERTS:")
        print(f"   Critical Tasks:  {len(critical_tasks)}")
        print(f"   Overdue Tasks:   {len(overdue_tasks)}")

        if overdue_tasks:
            print(f"\n   Overdue items:")
            for task in sorted(overdue_tasks, key=lambda t: t.due_date)[:5]:
                days_overdue = (now - task.due_date).days
                print(f"     • [{task.priority}] {task.title[:50]}")
                print(f"       (overdue by {days_overdue} days)")

        # Integration status
        print(f"\n🔌 INTEGRATIONS:")
        print(f"   Obsidian:  ✅ Connected")
        if agent._todoist:
            print(f"   Todoist:   ✅ Connected")
        else:
            print(f"   Todoist:   ⚪ Disabled")

        print()

    elif args.command == 'complete':
        if not args.task_id:
            print("❌ --task-id required for complete command")
            return 1
        success = agent.mark_complete(args.task_id)
        if success:
            print(f"✅ Task {args.task_id} marked complete")
        else:
            print(f"❌ Failed to mark task {args.task_id} complete")

    elif args.command == 'cleanup':
        stale_tasks = agent.cleanup_stale_tasks(stale_threshold_days=args.stale_threshold)

        threshold = args.stale_threshold or agent.config.get('cleanup', {}).get('stale_threshold_days', 30)

        print(f"\n🧹 STALE TASKS (overdue by {threshold}+ days):")
        print("=" * 60)
        print(f"Found {len(stale_tasks)} stale tasks that may need review\n")

        if not stale_tasks:
            print("✅ No stale tasks found - everything is current!\n")
        else:
            print("These tasks are significantly overdue and may need attention:")
            print("- Archive/delete if no longer relevant")
            print("- Update due date if still important")
            print("- Complete if finished but not marked\n")

            for i, task in enumerate(stale_tasks, 1):
                days_overdue = task.metadata['days_overdue']
                print(f"{i}. [{task.priority}] {task.title}")
                print(f"   ID: {task.id}")
                print(f"   Due Date: {task.due_date.strftime('%Y-%m-%d')}")
                print(f"   Days Overdue: {days_overdue} days (⚠️  {days_overdue // 30} months)")
                print(f"   Attention Tax: {task.attention_tax:.1f}")
                print(f"   Sources: {', '.join(task.source_systems)}")
                print()

    elif args.command == 'sync-daily':
        success = agent.sync_daily_note()
        if success:
            print("✅ Tasks synced to today's daily note")
        else:
            print("❌ Failed to sync tasks to daily note")
            return 1

    elif args.command == 'sync-dashboard':
        success = agent.sync_dashboard()
        if success:
            print("✅ Task Dashboard updated at 80 - Tasks/Task Dashboard.md")
        else:
            print("❌ Failed to update Task Dashboard")
            return 1

    elif args.command == 'sync-completions':
        result = agent.sync_completions()
        completed = result['completed']
        failed = result['failed']

        print(f"\n✅ Completion Sync Results:")
        print(f"   Completed: {completed} tasks")
        print(f"   Failed: {failed} tasks")

        if completed > 0:
            print(f"\n✨ {completed} task(s) marked complete in source systems")
        if failed > 0:
            print(f"\n⚠️  {failed} task(s) could not be marked complete")

        return 0 if failed == 0 else 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
