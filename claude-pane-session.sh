#!/usr/bin/env bash
# Claude Code SessionStart hook (registered in ~/.claude/settings.json).
#
# Records the session id on the tmux pane Claude runs in, as the pane option
# @claude_session, so resurrect-fix-save.sh can save that pane's command as
# `claude --resume <id>` and a restore reopens the same conversation.
# SessionStart also fires on /clear and /resume, so the option follows
# whichever session the pane is showing.
[ -n "$TMUX_PANE" ] || exit 0
id=$(sed -n 's/.*"session_id" *: *"\([^"]*\)".*/\1/p')
[ -n "$id" ] && tmux set -p -t "$TMUX_PANE" @claude_session "$id"
exit 0
