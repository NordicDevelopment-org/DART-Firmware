# NDI 1 W Rev A0 firmware: sources of every number (M0)

Bottom line: pins come from the netlist, behaviour comes from upstream source at the pinned tag, and anything with no document is labelled ASSUMED.

Kinds: **nominal**, **maximum**, **measured** (nothing is measured yet), **derived** (arithmetic on cited values), **assumed** (no document gives it), **decided** (HL).

Design package = `NDI_1W_RevA0_files (2).zip` in Drive "Dart pcb" (netlist stamp 2026-11-11 12:24:47). Upstream = meshtastic/firmware at tag `v2.7.26.54e0d8d`, commit `54e0d8d0ab2ff56b3a9ce967e53f79e49af560fb`.

## Pins and boot states

| Item | Value | Kind | Source |
|---|---|---|---|
| All 48 GPIO numbers, nets, balls | see `pin_table/pin_table.csv` | derived from netlist | `hardware/NDI_1W_RevA0.net` U1; `check_netlist.py` proves 48 of 48 match in CI. Each row's `citations` column has the netlist line and design-script line |
| Arduino number | 32 x port + pin | derived | Arduino core `g_ADigitalPinMap` identity, as RAK4631 `variant.cpp` |
| Boot state per pin | `init_mode` column | derived from each net's pulls and loads | per-row `electrical_context` and `boot_action` in the table |
| Newest board page connectivity | identical to the netlist, 1,697 connected pins | measured by diff on 2026-11-12 | HL artifact `NDI 1W Radio PCB`, version 1794433625-d7d1 |

## Variant settings (`ndi_config.h`, `platformio.ini`, `variant.cpp`)

| Item | Value | Kind | Source |
|---|---|---|---|
| Hardware model | PRIVATE_HW = 255 | decided | plan notes line 102 ("PRIVATE_HW unless NDI gets a hardware-model number"); upstream `src/platform/nrf52/architecture.h:79-82` (RAK3401, RAK4630 tested first), `:120-121` (PRIVATE_HW) |
| `SX126X_MAX_POWER` | 10 (setting at the SX1262, dBm) | decided, interim | HL "all recommended" 2026-11-12, question 3. Clamp: upstream `src/mesh/SX126xInterface.cpp:89,248-249`, `src/mesh/RadioInterface.cpp:910-956` |
| Amplifier gain table | none | n/a | not measured |
| `SX126X_DIO3_TCXO_VOLTAGE` | 1.8 V default (flag `NDI_TCXO_VOLTAGE`) | assumed | RAK4631 profile (`variants/nrf52840/rak4631/variant.h:218`); `docs/review_revA0.md:44` (R-30) calls it unverified; fitted part undecided (OPEN-QUESTIONS 1) |
| TCXO supply range | ECS 1.7 to 3.6 V; Epson TG2016SMN 2.8 to 3.3 V | maximum/nominal as recorded | `out/NDI_1W_RevA_BOM_full.csv:305`; `docs/first_build_substitutions.md` (Y3 row) |
| DIO2 as RF switch | enabled | derived | DIO2 drives SKY66122-11 CTX (netlist U3 pin 2 via R138), `docs/review_revA0.md:44` |
| `SX126X_POWER_EN` P1.05 | high from radio init until sleep() | derived from source | upstream `SX126xInterface.cpp:53-56,395-396` |
| Battery multiplier | 1.66667 | derived | netlist R91 1.00 M, R92 1.50 M behind U85: pin = 0.6 x VBAT; stock RAK value 1.73 at `rak4631/variant.h:267` |
| `AREF_VOLTAGE`, `VBAT_AR_INTERNAL` | stock defaults (3.6 V full scale), RAK 3.0 V values forbidden | derived | RAK sets 3.0 V (`rak4631/variant.h:264-266`), which clips the VS_USB tap above 23 V (24.0 V eFuse OVLO maximum, `ndi_1w/core/SOURCES.md`) |
| SAADC acquisition time | 40 us | assumed | core option exists (`wiring_analog_nRF52.c:144-161`, default 3 us at `:33`); nRF52840 PS not opened |
| REG1 DC/DC | enabled by `NRF_POWER->DCDCEN` in `initVariant()`, flag `NDI_ENABLE_REG1_DCDC` | assumed safe | hardware: netlist U1 B3 DCC to L1 10 uH to L2 15 nH to DEC4/DEC6, `docs/review_revA0.md:43` (R-29). Stock sources never write DCDCEN (grep of core, Bluefruit and app sources). Hook timing: core `main.cpp` initVariant before FreeRTOS and the SoftDevice |
| NFC pins as GPIO, P0.18 as reset | build flags `CONFIG_NFCT_PINS_AS_GPIOS`, `CONFIG_GPIO_AS_PINRESET` | derived | core `system_nrf52840.c:145-173` honours both; P0.09 BTN1_M and P0.10 FEM_FPWM are NFC balls, P0.18 is NRST (netlist) |
| LED polarity | active low | derived | netlist D24, D25, R167-R170 (anodes on 3V3_LED) |
| LED drive | H0H1 on P1.03, P1.04, P0.08 | decided | design review m4 (standard drive 1 to 1.9 mA), board page "Open items" |
| `GPS_EN_ACTIVE` | 1 | derived | U6 TPS22918-Q1 enable active high with 100 k pull-down (pin table row P1.02); stock `src/gps/GPS.cpp:1548-1573` |
| `NRF_APM` | defined | decided | stock RAK pattern (`rak4631/variant.h:221`); VBUS via R120 from V5_NRF |
| Hook call sites | `earlyInitVariant` main.cpp:330, `lateInitVariant` main.cpp:991 | derived from source | upstream `src/main.cpp:268-272,330,991` |

## Upstream behaviour the design relies on

| Fact | Source |
|---|---|
| Scan loop at line 277; 0x6B case reads regs 0x0A, 0x14, 0x0F at lines 552, 558, 564 | `src/detect/ScanI2CTwoWire.cpp` at the tag |
| `limitPower()` skips region cap and gain for a licensed owner but always clamps to the maximum | `src/mesh/RadioInterface.cpp:910-956` at the tag |
| Gain table applied only at init; `reconfigure()` clamps with `SX126X_MAX_POWER` only | `SX126xInterface.cpp:89` and `:248-249` at the tag |
| US duty limiter off (hourly limiter runs only below 100 percent duty) | `src/airtime.cpp:136` (master 2.7.27; unchanged logic) |
| 500 kHz presets are only SHORT_TURBO and LONG_TURBO | `src/mesh/MeshRadio.h:136,161` (same file at master and tag) |
| PlatformIO platform `nordicnrf52@10.11.0` at the tag, framework branch `cpp17-platform`, toolchain `~1.90301.0`, RadioLib 7.6.0 | `variants/nrf52840/nrf52.ini`, root `platformio.ini` at the tag |

## Not verified against a maker document yet

Everything in `OPEN-QUESTIONS.md` under "Data sheets I need open". The design package records maker values (for example the amplifier input maximum of +16 dBm and the charger watchdog of 130 to 160 s) but the PDFs are not in the package.

Core logic numbers (ADC ratios, button timing, duty cap) are in `ndi_1w/core/SOURCES.md`.
