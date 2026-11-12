"""Tests for gen_variant.py: the generator must accept the real table, refuse broken tables,
and keep the safe boot states HL's hard limits depend on."""
import csv
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import gen_variant as gv  # noqa: E402


def real_rows():
    return gv.load_table(gv.DEFAULT_TABLE)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def forbidden():
    return gv.load_forbidden(gv.DEFAULT_FORBIDDEN)


def row(rows, pin):
    return next(r for r in rows if r["port_pin"].strip() == pin)


class RealTable(unittest.TestCase):
    def test_validates(self):
        self.assertEqual(gv.validate(real_rows(), forbidden()), [])

    def test_generated_files_are_up_to_date(self):
        self.assertEqual(gv.main(["--check"]), 0)

    def test_48_pins_unique_arduino_numbers(self):
        nums = [int(r["arduino_number"]) for r in real_rows()]
        self.assertEqual(nums, list(range(48)))

    def test_every_stock_macro_is_in_the_header(self):
        header = read(os.path.join(gv.DEFAULT_OUT, "variant.h"))
        for name in gv.STOCK_MACROS + tuple(gv.ALLOWED_ALIASES):
            self.assertRegex(header, r"\b" + name + r"\b", name)

    def test_header_defines_no_forbidden_macro(self):
        header = read(os.path.join(gv.DEFAULT_OUT, "variant.h"))
        body = re.sub(r"/\*.*?\*/", "", header, flags=re.S)
        body = re.sub(r"//[^\n]*", "", body)
        for name in forbidden():
            self.assertNotRegex(body, r"#\s*define\s+" + name + r"\b", name)

    def test_generated_text_is_ascii_without_dashes(self):
        for fn in ("variant.h", "ndi_pin_init.inc", "ndi_forbidden_guard.h"):
            text = read(os.path.join(gv.DEFAULT_OUT, fn))
            self.assertTrue(text.isascii(), fn)
        self.assertTrue(read(gv.DEFAULT_MD).isascii())

    def test_init_table_has_only_applied_modes(self):
        rows = real_rows()
        text = read(os.path.join(gv.DEFAULT_OUT, "ndi_pin_init.inc"))
        listed = {int(n) for n in re.findall(r"NDI_PIN_INIT_ROW\((\d+),", text)}
        want = {int(r["arduino_number"]) for r in rows if r["init_mode"].strip() in gv.APPLIED_MODES}
        self.assertEqual(listed, want)


class SafeBootStates(unittest.TestCase):
    """Golden expectations, written out independently of the table (hand-off hard limits,
    ndi_1w/docs/SAFETY.md). A table edit that changes one of these must be a conscious decision."""

    EXPECT = {
        "P0.07": "OUTPUT_LOW",    # heater veto idle low = no veto; firmware can only veto, never enable
        "P1.05": "OUTPUT_LOW",    # FEM and 4.9 V boost enable: off until radio init
        "P1.02": "OUTPUT_LOW",    # GNSS rail off at boot
        "P0.25": "OUTPUT_LOW",    # ID_EN: VLOGIC off on the pack alone
        "P1.03": "OUTPUT_HIGH",   # status LEDs active low: off
        "P1.04": "OUTPUT_HIGH",
        "P0.08": "OUTPUT_HIGH",
        "P0.06": "OUTPUT_HIGH",   # heartbeat LED off
        "P1.10": "OUTPUT_HIGH",   # SX1262 NSS idle high
        "P0.21": "INPUT_PULLUP",  # COLD_STAT has no external pull-up
        "P0.10": "INPUT",         # amplifier mode: never driven by default (forced PWM by pull-up)
        "P0.09": "INPUT",         # user button: never an output
        "P0.23": "INPUT",         # SOS clear: open-drain style, never driven high
        "P0.27": "INPUT",         # Qwiic enable: port on by default
        "P1.14": "INPUT",
        "P1.15": "INPUT",
    }

    def test_boot_states(self):
        rows = real_rows()
        for pin, mode in self.EXPECT.items():
            self.assertEqual(row(rows, pin)["init_mode"].strip(), mode, pin)

    def test_no_pin_that_must_stay_input_is_an_output(self):
        for pin in ("P0.09", "P0.10", "P0.12", "P0.22", "P0.23", "P0.24", "P0.26", "P0.29", "P1.14", "P1.15"):
            self.assertNotIn(row(real_rows(), pin)["init_mode"].strip(), ("OUTPUT_HIGH", "OUTPUT_LOW"), pin)


