"""Tests for check_netlist.py: the pin table must match the netlist, and every kind of
disagreement must be caught."""
import csv
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import check_netlist as cn  # noqa: E402


class RealData(unittest.TestCase):
    def test_table_matches_netlist(self):
        errs, nrows, ngpio = cn.check(cn.DEFAULT_TABLE, cn.DEFAULT_NET)
        self.assertEqual(errs, [])
        self.assertEqual((nrows, ngpio), (48, 48))

    def test_cli_exit_code(self):
        self.assertEqual(cn.main([]), 0)


class Disagreements(unittest.TestCase):
    def table_copy(self, d, edit):
        with open(cn.DEFAULT_TABLE, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames
            rows = list(reader)
        rows = edit(rows)
        path = os.path.join(d, "t.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        return path

    def test_wrong_net(self):
        with tempfile.TemporaryDirectory() as d:
            def edit(rows):
                next(r for r in rows if r["port_pin"] == "P0.07")["net"] = "HEAT_ENABLE"
                return rows
            errs, _, _ = cn.check(self.table_copy(d, edit), cn.DEFAULT_NET)
            self.assertTrue(any("P0.07" in e and "net" in e for e in errs), errs)

    def test_wrong_ball(self):
        with tempfile.TemporaryDirectory() as d:
            def edit(rows):
                next(r for r in rows if r["port_pin"] == "P1.05")["ball"] = "T22"
                return rows
            errs, _, _ = cn.check(self.table_copy(d, edit), cn.DEFAULT_NET)
            self.assertTrue(any("P1.05" in e and "ball" in e for e in errs), errs)

    def test_missing_row(self):
        with tempfile.TemporaryDirectory() as d:
            errs, _, _ = cn.check(self.table_copy(d, lambda rows: [r for r in rows if r["port_pin"] != "P0.26"]), cn.DEFAULT_NET)
            self.assertTrue(any("P0.26" in e and "missing" in e for e in errs), errs)

    def test_extra_row(self):
        with tempfile.TemporaryDirectory() as d:
            def edit(rows):
                extra = dict(rows[0])
                extra["port_pin"] = "P1.99"
                return rows + [extra]
            errs, _, _ = cn.check(self.table_copy(d, edit), cn.DEFAULT_NET)
            self.assertTrue(any("P1.99" in e for e in errs), errs)

    def test_netlist_changed(self):
        """A net renamed in the netlist (hardware moved on) must fail the table check."""
        with tempfile.TemporaryDirectory() as d:
            text = open(cn.DEFAULT_NET, encoding="utf-8", newline="").read()
            self.assertIn('(name "HEAT_INH")', text)
            path = os.path.join(d, "changed.net")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text.replace('(name "HEAT_INH")', '(name "HEAT_INH_RENAMED")'))
            errs, _, _ = cn.check(cn.DEFAULT_TABLE, path)
            self.assertTrue(any("P0.07" in e for e in errs), errs)

    def test_gpio_moved_in_netlist(self):
        """Swap two nets between balls: both pins must be reported."""
        with tempfile.TemporaryDirectory() as d:
            text = open(cn.DEFAULT_NET, encoding="utf-8", newline="").read()
            a = '(node (ref "U1") (pin "T23")'
            b = '(node (ref "U1") (pin "J24")'
            self.assertIn(a, text)
            self.assertIn(b, text)
            swapped = text.replace(a, "@@A@@").replace(b, a).replace("@@A@@", b)
            path = os.path.join(d, "swapped.net")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(swapped)
            errs, _, _ = cn.check(cn.DEFAULT_TABLE, path)
            self.assertGreaterEqual(len(errs), 2, errs)


if __name__ == "__main__":
    unittest.main()
