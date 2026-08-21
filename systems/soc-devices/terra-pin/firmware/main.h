/**
 * terra_pin/main.h — Terra Pin Soil Microbiome Activity Probe
 *
 * ESP32-S3-WROOM-1 main firmware header.
 * FreeRTOS tasks:
 *   flux_task      — SCD41 chamber CO2 rise rate → respiration
 *   ambient_task   — SCD41 ambient CO2 baseline
 *   orp_task       — EZO-ORP redox potential (mV)
 *   ec_task        — EZO-EC conductivity (µS/cm)
 *   moisture_task  — capacitive VWC via PCNT frequency
 *   temp_task      — DS18B20 soil temperature
 *   shi_task       — Soil Health Index fusion (0–100)
 *   display_task   — SH1106 OLED UI
 *   sdlog_task     — FAT32 CSV logging
 *   ble_task       — BLE GATT notifications
 *   button_task    — button + encoder polling
 */

#ifndef TERRA_PIN_MAIN_H
#define TERRA_PIN_MAIN_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* ── Pin assignments (ESP32-S3-WROOM-1) ──────────────────────────── */

#define PIN_UART_ORP_TX     1    /* GPIO1  → EZO-ORP RX  */
#define PIN_UART_ORP_RX     2    /* GPIO2  ← EZO-ORP TX  */
#define PIN_SCD41_RESET     3    /* GPIO3  → SCD41 reset */
#define PIN_UART_EC_TX      4    /* GPIO4  → EZO-EC RX   */
#define PIN_UART_EC_RX      5    /* GPIO5  ← EZO-EC TX   */
#define PIN_I2C_SCL         6    /* GPIO6  I2C SCL       */
#define PIN_I2C_SDA         7    /* GPIO7  I2C SDA       */
#define PIN_SD_CS           8    /* GPIO8  SD CS          */
#define PIN_SPI_MISO        9    /* GPIO9  SD MISO        */
#define PIN_SPI_MOSI        10   /* GPIO10 SD MOSI        */
#define PIN_SPI_SCK         11   /* GPIO11 SD SCK         */
#define PIN_ONEWIRE         12   /* GPIO12 DS18B20        */
#define PIN_MOIST_FREQ      13   /* GPIO13 PCNT input     */
#define PIN_BTN_MEASURE     14   /* GPIO14 button         */
#define PIN_BTN_MODE        15   /* GPIO15 button         */
#define PIN_ENC_A           16   /* GPIO16 encoder A      */
#define PIN_ENC_B           17   /* GPIO17 encoder B      */
#define PIN_ENC_BTN         18   /* GPIO18 encoder push   */
#define PIN_WS2812          19   /* GPIO19 RGB LED        */
#define PIN_LED_STATUS      20   /* GPIO20 status LED     */
#define PIN_CHG_STAT        21   /* GPIO21 charger status */
#define PIN_BATT_DIV        22   /* GPIO22 ADC battery    */

/* ── I2C addresses ────────────────────────────────────────────────── */

#define SCD41_I2C_ADDR      0x62
#define TCA9548A_I2C_ADDR   0x70
#define SH1106_I2C_ADDR     0x3C

#define TCA9548A_CH_CHAMBER 0x01   /* SCD41 #1 in probe tip  */
#define TCA9548A_CH_AMBIENT 0x02   /* SCD41 #2 in handle     */
#define TCA9548A_CH_OLED    0x04   /* passthrough to OLED    */

/* ── UART config ──────────────────────────────────────────────────── */

#define UART_ORP_NUM        UART_NUM_1
#define UART_EC_NUM         UART_NUM_2
#define EZO_BAUD            9600
#define EZO_TIMEOUT_MS      300

/* ── Measurement parameters ───────────────────────────────────────── */

#define FLUX_MEASURE_SEC    60     /* CO2 rise measurement duration   */
#define FLUX_SAMPLE_HZ      1      /* SCD41 single-shot interval = 5s */
#define CHAMBER_VOL_ML      15.0f  /* chamber volume in mL            */
#define CHAMBER_AREA_CM2    2.54f  /* membrane area cm²               */
#define AMBIENT_UPDATE_MS   10000  /* ambient CO2 every 10 s          */

/* ── Soil Health Index model ──────────────────────────────────────── */

#define SHI_WEIGHT_RESP     0.30f
#define SHI_WEIGHT_REDOX    0.25f
#define SHI_WEIGHT_EC       0.20f
#define SHI_WEIGHT_MOIST    0.15f
#define SHI_WEIGHT_TEMP     0.10f

