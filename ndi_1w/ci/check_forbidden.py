#!/usr/bin/env python3
"""Static checks for the NDI 1 W Meshtastic overlay.

1. No forbidden macro (meshtastic/forbidden_macros.txt) is DEFINED, by #define or by a -D build
   flag, in the overlay. Mentions in comments and #ifdef guards are fine.
2. platformio.ini carries every flag the board needs.
3. With --upstream DIR (an upstream checkout with the overlay copied in and the patches applied):
   the I2C scan skip sits inside the scan loop before the first beginTransmission(), and every
   place upstream src/ mentions 0x6A, 0x6B or the devices that live there is printed for review.

Usage:
  python3 -I check_forbidden.py [--overlay DIR] [--upstream DIR]
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # ndi_1w/
DEFAULT_OVERLAY = os.path.join(ROOT, "meshtastic", "overlay", "variants", "nrf52840", "ndi_1w")
DEFAULT_FORBIDDEN = os.path.join(ROOT, "meshtastic", "forbidden_macros.txt")

# (macro, file) pairs allowed to define a forbidden name: NDI owns the one place that sets it.
ALLOWED_DEFINITIONS = {("SX126X_MAX_POWER", "ndi_config.h")}

REQUIRED_FLAGS = (
    "PRIVATE_HW",
    "CONFIG_NFCT_PINS_AS_GPIOS",
    "CONFIG_GPIO_AS_PINRESET",
    "MESHTASTIC_EXCLUDE_ACCELEROMETER",
    "NDI_I2C_SKIP_CHARGER_IMU",
)

SCAN_LOOP = "for (addr.address = 8; addr.address < 120; addr.address++) {"


def forbidden_names(path):
    names = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            body = line.split("#", 1)[0].strip()
            if body:
                names.append(body.split()[0])
    return names


def strip_c_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def ini_flags(text):
    """Names given with -D in an ini file, ignoring full-line and trailing ';' comments."""
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith((";", "#")):
            continue
        kept.append(re.split(r"\s;", line, maxsplit=1)[0])
    return set(re.findall(r"(?:^|\s)-D\s*([A-Za-z_]\w*)", "\n".join(kept)))


def check_overlay(overlay, forbidden):
    errs = []
    bad = set(forbidden)
    for name in sorted(os.listdir(overlay)):
        path = os.path.join(overlay, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if name == "platformio.ini":
            defined = ini_flags(text)
            for req in REQUIRED_FLAGS:
                if req not in defined:
                    errs.append(f"{name}: required build flag -D {req} is missing")
        else:
            defined = set(re.findall(r"^\s*#\s*define\s+(\w+)", strip_c_comments(text), flags=re.M))
        for macro in sorted(defined & bad):
            if (macro, name) not in ALLOWED_DEFINITIONS:
                errs.append(f"{name}: forbidden macro {macro} is defined")
    return errs


def check_upstream(upstream):
    errs = []
    scanner = os.path.join(upstream, "src", "detect", "ScanI2CTwoWire.cpp")
    with open(scanner, encoding="utf-8") as f:
        text = f.read()
    if text.count(SCAN_LOOP) != 1:
        return [f"scanner loop header found {text.count(SCAN_LOOP)} times, expected exactly 1"]
    i = text.index(SCAN_LOOP)
    j = text.find("NDI_I2C_SKIP_CHARGER_IMU", i)
    k = text.find("beginTransmission", i)
    if j < 0:
        errs.append("scan skip (patch 0001) is not applied: NDI_I2C_SKIP_CHARGER_IMU not found after the scan loop header")
    elif not (i < j < k):
        errs.append("scan skip is not before the first beginTransmission() in the scan loop")
    else:
        block = text[j:k]
        for need in ("0x6A", "0x6B", "continue"):
            if need not in block:
                errs.append(f"scan skip block does not mention {need}")
    return errs


def audit_upstream(upstream):
    """Print every mention of the charger and IMU addresses in upstream src/ for human review."""
    pat = re.compile(r"0x6[Aa]\b|0x6[Bb]\b|QMI8658_ADDR|BQ25896_ADDR|BQ24295_ADDR|LSM6DS3_ADDR|BQ25896|HAS_PPM")
    print("audit: upstream src/ mentions of 0x6A, 0x6B and their devices (review, not a failure)")
    total = 0
    for dirpath, _dirs, files in os.walk(os.path.join(upstream, "src")):
        for fn in sorted(files):
            if not fn.endswith((".c", ".cpp", ".h", ".hpp")):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8", errors="replace") as f:
                for n, line in enumerate(f, 1):
                    if pat.search(line):
                        total += 1
                        print(f"  {os.path.relpath(path, upstream)}:{n}: {line.strip()[:110]}")
    print(f"audit: {total} mentions")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--overlay", default=DEFAULT_OVERLAY)
    ap.add_argument("--forbidden", default=DEFAULT_FORBIDDEN)
    ap.add_argument("--upstream", default=None)
    a = ap.parse_args(argv)

    errs = check_overlay(a.overlay, forbidden_names(a.forbidden))
    if a.upstream:
        errs += check_upstream(a.upstream)
        audit_upstream(a.upstream)
    if errs:
        print("overlay checks FAILED:", file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        return 1
    print("overlay checks passed: no forbidden macro defined, required build flags present"
          + (", scan skip in place" if a.upstream else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
