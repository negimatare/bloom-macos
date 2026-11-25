import os
import plistlib

from bloom import APP_NAME, BUNDLE_ID, watcher


def test_helper_bundle_carries_the_app_name_icon_and_starts_the_watcher(tmp_path):
    bundle = tmp_path / f"{APP_NAME}.app"
    executable = watcher.write_helper_bundle(bundle, "/my venv/bin/bloom")

    info = plistlib.loads((bundle / "Contents" / "Info.plist").read_bytes())
    assert info["CFBundleName"] == APP_NAME
    assert executable.name == info["CFBundleExecutable"] == APP_NAME
    assert info["CFBundleIdentifier"] != BUNDLE_ID  # the launcher app owns that ID
    assert (bundle / "Contents" / "Resources" / f"{info['CFBundleIconFile']}.icns").exists()
    assert os.access(executable, os.X_OK)
    assert "exec '/my venv/bin/bloom' watch" in executable.read_text()
