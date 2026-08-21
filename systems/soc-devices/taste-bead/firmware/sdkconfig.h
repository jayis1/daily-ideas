/* sdkconfig.h — build-time configuration for Taste Bead
 *
 * Pocket electronic tongue — 5-electrode EIS liquid fingerprinter
 * ESP32-S3 + AD5941 analog front-end
 */

#ifndef TASTE_BEAD_SDKCONFIG_H
#define TASTE_BEAD_SDKCONFIG_H

/* ---- EIS Measurement ---- */
#define NUM_ELECTRODES           5    /* Au, Pt, Ag/AgCl, GC, Cu */
#define NUM_FREQS                20   /* log-spaced from 1 Hz to 100 kHz */
#define FREQ_MIN_HZ              1.0f
#define FREQ_MAX_HZ              100000.0f
#define EIS_EXCITION_AMPLITUDE   100.0f   /* mV peak (100mV = safe for samples) */
#define EIS_SETTLING_CYCLES      3        /* cycles to wait before measuring */

/* Frequency table (log-spaced): 1, 1.5, 2.3, 3.4, 5.1, 7.7, 12, 17, 26, 39,
 *                                  59, 88, 132, 199, 299, 449, 674, 1012,
 *                                  1519, 2281, 3426, 5147, 7732, 11610,
 *                                  17425, 26156, 39269, 58945, 88481,
 *                                  132864 Hz → truncated to 20 points */
#define FREQ_TABLE \
    {1.0f, 2.15f, 4.64f, 10.0f, 21.5f, 46.4f, 100.0f, 215.0f, 464.0f, \
     1000.0f, 2150.0f, 4640.0f, 10000.0f, 21500.0f, 46400.0f, 100000.0f, \
     1.47f, 3.16f, 6.81f, 14.68f}

/* ---- Classification ---- */
#define NUM_FEATURES            48    /* features per measurement */
#define LIBRARY_MAX_ENTRIES     50    /* max reference liquids in flash */
#define KNN_K                   5     /* k-NN k value */
#define CONFIDENCE_THRESHOLD    70    /* minimum % confidence to report */

/* ---- Pin assignments (ESP32-S3-WROOM-1) ---- */
#define PIN_I2C_SDA             0
#define PIN_I2C_SCL             1
#define PIN_SPI_CS_AD5941        2
#define PIN_SPI_SCK              3
#define PIN_SPI_MISO             4
#define PIN_SPI_MOSI             5
#define PIN_AD5941_IRQ           6
#define PIN_AD5941_RESET         7
#define PIN_MUX_EN               8
#define PIN_MUX_S0               9
#define PIN_MUX_S1               10
#define PIN_MUX_S2               11
#define PIN_SD_CS                12
#define PIN_SD_SCK               13
#define PIN_SD_MOSI              14
#define PIN_SD_MISO              15
#define PIN_BTN_ID               16
#define PIN_BTN_MODE             17
#define PIN_BTN_LIB              18
#define PIN_LED_R                19
#define PIN_LED_G                20
#define PIN_LED_B                21
#define PIN_ADC_BATT             38
#define PIN_CHRG_STATUS          39
#define PIN_SD_CARD_DETECT       42

/* ---- I2C addresses ---- */
#define BME280_I2C_ADDR         0x76
#define SSD1306_I2C_ADDR        0x3C

/* ---- SPI buses ---- */
#define SPI_AD5941_HOST         SPI2_HOST
#define SPI_AD5941_FREQ_HZ      16000000   /* 16 MHz */
#define SPI_SD_HOST             SPI3_HOST
#define SPI_SD_FREQ_HZ           8000000    /* 8 MHz */

/* ---- Measurement timing ---- */
#define MEASUREMENT_TIMEOUT_MS  30000   /* per full sweep */
#define MONITOR_INTERVAL_MS     10000   /* monitor mode sweep interval */

/* ---- Library / NVS ---- */
#define LIBRARY_NVS_NAMESPACE   "taste_bead"
#define LIBRARY_NVS_KEY         "library"
#define LIBRARY_MAX_NAME_LEN    32

/* ---- SD logging ---- */
#define SD_MAX_FILE_SIZE_MB     50
#define SD_BUFFER_SIZE          4096

/* ---- BLE protocol ---- */
#define BLE_SERVICE_UUID        "0000f00d-0000-1000-8000-00805f9b34fb"
#define BLE_CHAR_RESULT_UUID    "0000f001-0000-1000-8000-00805f9b34fb"
#define BLE_CHAR_SPECTRUM_UUID  "0000f002-0000-1000-8000-00805f9b34fb"
#define BLE_CHAR_COMMAND_UUID   "0000f003-0000-1000-8000-00805f9b34fb"
#define BLE_CHAR_LIBRARY_UUID   "0000f004-0000-1000-8000-00805f9b34fb"
#define BLE_CHAR_STATUS_UUID    "0000f005-0000-1000-8000-00805f9b34fb"

#define BLE_MSG_RESULT          0x01
#define BLE_MSG_SPECTRUM        0x02
#define BLE_MSG_COMMAND         0x03
#define BLE_MSG_LIBRARY_ENTRY   0x04
#define BLE_MSG_STATUS          0x05
#define BLE_MSG_ACK             0x06

/* ---- Calibration ---- */
#define CAL_OPEN                0
#define CAL_SHORT               1
#define CAL_KCL_001M            2  /* 0.01M KCl = 1413 µS/cm at 25°C */

#endif /* TASTE_BEAD_SDKCONFIG_H */