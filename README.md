# tmux config

tmux 3.1 and later read `~/.config/tmux/tmux.conf` directly, so this folder needs no symlinks.
TPM sees the config here and installs plugins into `plugins/`, which git ignores.

## New machine

```sh
brew install tmux fzf zoxide lsd
git clone <remote> ~/.config/tmux
git clone https://github.com/tmux-plugins/tpm ~/.config/tmux/plugins/tpm
tmux
```

Inside tmux, press `prefix + I` to install the plugins listed in `tmux.conf`.

Delete any old `~/.tmux.conf` first, because tmux checks that path before this one.
If a tmux server from an old `~/.tmux` setup is still running, restart it with `tmux kill-server`.
A running server keeps `TMUX_PLUGIN_MANAGER_PATH` pointed at the old folder, and TPM won't find the plugins until that variable is gone.

## Editing the theme

`pill-theme.conf` is generated.
Edit `pill-theme.gen.py`, then run the command in its docstring to regenerate and reload.
