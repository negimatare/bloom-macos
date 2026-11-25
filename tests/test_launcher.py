import os
import plistlib

from bloom import APP_NAME, BUNDLE_ID, launcher


def test_the_launcher_is_a_dock_app_that_opens_the_window(tmp_path):
    bundle = tmp_path / f"{APP_NAME}.app"
    executable = launcher.write_launcher_bundle(bundle, "/my venv/bin/bloom-gui")

    info = plistlib.loads((bundle / "Contents" / "Info.plist").read_bytes())
    assert info["CFBundleName"] == APP_NAME
    assert info["CFBundleIdentifier"] == BUNDLE_ID
    assert "LSBackgroundOnly" not in info
    assert info["NSHighResolutionCapable"] is True
    assert (bundle / "Contents" / "Resources" / f"{info['CFBundleIconFile']}.icns").exists()
    assert os.access(executable, os.X_OK)
    assert "exec '/my venv/bin/bloom-gui'" in executable.read_text()
