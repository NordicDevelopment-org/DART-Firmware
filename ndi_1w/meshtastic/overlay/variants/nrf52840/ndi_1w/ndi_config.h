/*
  NDI 1 W LoRa radio, Rev A0: hand-written variant settings (everything that is not a pin number).
  Included at the end of the generated variant.h. Pin numbers live in ndi_1w/pin_table/pin_table.csv.

  Every value says where it comes from. ASSUMED means no document gives the number yet.
  The source index is ndi_1w/docs/SOURCES.md; behaviour changes are logged in
  ndi_1w/docs/CHANGELOG-BEHAVIOUR.md.
*/

#ifndef NDI_CONFIG_H
#define NDI_CONFIG_H

/* ---- 1. Guards ---------------------------------------------------------------------------
 * Stock RAK and upstream macros that would drive NDI nets or report the wrong hardware.
 * Generated from ndi_1w/meshtastic/forbidden_macros.txt.
 */
#include "ndi_forbidden_guard.h"

/* ---- 2. Identity and UICR ----------------------------------------------------------------
 * PRIVATE_HW (hardware model 255) is set in platformio.ini, as upstream asks for custom boards.
 * P0.09 (user button) and P0.10 (amplifier supply mode) are NFC pins; P0.18 is nRESET (SW1,
 * JP4, J12 pin 3, supervisor). Stock sources write neither UICR word, so the build flags do.
 */
#ifndef PRIVATE_HW
#error "NDI 1 W builds must define PRIVATE_HW (platformio.ini build_flags)"
#endif
#ifndef CONFIG_NFCT_PINS_AS_GPIOS
#error "P0.09 and P0.10 are NFC pins: build with -D CONFIG_NFCT_PINS_AS_GPIOS=1"
#endif
#ifndef CONFIG_GPIO_AS_PINRESET
#error "P0.18 is the reset pin: build with -D CONFIG_GPIO_AS_PINRESET=1"
#endif

/* ---- 3. LEDs -------------------------------------------------------------------------------
 * Status RGB and heartbeat are active low (anodes on the DIP-switched 3V3_LED rail).
 * PIN_LED1 (green, P1.03) is generated. LED_NOTIFICATION is deliberately not defined until HL
 * chooses which die it is. NDI_PIN_LED_R, NDI_PIN_LED_B and NDI_PIN_LED_HB are generated too.
 */
#define LED_STATE_ON 0

/* ---- 4. LoRa: SX1262 with SKY66122-11 (RAK13302 topology) --------------------------------
 * Pins (CS, BUSY, DIO1, RESET, POWER_EN) are generated. P1.05 SX126X_POWER_EN enables the
 * TPS61033-Q1 boost and the SKY66122-11 CSD and CPS; stock code holds it high from radio init
 * until sleep(), which is what keeps the amplifier LNA alive in receive.
 */
#define USE_SX1262
/* DIO2 drives SKY66122-11 CTX (netlist U3 pin 2 via R138): the RF switch. */
#define SX126X_DIO2_AS_RF_SWITCH
/* TCXO Y3 is powered from DIO3. Supply must be programmed to the FITTED part:
 *  - ECS-TXO-20CSMV4-320-AP-TR (the designed part, 1.7 to 3.6 V): 1.8 V works with only 0.1 V margin
 *    over its minimum (docs/review_revA0.md R-30; the 1.8 V is the RAK4631 profile, unverified).
 *  - Epson TG2016SMN (stocked at JLC, 2.8 to 3.3 V): needs 3.0 V; 1.8 V cannot power it
 *    (docs/first_build_substitutions.md). The SX1262 needs VBAT_SX >= VTCXO + 0.2 V (Semtech DS Table 2-1).
 * OPEN QUESTION for HL: which TCXO is fitted on the first boards. Default below is the designed part.
 */
#ifndef NDI_TCXO_VOLTAGE
#define NDI_TCXO_VOLTAGE 1.8
#endif
#define SX126X_DIO3_TCXO_VOLTAGE NDI_TCXO_VOLTAGE

