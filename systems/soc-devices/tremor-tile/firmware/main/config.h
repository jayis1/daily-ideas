/*
 * Tremor Tile — Configuration Header
 * config.h — All tunable parameters, pin definitions, and constants
 */

#ifndef TREMOR_TILE_CONFIG_H
#define TREMOR_TILE_CONFIG_H

#include "hardware/pwm.h"

// ============================================================
// Device Identity
// ============================================================
#define DEVICE_ID           0x0001
#define DEVICE_NAME         "TremorTile"
#define FW_VERSION          "1.0.0"

// ============================================================
// Pin Definitions (RP2040)
// ============================================================

// SPI0 — ADXL355
#define SPI0_MISO_PIN       0   // GPIO0 — ADXL355 DOUT
#define SPI0_CS_PIN         1   // GPIO1 — ADXL355 CS
#define SPI0_SCK_PIN        2   // GPIO2 — ADXL355 SCLK
#define SPI0_MOSI_PIN       3   // GPIO3 — ADXL355 DIN (unused)

// SPI1 — SX1262
#define SPI1_MISO_PIN       4   // GPIO4 — SX1262 MISO
#define SPI1_CS_PIN         5   // GPIO5 — SX1262 NSS
#define SPI1_SCK_PIN        6   // GPIO6 — SX1262 SCK
#define SPI1_MOSI_PIN       7   // GPIO7 — SX1262 MOSI

// ADXL355 control
#define ADXL355_DRDY_PIN    8   // GPIO8 — Data-ready interrupt
#define ADXL355_INT1_PIN    9   // GPIO9 — FIFO watermark/overrun
#define ADXL355_RANGE_PIN   27  // GPIO27 — Range select (0=±2g, 1=±4g)

// SX1262 control
#define SX1262_DIO1_PIN     10  // GPIO10 — LoRa interrupt
#define SX1262_RESET_PIN   11  // GPIO11 — LoRa reset (active low)
#define SX1262_BUSY_PIN    12  // GPIO12 — LoRa busy
#define SX1262_TCXO_EN_PIN 13  // GPIO13 — TCXO enable
#define SX1262_RF_SW_PIN   14  // GPIO14 — RF switch (TX/RX path)

// I2C0 — BME280 + DS3231
#define I2C0_SDA_PIN        15  // GPIO15
#define I2C0_SCL_PIN        16  // GPIO16

// Miscellaneous GPIO
#define STATUS_LED_PIN      17  // GPIO17 — SK6812MINI data
#define BUZZER_PIN          18  // GPIO18 — Piezo buzzer PWM
#define TAMPER_PIN          19  // GPIO19 — Reed switch (tamper detect)
#define BOOT_PIN             20  // GPIO20 — Boot button
#define SENSOR_RAIL_EN_PIN  21  // GPIO21 — Sensor power gate
#define BATTERY_ADC_PIN     22  // GPIO22 — Battery voltage divider
#define SOLAR_ADC_PIN       23  // GPIO23 — Solar panel voltage
#define FLASH_CS_PIN        24  // GPIO24 — W25Q128 CS (external)
#define BOARD_LED_PIN       25  // GPIO25 — Onboard LED (active low)
#define ADXL_TEMP_PIN       26  // GPIO26 — ADXL355 analog temp
#define DS3231_INT_PIN      28  // GPIO28 — DS3231 alarm interrupt

// ============================================================
// Sensor Configuration
// ============================================================

// ADXL355
#define ADXL355_ODR             400     // Output data rate (Hz): 4000, 2000, 1000, 400, 200, 100
#define ADXL355_RANGE_G         2       // ±2g (options: 2, 4, 8)
#define ADXL355_FIFO_WATERMARK  32      // Samples before watermark interrupt
#define ADXL355_SPI_FREQ        4000000 // 4 MHz SPI clock

// BME280
#define BME280_I2C_ADDR         0x77
#define BME280_OVERSAMPLE_TEMP   1       // 1x oversampling
#define BME280_OVERSAMPLE_PRESS  1
#define BME280_OVERSAMPLE_HUMID  1
#define BME280_MODE             1       // Forced mode (sleep between reads)
#define BME280_READ_INTERVAL_S  60      // Read every 60 seconds

// DS3231
#define DS3231_I2C_ADDR         0x68
#define DS3231_SQW_FREQ          1       // 1 Hz square wave output

// ============================================================
// FFT Configuration
// ============================================================
#define FFT_SIZE                1024    // Number of FFT points
#define FFT_OVERLAP             0.5     // 50% window overlap
#define FFT_WINDOW_TYPE         1       // 0=None, 1=Hann, 2=Hamming, 3=Blackman

