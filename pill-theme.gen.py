#!/usr/bin/env python3
"""Generator for ~/.config/tmux/pill-theme.conf.

The rounded caps are Private Use Area codepoints U+E0B6 / U+E0B4. They are
invisible in most editors and are routinely stripped in transit, so every
non-ASCII glyph in this file is written as a \\uXXXX escape and never typed
or pasted literally. That applies to editing this file too: match on the
escape, never on the character. Regenerate with:

    python3 ~/.config/tmux/pill-theme.gen.py && tmux source-file ~/.config/tmux/tmux.conf

then confirm the cap counts printed at the end are both 7.
"""
import os, sys

L, R = chr(0xE0B6), chr(0xE0B4)   # rounded pill caps (Powerline Extra)
DIV  = chr(0x2503)                # heavy vertical divider (box-drawing)
BG,PILL,DIM,TXT,BRT = "#16181d","#232830","#6b7684","#8b96a5","#dce6f2"
ACC,ACC2,DEEP,DARK  = "#87d7ff","#3fa9e0","#0087d7","#005f87"
INK,WARN,BORD       = "#0f1319","#f0b072","#2c333f"

fill = f"#{{?window_bell_flag,{WARN},#{{?window_activity_flag,{ACC2},{PILL}}}}}"
ifg  = f"#{{?window_bell_flag,{INK},#{{?window_activity_flag,{INK},{DIM}}}}}"
nfg  = f"#{{?window_bell_flag,{INK},#{{?window_activity_flag,{INK},{TXT}}}}}"

snip = f'''# ═══════════════════════════════════════════════════════════
#  Rounded-pill status bar — true colour (24-bit)
#
#  bar bg      {BG}   base status background; pills float on it
#  pill        {PILL}   inactive pill fill
#  text dim    {DIM}   window index, secondary labels, session divider
#  text        {TXT}   inactive window name
#  text bright {BRT}   high-emphasis (clock)
#  accent      {ACC}   identity blue — active window fill, session name
#  accent mid  {ACC2}   activity highlight
#  accent deep {DEEP}   secondary blue
#  accent dark {DARK}   selection fill
#  ink         {INK}   text on light-blue fills
#  warn        {WARN}   prefix armed / bell
#  border      {BORD}   inactive pane border
#
#  Pill construction:  #[fg=FILL,bg=BAR]{L}#[fg=INK,bg=FILL] text #[fg=FILL,bg=BAR]{R}
#  The caps ({L} U+E0B6, {R} U+E0B4) are drawn as FOREGROUND in the pill
#  colour over the bar background — that is what rounds the ends.
#  Requires a Nerd Font / Powerline-Extra patched font.
#
#  Session vs window: the session is not a capsule at all — it is bare
#  {ACC} text, then a {DIM} heavy divider ({DIV} U+2503) separating it from
#  the window run. Windows are capsules; the session is a label. Note the
#  caps are SOLID half-discs, not outline strokes, so an "unfilled pill" is
#  not achievable — dropping the fill just leaves two blobs either side of
#  the text. Capsule vs no capsule is the only shape axis these glyphs give.
# ═══════════════════════════════════════════════════════════

# True colour — required, the palette degrades badly without it
set -as terminal-features ',*:RGB'

# ── Status bar ───────────────────────────────────────────
set -g status on
set -g status-interval 5
set -g status-justify left
set -g status-style "bg={BG},fg={TXT}"

# Left: session label — bare text, no capsule, then the group divider
set -g status-left-length 40
set -g status-left "#[fg={ACC},bg={BG},bold] #S  #[fg={DIM},bg={BG},nobold]{DIV}  "

# Right: prefix (amber, only when armed) · day+time pill · date pill
set -g status-right-length 90
set -g status-right "#{{?client_prefix,#[fg={WARN}#,bg={BG}]{L}#[fg={INK}#,bg={WARN}#,bold] PREFIX #[fg={WARN}#,bg={BG}]{R} ,}}#[fg={PILL},bg={BG}]{L}#[fg={DIM},bg={PILL}] %a #[fg={BRT},bg={PILL},bold]%H:%M #[fg={PILL},bg={BG}]{R} #[fg={ACC},bg={BG}]{L}#[fg={INK},bg={ACC},bold] %d %b #[fg={ACC},bg={BG}]{R}"

# Windows: one pill each, gap between them
set -g window-status-separator " "
set -g window-status-format         "#[fg={fill},bg={BG}]{L}#[fg={ifg},bg={fill}] #I #[fg={nfg},bg={fill}]#W #[fg={fill},bg={BG}]{R}"
set -g window-status-current-format "#[fg={ACC},bg={BG}]{L}#[fg={INK},bg={ACC},bold] #I #W #[fg={ACC},bg={BG}]{R}"

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

# ── Command / message line ───────────────────────────────
set -g message-style         "bg={ACC},fg={INK}"
set -g message-command-style "bg={DEEP},fg={BRT}"

# ── Clock (prefix + t) ───────────────────────────────────
set -g clock-mode-colour "{ACC}"
set -g clock-mode-style  24
'''

dest = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.config/tmux/pill-theme.conf")
os.makedirs(os.path.dirname(dest), exist_ok=True)
with open(dest, "w", encoding="utf-8") as f:
    f.write(snip)

# 7 pairs: 2 in the doc comment, 3 in status-right (prefix/clock/date), and
# 1 each in window-status-format / -current-format. The session label is bare
# text, so it contributes none. Bump this if you add or remove a capsule.
EXPECT = 7
nl, nr, nd = snip.count(L), snip.count(R), snip.count(DIV)
print(f"wrote {dest}")
print(f"  U+E0B6 left caps : {nl}  (expect {EXPECT})")
print(f"  U+E0B4 right caps: {nr}  (expect {EXPECT})")
print(f"  U+2503 dividers  : {nd}  (expect 2: one in the comment, one live)")
print("  OK" if nl == nr == EXPECT and nd == 2
      else "  BROKEN - glyphs stripped, regenerate")
