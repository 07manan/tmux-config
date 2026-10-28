#!/usr/bin/env bash
# Repairs a tmux-resurrect save file in place. Wired in from tmux.conf as
# @resurrect-hook-post-save-layout, which passes the file path.
#
# 1. Shifted lines. resurrect writes one tab-separated line per pane and reads
#    it back with `IFS=$'\t' read`. Tab counts as whitespace there, so an
#    empty field vanishes: a pane with an empty title shifts every later field
#    left by one. The directory lands in the title slot and the dir slot gets
#    "1" (pane_active), so on restore the pane starts in $HOME instead of its
#    directory. A good line has the dir (always ":"-prefixed) in field 8; a
#    shifted one has it in field 7, so put it back and give the title a
#    placeholder that can't collapse. The shifted pid is useless as a command,
#    so the full command is left empty and the pane restores to a plain shell.
#
# 2. Claude Code panes. The saved command is whatever started Claude (often
#    `claude -r`, which would reopen the picker). Rewrite it to resume the
#    exact session, using the id claude-pane-session.sh stored on the pane,
#    or `claude --continue` (latest session in that dir) when there is none.
#    `claude` is on @resurrect-processes, so the restore runs this command.
file=$1
[ -f "$file" ] || exit 0
tmp=$(mktemp) || exit 1
awk -F'\t' -v OFS='\t' '
	$1 == "pane" && $8 !~ /^:/ && $7 ~ /^:/ {
		print $1, $2, $3, $4, $5, $6, "-", $7, $8, $9, ":"
		next
	}
	{ print }
' "$file" >"$tmp"

out=$(mktemp) || exit 1
while IFS= read -r line; do
	IFS=$'\t' read -r -a f <<<"$line"
	if [ "${f[0]}" = pane ] && [[ "${f[10]}" =~ ^:claude( |$) ]]; then
		id=$(tmux show -pqv -t "=${f[1]}:${f[2]}.${f[5]}" @claude_session 2>/dev/null)
		# Keep the other flags; drop any resume/continue and its session arg
		args=$(sed -E 's/^:claude//; s/ (-r|--resume|-c|--continue)( [0-9a-f-]{36})?//g' <<<"${f[10]}")
		if [ -n "$id" ]; then f[10]=":claude --resume $id$args"; else f[10]=":claude --continue$args"; fi
		line=$(IFS=$'\t'; echo "${f[*]}")
	fi
	printf '%s\n' "$line"
done <"$tmp" >"$out" && cat "$out" >"$file"
rm -f "$tmp" "$out"
