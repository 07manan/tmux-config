#!/usr/bin/env python3
"""What tmux-sessionx's fzf does on the binds tmux.conf gives it, printed as
fzf actions. tmux.conf runs this through transform() with the bind's name:

  start, resize   draw the frame below for the popup's height
  enter           switch to the focused session, or create one from the
                  query, as the plugin's enter did
  esc             close the popup
  kill            (alt-bspace) kill the focused session
  rename          (ctrl-r) rename the focused session in place

The plugin binds its own keys after tmux.conf's options, and where both bind
a key the plugin's bind wins. tmux.conf parks the plugin's enter, esc, kill
and rename on F-keys that the start bind unbinds, which leaves those four
keys to this script. Kill and rename reload sessionx-list.py's rows
themselves, so the plugin's reload to bare session names never happens.

The frame:

  * The border label names the session you're switching from. The plugin's
    own --border-label captures that at config-load time and freezes it into
    a tmux option, so it went stale; tmux.conf turns the plugin's label off
    (@sessionx-legacy-fzf-support) and this one is computed per popup.
  * The keys go in the middle of the list box's top edge. (The plugin's
    header, a row of key names and bare icons, is hidden by the start bind.)
  * The preview gets every row the list doesn't need: the list box is as
    tall as the session list, up to MAX_ROWS, and scrolls past that.

Renaming: the plugin's rename cleared the popup for a bare "New name:"
prompt. Here the search box becomes the name field. The prompt shows the
old name and an arrow, the field starts with that name to edit, search is
off so the list holds still, and the legend shows enter and esc. Enter
renames and esc goes back. While renaming, alt-bspace deletes a word, as in
any macOS text field, instead of killing the session. fzf holds the mode
itself: search is off only while renaming, and the prompt carries the old
name.
"""
import importlib.util, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sessionx_list", f"{HERE}/sessionx-list.py")
rows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rows)

ACC  = "\x1b[38;2;154;181;221m"   # #9ab5dd, pill-theme accent
DIM  = "\x1b[38;2;114;127;146m"   # #727f92, pill-theme text dim
WARN = "\x1b[38;2;220;178;126m"   # #dcb27e, pill-theme warn
OFF  = "\x1b[0m"
PENCIL = "\uf040"                 # nf-fa-pencil
MAX_ROWS = 5
# Rows that are neither list rows nor the preview size fzf is given: the
# search box (3), the list box's top edge (1), and the preview box's top and
# bottom edges (2), which fzf adds on top of the size. fzf's own border is
# already outside FZF_LINES.
CHROME = 6
GHOST = "find or start a session"
# The keys tmux.conf binds to this script, as the legend shows them
LEGEND = [("enter", "switch"), ("alt-bspace", "kill"), ("ctrl-r", "rename")]
RENAMING = [("enter", "rename"), ("esc", "cancel")]
# Unbound while renaming: moving would leave the session being renamed, and
# the plugin's change:first would jump to the first row as you type
HOLD = "change,up,down,ctrl-p,ctrl-n,ctrl-j,ctrl-k"
ANSI = re.compile(r"\x1b\[[0-9;:]*m")


def tmux(*args):
    return subprocess.run(["tmux", *args], capture_output=True, text=True)


def act(action, arg):
    """action(arg), bracketed with a pair arg doesn't contain the closer of,
    so a ")" in a session name can't end it early."""
    for pair in ("()", "[]", "{}", "<>", "~~", "!!", "@@", "##", "%%", "^^", "&&", "||"):
        if pair[1] not in arg:
            return f"{action}{pair[0]}{arg}{pair[1]}"


def pretty(key):
    """ctrl-r -> ^R, alt-bspace -> ⌥⌫, enter -> ↵"""
    names = {"enter": "↵", "bspace": "⌫", "esc": "esc", "space": "␣"}
    mod, _, base = key.rpartition("-")
    base = names.get(base, base.upper() if len(base) == 1 else base)
    return {"ctrl": "^", "alt": "⌥", "": ""}.get(mod, mod + "-") + base


def legend(keys, note=""):
    return act("change-list-label", f" {note}" + "   ".join(
        f"{ACC}{pretty(key)} {DIM}{label}" for key, label in keys) + f" {OFF}")


def focused():
    """The focused row's session, or None for an empty list or a row that
    isn't a running session (a folder)."""
    words = ANSI.sub("", os.environ.get("FZF_CURRENT_ITEM", "")).split()
    if words and not tmux("has-session", "-t", f"={words[0]}").returncode:
        return words[0]


def renaming():
    """The session being renamed, read back from the prompt rename() set,
    or None outside rename mode."""
    if os.environ.get("FZF_INPUT_STATE") == "disabled":
        return ANSI.sub("", os.environ.get("FZF_PROMPT", ""))[2:].rsplit(" → ", 1)[0]


def frame(name=None):
    """Legend, ghost, preview height and border label; rename mode's legend
    and ghost when name is the session being renamed."""
    sessions, _, current = rows.sessions()
    shown = max(1, min(len(sessions), MAX_ROWS))
    preview = max(3, int(os.environ.get("FZF_LINES", 40)) - CHROME - shown)
    label = f" {ACC}\x1b[1mSessions{OFF}{DIM}  from {current} {OFF}"
    # A preview that started before a resize drew for the old height and fzf
    # doesn't rerun it when the box grows, leaving blank rows under it, so
    # refresh-preview reruns it at the new size. The label goes last, in the
    # colon form that takes the rest of the line, so a ")" in a session name
    # can't end it early.
    return (f"{legend(RENAMING) if name else legend(LEGEND)}"
            f"+{act('change-ghost', f'new name for {name}' if name else GHOST)}"
            f"+change-preview-window(up,{preview},border-block,noinfo)+refresh-preview"
            f"+change-border-label:{label}")


def leave():
    """Back from rename mode to switching."""
    prompt = tmux("display-message", "-p", "#{@sessionx-prompt}").stdout.rstrip("\n")
    return (f"enable-search+change-query()+{act('change-prompt', prompt or ' ')}"
            f"+rebind({HOLD})+{frame()}")


def enter():
    old = renaming()
    if old is None:
        return "replace-query+print-query"
    new = os.environ.get("FZF_QUERY", "").strip()
    if new == old:
        return leave()
    # Rows and the plugin take a session's name to be a row's first word
    problem = ("type a name, or esc to keep it" if not new else
               "no spaces in a session name" if re.search(r"\s", new) else
               tmux("rename-session", "-t", f"={old}", new).stderr.strip())
    if problem:
        return legend(RENAMING, f"{WARN}{problem}   ")
    return f"reload({HERE}/sessionx-list.py)+{leave()}"


def esc():
    return "abort" if renaming() is None else leave()


def kill():
    if renaming() is not None:
        return "backward-kill-word"
    name = focused()
    if not name:
        return ""
    tmux("kill-session", "-t", f"={name}")
    return f"reload({HERE}/sessionx-list.py)+{frame()}"


def rename():
    name = focused()
    if renaming() is not None or not name:
        return ""
    # unbind(change) comes before change-query, which would otherwise fire it
    return (f"disable-search+unbind({HOLD})"
            f"+{act('change-prompt', f'{WARN}{PENCIL} {DIM}{name} {ACC}→ {OFF}')}"
            f"+{act('change-query', name)}+{frame(name)}")


BINDS = {"start": frame, "resize": lambda: frame(renaming()), "enter": enter,
         "esc": esc, "kill": kill, "rename": rename}
print(BINDS[sys.argv[1]]())
