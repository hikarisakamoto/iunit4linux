# Antec temperature display on Linux

Replaces Antec's Windows-only **iUnity** software for the temperature panel on
Antec cases (Performance 1 FT, Flux Pro, and others using the same controller).

The panel is a plain USB HID device on an internal USB 2.0 header:

```
Bus 001 Device 002: ID 2022:0522 DINK_HID_DEVICE
```

No kernel module, no `pyusb`, no Wine. The service reads `hwmon` and writes one
HID output report per second.

## Install

```sh
sudo ./install.sh
```

That copies the script to `/usr/local/bin`, installs a udev rule and a systemd
unit, and starts the service. Check it with:

```sh
systemctl status antec-display
journalctl -u antec-display -f
```

## Build it yourself

The repo also contains a three-part tutorial that reimplements the daemon from
scratch, for anyone who would rather understand the device than install a script.
Open the HTML files in a browser:

| Page | What's in it |
|------|--------------|
| [`foundations.html`](foundations.html) | The hardware, the HID report descriptor decoded, the protocol, `hwmon`, permissions, and a debugging toolkit. Language-agnostic — read it first. |
| [`go.html`](go.html) | Nine steps to a systemd service in Go. Assumes you already know some Go. |
| [`rust.html`](rust.html) | The same nine steps in Rust, written for someone who has never used it. |

Both language tutorials give you the goal, the APIs worth reaching for, and the
gotchas at each step, with reference implementations tucked behind collapsed
blocks so you can write the code yourself. Every reference implementation
compiles and its tests pass — Go 1.26.5 and rustc 1.97.1, the Rust one clean
under `cargo clippy` in both debug and release profiles.

## Protocol

The device exposes a vendor-defined HID interface (usage page `0xFFA0`) with a
64-byte interrupt OUT endpoint at `0x02` and **no report IDs**, so a write to
`/dev/hidrawN` must be prefixed with a `0x00` byte that the kernel strips.

The payload is 12 bytes:

| Byte  | Meaning                                          |
|-------|--------------------------------------------------|
| 0–1   | Header, always `0x55 0xAA`                       |
| 2–4   | Command, always `0x01 0x01 0x06`                 |
| 5–7   | CPU temperature: tens, ones, tenths (`0x00`–`0x09`) |
| 8–10  | GPU temperature: tens, ones, tenths              |
| 11    | Checksum: `sum(bytes 0..10) & 0xFF`              |

Digits are raw values, not ASCII: 44.3 °C is `0x04 0x04 0x03`. Sending
`0xEE 0xEE 0xEE` for a digit triple blanks that half of the panel to `--.-`.

The packet always carries both temperatures; the physical button on the top I/O
selects which one is shown.

Credit for the protocol goes to the Antec Flux Pro reverse-engineering work by
[nishtahir](https://github.com/nishtahir/antec-flux-pro-display) and
[systemdbrew](https://github.com/systemdbrew/antec-flux-display).

## Sensor selection

Auto-detected: `k10temp`/`coretemp` for the CPU, `amdgpu`/`nvidia` for the GPU.
When two `amdgpu` devices exist (discrete card plus an integrated one on Ryzen
desktop CPUs), the one exposing the most sensors is picked as the discrete card.

Override either sensor with an environment variable, e.g. in a systemd drop-in:

```sh
ANTEC_CPU_SENSOR=/sys/class/hwmon/hwmon4/temp1_input
ANTEC_GPU_SENSOR=/sys/class/hwmon/hwmon2/temp2_input
ANTEC_INTERVAL=1.0
```

`hwmon` numbering is not stable across reboots — the display itself is found by
USB ID rather than by `/dev/hidraw` number, but hardcoded sensor paths are not.

## Uninstall

```sh
sudo systemctl disable --now antec-display
sudo rm /usr/local/bin/antec-display.py \
        /etc/systemd/system/antec-display.service \
        /etc/udev/rules.d/99-antec-display.rules
sudo systemctl daemon-reload && sudo udevadm control --reload-rules
```
