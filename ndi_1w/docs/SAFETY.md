# NDI 1 W Rev A0: firmware safety rules

Bottom line: M0 builds are bench builds. Nothing has run on hardware. Do not ship one.

## Hard limits and where the repo enforces each

| Hard limit (HL hand-off, 2026-11-11) | Enforced by | Status |
|---|---|---|
| Never set EN_REV or EN_AUTO_REV in the BQ25856-Q1 | No charger register code exists. Charger code arrives in M2 with the TI data sheet open; policy is read status and faults and feed the watchdog only | M0: nothing writes the charger |
| Never raise the hardware charge or input limits by register | Same. No ICHG, ILIM or EN_ICHG_PIN writes (HL default d) | M0: nothing writes the charger |
| Never drive the heater on; firmware can only veto | No MCU pin reaches the heater enable. P0.07 (veto) boots LOW = no veto. Golden test `SafeBootStates` fails if the table changes that | Enforced by hardware and test |
| Do not use the battery temperature reading to override the hardware charge gate | No MCU pin reaches charger CE. Temperature is for display and the heater veto only | Enforced by hardware |
| Do not ship a build that can leave the US 500 kHz plan | Core patch at the modem-config choke point (M1). Upstream has no hard lock | NOT implemented in M0: M0 builds can leave the plan |
| Keep transmit duty within what Skyworks tested (30 percent at +30 dBm) until measured | `duty_cap` module (host-tested) integrated at the send path in M1. Upstream US duty limiter is off | NOT integrated in M0: M0 builds have no duty cap |

## Transmit power

- `SX126X_MAX_POWER` is a **setting at the SX1262 in dBm**, not power at the connector. M0 value 10 (HL "all recommended", 2026-11-12). Nobody has measured the amplifier chain.
- It is the only clamp that holds on every path. At the pinned tag (`v2.7.26.54e0d8d`):
  - `src/mesh/SX126xInterface.cpp:89` calls `limitPower(SX126X_MAX_POWER)` at radio init.
  - `src/mesh/SX126xInterface.cpp:248-249` clamps to `SX126X_MAX_POWER` again in `reconfigure()`.
  - `src/mesh/RadioInterface.cpp:910-956` (`limitPower`): the region cap and any PA gain subtraction are skipped for a licensed owner, but the final `power > loraMaxPower` clamp is not.
- A `TX_GAIN_LORA` table is applied only inside `limitPower()`, which only runs at init. Every later config save calls `reconfigure()`, which re-reads the unadjusted power. So a measured gain table would be bypassed until reboot. The NDI build therefore defines **no** gain table, and `forbidden_macros.txt` blocks `TX_GAIN_LORA`, `NUM_PA_POINTS` and `HAS_LORA_FEM`.
- `ndi_config.h` refuses to build with a setting above the interim cap unless `NDI_TX_CAP_RAISED_AFTER_MEASUREMENT` is defined, and refuses values outside -9 to +22.
- Plausibility only, not a spec: the RAK13302 table in HL's research doc gives about +18 dBm out for a 10 dBm setting (RAK figure, not labelled conducted). The NDI chain has a different pad, so the real number is unknown. Derived drive at the SKY66122-11 input is about -0.3 to -0.6 dBm at the +22 setting against +16 dBm absolute maximum (docs/review_revA0.md lines 42 and 44, as recorded by the design), so the amplifier input is not at risk. The cap protects radiated power and duty, not the input.
- First carrier test (M3 bring-up image): attenuator and power meter on the connector, lowest setting first, never without an antenna or dummy load. Raising the cap needs a measured table.

## The I2C scan and the charger

- Stock `ScanI2CTwoWire::scanPort()` (loop at `src/detect/ScanI2CTwoWire.cpp:277`) sends an address-only write to every address from 0x08 to 0x77. At 0x6B (`case QMI8658_ADDR`, lines 551-564) it also sends register-pointer writes for registers 0x0A, 0x14 and 0x0F. No macro filters scanner addresses.
- On this board 0x6B is the BQ25856-Q1 charger. Whether a register-pointer write starts charger host mode (130 to 160 s watchdog, per the design review) is **unknown** until TI section 7.4 and an EVM run settle it. So the scan must not touch it.
- Patch `0001-i2c-scan-skip-charger-and-imu.patch` skips 0x6A and 0x6B inside the scan loop. `MESHTASTIC_EXCLUDE_ACCELEROMETER` removes the LSM6DS3 path that would write registers there. `HAS_PPM` (stock charger-writing code for 0x6B) is forbidden.
- No Qwiic device at 0x36, 0x6A or 0x6B.

## Pins stock Meshtastic must never drive

Copying RAK4631's `variant.h` would make stock code drive these NDI nets. The overlay is generated from the pin table instead, and the macros below are forbidden (`meshtastic/forbidden_macros.txt`, enforced by CI and by `#error` guards).

| Stock macro | Net it would hit | Effect |
|---|---|---|
| `PIN_BUZZER` 21 | COLD_STAT P0.21 | `tone()` on the heater read-back |
| `AQ_SET_PIN`, `PMSA003I_ENABLE_PIN` 10 | FEM_FPWM P0.10 | amplifier supply mode driven high at boot, low in deep sleep |
| `DETECTION_SENSOR_EN` 4 | BT_TEMP P0.04 | battery temperature tap driven as an output |
| `PIN_3V3_EN` 34 | GNSS_EN P1.02 | GNSS rail forced on at boot |
| `LED_BLUE` 36 | LED_R P1.04 | the red die |
| `HAS_ETHERNET`, `RAK4630`, `RAK_4631`, `RAK3401`, `RAK13302` | several | wrong pins and wrong hardware model |

Source: RAK4631 `variant.h` lines 48, 204, 206, 215, 229, 251, 283-290 (read directly), netlist for the nets.

## First flash

- The board starts OFF. USB alone does not enable 3V3 (power latch cleared). Press the user button (SW2 with the cap off, or J7) or bridge JP3 FORCE ON before connecting the probe.
- J12 pin 1 is tied to 3V3: use the probe as a VTref input only. A powering probe would back-feed every 3V3 load.
- A blank chip needs MBR, S140 6.1.1 and a bootloader before Meshtastic can run (M3). First boards are unsigned dev units.
