#!/usr/bin/env bash
# Dynamic border label for tmux-sessionx.
#
# The plugin builds `--border-label "Current session: \"$CURRENT\""` from a
# CURRENT it captures at config-load time (sessionx.tmux:5, used at :138) and
# freezes the whole arg list into a tmux option (:174). So the label is stuck
# on whichever session you happened to be in when tmux.conf was last sourced.
#
# fzf's transform-border-label action runs at popup time, after those static
# args are applied, so this recomputes the real answer and wins.
printf ' Current session: "%s" ' "$(tmux display-message -p '#S')"
