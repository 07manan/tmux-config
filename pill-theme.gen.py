#!/usr/bin/env python3
"""Generator for ~/.config/tmux/pill-theme.conf.

The rounded caps are Private Use Area codepoints U+E0B6 / U+E0B4. They are
invisible in most editors and are routinely stripped in transit, so every
non-ASCII glyph in this file is written as a \\uXXXX escape and never typed
or pasted literally. That applies to editing this file too: match on the
escape, never on the character. Regenerate with:

    python3 ~/.config/tmux/pill-theme.gen.py && tmux source-file ~/.config/tmux/tmux.conf

then confirm the glyph check printed at the end says OK.
"""
import os, sys

L, R = chr(0xE0B6), chr(0xE0B4)   # rounded pill caps (Powerline Extra)
DIV  = chr(0x2503)                # heavy vertical divider (box-drawing)
ICON = chr(0xF489)                # session icon (nf-oct-terminal)
ZOOM = chr(0xF065)                # zoomed-window flag (nf-fa-expand)
ELL  = chr(0x2026)                # name-truncation ellipsis
BAR  = "#1e2532"                  # status bar strip, a step above the terminal's bg
BG,PILL,DIM,TXT,BRT = "#151921","#202733","#727f92","#909bad","#e0e6f0"
ACC,ACC2,DEEP,DARK  = "#9ab5dd","#7794c7","#5f7fb3","#2e405e"
INK,WARN,BORD       = "#0f131b","#dcb27e","#2c3442"
# Inactive window pills are a greyer steel blue, a quarter of the way from
# the theme's blues to neutral grey, and a step lighter than the strip they
# sit on: fill, index block, index, name
WPILL,WIDX,WDIM,WTXT = "#2d333f","#39414f","#757f8d","#939ba9"

def alert(normal, bell=WARN, activity=ACC2):
    """A window's colour: bell beats activity beats the normal colour."""
    return f"#{{?window_bell_flag,{bell},#{{?window_activity_flag,{activity},{normal}}}}}"

def pill(fill, ink, text):
    return f"#[fg={fill},bg={BAR}]{L}#[fg={ink},bg={fill},bold]{text}#[fg={fill},bg={BAR},nobold]{R}"

def esc(s):
    """Commas inside a #{?cond,yes,no} branch have to be written #,"""
    return s.replace(",", "#,")

ibg, nbg = alert(WIDX), alert(WPILL)
ifg, nfg = alert(WDIM, INK, INK), alert(WTXT, INK, INK)
name = f"#{{=/20/{ELL}:window_name}}#{{?window_zoomed_flag, {ZOOM},}}"

# Window label, explained where automatic-rename-format uses it below
cmd   = "#{pane_current_command}"
label = (f"#{{?#{{m/r:^(zsh|bash|fish|sh)$,{cmd}}},#{{b:pane_current_path}},"
         f"#{{?#{{m/r:^[0-9]+([.][0-9]+)+$,{cmd}}},claude,{cmd}}}}}")

mode = (f"#{{?client_prefix,{esc(pill(WARN, INK, 'PREFIX'))} ,"
        f"#{{?#{{==:#{{pane_mode}},copy-mode}},{esc(pill(ACC2, INK, 'COPY'))} ,}}}}")