/* Optimal ranges for sub-score bell curves */
#define RESP_OPT_MIN    15.0f   /* mg C m⁻² h⁻¹ */
#define RESP_OPT_MAX    60.0f
#define RESP_OPT_PEAK   30.0f

#define REDOX_GOOD_MIN  300.0f  /* mV */
#define REDOX_GOOD_MAX  550.0f
#define REDOX_RAMP_LOW  100.0f

#define EC_OPT_MIN      100.0f  /* µS/cm */
#define EC_OPT_MAX      1500.0f
#define EC_OPT_PEAK     600.0f

#define MOIST_OPT_MIN   25.0f   /* VWC % */
#define MOIST_OPT_MAX   45.0f
#define MOIST_OPT_PEAK  35.0f

#define TEMP_OPT_MIN    15.0f   /* °C */
#define TEMP_OPT_MAX    25.0f
#define TEMP_OPT_PEAK   20.0f

/* Q10 temperature correction for respiration */
#define Q10_FACTOR      2.0f
#define Q10_REF_TEMP    20.0f

/* ── Operating modes ──────────────────────────────────────────────── */

typedef enum {
    MODE_POINT = 0,       /* single measurement on button press */
    MODE_CONTINUOUS,      /* continuous logging                 */
    MODE_CALIBRATE,       /* calibration mode                   */
} terra_mode_t;

/* ── Measurement data structure ───────────────────────────────────── */

typedef struct {
    /* Raw sensor values */
    uint16_t co2_chamber;      /* ppm                */
    uint16_t co2_ambient;      /* ppm                */
    float    flux_ppm_min;     /* CO2 rise rate      */
    float    flux_mgC;         /* mg C m⁻² h⁻¹      */
    int16_t  orp_mv;           /* redox mV           */
    uint16_t ec_us;            /* µS/cm              */
    float    moisture_vwc;     /* VWC %              */
    float    temp_c;           /* soil temp °C       */
    float    pressure_hpa;     /* from SCD41         */
    float    humidity_pct;     /* from SCD41         */

    /* Sub-scores (0.0–1.0) */
    float    shi_resp;
    float    shi_redox;
    float    shi_ec;
    float    shi_moist;
    float    shi_temp;

    /* Final index */
    uint8_t  shi;              /* 0–100              */

    /* Metadata */
    uint32_t timestamp;        /* Unix epoch         */
    uint8_t  mode;             /* terra_mode_t       */
    bool     valid;
} terra_reading_t;

/* ── Global handles ───────────────────────────────────────────────── */

extern QueueHandle_t g_reading_queue;      /* shi_task → sdlog/ble   */
extern SemaphoreHandle_t g_i2c_mutex;      /* I2C bus protection      */
extern volatile terra_mode_t g_mode;
extern volatile bool g_measure_trigger;

/* ── Function prototypes ──────────────────────────────────────────── */

/* Sensor drivers */
esp_err_t scd41_init(void);
esp_err_t scd41_select_channel(uint8_t ch);
esp_err_t scd41_measure_chamber(uint16_t *co2, float *temp, float *rh);
esp_err_t scd41_measure_ambient(uint16_t *co2, float *temp, float *rh);
esp_err_t scd41_start_periodic_chamber(void);
esp_err_t scd41_stop_periodic_chamber(void);

esp_err_t ezo_orp_init(void);
esp_err_t ezo_orp_read(int16_t *orp_mv);

esp_err_t ezo_ec_init(void);
esp_err_t ezo_ec_read(uint16_t *ec_us, float *temp_comp);

esp_err_t ds18b20_init(void);
esp_err_t ds18b20_read(float *temp_c);

esp_err_t moisture_init(void);
esp_err_t moisture_read(float *vwc);
esp_err_t moisture_calibrate(float freq_dry, float freq_wet);

/* SHI computation */
void shi_compute(terra_reading_t *r);

/* Display */
esp_err_t sh1106_init(void);
void sh1106_update(const terra_reading_t *r, uint8_t battery_pct, terra_mode_t mode);

/* SD logging */
esp_err_t sdlog_init(void);
esp_err_t sdlog_write(const terra_reading_t *r, uint32_t session_id);

/* BLE */
esp_err_t ble_init(void);
void ble_notify_reading(const terra_reading_t *r);

/* RGB LED */
void rgb_set_color(uint8_t shi);

/* Battery */
uint8_t battery_read_pct(void);

/* Utility */
uint64_t rtc_get_unix_time(void);
void rtc_sync_from_compile(void);

#endif /* TERRA_PIN_MAIN_H */