class BrokenTables(unittest.TestCase):
    def mutate(self, fn):
        rows = real_rows()
        fn(rows)
        return gv.validate(rows, forbidden())

    def test_duplicate_macro(self):
        errs = self.mutate(lambda rs: row(rs, "P0.07").__setitem__("variant_macro", "NDI_PIN_LED_B"))
        self.assertTrue(any("already used" in e for e in errs), errs)

    def test_bad_init_mode(self):
        errs = self.mutate(lambda rs: row(rs, "P0.07").__setitem__("init_mode", "OUTPUT_MAYBE"))
        self.assertTrue(any("init_mode" in e for e in errs), errs)

    def test_forbidden_macro(self):
        def f(rs):
            r = row(rs, "P0.21")
            r["variant_macro"], r["macro_kind"] = "PIN_BUZZER", "stock"
        errs = self.mutate(f)
        self.assertTrue(any("forbidden" in e for e in errs), errs)

    def test_missing_required_stock_macro(self):
        def f(rs):
            r = row(rs, "P1.05")
            r["variant_macro"], r["macro_kind"] = "", "none"
        errs = self.mutate(f)
        self.assertTrue(any("SX126X_POWER_EN" in e for e in errs), errs)

    def test_wrong_arduino_number(self):
        errs = self.mutate(lambda rs: row(rs, "P1.05").__setitem__("arduino_number", "36"))
        self.assertTrue(any("arduino_number" in e for e in errs), errs)

    def test_alias_on_wrong_macro(self):
        errs = self.mutate(lambda rs: row(rs, "P1.04").__setitem__("variant_macro_aliases", "LED_GREEN"))
        self.assertTrue(any("LED_GREEN" in e for e in errs), errs)

    def test_unknown_stock_macro(self):
        def f(rs):
            r = row(rs, "P1.03")
            r["variant_macro"] = "PIN_LED_ONE"
        errs = self.mutate(f)
        self.assertTrue(any("PIN_LED_ONE" in e for e in errs), errs)

    def test_missing_row(self):
        rows = [r for r in real_rows() if r["port_pin"].strip() != "P0.30"]
        self.assertTrue(gv.validate(rows, forbidden()))

    def test_cli_refuses_a_broken_table(self):
        with tempfile.TemporaryDirectory() as d:
            rows = real_rows()
            row(rows, "P0.07")["init_mode"] = "OUTPUT_MAYBE"
            path = os.path.join(d, "t.csv")
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            self.assertEqual(gv.main(["--table", path, "--out-dir", d, "--md", ""]), 2)
            self.assertFalse(os.path.exists(os.path.join(d, "variant.h")))


class Check(unittest.TestCase):
    def test_check_mode_detects_a_stale_file(self):
        with tempfile.TemporaryDirectory() as d:
            for fn in ("variant.h", "ndi_pin_init.inc", "ndi_forbidden_guard.h"):
                shutil.copy(os.path.join(gv.DEFAULT_OUT, fn), os.path.join(d, fn))
            self.assertEqual(gv.main(["--out-dir", d, "--md", "", "--check"]), 0)
            with open(os.path.join(d, "variant.h"), "a", encoding="utf-8") as f:
                f.write("#define SOMETHING_TYPED_BY_HAND 1\n")
            self.assertEqual(gv.main(["--out-dir", d, "--md", "", "--check"]), 1)

    def test_ascii_clean_removes_dashes(self):
        text = "a" + chr(0x2014) + "b" + chr(0x2013) + "c" + chr(0x03A9)
        out = gv.ascii_clean(text)
        self.assertEqual(out, "a-b-cohm")


if __name__ == "__main__":
    unittest.main()
