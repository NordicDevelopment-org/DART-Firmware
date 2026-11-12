#!/usr/bin/env python3
"""Minimal KiCad s-expression netlist reader (stdlib only).

Usage:
  python3 -I netlist.py NETLIST.net summary
  python3 -I netlist.py NETLIST.net ref U1           # pin table for one part
  python3 -I netlist.py NETLIST.net net FEM_FPWM     # endpoints of one net
  python3 -I netlist.py NETLIST.net json OUT.json    # full model as JSON
"""
import json
import sys


def _tokenize(text):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "(" or c == ")":
            yield c
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                    continue
                if text[j] == '"':
                    break
                buf.append(text[j])
                j += 1
            yield ("S", "".join(buf))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n()":
                j += 1
            yield ("A", text[i:j])
            i = j


def parse_sexp(text):
    stack, cur = [], []
    for tok in _tokenize(text):
        if tok == "(":
            stack.append(cur)
            cur = []
        elif tok == ")":
            done, cur = cur, stack.pop()
            cur.append(done)
        else:
            cur.append(tok[1])
    return cur[0] if cur else []


def _kids(node, name):
    return [k for k in node if isinstance(k, list) and k and k[0] == name]


def _val(node, name, default=""):
    for k in _kids(node, name):
        if len(k) > 1 and not isinstance(k[1], list):
            return k[1]
    return default


def load(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        root = parse_sexp(f.read())
    comps = {}
    for comp_list in _kids(root, "components"):
        for c in _kids(comp_list, "comp"):
            ref = _val(c, "ref")
            sheet = ""
            for sp in _kids(c, "sheetpath"):
                sheet = _val(sp, "names")
            fields = {}
            for fl in _kids(c, "fields"):
                for fld in _kids(fl, "field"):
                    nm = _val(fld, "name")
                    # field value is the trailing atom
                    vals = [x for x in fld[1:] if not isinstance(x, list)]
                    fields[nm] = vals[-1] if vals else ""
            comps[ref] = {
                "value": _val(c, "value"),
                "footprint": _val(c, "footprint"),
                "sheet": sheet,
                "fields": fields,
            }
    nets = {}
    for net_list in _kids(root, "nets"):
        for n in _kids(net_list, "net"):
            name = _val(n, "name")
            nodes = []
            for nd in _kids(n, "node"):
                nodes.append([_val(nd, "ref"), _val(nd, "pin"),
                              _val(nd, "pinfunction"), _val(nd, "pintype")])
            nets[name] = nodes
    return {"components": comps, "nets": nets}


def pins_of(model, ref):
    """pin -> (pinfunction, netname) for one component."""
    out = {}
    for name, nodes in model["nets"].items():
        for r, pin, fn, ty in nodes:
            if r == ref:
                out[pin] = (fn, name, ty)
    return out


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    model = load(argv[1])
    cmd = argv[2]
    comps, nets = model["components"], model["nets"]
    if cmd == "summary":
        print(f"components={len(comps)} nets={len(nets)} "
              f"pins={sum(len(v) for v in nets.values())}")
    elif cmd == "ref":
        ref = argv[3]
        print(f"{ref}: {comps.get(ref, {}).get('value')}  "
              f"[{comps.get(ref, {}).get('sheet')}]")
        pins = pins_of(model, ref)

        def key(p):
            return (len(p), p)
        for pin in sorted(pins, key=key):
            fn, net, ty = pins[pin]
            others = [f"{r}.{p}" for r, p, _, _ in nets[net] if r != ref][:5]
            print(f"{pin:>5}  {fn:<16} {net:<28} -> {', '.join(others)}")
    elif cmd == "net":
        for r, p, fn, ty in nets.get(argv[3], []):
            print(f"{r}.{p} ({fn}) [{comps.get(r, {}).get('value', '')}]")
    elif cmd == "json":
        with open(argv[3], "w", encoding="utf-8") as f:
            json.dump(model, f, indent=1)
        print("wrote", argv[3])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
