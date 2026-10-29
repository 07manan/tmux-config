#!/usr/bin/env python3
"""Border label, key legend, preview height and row reloads for
tmux-sessionx, printed as fzf actions.

Run through transform() by three fzf binds in tmux.conf:

  start   applies the frame below
  resize  applies it again for the new height
  load    runs this with --if-bare and the focused row. The plugin's kill
          and rename keys reload bare session names. For those this answers
          with a reload to sessionx-list.py's full rows plus the frame
          refitted to the new count, and with nothing otherwise. tmux.conf
          only calls it for a row with no space or slash in it, so the load
          after our own reload (full rows) and folder lists start no Python.

The frame:

  * The border label names the session you're switching from. The plugin's
    own --border-label captures that at config-load time and freezes it into
    a tmux option, so it went stale; tmux.conf turns the plugin's label off
    (@sessionx-legacy-fzf-support) and this one is computed per popup.
  * The three keys tmux.conf leaves bound go in the middle of the list box's
    top edge, read from the same @sessionx-bind-* options the plugin
    reads, so a rebind in tmux.conf shows up here too. (The plugin's header,
    a row of key names and bare icons, is hidden by the start bind.)
  * The preview gets every row the list doesn't need: the list box is as
    tall as the session list, up to MAX_ROWS, and scrolls past that.
"""
import importlib.util, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sessionx_list", f"{HERE}/sessionx-list.py")
rows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rows)

ACC = "\x1b[38;2;154;181;221m"   # #9ab5dd, pill-theme accent
DIM = "\x1b[38;2;114;127;146m"   # #727f92, pill-theme text dim
OFF = "\x1b[0m"
MAX_ROWS = 5
# Rows that are neither list rows nor the preview size fzf is given: the
# search box (3), the list box's top and bottom edges (2), and the preview
# box's (2), which fzf adds on top of the size. fzf's own border is already
# outside FZF_LINES.
CHROME = 7

# (option, plugin default, label)
KEYS = [("@sessionx-bind-accept", "enter", "switch"),
        ("@sessionx-bind-kill-session", "alt-bspace", "kill"),
        ("@sessionx-bind-rename-session", "ctrl-r", "rename")]


def pretty(key):
    """ctrl-r -> ^R, alt-bspace -> ⌥⌫, enter -> ↵"""
    names = {"enter": "↵", "bspace": "⌫", "esc": "esc", "space": "␣"}
    mod, _, base = key.rpartition("-")
    base = names.get(base, base.upper() if len(base) == 1 else base)
    return {"ctrl": "^", "alt": "⌥", "": ""}.get(mod, mod + "-") + base


def main():
    bare = sys.argv[1:2] == ["--if-bare"]
    item = " ".join(sys.argv[2:]).strip()
    if bare and not item:
        return
    # The bind options, then (for --if-bare) whether the row names a session.
    # tmux stops at a failing command, so a non-session leaves returncode 1.
    check = [";", "has-session", "-t", f"={item}"] if bare else []
    out = subprocess.run(["tmux", "display-message", "-p",
                          "\t".join(f"#{{{o}}}" for o, _, _ in KEYS), *check],
                         capture_output=True, text=True)
    if bare and out.returncode:
        return
    bound = out.stdout.rstrip("\n").split("\t")
    legend = "   ".join(f"{ACC}{pretty(key or default)} {DIM}{label}"
                        for key, (_, default, label) in zip(bound, KEYS))

    sessions, _, current = rows.sessions()
    shown = max(1, min(len(sessions), MAX_ROWS))
    preview = max(3, int(os.environ.get("FZF_LINES", 40)) - CHROME - shown)

    label = f" {ACC}\x1b[1mSessions{OFF}{DIM}  from {current} {OFF}"
    # A preview that started before this resize drew for the old height and
    # fzf doesn't rerun it when the box grows, leaving blank rows under it,
    # so refresh-preview reruns it at the new size. The label goes last, in
    # the colon form that takes the rest of the line, so a ")" in a session
    # name can't end it early.
    print((f"reload({HERE}/sessionx-list.py)+" if bare else "") +
          f"change-list-label( {legend} {OFF})"
          f"+change-preview-window(down,{preview},border-rounded,noinfo)+refresh-preview"
          f"+change-border-label:{label}")


main()
