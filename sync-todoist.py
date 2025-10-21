#!/usr/bin/env python3
"""
Sync Todoist tasks to cache for task-manager

This script is meant to be run by Claude Code using MCP tools.
It fetches all Todoist tasks and saves them to cache/todoist_tasks.json.

Usage (in Claude Code):
> Run sync-todoist.py to refresh the Todoist cache
"""

import json
import sys
from pathlib import Path

def sync_todoist_via_mcp():
    """
    This function is a placeholder.

    Claude Code should run this file and then use MCP tools to:
    1. Call mcp__todoist__get_tasks_list with appropriate filters
    2. Save results to cache/todoist_tasks.json

    Example Claude Code workflow:
    ```
    # Get all active tasks from key projects
    tasks = mcp__todoist__get_tasks_list(limit=200)

    # Save to cache
    cache_file = Path('~/git/task-manager/cache/todoist_tasks.json').expanduser()
    cache_file.parent.mkdir(exist_ok=True)

    with open(cache_file, 'w') as f:
        json.dump(tasks, f, indent=2, default=str)

    print(f"✅ Synced {len(tasks)} Todoist tasks to {cache_file}")
    ```
    """
    print("⚠️  This script requires Claude Code with MCP access.")
    print("Please ask Claude Code to sync Todoist using MCP tools.")
    print("\nSee docs/TODOIST_SYNC.md for instructions.")
    return 1

if __name__ == '__main__':
    sys.exit(sync_todoist_via_mcp())
