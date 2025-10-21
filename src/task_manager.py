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

        # Initialize integrations (lazy loaded)
        self._todoist = None
        self._obsidian = None

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

        # TODO: Implement in Increment 1-3
        # tasks.extend(self._get_todoist_tasks())
        # tasks.extend(self._get_obsidian_tasks())
        # tasks.extend(self._get_daily_note_tasks())

        self.logger.info(f"Found {len(tasks)} total tasks")
        return tasks

    def deduplicate_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Deduplicate tasks using task_deduplicator agent

        Args:
            tasks: List of tasks potentially containing duplicates

        Returns:
            List of unique tasks
        """
        self.logger.info(f"Deduplicating {len(tasks)} tasks...")

        # TODO: Implement in Increment 4
        # - Import task_deduplicator from AI-assistant
        # - Run deduplication
        # - Merge source_systems for duplicates

        return tasks

    def get_current_capacity(self) -> Capacity:
        """
        Read current energy/attention from today's daily note

        Returns:
            Capacity object with energy and attention levels
        """
        self.logger.info("Reading current capacity from daily note...")

        # TODO: Implement in Increment 3
        # - Read today's daily note
        # - Parse "How I'm Feeling" section
        # - Extract energy and attention levels

        # Default to medium/medium if not found
        return Capacity(energy="medium", attention="medium")

    def calculate_attention_tax(self, task: Task) -> float:
        """
        Calculate Attention Tax score using Obsidian formula

        Formula: Priority × Energy Multiplier × Deadline Multiplier

        Args:
            task: Task to calculate score for

        Returns:
            Attention Tax score
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

        return priority_score * energy_mult * deadline_mult

    def recommend_next_actions(
        self,
        capacity: Optional[Capacity] = None,
        max_tasks: Optional[int] = None
    ) -> List[Task]:
        """
        Recommend tasks matching current capacity

        Args:
            capacity: Current energy/attention (if None, will read from daily note)
            max_tasks: Maximum tasks to return (default from config)

        Returns:
            List of recommended tasks sorted by Attention Tax
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

        # Filter by capacity match
        # TODO: Implement smart filtering in Increment 6
        matched_tasks = all_tasks

        # Sort by Attention Tax (highest first)
        matched_tasks.sort(key=lambda t: t.attention_tax, reverse=True)

        # Return top N
        recommendations = matched_tasks[:max_tasks]

        self.logger.info(f"Recommended {len(recommendations)} tasks")
        return recommendations

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
        """Get tasks from Todoist via MCP"""
        # TODO: Implement in Increment 1
        return []

    def _get_obsidian_tasks(self) -> List[Task]:
        """Get tasks from Obsidian task database"""
        # TODO: Implement in Increment 2
        return []

    def _get_daily_note_tasks(self) -> List[Task]:
        """Get tasks from today's daily note action items"""
        # TODO: Implement in Increment 3
        return []


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
        recommendations = agent.recommend_next_actions(max_tasks=args.max_tasks)
        print(f"\n📋 Recommended Tasks ({len(recommendations)}):\n")
        for i, task in enumerate(recommendations, 1):
            print(f"{i}. [{task.priority}] {task.title}")
            print(f"   Attention Tax: {task.attention_tax:.1f}")
            print(f"   Energy: {task.energy}, Attention: {task.attention}")
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
