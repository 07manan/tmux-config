#!/usr/bin/env python3
"""Session rows for tmux-sessionx: most recently used first, each with how
long ago you were last in it, its window count, a marker when Claude Code is
running in it, and the directory of its active pane.

    Magcore    2m  ⧉ 2 ✻  ~/work/magcore
    Kenstar    2h  ⧉ 2    ~/work/kenstar/kenstar-frontend

(⧉ stands in for the Nerd Font window icon in WIN, which doesn't survive
being pasted.)

Wired in from tmux.conf through fzf binds in @sessionx-additional-options, so
the plugin stays unmodified: 'start' loads these rows in place of the
plugin's bare names, sessionx-binds.py reloads them after a kill or rename,
and it imports sessions() to size the list box.

Output is oldest-first on purpose: sessionx always runs fzf with --tac, so
the LAST line printed here is the first row under the prompt.

The name has to come first and be one word. Only a row's first word is ever
used: enter goes through the plugin's strip_git_branch_info, which drops
everything from the first space, and sessionx-binds.py's kill and rename
take the first word of the focused row.
"""
import os, re, subprocess, time

DIM  = "\x1b[38;2;114;127;146m"   # #727f92, pill-theme text dim
FADE = "\x1b[38;2;74;84;102m"     # #4a5466, between dim and border
ACC  = "\x1b[38;2;154;181;221m"   # #9ab5dd, pill-theme accent
OFF  = "\x1b[0m"
WIN    = "\uf2d2"                 # window count (nf-fa-window_restore)
CLAUDE = "✻"                 # Claude Code's own spinner glyph
# Claude Code's executable is named after its version (2.1.312), the same
# reason tmux.conf's automatic-rename-format checks for it
VERSION = re.compile(r"^[0-9]+([.][0-9]+)+$")


def tmux(*args):
    return subprocess.run(["tmux", *args], capture_output=True, text=True).stdout


def ago(then):
    s = time.time() - then
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if s >= size:
            return f"{int(s // size)}{unit}"
    return "now"


def sessions():
    """The sessions the rows show, oldest first, as (last attached, window
    count, active pane's path, name), plus the names running Claude and the
    current session. One tmux call: tmux runs ";"-separated commands in
    order, and each line is tagged with which command printed it."""
    out = tmux("list-panes", "-a", "-F", "P\t#{session_name}\t#{pane_current_command}", ";",
               "list-sessions", "-F", "S\t#{session_last_attached}\t#{session_windows}\t"
               "#{pane_current_path}\t#{session_name}", ";",
               "display-message", "-p", "O\t#{@sessionx-filtered-sessions}\t"
               "#{@sessionx-filter-current}\t#S")
    claude, rows, options = set(), [], ["", "", ""]
    for line in out.splitlines():
        tag, *fields = line.split("\t")
        if tag == "P" and (fields[1] == "claude" or VERSION.match(fields[1])):
            claude.add(fields[0])
        elif tag == "S":
            rows.append(fields)
        elif tag == "O":
            options = fields
    filtered, filter_current, current = options

    # session_last_attached = when you last switched to it, which is the
    # "most used" signal you actually want. session_activity would also tick
    # up from background pane output in sessions you never looked at.
    rows.sort(key=lambda s: int(s[0] or 0))
    if filtered:
        rows = [s for s in rows if not re.search(filtered.replace(",", "|"), s[3])]
    # With only one session, filtering out the current one leaves no rows,
    # and sessionx's --exit-0 closes the popup the moment it opens. Show the
    # current session then, like the plugin's own input() does.
    if (filter_current or "true") == "true":
        rows = [s for s in rows if s[3] != current] or [s for s in rows if s[3] == current]
    return rows, claude, current


def main():
    rows, claude, _ = sessions()
    home = os.path.expanduser("~")
    width = max((len(s[3]) for s in rows), default=0)
    for last, windows, path, name in rows:
        if path == home or path.startswith(home + "/"):
            path = "~" + path[len(home):]
        mark = f"{ACC}{CLAUDE}" if name in claude else " "
        # Bold but uncoloured, so fzf still brightens the focused row's name
        print(f"\x1b[1m{name:<{width}}\x1b[22m  {DIM}{ago(int(last)) if int(last or 0) else '':>4}  "
              f"{FADE}{WIN} {windows:<2}{mark}  {DIM}{path}{OFF}")


if __name__ == "__main__":
    main()
