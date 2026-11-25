# Changelog

Each release of Bloom. To update a checkout, pull the release tag, run
`uv sync`, then `uv run bloom app install` and `uv run bloom agent install`
again.

## 0.1.0 — unreleased

The first release. The keyboard app gets its own name, Bloom, and new
Lighting, Keymap and Profiles screens.

### Update

- **From the old `bw` commands.** Run `uv run bw agent uninstall` before the
  update. After it, move `~/Library/Application Support/BlackWidowControl` to
  `~/Library/Application Support/Bloom`, delete
  `~/Library/Logs/BlackWidowControl`, and run `uv run bloom agent install`.

### Bloom

- **Lighting Studio.** A backlight switch, a live brightness slider, the
  Night, Soft, Normal and Maximum presets, and a Static or Breathing effect,
  with a preview of the real keyboard.
- **Keymap Studio.** Click a key, then press the key that it should become.
  When one other key already gives that function, the two keys swap, so no
  function is lost. The toast offers "Undo" and "Keep both".
- **Profile Studio.** Profiles with an icon, edit, duplicate, "Restore to
  default", delete with "Undo", and JSON export and import.
- **An app in Launchpad.** `bloom app install` adds Bloom MacOS to
  `~/Applications`, so the window opens without a terminal.
- **The background helper.** It re-applies the remaps at login and after a
  replug, and Login Items show it as Bloom MacOS.
