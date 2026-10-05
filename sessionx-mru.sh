#!/usr/bin/env bash
# MRU-ordered session list for tmux-sessionx.
#
# Wired in from tmux.conf via @sessionx-additional-options as an fzf
# 'start:reload(...)' bind, so the plugin itself stays unmodified and this
# survives TPM updates.
#
# Output is oldest-first on purpose: sessionx runs fzf with --tac and the
# default bottom-up layout, so the LAST line printed here is what ends up at
# the bottom of the list under the cursor.

tmux_option_or_fallback() {
	local value
	value="$(tmux show-option -gqv "$1")"
	[ -z "$value" ] && value="$2"
	echo "$value"
}

# session_last_attached = when you last switched to it, which is the "most
# used" signal you actually want. session_activity would also tick up from
# background pane output in sessions you never looked at.
sessions=$(tmux list-sessions -F '#{session_last_attached} #{session_name}' |
	sort -n | cut -d' ' -f2-)

filtered=$(tmux_option_or_fallback "@sessionx-filtered-sessions" "")
if [[ -n "$filtered" ]]; then
	sessions=$(echo "$sessions" | grep -Ev "$(echo "$filtered" | sed -E 's/,/|/g')")
fi

if [[ "$(tmux_option_or_fallback "@sessionx-filter-current" "true")" == "true" ]]; then
	current=$(tmux display-message -p '#S')
	sessions=$(echo "$sessions" | grep -Fxv "$current")
fi

echo "$sessions"
