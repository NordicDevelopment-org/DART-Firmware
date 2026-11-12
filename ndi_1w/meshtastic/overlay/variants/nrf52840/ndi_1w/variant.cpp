/*
  NDI 1 W LoRa radio, Rev A0: variant code.

  Boot pin states (table driven), REG1 DC/DC, status LED drive, SAADC acquisition time.
  Hooks used (upstream meshtastic/firmware, cited in ndi_1w/docs/SOURCES.md):
    initVariant()      core cores/nRF5/main.cpp: before FreeRTOS and before the SoftDevice is enabled
    lateInitVariant()  src/main.cpp: after initLoRa(), after stock pinMode() calls on the LED pins

  Board-support logic (charger, heater veto, temperature, chemistry ID, input sources, low-battery
  shutdown) is NOT here yet: it lands in M2 as a separate module with host-tested core logic.
*/

#include "Arduino.h"
#include "nrf.h"
#include "variant.h"
#include "wiring_constants.h"
#include "wiring_digital.h"

const uint32_t g_ADigitalPinMap[] = {
    // P0
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31,

    // P1
    32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47};

namespace
{
enum NdiInitMode : uint8_t { NDI_INIT_INPUT, NDI_INIT_INPUT_PULLUP, NDI_INIT_OUTPUT_HIGH, NDI_INIT_OUTPUT_LOW };

struct NdiPinInit {
    uint8_t pin;
    NdiInitMode mode;
};

// Generated from pin_table.csv (init_mode column). The port pin and net strings are for readers only.
#define NDI_PIN_INIT_ROW(pin, mode, port, net) {(uint8_t)(pin), mode},
const NdiPinInit kPinInit[] = {
#include "ndi_pin_init.inc"
};
#undef NDI_PIN_INIT_ROW

// Status RGB dies (green P1.03, red P1.04, blue P0.08), active low. Review m4: standard drive gives
// only about 1 to 1.9 mA, so they get high drive (H0H1). The heartbeat LED stays at standard drive.
const uint8_t kStatusLedPins[] = {PIN_LED1, NDI_PIN_LED_R, NDI_PIN_LED_B};
} // namespace

void initVariant()
{
#if defined(NDI_ENABLE_REG1_DCDC)
    // REG1 DC/DC: hardware is present (DCC -> L1 10 uH -> L2 15 nH -> DEC4/DEC6, VDDH = VDD = 3V3;
    // docs/review_revA0.md R-29). Stock Meshtastic never sets DCDCEN. The direct register write is valid
    // here because initVariant() runs before the SoftDevice is enabled. UNVERIFIED on hardware: confirm
    // against the nRF52840 product specification (POWER, DCDCEN) and with a first-board current and
    // brown-out check; build with -D NDI_ENABLE_REG1_DCDC=0 to run in LDO mode instead.
    NRF_POWER->DCDCEN = POWER_DCDCEN_DCDCEN_Enabled << POWER_DCDCEN_DCDCEN_Pos;
#endif

    // Safe boot states for every NDI-owned GPIO. Outputs get their latch written before they become
    // outputs, so no pin glitches. Heater veto starts low (no veto), ID_EN low (VLOGIC off on the pack
    // alone), FEM_EN low (amplifier and boost off until radio init), LEDs high (off, active low).
    for (const NdiPinInit &p : kPinInit) {
        switch (p.mode) {
        case NDI_INIT_INPUT:
            pinMode(p.pin, INPUT);
            break;
        case NDI_INIT_INPUT_PULLUP:
            pinMode(p.pin, INPUT_PULLUP);
            break;
        case NDI_INIT_OUTPUT_HIGH:
            digitalWrite(p.pin, HIGH);
            pinMode(p.pin, OUTPUT);
            break;
        case NDI_INIT_OUTPUT_LOW:
            digitalWrite(p.pin, LOW);
            pinMode(p.pin, OUTPUT);
            break;
        }
    }
}

void lateInitVariant()
{
    // pinMode(OUTPUT_H0H1) rewrites only PIN_CNF, so the LED level stock code set is kept.
    for (const uint8_t pin : kStatusLedPins) {
        pinMode(pin, OUTPUT_H0H1);
    }

    // VBAT, VS_USB, VS_AUX and the ID taps are 150 k to 10 M dividers: a 600 kohm source needs a long
    // SAADC acquisition time. The core default is 3 us. ASSUMED 40 us (the longest the core offers);
    // the nRF52840 product specification must confirm it (open item in ndi_1w/docs/OPEN-QUESTIONS.md).
    analogSampleTime(40);
}
