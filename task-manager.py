#!/usr/bin/env python3
"""
task-manager CLI

AI-powered task orchestrator that aggregates tasks from multiple systems
and recommends what to work on based on current energy/attention capacity.

Usage:
    ./task-manager.py recommend              # Get 3-5 recommended tasks
    ./task-manager.py list                   # List all tasks
    ./task-manager.py complete <task_id>     # Mark task complete
    ./task-manager.py cleanup                # Find stale tasks

Examples:
    # Get task recommendations for current capacity
    ./task-manager.py recommend

    # Get up to 10 recommendations
    ./task-manager.py recommend --max-tasks 10

    # Mark task complete across all systems
    ./task-manager.py complete abc123

    # Find tasks with no activity in 30+ days
    ./task-manager.py cleanup
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from task_manager import main

if __name__ == '__main__':
    sys.exit(main())
