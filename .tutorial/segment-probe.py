#!/usr/bin/env python3
"""Probe the Antec panel for undocumented digit values.

The documented protocol only knows digits 0-9 and 0xEE (blank). This script
puts one test byte in a single digit position, blanks everything else, and
steps through every value so you can watch what the panel does with each one.

Usage (the hidraw node is root-only unless the udev rule is installed):

    sudo ./segment-probe.py                # sweep 0x0A..0xFF in the CPU tens digit
    sudo ./segment-probe.py --value 0x7F   # show one value and leave it up
    sudo ./segment-probe.py --pos 4        # sweep the GPU ones digit instead
    sudo ./segment-probe.py --start 0x40 --end 0x5F --delay 1.0

Positions: 0=CPU tens  1=CPU ones  2=CPU tenths  3=GPU tens  4=GPU ones  5=GPU tenths

Press Ctrl-C to stop; the panel is blanked on exit.
"""

import argparse
import os
import sys
import time

VENDOR_ID = 0x2022
PRODUCT_ID = 0x0522
HEADER = [0x55, 0xAA]
COMMAND = [0x01, 0x01, 0x06]
BLANK = 0xEE


def find_hidraw():
    want = f":{VENDOR_ID:08X}:{PRODUCT_ID:08X}"
    for entry in sorted(os.listdir("/sys/class/hidraw")):
        try:
            with open(f"/sys/class/hidraw/{entry}/device/uevent") as fh:
                if want in fh.read().upper():
                    return f"/dev/{entry}"
        except OSError:
            continue
    return None


def packet(digits):
    body = HEADER + COMMAND + list(digits)
    return bytes([0x00] + body + [sum(body) & 0xFF])


def send(fd, digits):
    pkt = packet(digits)
    try:
        os.write(fd, pkt)
    except OSError:
        # Some firmware wants the full 64-byte report.
        os.write(fd, pkt.ljust(65, b"\x00"))


def auto_int(s):
    return int(s, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pos", type=int, default=0, choices=range(6), help="digit position to test (default 0, CPU tens)")
    ap.add_argument("--value", type=auto_int, help="send this one value and leave it on the panel")
    ap.add_argument("--start", type=auto_int, default=0x0A, help="first value of the sweep (default 0x0A)")
    ap.add_argument("--end", type=auto_int, default=0xFF, help="last value of the sweep (default 0xFF)")
    ap.add_argument("--delay", type=float, default=0.7, help="seconds each value stays up (default 0.7)")
    args = ap.parse_args()

    path = find_hidraw()
    if path is None:
        sys.exit("display not found: is it plugged into the internal USB header?")
    try:
        fd = os.open(path, os.O_WRONLY)
    except PermissionError:
        sys.exit(f"{path} is not writable: run with sudo, or install the udev rule")
    print(f"using {path}", flush=True)

    digits = [BLANK] * 6

    if args.value is not None:
        digits[args.pos] = args.value & 0xFF
        send(fd, digits)
        print(f"pos {args.pos} = 0x{args.value:02X}  (left on the panel)")
        return

    print("watch the panel; each line is the value currently shown. Ctrl-C to stop.")
    try:
        for v in range(args.start, args.end + 1):
            digits[args.pos] = v
            send(fd, digits)
            print(f"pos {args.pos} = 0x{v:02X} ({v})", flush=True)
            time.sleep(args.delay)
    except KeyboardInterrupt:
        pass
    finally:
        send(fd, [BLANK] * 6)
        print("panel blanked")


if __name__ == "__main__":
    main()
