# Bloom

[![Latest release](https://img.shields.io/github/v/release/negimatare/bloom-macos?style=flat-square&label=release&color=e6a0cd)](https://github.com/negimatare/bloom-macos/releases/latest)
[![Licence](https://img.shields.io/github/license/negimatare/bloom-macos?style=flat-square&label=licence&color=c9a0dc)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/negimatare/bloom-macos/tests.yml?branch=main&style=flat-square&label=tests)](https://github.com/negimatare/bloom-macos/actions/workflows/tests.yml)
[![CodeQL](https://img.shields.io/github/actions/workflow/status/negimatare/bloom-macos/codeql.yml?branch=main&style=flat-square&label=CodeQL)](https://github.com/negimatare/bloom-macos/actions/workflows/codeql.yml)

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

## Install the app

```sh
uv run bloom app install      # adds "Bloom MacOS" to ~/Applications
```

Open Bloom MacOS from Launchpad or Spotlight, or drag it to the Dock. The app
starts the window from this folder's `.venv`, so you do not need a terminal.
To remove it, run `uv run bloom app uninstall`.

macOS asks for Input Monitoring permission the first time Bloom talks to the
keyboard. Give it to Bloom MacOS, or to the terminal that runs Bloom.

The app and the helper run Bloom from this folder's `.venv`. Before you move
or delete the folder, run `uv run bloom app uninstall` and
`uv run bloom agent uninstall`.

## Test

```sh
uv run pytest
```

## Contributing

`CONTRIBUTING.md` has the branches and the release steps. Report a
vulnerability as `SECURITY.md` says.

## Licence

[MIT](LICENSE)