snip = f'''# ═══════════════════════════════════════════════════════════
#  Rounded-pill status bar — true colour (24-bit)
#
#  bar bg      {BAR}   a strip a step lighter than the terminal's own
#                       background (iTerm2 dark is #15191f), so the bar
#                       stands apart from the panes above it
#  canvas      {BG}   menu and popup background
#  pill        {PILL}   copy-mode position indicator
#  window pill {WPILL}   inactive window pill fill (greyer than PILL)
#  window idx  {WIDX}   inactive window index block
#  window dim  {WDIM}   inactive window index
#  window text {WTXT}   inactive window name
#  text dim    {DIM}   secondary labels, session divider
#  text        {TXT}   status and menu text
#  text bright {BRT}   selected text
#  accent      {ACC}   identity blue — active window, clock, session name
#  accent mid  {ACC2}   copy-mode pill, activity highlight
#  accent deep {DEEP}   search matches, pane numbers, menu border
#  accent dark {DARK}   active index block, date block, selection fill
#  ink         {INK}   text on light fills
#  warn        {WARN}   prefix armed / bell
#  border      {BORD}   pane and popup borders
#
#  Pill construction:  #[fg=FILL,bg=BAR]{L}#[fg=INK,bg=FILL] text #[fg=FILL,bg=BAR]{R}
#  The caps ({L} U+E0B6, {R} U+E0B4) are drawn as FOREGROUND in the pill
#  colour over the bar background — that is what rounds the ends.
#  Requires a Nerd Font / Powerline-Extra patched font.
#
#  Window pills and the clock are two-tone: a darker block (window index,
#  date) butts straight into the main fill with no glyph between them, so the
#  left cap takes the dark block's colour and the right cap the main fill's.
#
#  Session vs window: the session is not a capsule at all — it is bare
#  {ACC} text, then a {DIM} heavy divider ({DIV} U+2503) separating it from
#  the window run. Windows are capsules; the session is a label. Note the
#  caps are SOLID half-discs, not outline strokes, so an "unfilled pill" is
#  not achievable — dropping the fill just leaves two blobs either side of
#  the text. Capsule vs no capsule is the only shape axis these glyphs give.
# ═══════════════════════════════════════════════════════════

# True colour (RGB) is switched on in tmux.conf — the palette degrades badly
# without it.

# ── Status bar ───────────────────────────────────────────
set -g status on
set -g status-interval 5
set -g status-justify left
set -g status-style "bg={BAR},fg={TXT}"

# Left: session label — bare text, no capsule, then the group divider
set -g status-left-length 40
set -g status-left "#[fg={ACC},bg={BAR},bold] {ICON} #S  #[fg={DIM},nobold]{DIV}  "

# Right: mode pill (amber while the prefix is armed, blue in copy mode,
# otherwise nothing) · date+time capsule
set -g status-right-length 90
set -g status-right "{mode}#[fg={DARK},bg={BAR}]{L}#[fg={ACC},bg={DARK}]%a %d %b #[fg={INK},bg={ACC},bold] %H:%M#[fg={ACC},bg={BAR},nobold]{R} "

# Windows: one pill each, gap between them. Names are cut at 20 columns, and
# a zoomed window gets {ZOOM} after its name.
set -g window-status-separator " "
set -g window-status-format         "#[fg={ibg},bg={BAR}]{L}#[fg={ifg},bg={ibg}]#I #[fg={nfg},bg={nbg}] {name} #[fg={nbg},bg={BAR}]{R}"
set -g window-status-current-format "#[fg={DARK},bg={BAR}]{L}#[fg={ACC},bg={DARK},bold]#I #[fg={INK},bg={ACC}] {name} #[fg={ACC},bg={BAR},nobold]{R}"

# Window names (unless renamed by hand) say what the active pane is doing:
# the running program, or for an idle shell the directory it sits in.
# Claude Code's executable is named after its version (2.1.312), so a bare
# version number reads as "claude".
set -g automatic-rename-format "{label}"

# Activity / bell are folded into the pill fill above, so these style
# options are neutralised to stop them overriding the pill colours.
# Activity highlighting is OFF for now — background windows stay dark instead
# of turning {ACC2}. Flip this back to "on" to restore the blue; the ding will
# not come back with it, because activity-action below stays at none.
setw -g monitor-activity off
set  -g visual-activity off
# activity-action none = highlight only, no audible bell on activity. Despite
# the man page calling it "equivalent to monitor-activity being off", the
# window_activity_flag is still set, so the pill still turns blue — measured,
# not assumed. Leaving this at the default "other" makes tmux emit a BEL to
# the terminal every time a background window writes output.
# This does NOT touch real application bells; those follow bell-action.
set  -g activity-action none
set  -g window-status-activity-style default
set  -g window-status-bell-style     default

# ── Panes ────────────────────────────────────────────────
set -g pane-border-style         "fg={BORD}"
set -g pane-active-border-style  "fg={ACC}"
set -g display-panes-colour        "{DEEP}"
set -g display-panes-active-colour "{ACC}"

# ── Copy mode / selection / search ───────────────────────
set -g mode-style "bg={DARK},fg={BRT}"
set -g copy-mode-match-style         "bg={DEEP},fg={INK}"
set -g copy-mode-current-match-style "bg={ACC},fg={INK}"
set -g copy-mode-mark-style          "bg={ACC},fg={INK}"
set -g copy-mode-position-style      "bg={PILL},fg={ACC}"

# ── Menus (right-click, prefix + <) and popups ───────────
# Menus open straight over pane text on the same dark canvas, so their border
# is blue: in {BORD} the frame and the title on it all but vanish.
set -g menu-style          "bg={BG},fg={TXT}"
set -g menu-selected-style "bg={ACC},fg={INK},bold"
set -g menu-border-style   "fg={DEEP}"
set -g menu-border-lines   rounded
set -g popup-style         "bg={BG}"
set -g popup-border-style  "fg={BORD}"
set -g popup-border-lines  rounded

# ── Command / message line ───────────────────────────────
# Accent text straight on the bar, not a solid strip across it
set -g message-style         "bg={BAR},fg={ACC},bold"
set -g message-command-style "bg={BAR},fg={ACC2},bold"
set -g prompt-cursor-colour  "{ACC}"

# ── Clock (prefix + t) ───────────────────────────────────
set -g clock-mode-colour "{ACC}"
set -g clock-mode-style  24
'''

dest = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.config/tmux/pill-theme.conf")
os.makedirs(os.path.dirname(dest), exist_ok=True)
with open(dest, "w", encoding="utf-8") as f:
    f.write(snip)

# Expected glyph counts. Caps: 7 pairs — 2 in the doc comment, 3 in
# status-right (prefix, copy, clock), and 1 each in window-status-format /
# -current-format. The session label is bare text, so it contributes none.
# Zoom flag: 1 in a comment plus the name shared by both window formats.
# Update these when you add or remove a glyph.
checks = [("U+E0B6 left caps", L, 7), ("U+E0B4 right caps", R, 7),
          ("U+2503 dividers", DIV, 2), ("U+F489 session icon", ICON, 1),
          ("U+F065 zoom flag", ZOOM, 3)]
print(f"wrote {dest}")
ok = True
for what, glyph, want in checks:
    n = snip.count(glyph)
    ok &= n == want
    print(f"  {what:<20}: {n}  (expect {want})")
print("  OK" if ok else "  BROKEN - glyphs stripped, regenerate")
