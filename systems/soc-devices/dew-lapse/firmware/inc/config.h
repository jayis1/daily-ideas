/* config.h — Frost Point application configuration
 * Flat config header (no Kconfig dependency).
 */
#ifndef FROST_POINT_CONFIG_H
#define FROST_POINT_CONFIG_H

/* ---- Firmware version ---- */
#define FW_VERSION_MAJOR  1
#define FW_VERSION_MINOR  0
#define FW_VERSION_PATCH  0

/* ---- Clock tree ---- */
#define HSE_VALUE          8000000UL
#define LSE_VALUE          32768UL
#define SYSCLK_FREQ        80000000UL
#define APB1_FREQ          80000000UL   /* L4: PPRE1 = 1 */
#define APB2_FREQ          80000000UL

/* ---- I2C buses ---- */
#define I2C1_TIMEOUT_MS   100
#define I2C3_TIMEOUT_MS   100
#define ADC_I2C_ADDR       (0x40 << 1)   /* ADS122U04 address (GND = 0x40) */
#define OLED_I2C_ADDR       (0x3C << 1)
#define BME280_I2C_ADDR     (0x76 << 1)
#define SCD41_I2C_ADDR      (0x62 << 1)
#define SHT45_I2C_ADDR      (0x44 << 1)

/* ---- TEC drive ---- */
#define TEC_PWM_HZ         20000
#define TEC_PWM_MAX        1000          /* timer ARR */
#define TEC_CURRENT_LIMIT_A   3.5f      /* A */
#define TEC_HOT_LIMIT_C       70.0f
#define TEC_DEFROST_C         45.0f
#define TEC_DEFROST_S         2

/* ---- ADS122U04 ---- */
#define ADC_SPS             20
#define ADC_PGA_GAIN        8

/* ---- Mirror thermistor ---- */
#define NTC_R_REF          100000.0f     /* 100k at 25 C */
#define NTC_B              3950.0f
#define NTC_REF_RES        100000.0f     /* precision reference resistor */
#define NTC_PULLUP_V       3.3f
#define NTC_FAULT_OHM_HI   150000.0f
#define NTC_FAULT_OHM_LO   10000.0f

/* ---- Optics / chopper ---- */
#define IR_CHOP_HZ         38000
#define IR_CHOP_SAMPLES    50            /* per 38 kHz burst */
#define IR_DEMOD_LEN       50            /* demodulator buffer */

/* ---- PID ---- */
#define PID_KP             120.0f
#define PID_KI             4.0f
#define PID_KD             1800.0f
#define PID_OUT_MIN        -0.9f         /* fraction of TEC_PWM_MAX */
#define PID_OUT_MAX         0.9f
#define FILM_SETPOINT_K    0.10f         /* target |T_m - T_r| */
#define TRACK_STABLE_DT    0.005f        /* K/s */
#define TRACK_STABLE_COUNT 10

/* ---- Logging ---- */
#define LOG_FLASH_ADDR     0x000000
#define LOG_FLASH_SIZE     0x1000000    /* 16 MB */
#define LOG_RATE_HZ        1

/* ---- BLE ---- */
#define BLE_UART_BAUD      115200

/* ---- Safety ---- */
#define HOT_RISE_LIMIT_KS  2.0f          /* cut TEC if hot T rises > this */
#define WATCHDOG_MS       2000

#endif /* FROST_POINT_CONFIG_H */