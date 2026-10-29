# tmux config

tmux 3.1 and later read `~/.config/tmux/tmux.conf` directly, so this folder needs no symlinks.
TPM sees the config here and installs plugins into `plugins/`, which git ignores.

## New machine

```sh
brew install tmux fzf zoxide lsd
brew install --cask font-jetbrains-mono-nerd-font
git clone <remote> ~/.config/tmux
git clone https://github.com/tmux-plugins/tpm ~/.config/tmux/plugins/tpm
grep -q 'zoxide init' ~/.zshrc || echo 'eval "$(zoxide init zsh)"' >> ~/.zshrc
tmux -V; fzf --version   # check the minimums below
tmux
```

Homebrew can't pin versions, so check the minimums after installing:

- tmux 3.1 or later. Older versions don't read this folder.
- fzf 0.59 or later. The sessionx popup uses `--input-border`, `--list-border` and the `ghost` colour.
- python3 from the Xcode Command Line Tools is enough. The scripts use only the standard library.

Inside tmux, press `prefix + I` to install the plugins listed in `tmux.conf`.

Delete any old `~/.tmux.conf` first, because tmux checks that path before this one.
If a tmux server from an old `~/.tmux` setup is still running, restart it with `tmux kill-server`.
A running server keeps `TMUX_PLUGIN_MANAGER_PATH` pointed at the old folder, and TPM won't find the plugins until that variable is gone.

## Manual setup

These steps can't be done with the commands above. Do them by hand, or ask Claude Code to do them from this section.

**iTerm2**

- Settings → Profiles → Text → Font: pick the Nerd Font installed above (JetBrainsMono Nerd Font). Without it, the status bar's pill glyphs show as boxes.
- Settings → Profiles → Keys → General → Left Option key: set it to Esc+. Without it, Option+A types a character instead of opening sessionx, and Option+Q and Option+W don't switch windows.
- Settings → General → Selection: turn on "Applications in terminal may access clipboard". Without it, `y` in copy mode won't reach the macOS clipboard.

**Claude Code hook**

This hook lets tmux-resurrect reopen each Claude pane on the conversation it last showed.
Merge this into `hooks` in `~/.claude/settings.json`, keeping any hooks already there:

```json
"SessionStart": [
  {
    "hooks": [
      { "type": "command", "command": "~/.config/tmux/claude-pane-session.sh" }
    ]
  }
]
```

## Editing the theme

`pill-theme.conf` is generated.
Edit `pill-theme.gen.py`, then run the command in its docstring to regenerate and reload.