/* ---- 5. TX power cap ---------------------------------------------------------------------
 * INTERIM, ASSUMED: the amplifier gain table is not measured. SX126X_MAX_POWER is a SETTING AT THE
 * SX1262 in dBm, not power at the connector. It is the only clamp stock Meshtastic applies on both
 * the init path and every later reconfigure (a TX_GAIN_LORA table applies at init only), so it is
 * the cap. The value is HL's "all recommended" answer of 2026-11-12 to question 3. The RAK13302
 * table in HL's research doc (10 dBm setting gives about +18 dBm out; RAK figure, not labelled
 * conducted) is a plausibility hint only, not a specification of this board.
 * Raising it needs a measured gain table and an explicit define after the measurement.
 * A 30 percent duty cap (Skyworks tested 30 percent at +30 dBm only) is NDI code, not in this header.
 */
#define NDI_TX_INTERIM_CAP_SETTING_DBM 10
#ifndef NDI_TX_MAX_SETTING_DBM
#define NDI_TX_MAX_SETTING_DBM NDI_TX_INTERIM_CAP_SETTING_DBM
#endif
#if (NDI_TX_MAX_SETTING_DBM > NDI_TX_INTERIM_CAP_SETTING_DBM) && !defined(NDI_TX_CAP_RAISED_AFTER_MEASUREMENT)
#error "TX setting above the interim cap needs NDI_TX_CAP_RAISED_AFTER_MEASUREMENT (gain table not measured yet)"
#endif
#if (NDI_TX_MAX_SETTING_DBM > 22) || (NDI_TX_MAX_SETTING_DBM < -9)
#error "NDI_TX_MAX_SETTING_DBM is outside the SX1262 range (-9 to +22 dBm)"
#endif
#define SX126X_MAX_POWER NDI_TX_MAX_SETTING_DBM

/* ---- 6. Battery and USB ------------------------------------------------------------------
 * P0.05 (A0, BATTERY_PIN) reads VBAT through R91 1.00 M / R92 1.50 M behind U85 (TMUX1511), so the
 * pin sees 0.6 x VBAT and the multiplier is 1 / 0.6 = 1.66667 (DERIVED from the netlist values;
 * RAK4631's 1.73 reads about 3.8 percent high). Calibrate on the first board.
 * RAK's AREF_VOLTAGE 3.0 / VBAT_AR_INTERNAL are NOT used: stock defaults (3.6 V full scale) keep
 * the 24 V VS_USB tap on scale (forbidden_macros.txt). The 600 kohm source resistance needs a long
 * SAADC acquisition time: lateInitVariant() sets it (ASSUMED 40 us, see variant.cpp and SOURCES.md).
 */
#define BATTERY_SENSE_RESOLUTION_BITS 12
#define BATTERY_SENSE_RESOLUTION 4096.0
#define ADC_MULTIPLIER 1.66667

/* VBUS detect: USB VBUS reaches the nRF52840 through R120 from V5_NRF (any attached USB-C source).
 * NRF_APM makes stock code treat that as 'USB connected'. Pads and pack-full are NOT seen by it;
 * NDI board support (M2) reports the live source.
 */
#define NRF_APM

/* ---- 7. GNSS ----------------------------------------------------------------------------
 * MAX-M10S behind load switch U6 (TPS22918-Q1, active high, 100 k pull-down: off by default).
 * PIN_GPS_EN (P1.02), PIN_GPS_PPS, GPS_RX_PIN and GPS_TX_PIN are generated (the GPS_* names are the
 * MCU side: RX = P0.15 is the module TXD net). Stock GPS code owns P1.02.
 */
#define GPS_EN_ACTIVE 1

/* ---- 8. NDI board support (see variant.cpp) ---------------------------------------------
 * NDI_ENABLE_REG1_DCDC and NDI_I2C_SKIP_CHARGER_IMU come from platformio.ini build flags.
 */

#endif /* NDI_CONFIG_H */
