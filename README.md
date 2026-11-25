# Bloom

Make every key yours. Keyboard customisation for macOS.

Bloom controls the white backlight of a Razer BlackWidow Lite and remaps its
keys 1:1. Remaps apply to the Razer only; other keyboards are not affected.
Everything is stored locally, and nothing is installed system-wide.

## Run

Bloom uses [uv](https://docs.astral.sh/uv/) and a project-local `.venv`.

```sh
uv sync
uv run bloom-gui              # the window
uv run bloom probe            # find the keyboard
uv run bloom brightness 70    # 0..100
uv run bloom map caps_lock escape
uv run bloom agent install    # re-apply remaps at login and after a replug
```

macOS asks for Input Monitoring permission the first time Bloom talks to the
keyboard. Give it to the terminal that runs Bloom.

The helper runs `bloom` from this folder's `.venv`. Before you move or delete
the folder, run `uv run bloom agent uninstall`.

## Test

```sh
uv run pytest
```
