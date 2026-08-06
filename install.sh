#!/usr/bin/env bash
# Install the Antec display service. Run with sudo.
set -euo pipefail

src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install -m 0755 "$src/antec-display.py"       /usr/local/bin/antec-display.py
install -m 0644 "$src/99-antec-display.rules" /etc/udev/rules.d/99-antec-display.rules
install -m 0644 "$src/antec-display.service"  /etc/systemd/system/antec-display.service

udevadm control --reload-rules
udevadm trigger --subsystem-match=hidraw

systemctl daemon-reload
systemctl enable --now antec-display.service

echo
systemctl --no-pager --full status antec-display.service || true
