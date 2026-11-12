# NDI 1 W LoRa radio, Rev A0: firmware

Bottom line: Meshtastic for the NDI 1 W board, as stock upstream source at a pinned release tag plus a generated board definition and a short patch set. Nothing has run on hardware. No board exists yet.

## Status

| Milestone | What | State |
|---|---|---|
| M0 | Variant builds in CI from a generated pin map; unsafe stock behaviour removed; host tests | in progress |
| M1 | Core logic and ATtiny402 build; US 500 kHz lock; duty cap in the send path | not started |
| M2 | Board support: charger (read only), heater veto, temperature, chemistry ID, input sources, low-battery shutdown, gestures | not started |
| M3 | NDI bootloader, bring-up image, first-flash sheet | not started |

## Layout

```
upstream.lock          Meshtastic tag, 40-hex commit, tool versions
hardware/              pinned netlist copy and provenance (sha256)
pin_table/             pin_table.csv, gen_variant.py, check_netlist.py, tests
meshtastic/
  overlay/variants/nrf52840/ndi_1w/   platformio.ini, ndi_config.h, variant.cpp + GENERATED variant.h
  patches/             numbered, each justified
  forbidden_macros.txt macros that may never be defined
core/                  plain C++ logic, host-tested (ADC taps, hold detector, duty cap)
ci/                    resolve_upstream.sh, build_variant.sh, check_forbidden.py
docs/                  SAFETY, DECISIONS, OPEN-QUESTIONS, SOURCES, CHANGELOG-BEHAVIOUR, PINMAP
```

## How it fits together

1. `pin_table.csv` is the only place a pin number is written. `check_netlist.py` proves it against `hardware/NDI_1W_RevA0.net`.
2. `gen_variant.py` writes `variant.h`, the boot-state table, the forbidden-macro guard and `docs/PINMAP.md`. `--check` fails on drift.
3. CI clones upstream at the pinned tag, copies the overlay in, applies the patches, runs `check_forbidden.py`, and builds `ndi_1w` next to a stock `rak4631` control.

## Run it

Host checks need only Python 3 and g++:

```bash
python3 -I ndi_1w/pin_table/check_netlist.py
python3 -I ndi_1w/pin_table/gen_variant.py --check
python3 -I -m unittest discover -s ndi_1w/pin_table/tests
python3 -I ndi_1w/ci/check_forbidden.py
make -C ndi_1w/core test
```

The Meshtastic build runs in GitHub Actions (`ndi-1w variant build`). It needs the PlatformIO registry and GitHub archives.

To change a pin: edit `pin_table.csv`, run `python3 -I ndi_1w/pin_table/gen_variant.py`, commit the generated files with it. Never edit `variant.h` by hand.

## Rules

- Never invent a specification. `docs/SOURCES.md` says where each number came from and whether it is nominal, maximum, measured, derived or assumed.
- Safety first: read `docs/SAFETY.md` before touching charging, heating or transmit power.
- Every change that alters behaviour goes in `docs/CHANGELOG-BEHAVIOUR.md`.
- Questions waiting on HL: `docs/OPEN-QUESTIONS.md`.
