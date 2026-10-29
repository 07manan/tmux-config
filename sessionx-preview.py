#!/usr/bin/env python3
"""Session preview for tmux-sessionx that shows every pane.

The plugin's preview runs `tmux capture-pane -t <session>`, which captures
only the active pane, so a split window previews as one pane. This draws the
session's current window the way tmux lays it out instead: each pane's text
scaled into its share of the preview, box-drawing borders between panes, and
the borders around the active pane in the accent blue. Each pane shows the
rows that end at its cursor or last output, so prompts and recent output stay
in view when a pane is cut down to fit.

Under the panes, where tmux's own status bar sits, is that session's status
bar: its name, then its windows as the same pills (current window in blue),
with the active pane's directory and git branch on the right, so you see
what's in a session before you switch to it.

Wired in from tmux.conf through the fzf 'start:' bind in
@sessionx-additional-options, so the plugin stays unmodified. Anything that
isn't a running session (a directory, *Last*) goes to the plugin's own
preview.sh.
"""
import os, re, subprocess, sys, unicodedata

PLUGIN_PREVIEW = os.path.expanduser(
    "~/.config/tmux/plugins/tmux-sessionx/scripts/preview.sh")
BORD = "\x1b[0;38;2;44;52;66m"     # #2c3442, pill-theme border
ACC  = "\x1b[0;38;2;154;181;221m"  # #9ab5dd, pill-theme accent
DIM  = "\x1b[0;38;2;114;127;146m"  # #727f92, pill-theme text dim
PLAIN = "\x1b[0m"
# Window pills, as pill-theme.gen.py draws them: rounded caps (U+E0B6 and
# U+E0B4) in the fill colour, then an index block and a name block
L, R, BRANCH = "\ue0b6", "\ue0b4", "\ue0a0"
# Session label, as status-left draws it: nf-oct-terminal icon, then a heavy divider
TERM, DIV = "\uf489", "\u2503"
# Between captured panes in capture(); no pane prints this line. It mustn't
# start with "-", or display-message reads it as flags and the call fails.
BREAK = "<<sessionx-preview pane break>>"
PILL_ON  = ("46;64;94", "154;181;221", "154;181;221", "15;19;27")   # index bg/fg, name bg/fg
PILL_OFF = ("57;65;79", "117;127;141", "45;51;63", "147;155;169")
# The strip under the label and pills, pill-theme BAR (#1e2532)
BAR = "30;37;50"
ON_BAR = f"\x1b[48;2;{BAR}m"

ESC = re.compile(r"\x1b(?:\[([0-9;:]*)([A-Za-z])|\][^\x07\x1b]*(?:\x07|\x1b\\))")
ATTR_OFF = {"22": ("1", "2"), "23": ("3",), "24": ("4",), "25": ("5", "6"),
            "27": ("7",), "28": ("8",), "29": ("9",)}
# Border glyph by which neighbours are also border: (up, down, left, right)
BOX = {(1, 1, 0, 0): "│", (0, 0, 1, 1): "─", (1, 1, 1, 1): "┼",
       (1, 1, 0, 1): "├", (1, 1, 1, 0): "┤", (0, 1, 1, 1): "┬",
       (1, 0, 1, 1): "┴", (0, 1, 0, 1): "┌", (0, 1, 1, 0): "┐",
       (1, 0, 0, 1): "└", (1, 0, 1, 0): "┘", (0, 0, 1, 0): "─",
       (0, 0, 0, 1): "─"}


def tmux(*args):
    return subprocess.run(["tmux", *args], capture_output=True, text=True).stdout


def apply_sgr(state, params):
    """Fold one SGR sequence into state: {"38": fg, "48": bg, "1": bold, ...}."""
    ps = params.split(";") if params else ["0"]
    i = 0
    while i < len(ps):
        p = ps[i]
        if p in ("", "0"):
            state.clear()
        elif p in ("38", "48", "58"):           # 5;n or 2;r;g;b follows
            n = 3 if ps[i + 1:i + 2] == ["5"] else 5
            state[p] = ";".join(ps[i:i + n])
            i += n - 1
        elif p in ("39", "49", "59"):
            state.pop(str(int(p) - 1), None)
        elif p.isdigit() and (30 <= int(p) <= 37 or 90 <= int(p) <= 97):
            state["38"] = p
        elif p.isdigit() and (40 <= int(p) <= 47 or 100 <= int(p) <= 107):
            state["48"] = p
        elif p in ATTR_OFF:
            for a in ATTR_OFF[p]:
                state.pop(a, None)
        else:                                   # attribute on, e.g. 1 or 4:3
            state[p.split(":")[0]] = p
        i += 1


