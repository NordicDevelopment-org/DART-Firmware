# NDI 1 W Rev A0 firmware: behaviour changes against stock Meshtastic

Bottom line: every row is something the NDI build does differently from upstream `v2.7.26.54e0d8d`. Newest first.

## 2026-11-12, M0 (not run on hardware)

| Change | Stock behaviour | NDI behaviour | Why |
|---|---|---|---|
| Hardware model | RAK builds report their model | reports PRIVATE_HW (255) | custom board, no model number |
| I2C scan | probes every address 0x08 to 0x77, register-pointer writes at 0x6B | never touches 0x6A or 0x6B (patch 0001) | 0x6B is the BQ25856-Q1 charger |
| Accelerometer | LSM6DS3 path may write registers at 0x6A or 0x6B | excluded (`MESHTASTIC_EXCLUDE_ACCELEROMETER`) | same |
| TX power | region cap, then optional gain table, then clamp to 22 | clamp to 10 (setting at the SX1262) on init and reconfigure; no gain table | amplifier chain unmeasured |
| REG1 DC/DC | never enabled | enabled in `initVariant()` (flag) | hardware present; unverified |
| NFC pins, reset pin | NFC pins stay NFC, P0.18 may not be reset | freed as GPIO, P0.18 is reset (UICR written on first boot, one reset) | P0.09, P0.10 are used; P0.18 is NRST |
| Boot GPIO states | not set | table-driven, see `docs/PINMAP.md` | safe states: GNSS off, FEM off, heater veto idle, LEDs off |
| Status LEDs | active high, standard drive | active low; green, red, blue at high drive | board wiring, review m4 |
| Notification LED | LED_BLUE on RAK | not defined | choice pending |
| Battery sense | RAK multiplier 1.73, AREF 3.0 V | multiplier 1.66667, stock 3.6 V full scale, SAADC acquisition 40 us | divider values, VS_USB range |
| GNSS enable | `PIN_3V3_EN` high at boot on RAK | P1.02 driven by stock GPS logic, low at boot | GNSS load switch active high |
| Button 2 | `PIN_BUTTON2` creates a back button | not mapped | role undecided |
| Serial module | present, pins from config, `Serial2` | excluded (`MESHTASTIC_EXCLUDE_SERIAL`) | runtime pin selector; also `Serial2` has no pins on this board |
| Remote Hardware module | present (off by default) | excluded (`MESHTASTIC_EXCLUDE_REMOTEHARDWARE`) | a mesh peer could read and write GPIOs on NDI nets |
| RAK peripherals | buzzer, ethernet, RAK RGB, RTC, air-quality pin | none | those pins are NDI nets |
| Region lock | none | none yet (M1) | |
| Duty cap | US limiter off | none yet (M1) | |
