# NDI 1 W Rev A0 firmware: open questions

Bottom line: question 1 can break the first power-up. Questions 2 to 4 gate M1 to M3.

## For HL, most blocking first

| # | Question | Why it matters | Default until answered |
|---|---|---|---|
| 1 | **Which TCXO is fitted on the first boards?** Y3 ECS-TXO-20CSMV4-320-AP-TR (designed, 1.7 to 3.6 V) is out of stock at JLC and must be consigned. The stocked Epson TG2016SMN is the 2.8 to 3.3 V version | DIO3 must be programmed to the fitted part. 1.8 V works for the ECS part with only 0.1 V margin over its minimum and cannot power the Epson part (needs 3.0 V). Wrong value: the radio never starts | `NDI_TCXO_VOLTAGE` 1.8 (ECS) |
| 2 | `docs/firmware_interface.md` is only in the 13.8 MB zip; put it unzipped in Drive "Dart pcb" or paste it | The hand-off calls it the pin truth. Any difference from `pin_table.csv` is reported, the netlist wins | Pins from the netlist (identical to the newest board page) |
| 3 | Which hardware do you have: RAK4631 + RAK5005, RAK13302, nRF52840-DK, BQ25856 evaluation module, SWD probe, RF power meter and attenuators? | Decides the HAL stand-in and the bring-up test plan (M3) | Assume none |
| 4 | Maker data sheets I need open (not in the package, sandbox cannot reach maker sites) | See table below | Written down as UNKNOWN, never filled from memory |
| 5 | USB product ID: NDI needs its own VID/PID pair before any shipped unit (the app layout borrows the RAK4631 board JSON) | USB identity and DFU | RAK board JSON for dev builds |
| 6 | May the plan notes strike the "BLE OTA on shipped units" lines? HL chose USB DFU | The notes still list BLE OTA as a requirement | USB DFU only |
| 7 | Hardware model: stay on PRIVATE_HW (255) or request a number from the Meshtastic maintainers? | The stock app shows PRIVATE_HW | PRIVATE_HW |
| 8 | GPLv3 section 6 against NDI-signed builds (counsel item in the plan) | Signing may have to change | Signing is a build option; first boards unsigned |
| 9 | Standby drain you accept with "System OFF, rails on" | Pack-monitor, gauge and TMUX switches stay powered | Measure on the first board |
| 10 | LED meanings (status RGB, heartbeat P0.06), SOS press pattern and payload, which die is the notification LED | Nothing sets them yet | I propose in M1 |

## Data sheets I need open

| Document | For | Settles |
|---|---|---|
| TI BQ25856-Q1 (section 7.4 host mode and watchdog, registers) | M2 charger | Does a register-pointer write start host mode; what EN_ICHG_PIN off does |
| Murata NCP15XH103F03RC full R-T table | M1 thermistor conversion | The design's thresholds used a table "as recalled"; firmware must use the real one |
| Skyworks SKY66122-11 (204782G) | M1 duty cap, M3 carrier test | What "30 percent duty" is measured over; thermal limits |
| Analog Devices MAX17048 | M2 gauge | Alert thresholds, hibernate, behaviour after the stock library's POR reset |
| Analog Devices MAX16150 | M2 SOS clear pulse | CLR timing (design notes record 51.2 to 76.8 ms lockout) |
| Nordic nRF52840 product specification | M0 follow-up | POWER DCDCEN with the SoftDevice, SAADC acquisition time against source resistance, UICR |
| ECS-TXO-20CSMV4 and Semtech SX1261/2 | TCXO | Output amplitude against supply; DIO3 voltage choices |
| MakerFocus 3000 mAh pack limits (ask the seller) | M2 | End-of-charge voltage, maximum charge current, protection limits |

## Assumptions in the code that need a document or a measurement

| Assumption | Where | Settled by |
|---|---|---|
| REG1 DC/DC may be enabled by a direct register write before the SoftDevice starts | `variant.cpp initVariant()`, flag `NDI_ENABLE_REG1_DCDC` | nRF52840 PS, then first-board current and brown-out check |
| SAADC acquisition time 40 us for the 600 kohm dividers (core default is 3 us) | `variant.cpp lateInitVariant()` | nRF52840 PS; first-board calibration |
| ADC multiplier 1.66667 is exact | `ndi_config.h` | First-board calibration |
| Duty window 60 s | `core/duty_cap` | Skyworks sheet |
| Amplifier gain table | not defined | Bench: attenuator and power meter |
| Charger watchdog behaviour | not implemented | EVM |
| Qwiic: no device at 0x36, 0x6A, 0x6B | docs | Rule for users |
| Stock stack: CI proves the build; nothing proves the behaviour on hardware | all | First boards |

## Found while reading (for the hardware lane)

- BOM maps R120 (2.2 ohm, series on the nRF52840 VBUS pin) to MPN 0402WGF220KTCE, LCSC C25101. That MPN reads like 220 k. A 220 k part would starve the USB regulator input. Check the LCSC listing before ordering.
- Plan notes still print superseded decisions (LiFePO4 modules, SOS button, 3.85 A charging). The firmware follows the newer board page.
- The design's flag that stock Meshtastic "reads 0x6B as an ISM330DHCX" does not match upstream: the scanner reads BQ24295, BQ25896, LSM6DS3 or QMI8658 there.
- `COLD_STAT` (P0.21) has no external pull-up; firmware enables the internal one.
- P0.04, P0.30 and P0.31 read about 0 V when VLOGIC is off (pack alone): reads must raise ID_EN first and wait at least 70 ms.
