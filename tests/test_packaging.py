from importlib.metadata import entry_points


def test_the_bloom_commands_are_installed_and_load():
    scripts = entry_points(group="console_scripts")
    # `bloom agent install` starts the helper through the script named "bloom".
    assert callable(scripts["bloom"].load())
    assert callable(scripts["bloom-gui"].load())
