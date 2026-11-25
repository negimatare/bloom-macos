"""Command-line interface: `bloom <command>`."""

from __future__ import annotations

import argparse
import sys

from . import config, device, hid_usages, keymap, lighting, watcher
from .apply import apply_profile
from .lighting import LightEffect
from .protocol import Status


def cmd_probe(_: argparse.Namespace) -> int:
    interfaces = device.list_interfaces()
    if not interfaces:
        print("Razer BlackWidow Lite (1532:0235) not found.")
        return 1
    print(f"Found {interfaces[0].product or 'keyboard'}: {len(interfaces)} HID collection(s)")
    permission = device.input_monitoring_status()
    print(f"Input Monitoring permission: {permission}\n")
    if permission == "denied":
        print(
            "macOS is blocking access. Enable your terminal under System Settings ->\n"
            "Privacy & Security -> Input Monitoring, then restart the terminal.\n"
        )
    for info in interfaces:
        print(info.describe())
        response, error = device.probe_interface(info)
        if error:
            print(f"    -> {error}")
        else:
            try:
                status = Status(response.status).name
            except ValueError:
                status = f"0x{response.status:02X}"
            line = f"    -> status {status}"
            if response.status == Status.SUCCESS:
                value = response.arguments[2]
                line += f", brightness {value}/255 ({round(value / 2.55)}%)"
            print(line)
    return 0


def cmd_brightness(args: argparse.Namespace) -> int:
    with device.Keyboard() as kb:
        if args.percent is not None:
            lighting.set_brightness(kb, args.percent)
            cfg = config.load()
            cfg.active.lighting.brightness = args.percent
            config.save(cfg)
        print(f"Brightness: {lighting.get_brightness(kb)}%")
    return 0


def cmd_effect(args: argparse.Namespace) -> int:
    with device.Keyboard() as kb:
        lighting.set_effect(kb, LightEffect(args.effect))
    cfg = config.load()
    cfg.active.lighting.effect = args.effect
    config.save(cfg)
    print(f"Effect: {args.effect}")
    return 0


def cmd_experiment(args: argparse.Namespace) -> int:
    """Send an effect OpenRazer doesn't list for this model and report the
    raw status, without treating a refusal as an error."""
    request = lighting.EXPERIMENTAL[args.effect](speed=args.speed)
    with device.Keyboard() as kb:
        response = kb.transact(request)
    try:
        status = Status(response.status).name
    except ValueError:
        status = f"unknown 0x{response.status:02X}"
    print(f"{args.effect}: keyboard answered {status}")
    if response.status == Status.SUCCESS:
        print("Accepted. Check whether the lighting actually changed, then restore with `bloom effect static`.")
    return 0


def _print_mappings(mappings: list[keymap.Mapping]) -> None:
    if not mappings:
        print("No key mappings on this keyboard.")
        return
    for src, dst in mappings:
        print(f"{hid_usages.label(src):>28}  ->  {hid_usages.label(dst)}")


def cmd_keys(_: argparse.Namespace) -> int:
    cfg = config.load()
    saved = keymap.normalise(cfg.active.mappings)
    active = keymap.current()
    print(f"Profile '{cfg.active_profile}':")
    _print_mappings(saved)
    if device.list_interfaces() and sorted(active) != sorted(saved):
        print("\nNote: macOS currently has different mappings active. Run `bloom apply`.")
    return 0


def _save_mappings(mappings: list[keymap.Mapping]) -> None:
    mappings = keymap.normalise(mappings)  # validate before saving
    cfg = config.load()
    cfg.active.mappings = mappings
    config.save(cfg)
    if device.list_interfaces():
        keymap.apply(mappings)
    else:
        print("Keyboard not connected; saved, will apply when it connects.")
    _print_mappings(mappings)


def cmd_map(args: argparse.Namespace) -> int:
    src, dst = hid_usages.normalise(args.src), hid_usages.normalise(args.dst)
    mappings = [m for m in config.load().active.mappings if m[0] != src]
    _save_mappings(mappings + [(src, dst)])
    return 0


def cmd_unmap(args: argparse.Namespace) -> int:
    mappings = []
    if args.src:
        src = hid_usages.normalise(args.src)
        mappings = [m for m in config.load().active.mappings if m[0] != src]
    _save_mappings(mappings)
    return 0


def cmd_apply(_: argparse.Namespace) -> int:
    cfg = config.load()
    apply_profile(cfg.active)
    print(f"Applied profile '{cfg.active_profile}'.")
    return 0


def cmd_watch(_: argparse.Namespace) -> int:
    watcher.watch()
    return 0


def cmd_agent(args: argparse.Namespace) -> int:
    if args.action == "install":
        path = watcher.agent_install()
        print(f"Background helper installed and started ({path}).")
        print(f"Log: {watcher.LOG_PATH}")
    elif args.action == "uninstall":
        removed = watcher.agent_uninstall()
        print("Background helper stopped and removed." if removed else "Not installed.")
    else:
        print(f"Background helper: {watcher.agent_status()}")
    return 0


def cmd_gui(_: argparse.Namespace) -> int:
    from .gui.app import main as gui_main

    return gui_main()


def cmd_keynames(_: argparse.Namespace) -> int:
    for name in hid_usages.names():
        print(f"{name:<18} {hid_usages.label(name)}")
    return 0


def _percent(value: str) -> int:
    n = int(value)
    if not 0 <= n <= 100:
        raise argparse.ArgumentTypeError("must be 0..100")
    return n


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bloom", description="Bloom: backlight and key mapping for the Razer BlackWidow Lite")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("probe", help="list HID interfaces and test which one accepts commands")

    p = sub.add_parser("brightness", help="show or set backlight brightness")
    p.add_argument("percent", nargs="?", type=_percent, help="0..100")

    p = sub.add_parser("effect", help="set backlight effect")
    p.add_argument("effect", choices=[e.value for e in LightEffect])

    p = sub.add_parser("experiment", help="try an effect not officially supported on this model")
    p.add_argument("effect", choices=sorted(lighting.EXPERIMENTAL))
    p.add_argument("--speed", type=int, default=2, help="1 (fast) .. 3/4 (slow)")

    sub.add_parser("keys", help="show key mappings on this keyboard")
    p = sub.add_parser("map", help="remap a key, e.g. `bloom map caps_lock escape`")
    p.add_argument("src")
    p.add_argument("dst")
    p = sub.add_parser("unmap", help="remove one mapping, or all if no key given")
    p.add_argument("src", nargs="?")
    sub.add_parser("keynames", help="list key names usable with `map`")

    sub.add_parser("gui", help="open the Bloom window")
    sub.add_parser("apply", help="apply the active profile (lighting and mappings)")
    sub.add_parser("watch", help="run the background helper in the foreground")
    p = sub.add_parser("agent", help="manage the background helper started at login")
    p.add_argument("action", choices=["install", "uninstall", "status"])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {
        "probe": cmd_probe,
        "brightness": cmd_brightness,
        "effect": cmd_effect,
        "experiment": cmd_experiment,
        "keys": cmd_keys,
        "map": cmd_map,
        "unmap": cmd_unmap,
        "keynames": cmd_keynames,
        "apply": cmd_apply,
        "gui": cmd_gui,
        "watch": cmd_watch,
        "agent": cmd_agent,
    }
    try:
        return handlers[args.command](args)
    except (device.DeviceError, keymap.KeymapError, KeyError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
