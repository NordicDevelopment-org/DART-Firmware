#!/usr/bin/env python3
"""Check pin_table.csv against the hardware netlist (KiCad s-expression export).

For every nRF52840 GPIO the table row must match the netlist: ball, net name, Arduino
number. Every GPIO in the netlist must be in the table, and nothing else. The netlist
wins any disagreement.

Usage:
  python3 -I check_netlist.py [--table pin_table.csv] [--netlist ../hardware/NDI_1W_RevA0.net] [--ref U1]
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import netlist  # noqa: E402

ROOT = os.path.dirname(HERE)
DEFAULT_TABLE = os.path.join(HERE, "pin_table.csv")
DEFAULT_NET = os.path.join(ROOT, "hardware", "NDI_1W_RevA0.net")


def short_net(name):
    """Strip the KiCad sheet prefix: '/MCU nRF52840/CHEM_ID_ADC' -> 'CHEM_ID_ADC'."""
    name = name.split("/")[-1]
    return "unconnected" if name.startswith("unconnected-") else name


def netlist_gpio(model, ref):
    """port pin name -> (ball, net) for the MCU."""
    out = {}
    for ball, (fn, net, _ty) in netlist.pins_of(model, ref).items():
        for m in re.finditer(r"P([01])\.(\d\d)", fn):
            out[f"P{m.group(1)}.{m.group(2)}"] = (ball, short_net(net))
    return out


def check(table_path, net_path, ref="U1"):
    errs = []
    with open(table_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    gpio = netlist_gpio(netlist.load(net_path), ref)
    seen = set()
    for r in rows:
        pin = r["port_pin"].strip()
        seen.add(pin)
        if pin not in gpio:
            errs.append(f"{pin}: not an {ref} GPIO in the netlist")
            continue
        ball, net = gpio[pin]
        if r["ball"].strip() != ball:
            errs.append(f"{pin}: ball {r['ball'].strip()!r} but netlist has {ball!r}")
        if short_net(r["net"].strip()) != net:
            errs.append(f"{pin}: net {r['net'].strip()!r} but netlist has {net!r}")
        m = re.fullmatch(r"P([01])\.(\d\d)", pin)
        if m and str(r["arduino_number"]).strip() != str(int(m.group(1)) * 32 + int(m.group(2))):
            errs.append(f"{pin}: arduino_number {r['arduino_number']!r} is wrong")
    for pin in sorted(set(gpio) - seen):
        errs.append(f"{pin}: in the netlist ({gpio[pin][1]}) but missing from the table")
    return errs, len(rows), len(gpio)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", default=DEFAULT_TABLE)
    ap.add_argument("--netlist", default=DEFAULT_NET)
    ap.add_argument("--ref", default="U1")
    a = ap.parse_args(argv)
    errs, nrows, ngpio = check(a.table, a.netlist, a.ref)
    if errs:
        print("pin table does NOT match the netlist:", file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        return 1
    print(f"pin table matches the netlist: {nrows} table rows, {ngpio} {a.ref} GPIO in the netlist, 0 differences")
    return 0


if __name__ == "__main__":
    sys.exit(main())
