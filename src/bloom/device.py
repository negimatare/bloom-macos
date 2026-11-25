"""Finding the BlackWidow Lite and exchanging control reports over HID."""

from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass

import hid

from . import protocol
from .protocol import REPORT_LEN, Report, Status

VENDOR_ID = 0x1532
PRODUCT_ID = 0x0235


def _use_shared_open() -> None:
    """hidapi on macOS seizes devices by default, which fails for a keyboard
    macOS is already using. The Python binding doesn't expose the switch, but
    the bundled hidapi exports it, so call it directly."""
    try:
        ctypes.CDLL(hid.__file__).hid_darwin_set_open_exclusive(0)
    except (OSError, AttributeError):
        pass


_use_shared_open()

_IOKIT = "/System/Library/Frameworks/IOKit.framework/IOKit"
_LISTEN_EVENT = 1  # kIOHIDRequestTypeListenEvent (Input Monitoring)


def input_monitoring_status() -> str:
    """'granted', 'denied' or 'unknown' for the current app (terminal)."""
    try:
        status = ctypes.CDLL(_IOKIT).IOHIDCheckAccess(_LISTEN_EVENT)
    except (OSError, AttributeError):
        return "unknown"
    return {0: "granted", 1: "denied"}.get(status, "unknown")

# Delay between sending a request and reading the response, and between retries.
RESPONSE_DELAY_S = 0.005
RETRIES = 5


class DeviceError(Exception):
    pass


class KeyboardNotFound(DeviceError):
    pass


class CommandFailed(DeviceError):
    def __init__(self, status: int):
        self.status = status
        try:
            name = Status(status).name
        except ValueError:
            name = f"unknown 0x{status:02X}"
        super().__init__(f"keyboard answered {name} (0x{status:02X})")


@dataclass(frozen=True)
class InterfaceInfo:
    path: bytes
    interface_number: int
    usage_page: int
    usage: int
    product: str

    def describe(self) -> str:
        return (
            f"interface {self.interface_number}  "
            f"usage_page 0x{self.usage_page:04X}  usage 0x{self.usage:04X}  "
            f"path {self.path.decode(errors='replace')}"
        )


def list_interfaces() -> list[InterfaceInfo]:
    """Every HID collection the keyboard exposes."""
    return [
        InterfaceInfo(
            path=d["path"],
            interface_number=d.get("interface_number", -1),
            usage_page=d.get("usage_page", 0),
            usage=d.get("usage", 0),
            product=d.get("product_string") or "",
        )
        for d in hid.enumerate(VENDOR_ID, PRODUCT_ID)
    ]


def _read_response(dev: hid.device) -> bytes:
    data = bytes(dev.get_feature_report(0, REPORT_LEN + 1))
    # hidapi returns the report id as the first byte for unnumbered reports.
    if len(data) == REPORT_LEN + 1:
        data = data[1:]
    if len(data) != REPORT_LEN:
        raise DeviceError(f"short response: {len(data)} bytes")
    return data


def transact(dev: hid.device, request: Report) -> Report:
    """Send a request and return the keyboard's matching response."""
    payload = b"\x00" + request.to_bytes()  # report id 0
    if dev.send_feature_report(payload) < 0:
        raise DeviceError(f"send failed: {dev.error()}")

    response: Report | None = None
    for _ in range(RETRIES):
        time.sleep(RESPONSE_DELAY_S)
        response = Report.from_bytes(_read_response(dev))
        if response.status != Status.BUSY:
            break
    assert response is not None
    return response


class Keyboard:
    """An open control channel to the BlackWidow Lite."""

    def __init__(self, path: bytes | None = None):
        self._path = path or find_control_interface().path
        self._dev = hid.device()
        try:
            self._dev.open_path(self._path)
        except OSError as exc:
            raise DeviceError(
                f"cannot open keyboard ({exc}). If macOS asked for Input "
                "Monitoring permission, grant it to your terminal and retry."
            ) from exc

    def close(self) -> None:
        self._dev.close()

    def __enter__(self) -> Keyboard:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def transact(self, request: Report) -> Report:
        """Send a request and return the raw response, whatever its status."""
        return transact(self._dev, request)

    def send(self, request: Report) -> Report:
        """Send a request; raise CommandFailed unless the keyboard succeeds."""
        response = transact(self._dev, request)
        if response.status != Status.SUCCESS:
            raise CommandFailed(response.status)
        return response


def probe_interface(info: InterfaceInfo) -> tuple[Report | None, str]:
    """Try the read-only 'get brightness' command on one interface."""
    dev = hid.device()
    try:
        dev.open_path(info.path)
    except OSError as exc:
        return None, f"open failed: {exc}"
    try:
        request = protocol.get_brightness()
        response = transact(dev, request)
        if not response.matches(request):
            return response, "response is for a different command"
        return response, ""
    except (OSError, ValueError, DeviceError) as exc:
        return None, str(exc)
    finally:
        dev.close()


def find_control_interface() -> InterfaceInfo:
    """The interface that answers control reports successfully."""
    interfaces = list_interfaces()
    if not interfaces:
        raise KeyboardNotFound("Razer BlackWidow Lite (1532:0235) not connected")
    # OpenRazer's report index 0x01 hints at interface 1; try it first.
    ordered = sorted(interfaces, key=lambda i: (i.interface_number != 1, i.interface_number))
    for info in ordered:
        response, _ = probe_interface(info)
        if response is not None and response.status == Status.SUCCESS:
            return info
    raise DeviceError("no keyboard interface accepted control reports")
