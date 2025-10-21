# Quick Start Guide

Get up and running with task-manager in 5 minutes.

## Prerequisites

- Python 3.13+
- Access to Obsidian vault
- Todoist account (optional but recommended)
- Claude Code with Todoist MCP server (for Todoist integration)

## Installation

```bash
# Clone the repository
git clone https://github.com/theaj42/task-manager.git
cd task-manager

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Edit config with your paths
# Required settings:
#   - obsidian.vault_path: Path to your Obsidian vault
#   - obsidian.task_database: Relative path to task database within vault
#   - obsidian.daily_notes_path: Relative path to daily notes
nano config/config.yaml
```

### Example Configuration

```yaml
obsidian:
  vault_path: "~/Dropbox/DropsyncFiles/git/obsidian/base_vault"
  task_database: "80 - Tasks/81 - Task Database/task_database.md"
  daily_notes_path: "1 - Daily"
  daily_note_format: "%Y-%m-%d"

todoist:
  enabled: true  # Set to false if not using Todoist
```

## First Run

```bash
# Test that configuration is working
./task-manager.py list

# Get task recommendations
./task-manager.py recommend
```

Expected output:
```
📋 Recommended Tasks (5):

1. [P1] Attend to Jira work (sprint end - today)
   Attention Tax: 15.0
   Energy: high, Attention: high
   Sources: obsidian, daily_note

2. [P2] Create test plan for Gemini CLI
   Attention Tax: 12.0
   Energy: medium, Attention: high
   Sources: todoist, obsidian
```

## Common Commands

```bash
# Get recommendations based on current capacity (from daily note)
./task-manager.py recommend

# Get more or fewer recommendations
./task-manager.py recommend --max-tasks 10

# List all tasks from all systems
./task-manager.py list

# Mark task complete (syncs to all systems)
./task-manager.py complete <task_id>

# Find stale tasks (30+ days old)
./task-manager.py cleanup
```

## Daily Workflow

### Morning (08:00)
1. Fill out "How I'm Feeling" in today's daily note:
   ```markdown
   ### How I'm Feeling
   - Current Energy Level: #energy/medium
   - Focus Capacity: #attention/high
   ```

2. Run recommendations:
   ```bash
   ./task-manager.py recommend
   ```

3. Pick a task and work on it

### During the Day
- Complete tasks via agent: `./task-manager.py complete <task_id>`
- Agent syncs completion to Todoist + Obsidian automatically
- Get fresh recommendations when switching tasks

### Evening (18:00)
- Run cleanup to review stale tasks:
  ```bash
  ./task-manager.py cleanup
  ```

## Integration with Claude Code

For best results, use task-manager from Claude Code sessions:

```bash
# In Claude Code
claude: Run task-manager recommend and tell me what I should focus on
```

Claude can:
- Interpret your capacity from daily note context
- Explain why certain tasks were recommended
- Help you complete tasks and track progress
- Suggest breaking down high-attention-tax tasks

## Troubleshooting

### Config file not found
```
❌ Config file not found: /path/to/config.yaml
```
**Solution**: Copy `config/config.example.yaml` to `config/config.yaml`

### Obsidian vault not found
```
⚠️  Obsidian vault not found: /path/to/vault
```
**Solution**: Update `obsidian.vault_path` in config.yaml with correct path

### No tasks returned
Check:
1. Obsidian task database exists and has uncompleted tasks
2. Daily note exists for today
3. Todoist MCP server is configured (if using Todoist)

### Todoist integration not working
- Ensure Todoist MCP server is installed for Claude Code
- Set `todoist.enabled: false` in config to disable if not needed

## Next Steps

- Read [PRD.md](../PRD.md) to understand the full vision
- Check [README.md](../README.md) for architecture details
- Review increment progress to see what's implemented

## Getting Help

- Check logs: `logs/task-manager.log`
- Run with debug logging: Set `logging.level: DEBUG` in config
- Open issue: https://github.com/theaj42/task-manager/issues