// Frequency bands (Hz)
#define BAND_VERY_LOW_MIN       0.1
#define BAND_VERY_LOW_MAX       10.0
#define BAND_LOW_MIN             10.0
#define BAND_LOW_MAX             50.0
#define BAND_MID_MIN             50.0
#define BAND_MID_MAX             200.0
#define BAND_HIGH_MIN            200.0
#define BAND_HIGH_MAX            500.0
#define BAND_VERY_HIGH_MIN       500.0
#define BAND_VERY_HIGH_MAX       1500.0

#define NUM_FREQ_BANDS           5
#define NUM_PEAK_FREQUENCIES    5

// ============================================================
// Anomaly Detection
// ============================================================
#define ANOMALY_THRESHOLD_SIGMA  5.0f    // Default: 5σ above baseline
#define PEAK_SHIFT_THRESHOLD     0.20f   // 20% frequency shift triggers anomaly
#define NEW_PEAK_THRESHOLD_SIGMA 6.0f    // 6σ above noise floor for new peak
#define KURTOSIS_THRESHOLD_SIGMA 3.0f   // 3σ for impulsive event detection
#define RMS_THRESHOLD_SIGMA      4.0f   // 4σ for overall RMS increase

#define BASELINE_LEARNING_HOURS   24     // Hours to learn baseline
#define BASELINE_SAMPLES_PER_BIN  3600   // Samples per statistical bin
#define BASELINE_FLASH_OFFSET     0x100000  // Offset in W25Q128 for baseline data

// ============================================================
// LoRa Configuration
// ============================================================
#define LORA_FREQ_EU              868.0f   // MHz (EU ISM band)
#define LORA_FREQ_US              915.0f   // MHz (US ISM band)
#define LORA_FREQ                 LORA_FREQ_EU  // Default: EU

#define LORA_BW                   125000   // Bandwidth (Hz)
#define LORA_SF_NORMAL            7        // Spreading factor (normal)
#define LORA_SF_ALERT             12       // Spreading factor (alert — max range)
#define LORA_CR                   5        // Coding rate 4/5
#define LORA_TX_POWER             22       // +22 dBm
#define LORA_PREAMBLE             8        // Preamble length
#define LORA_CRC_ENABLED          true

#define HEARTBEAT_INTERVAL_S      3600    // 1 hour
#define HEARTBEAT_INTERVAL_US     (HEARTBEAT_INTERVAL_S * 1000000ULL)
#define SPECTRAL_SUMMARY_INTERVAL_S 900  // 15 minutes
#define RAW_LOG_INTERVAL           10    // Log every 10th batch

// Packet sizes (bytes)
#define PKT_HEARTBEAT_SIZE        12
#define PKT_SPECTRAL_SIZE         48
#define PKT_ALERT_SIZE            32
#define PKT_RAW_DATA_SIZE         256

// ============================================================
// Power Management
// ============================================================
#define BATTERY_FULL_MV           3600    // LiFePO4 fully charged
#define BATTERY_EMPTY_MV          2500    // LiFePO4 cutoff
#define BATTERY_CAPACITY_MAH      1000   // 1000 mAh
#define SOLAR_CHARGE_CURRENT_MA   50     // Average indoor solar
#define LOW_POWER_SAMPLE_RATE_HZ  100    // Low power mode: 100 Hz
#define ACTIVE_SAMPLE_RATE_HZ     400    // Active mode: 400 Hz
#define DEEP_SLEEP_CURRENT_UA     25     // Estimated deep sleep current
#define MONITOR_AVG_CURRENT_UA    100    // Monitor mode average

// ============================================================
// Data Logging
// ============================================================
#define FLASH_LOG_OFFSET          0x100000  // 1MB offset in W25Q128
#define FLASH_LOG_SIZE            0x700000  // 7MB for logs
#define FLASH_BASELINE_OFFSET     0x800000  // 8MB offset for baseline data
#define FLASH_BASELINE_SIZE       0x100000  // 1MB for baseline

// ============================================================
// Alert Types
// ============================================================
#define ALERT_NEW_PEAK            1
#define ALERT_PEAK_SHIFT          2
#define ALERT_BAND_ENERGY         3
#define ALERT_RMS_INCREASE        4
#define ALERT_KURTOSIS            5
#define ALERT_TAMPER              6
#define ALERT_TEMPERATURE         7

// ============================================================
// Status LED Patterns
// ============================================================
#define LED_OFF          0
#define LED_STARTUP      1
#define LED_MONITORING   2
#define LED_ALERT        3
#define LED_WARNING      4
#define LED_LEARNING     5
#define LED_CHARGING     6

// ============================================================
// Buzzer Patterns
// ============================================================
#define ALERT_PATTERN     1  // 3 short beeps
#define TAMPER_PATTERN    2  // Continuous tone
#define CALIBRATE_PATTERN 3  // 1 long beep
#define HEARTBEAT_BEEP    4  // 1 short beep

#endif // TREMOR_TILE_CONFIG_H