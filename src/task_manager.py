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
            systems: List of systems to update (default: all source systems)

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Marking task {task_id} complete...")

        # TODO: Implement in Increment 7-8
        # - Find task by ID
        # - Determine which systems it came from
        # - Update Todoist via MCP
        # - Update Obsidian task database
        # - Archive if configured

        return False

    def cleanup_stale_tasks(self) -> List[Task]:
        """
        Find tasks with no activity in 30+ days

        Returns:
            List of stale tasks flagged for review
        """
        self.logger.info("Finding stale tasks...")

        # TODO: Implement in Increment 10
        # - Get all tasks
        # - Check last modified date
        # - Flag tasks older than config threshold

        return []

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
        choices=['recommend', 'list', 'complete', 'cleanup'],
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
            print(f"   Attention Tax: {task.attention_tax:.1f}")
            print(f"   Energy: {task.energy}, Attention: {task.attention}")
            if task.due_date:
                print(f"   Due: {task.due_date.strftime('%Y-%m-%d')}")
            print(f"   Sources: {', '.join(task.source_systems)}")
            print()

    elif args.command == 'list':
        tasks = agent.aggregate_tasks()
        print(f"\n📋 All Tasks ({len(tasks)}):\n")
        for task in tasks:
            print(f"- [{task.priority}] {task.title}")

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
        stale_tasks = agent.cleanup_stale_tasks()
        print(f"\n🧹 Stale Tasks ({len(stale_tasks)}):\n")
        for task in stale_tasks:
            print(f"- [{task.priority}] {task.title}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
