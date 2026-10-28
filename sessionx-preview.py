#!/usr/bin/env python3
"""Session preview for tmux-sessionx that shows every pane.

The plugin's preview runs `tmux capture-pane -t <session>`, which captures
only the active pane, so a split window previews as one pane. This draws the
session's current window the way tmux lays it out instead: each pane's text
scaled into its share of the preview, box-drawing borders between panes, and
the borders around the active pane in the accent blue. Each pane shows the
rows that end at its cursor or last output, so prompts and recent output stay
in view when a pane is cut down to fit.

Wired in from tmux.conf through the fzf 'start:' bind in
@sessionx-additional-options, so the plugin stays unmodified. Anything that
isn't a running session (a zoxide directory, *Last*) goes to the plugin's own
preview.sh. Known gap: the back key (ctrl-b) switches the preview back to the
plugin's script for the rest of that popup, because sessionx binds it after
our options and fzf keeps the last bind.
"""
import os, re, subprocess, sys, unicodedata

PLUGIN_PREVIEW = os.path.expanduser(
    "~/.config/tmux/plugins/tmux-sessionx/scripts/preview.sh")
BORD = "\x1b[0;38;2;44;52;66m"     # #2c3442, pill-theme border
ACC  = "\x1b[0;38;2;154;181;221m"  # #9ab5dd, pill-theme accent
PLAIN = "\x1b[0m"

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


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if not name or subprocess.run(["tmux", "has-session", "-t", f"={name}"],
                                  capture_output=True).returncode:
        os.execv(PLUGIN_PREVIEW, [PLUGIN_PREVIEW, *sys.argv[1:]])

    W = int(os.environ.get("FZF_PREVIEW_COLUMNS", 80))
    H = int(os.environ.get("FZF_PREVIEW_LINES", 24))
    target = f"={name}:"
    ww, wh, zoomed = map(int, tmux("display", "-p", "-t", target,
        "#{window_width} #{window_height} #{window_zoomed_flag}").split())
    X = lambda x: round(x * W / ww)
    Y = lambda y: round(y * H / wh)

    # own[y][x]: index of the pane whose text fills the cell, or -1 for border
    own = [[None] * W for _ in range(H)]
    grid = [[(PLAIN, " ")] * W for _ in range(H)]
    active = None
    for i, pane in enumerate(tmux("list-panes", "-t", target, "-F",
            "#{pane_id} #{pane_left} #{pane_top} #{pane_width} #{pane_height} "
            "#{pane_active} #{cursor_y}").splitlines()):
        pid, *nums = pane.split()
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
        if cw <= 0 or ch <= 0:
            continue

        rows = parse(tmux("capture-pane", "-ep", "-t", pid).split("\n")[:ph])
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
    sys.stdout.write("\n".join(out) + "\n")


main()
