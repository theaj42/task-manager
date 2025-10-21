# Todoist Sync via MCP

The task-manager uses a cache-based approach for Todoist integration:
1. Claude Code syncs Todoist→`cache/todoist_tasks.json` using MCP tools
2. Python reads from cache file
3. This decouples MCP calls from Python execution and improves performance

## Syncing Todoist Data

To populate the Todoist cache, ask Claude Code to run:

```python
# Claude Code will execute this to sync Todoist
import json
from pathlib import Path

# Use MCP tool to get all tasks
tasks = mcp__todoist__get_tasks_list()

# Save to cache
cache_dir = Path('~/git/task-manager/cache').expanduser()
cache_dir.mkdir(exist_ok=True)
cache_file = cache_dir / 'todoist_tasks.json'

with open(cache_file, 'w') as f:
    json.dump(tasks, f, indent=2, default=str)

print(f"✅ Synced {len(tasks)} Todoist tasks to {cache_file}")
```

## Automatic Sync

You can set up a cron job or LaunchAgent to periodically sync:

```bash
# Example: Sync every hour
*/60 * * * * cd ~/git/task-manager && /path/to/sync-todoist.py
```

## Manual Sync

Ask Claude Code:
> "Sync my Todoist tasks to task-manager cache"

## Label Convention

For task-manager to properly categorize Todoist tasks, use these labels:
- **Energy**: `energy-low`, `energy-medium`, `energy-high`
- **Attention**: `attention-low`, `attention-medium`, `attention-high`

Tasks without these labels default to `medium/medium`.

## Priority Mapping

Todoist priorities map to task-manager as:
- Todoist **Priority 4** (urgent) → **P1**
- Todoist **Priority 3** (high) → **P2**
- Todoist **Priority 2** (medium) → **P3**
- Todoist **Priority 1** (normal) → **P4**
