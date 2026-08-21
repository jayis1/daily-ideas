/*
 * config.h — Vibra Beam build & runtime configuration
 * STM32G474RET6
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>

/* ── MCU / build ─────────────────────────────────────────── */
#define CONFIG_MCU_STM32G474
#define CONFIG_CPU_FREQ_HZ        170000000U
#define CONFIG_FLASH_SIZE_BYTES    (512 * 1024)
#define CONFIG_SRAM_SIZE_BYTES     (96 * 1024)

/* ── Laser ──────────────────────────────────────────────── */
#define CONFIG_LASER_WAVELENGTH_NM    650.0f
#define CONFIG_LASER_DEFAULT_MW       1.0f    /* Class 2 default */
#define CONFIG_LASER_MAX_MW           5.0f    /* Class 3R limit */
#define CONFIG_LASER_PWM_HZ           1000.0f
#define CONFIG_LASER_EN_PORT          GPIOA
#define CONFIG_LASER_EN_PIN           GPIO_PIN_5
#define CONFIG_LASER_PWM_PORT         GPIOA
#define CONFIG_LASER_PWM_PIN          GPIO_PIN_4   /* DAC1_OUT1 */

/* ── ADC / I-Q sampling ──────────────────────────────────── */
#define CONFIG_ADC_SAMPLE_RATE_HZ     2500000U
#define CONFIG_ADC_BLOCK_SAMPLES      512
#define CONFIG_ADC_OVERSAMPLE         8
#define CONFIG_ADC_VREF_MV            3300.0f
#define CONFIG_ADC_BITS               12

/* ── Interferometer / phase ──────────────────────────────── */
#define CONFIG_LAMBDA_NM              650.0f
#define CONFIG_FRANGE_NM             (CONFIG_LAMBDA_NM / 2.0f)   /* 325 nm per 2π */
#define CONFIG_PHASE_WRAP_2PI         6.28318530717958647692f
#define CONFIG_UNWRAP_MAX_JUMP_RAD    4.0f   /* >π ⇒ jump */
#define CONFIG_BASELINE_TAU_MS        200.0f

/* ── Velocity / DSP ──────────────────────────────────────── */
#define CONFIG_VEL_LP_FC_DEFAULT_HZ   100000.0f
#define CONFIG_VEL_LP_FC_MIN_HZ       10.0f
#define CONFIG_VEL_LP_FC_MAX_HZ       100000.0f
#define CONFIG_FFT_SIZE_LOG2          12
#define CONFIG_FFT_SIZE               (1 << CONFIG_FFT_SIZE_LOG2)   /* 4096 */
#define CONFIG_FFT_WINDOW_HANN        1

/* ── IMU (self-motion compensation) ─────────────────────── */
#define CONFIG_IMU_SAMPLE_RATE_HZ     1000U
#define CONFIG_IMU_COMPENSATE_FC_HZ   20.0f   /* compensate device sway < 20 Hz */
#define CONFIG_IMU_I2C_ADDR           0x69

/* ── Audio (heterodyne-to-audio) ─────────────────────────── */
#define CONFIG_AUDIO_SAMPLE_RATE_HZ   44100U
#define CONFIG_AUDIO_GAIN_DEFAULT     100.0f
#define CONFIG_AUDIO_SHIFT_DEFAULT    1.0f

/* ── Temperature / sensors ───────────────────────────────── */
#define CONFIG_DS18B20_GPIO_PORT      GPIOC
#define CONFIG_DS18B20_GPIO_PIN       GPIO_PIN_8
#define CONFIG_BME280_I2C_ADDR        0x76

/* ── OLED ────────────────────────────────────────────────── */
#define CONFIG_OLED_I2C_ADDR          0x3C
#define CONFIG_OLED_WIDTH             128
#define CONFIG_OLED_HEIGHT            64

/* ── SD logging ──────────────────────────────────────────── */
#define CONFIG_SD_LOG_CSV_HZ          25000U  /* max CSV rate */
#define CONFIG_SD_LOG_BIN_HZ          2500000U
#define CONFIG_SD_LOG_CSV             1
#define CONFIG_SD_LOG_BIN             1

/* ── BLE bridge ──────────────────────────────────────────── */
#define CONFIG_BLE_UART_BAUD          115200U
#define CONFIG_BLE_MTU                244

/* ── Power ──────────────────────────────────────────────── */
#define CONFIG_BATTERY_MV_MIN         3300
#define CONFIG_BATTERY_MV_FULL         4200
#define CONFIG_BATTERY_MAH            1500

/* ── Safety ──────────────────────────────────────────────── */
#define CONFIG_SAFETY_TILT_MAX_DEG    45.0f
#define CONFIG_SAFETY_WATCHDOG_MS     1000U

#endif /* CONFIG_H */