# Security policy

## Supported versions

Only the latest release of Bloom gets fixes. To update a checkout, pull the
latest tag, run `uv sync`, then `uv run bloom app install` and
`uv run bloom agent install` again.

## Scope

Bloom runs on your Mac with your permissions. It opens the Razer keyboard
over HID, changes key mappings with `hidutil`, and installs a LaunchAgent and
two small app bundles in your home folder. It makes no network request.
Report a problem that lets Bloom do one of these actions:

- Run a command that you did not approve.
- Run code from an imported profile file.
- Change the keys of a keyboard other than the Razer BlackWidow Lite.
- Write outside its own files: `~/Library/Application Support/Bloom`,
  `~/Library/Logs/Bloom`, `~/Library/LaunchAgents/com.bloom.watch.plist` and
  `~/Applications/Bloom MacOS.app`.
- Send data to a location outside your Mac.

## Report a vulnerability

Do not open a public issue. Use
[private vulnerability reporting](https://github.com/negimatare/bloom-macos/security/advisories/new).
This link opens the report form.

Include these items:

- The Bloom release or commit.
- Your macOS version.
- The steps that show the problem.