def width(ch):
    if unicodedata.combining(ch) or ch in "​‍︎️":
        return 0
    return 2 if unicodedata.east_asian_width(ch) in "WF" else 1


def parse(lines):
    """Captured lines -> rows of (style, text, width) cells. capture-pane -e
    carries colours over from one line to the next, so state runs throughout."""
    state, style, rows = {}, PLAIN, []
    for line in lines:
        row, pos = [], 0
        for m in [*ESC.finditer(line), None]:
            for ch in line[pos:m.start() if m else len(line)]:
                w = width(ch)
                if w == 0 and row:
                    s, t, pw = row[-1]
                    row[-1] = (s, t + ch, pw)
                elif w:
                    row.append((style, ch, w))
            if m:
                if m.group(2) == "m":
                    apply_sgr(state, m.group(1))
                    style = "\x1b[0;" + ";".join(state.values()) + "m" if state else PLAIN
                pos = m.end()
        rows.append(row)
    return rows


def crop(row, w):
    """The first w columns of a row as exactly w grid cells ("" = wide-char tail)."""
    out = []
    for style, text, cw in row:
        if len(out) + cw > w:
            break
        out.append((style, text))
        out += [(style, "")] * (cw - 1)
    return out + [(PLAIN, " ")] * (w - len(out))


def pill(on, index, name):
    """One window pill and its width in columns."""
    ibg, ifg, nbg, nfg = PILL_ON if on else PILL_OFF
    text = (f"\x1b[0;38;2;{ibg};48;2;{BAR}m{L}\x1b[38;2;{ifg};48;2;{ibg}{';1' if on else ''}m{index} "
            f"\x1b[38;2;{nfg};48;2;{nbg}m {name} \x1b[0;38;2;{nbg};48;2;{BAR}m{R}")
    return text, len(index) + len(name) + 5


def branch(path):
    """git branch --show-current, without starting git: walk up to the .git
    directory (or the .git file a worktree has instead) and read its HEAD."""
    while True:
        git = os.path.join(path, ".git")
        try:
            if os.path.isfile(git):
                with open(git) as f:
                    git = os.path.join(path, f.read().split("gitdir:", 1)[-1].strip())
            if os.path.isdir(git):
                with open(os.path.join(git, "HEAD")) as f:
                    head = f.read().strip()
                return head[16:] if head.startswith("ref: refs/heads/") else ""
        except OSError:
            return ""
        if os.path.dirname(path) == path:
            return ""
        path = os.path.dirname(path)


def capture(panes):
    """capture-pane for every pane in one tmux call, split back apart at a
    line no pane will print."""
    args = []
    for pane in panes:
        args += [";", "capture-pane", "-ep", "-t", pane, ";", "display-message", "-p", BREAK]
    return tmux(*args[1:]).split(BREAK + "\n")[:len(panes)] if panes else []


def strip(session, windows, W):
    """The session label and window pills, with directory and branch
    right-aligned if they fit."""
    out = [f"{ACC}{ON_BAR}\x1b[1m {TERM} {session}  {DIM}{ON_BAR}{DIV}  "]
    used = len(session) + 8
    path = next((w[4] for w in windows if w[1] == "1"), "")
    for n, (index, active, name, cmd, cwd) in enumerate(windows):
        # An unnamed window shows what automatic-rename-format would
        name = name or (os.path.basename(cwd) if cmd in ("zsh", "bash", "fish", "sh")
                        else "claude" if re.match(r"^[0-9]+([.][0-9]+)+$", cmd) else cmd)
        name = name if len(name) <= 20 else name[:19] + "…"
        text, w = pill(active == "1", index, name)
        later = len(windows) - n - 1
        if used + w + (len(f" +{later}") if later else 0) > W:
            out.append(f"{DIM}{ON_BAR}+{later + 1}")      # windows that didn't fit
            used += len(f"+{later + 1}")
            break
        out.append(text + " ")
        used += w + 1

    home = os.path.expanduser("~")
    where = "~" + path[len(home):] if path == home or path.startswith(home + "/") else path
    ref = branch(path) if path else ""
    if ref:
        where += f"  {BRANCH} {ref}"
    # The strip runs the full width, with or without the directory
    if used + len(where) + 2 <= W:
        out.append(" " * (W - used - len(where)) + DIM + ON_BAR + where)
    else:
        out.append(" " * (W - used))
    return "".join(out) + PLAIN


