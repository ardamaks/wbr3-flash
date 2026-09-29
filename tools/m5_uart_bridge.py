#!/usr/bin/env python3
"""
m5_uart_bridge.py — use the M5 Cardputer (ESP32-Bit-Pirate) as a USB-UART
adapter for a Tuya WBR3 (RTL8720CF). Copied from wrg1-swd-flash.

Cardputer firmware facts (verified on a WRG1):
  - UART bridge uses GPIO1 = RX, GPIO2 = TX.
  - `mode uart` then `bridge` relays USB-CDC <-> those GPIOs transparently.
  - The bridge baud is whatever the host sets on /dev/ttyACM0 (USB line coding).

Wiring (WBR3 -> Cardputer):  TX2 -> GPIO1, RX2 -> GPIO2, GND -> GND (mandatory).

Usage:
  m5_uart_bridge.py [--baud 115200]            # log boot output to file
  m5_uart_bridge.py --enter-only               # start bridge, release port for ltchiptool
"""

import argparse
import sys
import time
from datetime import datetime

class LauncherDrive:
    def __init__(self, port, baud, verbose=False):
        import serial
        self.ser = serial.Serial(port, baud, timeout=0.2)
        self.verbose = verbose

    def _rx_until(self, needle: str, window: float) -> str:
        buf = b""
        deadline = time.monotonic() + window
        while time.monotonic() < deadline:
            chunk = self.ser.read(512)
            if chunk:
                buf += chunk
                if needle.lower() in buf.decode("utf-8", "replace").lower():
                    return buf.decode("utf-8", "replace")
            else:
                time.sleep(0.05)
        return buf.decode("utf-8", "replace")

    def cmd(self, text: str, expect: str, window: float = 8.0) -> str:
        self.ser.reset_input_buffer()
        self.ser.write(text.encode() + b"\r\n")
        got = self._rx_until(expect, window)
        if expect.lower() not in got.lower():
            raise RuntimeError(
                f"after {text!r} expected {expect!r}, got {got[-160:]!r}")
        if self.verbose:
            print(f"ok: {text!r} -> {expect!r}")
        return got

    def enter_uart_bridge(self):
        # wake the launcher prompt, switch to UART mode, start the bridge
        self.ser.reset_input_buffer()
        self.ser.write(b"\r\n")
        time.sleep(0.4)
        self.ser.reset_input_buffer()
        self.cmd("mode uart", "Mode changed to UART")
        self.cmd("bridge", "Uart Bridge: In progress", window=6.0)
        print("bridge active — streaming (Ctrl-C to stop)")

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--out", default="wbr3_uart", help="log file prefix")
    ap.add_argument("--timeout", type=int, default=0,
                    help="stop after N seconds (0 = run until Ctrl-C)")
    ap.add_argument("--raw-only", action="store_true", help="write raw bytes only")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--enter-only", action="store_true",
                    help="start the bridge, then close the port so ltchiptool can use it")
    args = ap.parse_args()

    dev = LauncherDrive(args.port, args.baud, verbose=args.verbose)
    try:
        dev.enter_uart_bridge()
    except RuntimeError as e:
        print(f"LAUNCHER-FAIL: {e}", file=sys.stderr)
        print("(is the M5 at the launcher prompt, not in openocd adapter mode? "
              "Use tools/m5_reentry.py to drive it there.)", file=sys.stderr)
        return 1
    if args.enter_only:
        dev.ser.close()  # ponytail: assumes the bridge survives port close; untested
        return 0

    out = f"{args.out}_{args.baud}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    raw_f = open(out + ".bin", "ab")
    txt_f = open(out + ".log", "ab") if not args.raw_only else None
    print(f"logging -> {out}.bin" + (" + .log" if txt_f else ""))
    t0 = time.monotonic()
    buf = bytearray()
    try:
        while True:
            if args.timeout and time.monotonic() - t0 > args.timeout:
                break
            data = dev.ser.read(4096)
            if not data:
                continue
            raw_f.write(data)
            raw_f.flush()
            if txt_f:
                for b in data:
                    if b == 0x0A:  # line end
                        line = bytes(buf).decode("utf-8", "replace")
                        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        txt_f.write(f"[{ts}] {line}\n".encode())
                        txt_f.flush()
                        print(f"[{ts}] {line}")
                        buf = bytearray()
                    else:
                        buf.append(b)
    except KeyboardInterrupt:
        pass
    finally:
        raw_f.close()
        if txt_f:
            txt_f.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())