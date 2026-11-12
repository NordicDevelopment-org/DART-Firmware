# NDI 1 W Rev A0 firmware: decisions

Bottom line: HL decided these. Do not reopen without asking.

## Decided in the hand-off (HL, 2026-11-11)

| Decision | Where it lands |
|---|---|
| Shipped units run NDI's own build: stock Meshtastic source plus an NDI board definition, NDI-signed, stock Meshtastic app. MeshCore and RNode later | M0 variant; signing is a build option (see below) |
| Certification path FCC 15.247 digital transmission: shipped builds locked to the US 500 kHz channel plan | M1 patch |
| Updates over USB. BLE antenna is inside the aluminium case | M3 bootloader |
| No SOS button on the case. SOS from the app or a user-button press pattern | M2 |
| Charging 1.0 A, charge only from 40 F, heat first, never heat on the pack alone: all hardware. Firmware stops the heater re-arming once the pack is full (veto pin) | M2 |
| The radio restores its last on or off state after a pack change. That is the ATtiny402's job (U89) | M1 |

## Answers of 2026-11-12 ("all recommended")

| Q | Answer | Lands in |
|---|---|---|
| 1 Repo | `NordicDevelopment-org/DART-Firmware`, NDI 1 W in `ndi_1w/`, shared tools at the root, push to a branch (never `main`) unless told | done |
| 2 I2C scan | Patch the scan to skip 0x6A and 0x6B (small, CI-applied, keeps Qwiic sensors) | M0, patch 0001 |
| 3 Interim TX | `SX126X_MAX_POWER` 10; duty cap 30 percent over a rolling 60 s window (the window is an assumption: Skyworks gives only the 30 percent figure) | cap in M0; duty cap code in M1 |
| 4 US lock | Carry a small patch set on the pinned tag; allowed preset LONG_TURBO only; default slot (from the channel name) | M1 |
| 5 Bootloader | NDI-built Adafruit bootloader with its own board file (DC/DC on, NFC as GPIO), proven on a RAK4631 or nRF52840-DK first; first boards unsigned until the GPLv3 section 6 answer | M3 |
| 6 Shutdown | System OFF with rails still on: save state, FEM and GNSS off, wake on button. Standby drain: measure on the first board | M2 |
| 7 Hardware in hand | No answer yet. Assumed none until told | open |

Defaults accepted at the same time:

| | Default | Lands in |
|---|---|---|
| a | CI resolves the newest stable Meshtastic tag and records tag and commit in `upstream.lock` | M0, done: `v2.7.26.54e0d8d` |
| b | Hardware model PRIVATE_HW (255); licensed mode forced off | M0 / M1 |
| c | GNSS rail off at boot; stock GPS logic drives P1.02 | M0 |
| d | Charger: read status and faults and feed the watchdog only. No ICHG, ILIM, EN_ICHG_PIN, EN_REV or EN_AUTO_REV writes; per-chemistry trim off until the EVM check | M2 |
| e | One Li-ion profile (4.20 V) as built; table can take other chemistries later | M2 |
| f | SOS is firmware state from the app or a press pattern; U8 latch ignored except one P0.23 clear at boot | M2 (needs the MAX16150 data sheet for the clear timing) |
| g | A 5 s hold saves NodeDB with no shutdown; stock triple-press GPS toggle off | M2 |
| h | Runtime GPIO selectors (buzzer, button, gps_en) locked out; P0.25 (ID_EN) pulsed only when a read is needed | M1 / M2 |

## Choices made in M0 that nobody asked for (change on request)

| Choice | Why |
|---|---|
| Generate `variant.h` from the pin table instead of starting from a RAK4631 copy | A copy makes stock code drive NDI nets (see SAFETY.md) |
| `ndi_1w` env follows upstream `rak3401_1watt` (1 W, same chain topology) but strips every RAK macro and library | Same env pattern, none of the RAK pins |
| Boot states come from the same table as the pin numbers | One place to review; golden safety test guards it |
| REG1 DC/DC enabled by a build flag, default on | Hardware is present and stock never enables it; unverified on hardware, flag turns it off |
| TCXO voltage is a named flag, default 1.8 V | Depends on which TCXO is fitted: open question 1 |
| Serial and Remote Hardware modules excluded | Both take pin numbers from runtime config (default h: runtime GPIO selectors locked out). External notification and detection sensor stay in until the LED scheme is decided (M1) |
| `board = wiscore_rak4631` for the app layout | Same MCU and SoftDevice layout; NDI needs its own USB product ID before shipping (open question) |
