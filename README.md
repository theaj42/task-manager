# task-manager

**Version**: 0.1.0 (Development)
**Status**: 🚧 Under Construction

AI-powered task management orchestrator that aggregates tasks from multiple systems (Todoist, Obsidian, daily notes) and recommends what to work on based on your current energy and attention capacity.

## Problem

I'm good at capturing tasks but terrible at organizing, executing, and maintaining them. This agent handles the organize/maintain steps so I can focus on execution.

## Features (Planned)

- ✅ **Multi-source aggregation**: Pulls from Todoist, Obsidian task database, daily notes
- ✅ **Smart deduplication**: Identifies same task across systems
- ✅ **Capacity-aware recommendations**: Suggests 3-5 tasks matching current energy/attention
- ✅ **Attention Tax scoring**: Uses Obsidian formula to prioritize high-impact tasks
- ✅ **Bidirectional sync**: Marks tasks complete across all systems
- ✅ **Automated maintenance**: Flags stale tasks, archives completed work

## Architecture

Self-contained Python agent following the `SelfContainedAgent` pattern from [AI-assistant](https://github.com/theaj42/AI-assistant).

**Integrations**:
- Todoist (via MCP server)
- Obsidian vault (direct file access)
- AI-assistant agents (`task_deduplicator`)

## Installation

```bash
# Clone repo
git clone https://github.com/theaj42/task-manager.git
cd task-manager

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure (copy template and edit)
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your paths
```

## Usage

```bash
# Get task recommendations based on current capacity
./task-manager.py recommend

# List all tasks from all sources
./task-manager.py list

# Mark task complete (syncs to all systems)
./task-manager.py complete <task_id>

# Find stale tasks needing review
./task-manager.py cleanup
```

## Development Status

See [PRD.md](PRD.md) for full project plan and increment breakdown.

**Current Phase**: Phase 1 (MVP - Read-only aggregation + recommendations)

**Progress**:
- [ ] Increment 1: Todoist integration
- [ ] Increment 2: Obsidian task database reading
- [ ] Increment 3: Daily note parsing
- [ ] Increment 4: Task deduplication
- [ ] Increment 5: Attention Tax calculation
- [ ] Increment 6: Capacity-based recommendations

## Contributing

This is a personal project built for my specific workflow, but feel free to fork and adapt for your needs!

## License

MIT

---

**Built with [Claude Code](https://claude.com/claude-code)**
