#!/usr/bin/env python3
"""Drive the Antec case temperature display (DINK 2022:0522) from Linux hwmon.

Writes a 12-byte vendor HID output report to the panel once a second:

    byte  0..1   header      0x55 0xAA
    byte  2..4   command     0x01 0x01 0x06
    byte  5..7   CPU temp    tens, ones, tenths (each 0x00-0x09)
    byte  8..10  GPU temp    tens, ones, tenths
    byte  11     checksum    sum(bytes 0..10) & 0xFF

A digit triple of 0xEE 0xEE 0xEE blanks that half of the panel to "--.-".
"""

import errno
import os
import re
import signal
import sys
import time

VENDOR_ID = 0x2022
PRODUCT_ID = 0x0522

HEADER = (0x55, 0xAA)
COMMAND = (0x01, 0x01, 0x06)
BLANK = (0xEE, 0xEE, 0xEE)

HWMON_ROOT = "/sys/class/hwmon"
INTERVAL = float(os.environ.get("ANTEC_INTERVAL", "1.0"))

# Override sensor choice with e.g. ANTEC_CPU_SENSOR=/sys/class/hwmon/hwmon4/temp1_input
CPU_SENSOR_ENV = os.environ.get("ANTEC_CPU_SENSOR")
GPU_SENSOR_ENV = os.environ.get("ANTEC_GPU_SENSOR")


def hwmon_name(path):
    try:
        with open(os.path.join(path, "name")) as fh:
            return fh.read().strip()
    except OSError:
        return ""


def label_of(temp_input):
    try:
        with open(temp_input.replace("_input", "_label")) as fh:
            return fh.read().strip()
    except OSError:
        return ""


def find_sensor(driver, prefer_labels=(), require_discrete=False):
    """Return a temp*_input path for the given hwmon driver name."""
    candidates = []
    for entry in sorted(os.listdir(HWMON_ROOT)):
        path = os.path.join(HWMON_ROOT, entry)
        if hwmon_name(path) != driver:
            continue
        inputs = sorted(
            os.path.join(path, f)
            for f in os.listdir(path)
            if re.fullmatch(r"temp\d+_input", f)
        )
        if inputs:
            candidates.append((path, inputs))

    if not candidates:
        return None

    if require_discrete and len(candidates) > 1:
        # An integrated GPU exposes only "edge"; a discrete card also reports
        # junction and memory. Prefer the one with the most sensors.
        candidates.sort(key=lambda c: len(c[1]), reverse=True)

    _, inputs = candidates[0]
    for wanted in prefer_labels:
        for path in inputs:
            if label_of(path).lower() == wanted.lower():
                return path
    return inputs[0]


def read_temp(path):
    with open(path) as fh:
        return int(fh.read().strip()) / 1000.0


def digits(celsius):
    """Split a temperature into the three BCD-ish digits the panel expects."""
    if celsius is None:
        return BLANK
    value = int(round(celsius * 10))
    value = max(0, min(999, value))
    return (value // 100, (value // 10) % 10, value % 10)


def build_packet(cpu_c, gpu_c):
    body = list(HEADER) + list(COMMAND) + list(digits(cpu_c)) + list(digits(gpu_c))
    return bytes(body + [sum(body) & 0xFF])


def find_hidraw():
    """Locate the /dev/hidrawN node for the display, by ID not by number."""
    # HID_ID is "bus:VVVVVVVV:PPPPPPPP" with zero-padded 8-digit hex IDs.
    want = f":{VENDOR_ID:08X}:{PRODUCT_ID:08X}"
    for entry in sorted(os.listdir("/sys/class/hidraw")):
        uevent = f"/sys/class/hidraw/{entry}/device/uevent"
        try:
            with open(uevent) as fh:
                if want in fh.read().upper():
                    return f"/dev/{entry}"
        except OSError:
            continue
    return None


class Display:
    """Keeps the hidraw node open, reopening it if the device is replugged."""

    REPORT_SIZE = 64

    def __init__(self):
        self.fd = None
        self.path = None
        self.pad = False

    def open(self):
        path = find_hidraw()
        if path is None:
            return False
        self.fd = os.open(path, os.O_WRONLY)
        self.path = path
        return True

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
        self.fd = None
        self.path = None

    def send(self, packet):
        # hidraw expects a leading report-ID byte; this descriptor declares no
        # report IDs, so it must be 0x00 and the kernel strips it.
        if self.pad:
            packet = packet.ljust(self.REPORT_SIZE, b"\x00")
        try:
            os.write(self.fd, b"\x00" + packet)
        except OSError as exc:
            # Some firmware revisions reject anything shorter than the declared
            # 64-byte report. Pad and stay padded for the rest of the run.
            if self.pad or exc.errno not in (errno.EINVAL, errno.EMSGSIZE):
                raise
            self.pad = True
            os.write(self.fd, b"\x00" + packet.ljust(self.REPORT_SIZE, b"\x00"))


def main():
    cpu_sensor = CPU_SENSOR_ENV or find_sensor("k10temp", ("Tctl",)) or find_sensor(
        "coretemp", ("Package id 0",)
    )
    gpu_sensor = GPU_SENSOR_ENV or find_sensor(
        "amdgpu", ("edge",), require_discrete=True
    ) or find_sensor("nvidia")

    if cpu_sensor is None and gpu_sensor is None:
        sys.exit("no CPU or GPU temperature sensor found under /sys/class/hwmon")

    print(f"cpu sensor: {cpu_sensor or 'none'}", flush=True)
    print(f"gpu sensor: {gpu_sensor or 'none'}", flush=True)

    display = Display()
    running = True

    def stop(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    while running:
        if display.fd is None:
            if not display.open():
                time.sleep(2.0)
                continue
            print(f"opened {display.path}", flush=True)

        try:
            cpu = read_temp(cpu_sensor) if cpu_sensor else None
            gpu = read_temp(gpu_sensor) if gpu_sensor else None
            display.send(build_packet(cpu, gpu))
        except OSError as exc:
            print(f"write failed ({exc}); reopening", flush=True)
            display.close()
            time.sleep(2.0)
            continue

        time.sleep(INTERVAL)

    # Blank the panel on the way out so it does not freeze on a stale reading.
    if display.fd is not None:
        try:
            display.send(build_packet(None, None))
        except OSError:
            pass
        display.close()


if __name__ == "__main__":
    main()
