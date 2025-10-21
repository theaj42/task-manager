# Project: task-manager

**Version**: 1.0
**Created**: 2025-10-21
**Time Budget**: 3 sessions (6-8 hours)

## Problem Statement

I'm good at capturing tasks across multiple systems (Todoist, Obsidian, daily notes, AI sessions) but terrible at organizing, executing, and maintaining them. Current friction points:
- **Organizing**: Gets skipped, feels overwhelming
- **Executing**: Distracted by "whatever has attention" instead of working from list
- **Maintaining**: Forget to review/check off, or too tired when I remember

I need AI to handle the organize/maintain steps and present me with "what should I work on NOW" based on my current capacity (energy/attention levels).

## Success Criteria

- [ ] Aggregates tasks from all capture points (Todoist, Obsidian, daily notes)
- [ ] Deduplicates tasks automatically
- [ ] Reads current energy/attention from daily note
- [ ] Calculates Attention Tax scores using Obsidian formula
- [ ] Recommends 3-5 tasks matching current capacity
- [ ] Marks tasks complete across all systems bidirectionally
- [ ] Auto-maintains task lists (archives completed, flags stale)
- [ ] Works as CLI tool and as importable agent

## Explicit Non-Goals

- **NOT building** a web interface or task tracker UI
- **NOT building** task dependencies or project management (v1)
- **NOT building** time tracking or pomodoro features
- **NOT replacing** existing systems - this aggregates/orchestrates them
- **NOT adding** new capture methods - use existing Todoist/Obsidian/notes
- **Keeping it simple**: Read from multiple sources, present unified view, sync completions

## Core Requirements

1. **Task aggregation**: Pull from Todoist (MCP), Obsidian task database, today's daily note action items
2. **Deduplication**: Use existing `task_deduplicator` agent to identify duplicates across systems
3. **Capacity reading**: Parse energy/attention levels from daily note "How I'm Feeling" section
4. **Attention Tax calculation**: Implement Obsidian formula (Priority × Energy Multiplier × Deadline Multiplier)
5. **Smart recommendations**: Return 3-5 tasks that match current capacity (don't overwhelm)
6. **Bidirectional sync**: Mark complete in Todoist + Obsidian when task done
7. **Maintenance**: Flag tasks with no activity in 30+ days, auto-archive completed tasks
8. **CLI interface**: Can run `task-manager recommend` or `task-manager complete <task_id>`

## Technical Approach

**Language**: Python 3.13 (matches AI-assistant agent pattern)

**Key components**:
- Main agent: `TaskManager` class extending `SelfContainedAgent`
- Todoist integration: Via existing MCP server
- Obsidian integration: Direct file read/write (task database, daily notes)
- Deduplication: Import existing `task_deduplicator` agent
- CLI wrapper: Argparse-based interface

**Pattern**: Self-contained agent following AI-assistant architecture (see tools/agents/)

**Integrations**:
- Todoist MCP (need to enable for Claude Code)
- Obsidian vault at `~/Dropbox/DropsyncFiles/git/obsidian/base_vault/`
- Existing agent: `~/AI-assistant/tools/agents/task_deduplicator.py`
- Daily notes: `~/Dropbox/DropsyncFiles/git/obsidian/base_vault/1 - Daily/YYYY-MM-DD.md`

## Increments

### Increment 1: Basic Todoist integration
**What**: Connect to Todoist MCP, list all tasks, parse into standard format
**Test**: Run agent, verify it prints all Todoist tasks with metadata (priority, due date, labels)

### Increment 2: Obsidian task database reading
**What**: Read Obsidian task database file, parse markdown tasks with tags
**Test**: Run agent, verify it prints all Obsidian tasks with P1/P2/P3/P4, energy, attention tags

### Increment 3: Daily note parsing
**What**: Read today's daily note, extract action items and current energy/attention levels
**Test**: Run with today's note, verify it extracts "How I'm Feeling" and tasks from morning pages analysis

### Increment 4: Task deduplication
**What**: Combine all tasks, use task_deduplicator to identify same task across systems
**Test**: Create same task in Todoist + Obsidian, verify agent recognizes as duplicate

### Increment 5: Attention Tax calculation
**What**: Implement Obsidian formula, calculate score for each task
**Test**: Given task with P1 + high energy + due date, verify score = 15.0

### Increment 6: Capacity-based recommendations
**What**: Filter tasks by energy/attention match, sort by Attention Tax, return top 5
**Test**: Set daily note to "energy=low, attention=low", verify recommended tasks are low energy/attention

### Increment 7: Mark complete in Todoist
**What**: When task marked done, update Todoist via MCP
**Test**: Complete task via agent, verify task marked complete in Todoist app

### Increment 8: Mark complete in Obsidian
**What**: When task marked done, update Obsidian task database (checkbox + archive)
**Test**: Complete task via agent, verify task checked off in Obsidian file

### Increment 9: CLI interface
**What**: Add argparse wrapper for `recommend`, `complete`, `list`, `cleanup` commands
**Test**: Run `./task-manager.py recommend`, verify returns 3-5 tasks

### Increment 10: Stale task detection
**What**: Identify tasks with no updates in 30+ days, flag for review
**Test**: Add old task with created date 45 days ago, verify flagged in cleanup report

## Time Budget

**Target**: 3 sessions (6-8 hours total)

**Stop if**:
- Hitting 5 sessions (10+ hours) - reassess approach
- Any increment takes >1 hour - split it or simplify
- Getting bogged down in sync conflict resolution

**Red flags**:
- Building task UI or dashboard (out of scope)
- Adding new capture methods (use existing systems)
- Over-engineering the recommendation algorithm
- Debugging Obsidian file conflicts >30 minutes

## Open Questions (Answer Before Building)

1. **Todoist MCP setup**: Need to enable Todoist MCP for Claude Code first
2. **Task ID strategy**: How to uniquely identify tasks across systems? (Use hash of normalized text?)
3. **Sync conflicts**: What if task modified in both Obsidian and Todoist? (Obsidian wins for v1?)
4. **Completion tracking**: Where to store which system(s) a task came from? (Metadata field in unified task object)
5. **Energy/attention parsing**: What if daily note missing "How I'm Feeling"? (Default to medium/medium)
6. **Recommendation refresh**: How often to re-calculate? (Every time agent called, no caching for v1)

## Success Metrics (How We Know It Works)

After building:
- [ ] Can run `task-manager recommend` and get 3-5 tasks matching my current state
- [ ] Complete task via agent, see it marked done in both Todoist and Obsidian
- [ ] Add same task to Todoist and Obsidian, agent recognizes as duplicate
- [ ] Run cleanup, see tasks older than 30 days flagged for review
- [ ] Check Attention Tax scores, verify P1+high energy+due date = higher score than P3+low energy

## Phased Rollout

**Phase 1 (MVP - This week)**: Read-only aggregation + recommendations
- Increments 1-6
- Can recommend tasks, but not complete them
- Proves the core value: "what should I work on now?"

**Phase 2 (Bidirectional - Next week)**: Complete tasks across systems
- Increments 7-8
- Can mark tasks done, syncs to all systems
- Makes agent actually useful for daily workflow

**Phase 3 (Maintenance - Week 3)**: CLI + cleanup features
- Increments 9-10
- Polished interface, automated maintenance
- Production-ready for daily use

---

**PRD Review Checklist**:
- ✅ Success criteria clear and measurable
- ✅ Non-goals prevent scope creep
- ✅ Each increment has explicit test
- ✅ Time budget realistic (3 sessions)
- ⏳ Open questions need answers before starting
- ✅ Phased rollout allows early value delivery
