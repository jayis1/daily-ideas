/* sdkconfig.h — Plume Sniffer project configuration (ESP32-C3, ESP-IDF v5.1+)
 *
 * These are the key configuration values. In a real ESP-IDF project these
 * would be set via `idf.py menuconfig` and stored in sdkconfig. This header
 * captures the important ones so the source compiles in a standalone context.
 */

#pragma once

/* ---- Target ---- */
#define CONFIG_IDF_TARGET_ESP32C3          1
#define CONFIG_IDF_TARGET                  "esp32c3"

/* ---- Clock ---- */
#define CONFIG_ESP_CPU_FREQ_MHZ            160

/* ---- Flash / Partition ---- */
#define CONFIG_ESPTOOLPY_FLASHSIZE_4MB     1
#define CONFIG_ESPTOOLPY_FLASHSIZE         "4MB"
#define CONFIG_PARTITION_TABLE_SINGLE_APP  1

/* ---- FreeRTOS ---- */
#define CONFIG_FREERTOS_HZ                 1000
#define CONFIG_FREERTOS_ENABLE_TASK_SNAPSHOT 1

/* ---- SPI ---- */
#define CONFIG_SPI_MASTER_IN_IRAM          1

/* ---- BLE ---- */
#define CONFIG_BT_ENABLED                  1
#define CONFIG_BT_BLE_ENABLED              1
#define CONFIG_BT_NIMBLE_ENABLED           1
#define CONFIG_BT_NIMBLE_ROLE_PERIPHERAL   1

/* ---- Wi-Fi (optional) ---- */
#define CONFIG_ESP_WIFI_ENABLED            1

/* ---- NVS ---- */
#define CONFIG_NVS_ENCRYPTION              0

/* ---- Logging ---- */
#define CONFIG_LOG_DEFAULT_LEVEL_INFO      1
#define CONFIG_LOG_MAXIMUM_LEVEL           5

/* ---- Application-specific ---- */
#define PLUME_TCD_SAMPLE_HZ                50    /* ADS122U04 data rate */
#define PLUME_TCD_SAMPLES_PER_RUN          12000 /* 4 min @ 50 Hz */
#define PLUME_COLUMN_RAMP_DEFAULT_CPM      10    /* °C/min */
#define PLUME_COLUMN_T_MAX                 180   /* °C */
#define PLUME_PRECONC_DESORB_TEMP          220   /* °C */
#define PLUME_PRECONC_DESORB_TIME_S        3
#define PLUME_SAMPLE_VOLUME_DEFAULT_ML     250
#define PLUME_PUMP_FLOW_ML_MIN             30
#define PLUME_BATTERY_MIN_MV               3500  /* gate RUN on this */
#define PLUME_HEATER_WATCHDOG_TEMP_C       220   /* cutoff */
#define PLUME_PEAK_DERIV_THRESHOLD_SIGMA   3.0f
#define PLUME_LIBRARY_MAX_ENTRIES          40
#define PLUME_LIBRARY_MAX_NAME_LEN         24