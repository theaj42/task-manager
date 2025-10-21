# Auto-Sync Documentation

## Overview

The task-manager auto-syncs with Obsidian daily at **04:00 AM** to prepare your day's tasks before you wake up.

## What Auto-Sync Does

Every morning at 0400, the system runs three commands:

1. **sync-completions**: Marks any tasks you checked in yesterday's daily note as complete in their source systems
2. **sync-daily**: Updates today's daily note with fresh task recommendations based on your current capacity
3. **sync-dashboard**: Refreshes the Task Dashboard (80 - Tasks/Task Dashboard.md) with current task status

## Manual Sync

You can manually run these syncs anytime:

```bash
# Update today's daily note with fresh recommendations
./task-manager.py sync-daily

# Sync checked boxes to mark tasks complete
./task-manager.py sync-completions

# Update the Task Dashboard
./task-manager.py sync-dashboard

# Or run all three at once
./auto-sync.sh
```

## Logs

Auto-sync logs are saved to:
- `logs/auto-sync.log` - Detailed sync activity
- `logs/launchd.log` - Standard output from launchd
- `logs/launchd-error.log` - Error output from launchd

## Managing the Schedule

**Check status**:
```bash
launchctl list | grep task-manager
```

**Disable auto-sync**:
```bash
launchctl unload ~/Library/LaunchAgents/com.user.task-manager.plist
```

**Re-enable auto-sync**:
```bash
launchctl load ~/Library/LaunchAgents/com.user.task-manager.plist
```

**Change the schedule**:
Edit `~/Library/LaunchAgents/com.user.task-manager.plist` and change the Hour/Minute values, then:
```bash
launchctl unload ~/Library/LaunchAgents/com.user.task-manager.plist
launchctl load ~/Library/LaunchAgents/com.user.task-manager.plist
```

## Workflow Integration

### Morning Routine
1. **04:00** - Auto-sync runs (you're asleep)
2. **Wake up** - Open today's daily note, find ## Tasks section pre-populated
3. **Work through tasks** - Check boxes as you complete them
4. **During day** - Run `./task-manager.py sync-daily` if capacity changes or you want fresh recommendations
5. **Anytime** - Run `./task-manager.py sync-completions` to sync checked boxes to source systems

### Manual Curation
- Open `80 - Tasks/Task Dashboard.md` anytime for full task list
- Check boxes to mark complete, run `sync-completions` to sync
- Edit tasks directly in Obsidian task database
- Run `sync-dashboard` to refresh the view

## How It Works

**Daily Note Integration**:
- Inserts `## Tasks` section between `## Planning` and `## Notes`
- Preserves checked boxes when re-syncing (won't undo your progress)
- Links to source tasks in Obsidian (clickable)

**Completion Sync**:
- Reads checked boxes from `## Tasks` section
- Finds matching tasks in source systems
- Marks complete in Obsidian task database (changes `- [ ]` to `- [x]`)
- Queues Todoist completions for MCP processing

**Task Dashboard**:
- Comprehensive view of ALL tasks (101 currently)
- Grouped by priority (P1 → P4), then by source
- Shows stats: total, critical, overdue
- Updated daily at 0400, or on-demand with `sync-dashboard`