def main():
    # The plugin passes the whole row; the session name is its first word
    name = sys.argv[1].split()[0] if len(sys.argv) > 1 and sys.argv[1].strip() else ""
    target = f"={name}:"
    # The window's size, its session's windows and its panes in one tmux
    # call, each line tagged with the command that printed it. has-session
    # goes first: tmux stops at a failing command, so anything that isn't a
    # session leaves returncode 1.
    info = subprocess.run(["tmux", "has-session", "-t", f"={name}", ";",
        "display-message", "-p", "-t", target,
        "D\t#{window_width}\t#{window_height}\t#{window_zoomed_flag}", ";",
        "list-windows", "-t", target, "-F", "W\t#{window_index}\t#{window_active}\t"
        "#{window_name}\t#{pane_current_command}\t#{pane_current_path}", ";",
        "list-panes", "-t", target, "-F", "P\t#{pane_id}\t#{pane_left}\t#{pane_top}\t"
        "#{pane_width}\t#{pane_height}\t#{pane_active}\t#{cursor_y}"],
        capture_output=True, text=True) if name else None
    if not info or info.returncode:
        os.execv(PLUGIN_PREVIEW, [PLUGIN_PREVIEW, *sys.argv[1:]])
    tagged = {"D": [], "W": [], "P": []}
    for line in info.stdout.splitlines():
        tag, *fields = line.split("\t")
        tagged.get(tag, []).append(fields)

    W = int(os.environ.get("FZF_PREVIEW_COLUMNS", 80))
    H = int(os.environ.get("FZF_PREVIEW_LINES", 24))
    # The window strip as the last row, unless the preview is tiny
    status = [strip(name, tagged["W"], W)] if H >= 6 else []
    H -= len(status)
    ww, wh, zoomed = map(int, tagged["D"][0])
    X = lambda x: round(x * W / ww)
    Y = lambda y: round(y * H / wh)

    # own[y][x]: index of the pane whose text fills the cell, or -1 for border
    own = [[None] * W for _ in range(H)]
    grid = [[(PLAIN, " ")] * W for _ in range(H)]
    active, shown = None, []
    for i, (pid, *nums) in enumerate(tagged["P"]):
        left, top, pw, ph, is_active, cursor = map(int, nums)
        if zoomed and not is_active:            # zoomed: only that pane shows
            continue
        if zoomed:
            left, top, pw, ph = 0, 0, ww, wh
        if is_active:
            active = i
        # Each pane's share runs up to and including the border cell after
        # it, so neighbouring shares meet exactly however the scale rounds.
        right, below = left + pw < ww, top + ph < wh
        x0, x1 = X(left), X(min(left + pw + 1, ww))
        y0, y1 = Y(top), Y(min(top + ph + 1, wh))
        cw, ch = x1 - x0 - right, y1 - y0 - below
        for y in range(y0, y1):
            if right:
                own[y][x1 - 1] = -1
        if below:
            for x in range(x0, x1):
                own[y1 - 1][x] = -1
        if cw > 0 and ch > 0:
            shown.append((i, pid, x0, y0, cw, ch, ph, cursor))

    for (i, pid, x0, y0, cw, ch, ph, cursor), text in zip(shown, capture([s[1] for s in shown])):
        rows = parse(text.split("\n")[:ph])
        used = [r for r, row in enumerate(rows) if any(t.strip() for _, t, _ in row)]
        end = max([cursor, *used])
        start = max(0, end - ch + 1)
        rows = rows[start:start + ch]
        for dy in range(ch):
            cells = crop(rows[dy] if dy < len(rows) else [], cw)
            for dx in range(cw):
                own[y0 + dy][x0 + dx] = i
                grid[y0 + dy][x0 + dx] = cells[dx]

    is_border = lambda x, y: 0 <= x < W and 0 <= y < H and own[y][x] == -1
    for y in range(H):
        for x in range(W):
            if own[y][x] != -1:
                continue
            key = (is_border(x, y - 1), is_border(x, y + 1),
                   is_border(x - 1, y), is_border(x + 1, y))
            near_active = any(0 <= x + dx < W and 0 <= y + dy < H and own[y + dy][x + dx] == active
                              for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            grid[y][x] = (ACC if near_active else BORD, BOX.get(tuple(map(int, key)), "│"))

    out = []
    for row in grid:
        line, last = [], None
        for style, text in row:
            if style != last:
                line.append(style)
                last = style
            line.append(text)
        out.append("".join(line) + PLAIN)
    sys.stdout.write("\n".join(out + status) + "\n")


main()
