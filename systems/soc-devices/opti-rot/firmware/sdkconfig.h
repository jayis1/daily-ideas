/*
 * sdkconfig.h — Build configuration for Opti Rot
 * Opti Rot — Pocket Digital Polarimeter
 * STM32G491RET6 + ESP32-C3
 *
 * Target: STM32G491RET6 (Cortex-M4F @ 170 MHz, 128 KB flash, 32 KB SRAM)
 * Companion: ESP32-C3-MINI-1 (RISC-V, BLE 5.0 + Wi-Fi)
 */
#ifndef SDKCONFIG_H
#define SDKCONFIG_H

/* ======== Hardware Configuration ======== */
#define MCU_CLOCK_HZ            170000000
#define PATH_LENGTH_DM          1.0          /* 100 mm = 1 decimeter */
#define REFERENCE_TEMP_C        20.0         /* Specific rotation reference temp */

/* ======== Optical Configuration ======== */
#define NUM_WAVELENGTHS         3
#define WAVELENGTH_405_NM       405.0
#define WAVELENGTH_520_NM       520.0
#define WAVELENGTH_589_NM       589.0
#define DEFAULT_WAVELENGTH_IDX  2             /* 589 nm */

#define LED_INTENSITY_DAC       2048          /* 12-bit DAC midpoint (~1.65V) */

/* ======== Stepper Motor (28BYJ-48 via ULN2003) ======== */
#define STEPPER_STEPS_PER_REV   4096          /* half-step, 64:1 gearbox */
#define STEPPER_STEP_ANGLE      (360.0 / 4096.0)  /* 0.08789° per step */
#define STEPPER_STEP_DELAY_US   1200          /* half-step interval */
#define STEPPER_SWEEP_STEPS     2048          /* ±90° sweep range in steps (half revolution) */
#define STEPPER_NULL_SEARCH_STEPS 64         /* angular samples per null fit */

/* ======== Photodiode (TSL257 via ADC) ======== */
#define PHOTODIODE_ADC_CHANNEL   ADC_CHANNEL_2
#define PHOTODIODE_OVERSAMPLE_N  100          /* samples to average per point */
#define PHOTODIODE_SAMPLE_HZ     1000
#define ADC_VREF_V              3.3
#define ADC_RESOLUTION_BITS     12

/* ======== Malus's Law Curve Fitting ======== */
#define MALUS_FIT_POINTS       64            /* angular samples for curve fit */
#define MALUS_FIT_MAX_ANGLE     90.0          /* ± degrees around estimate */
#define MALUS_FIT_MIN_INTENSITY  50           /* ADC counts — minimum signal */
#define AUTOZERO_RETRY_MAX      3             /* retry auto-zero on failure */

/* ======== Temperature (DS18B20) ======== */
#define DS18B20_GPIO_PIN       0              /* GPIO port C, pin 0 (PC0) */
#define DS18B20_CONV_TIME_MS   750

/* ======== OLED Display (SSD1306) ======== */
#define OLED_I2C_ADDR          0x3C
#define OLED_WIDTH             128
#define OLED_HEIGHT            64

/* ======== SD Card ======== */
#define SD_SPI_CS_GPIO_PIN     8              /* PB8 */
#define SD_LOG_FILENAME        "/opti_rot/log.csv"
#define SD_LIBRARY_FILENAME    "/opti_rot/library.bin"

/* ======== UART Bridge to ESP32-C3 ======== */
#define BLE_UART_BAUD          1000000        /* 1 Mbps */
#define BLE_UART_BUFFER_SIZE   256
#define BLE_FRAME_SYNC_BYTE    0xA5
#define BLE_FRAME_VERSION      1

/* ======== Compound Library ======== */
#define LIBRARY_MAX_COMPOUNDS  50
#define LIBRARY_MAX_CUSTOM     10             /* custom user entries */
#define LIBRARY_NAME_MAX_LEN   24

/* ======== Measurement Timing ======== */
#define MEASURE_SWEEP_DELAY_MS 50             /* settle after stepper move */
#define MEASURE_SETTLE_MS      200            /* light path stabilization */
#define MONITOR_INTERVAL_MS    10000          /* 10 seconds */

/* ======== Power Management ======== */
#define BATTERY_ADC_CHANNEL    ADC_CHANNEL_3  /* PA3 */
#define BATTERY_DIVIDER_RATIO  3.0            /* 1:3 voltage divider */
#define BATTERY_LOW_MV         3300           /* 3.3V threshold */
#define SLEEP_TIMEOUT_S         120            /* sleep after 2 min idle */

/* ======== UI ======== */
#define BUTTON_DEBOUNCE_MS     50
#define UI_MODE_COUNT           6              /* Measure, Identify, Monitor, Library, Calibrate, Config */

/* ======== RGB LED ======== */
#define LED_PWM_FREQ_HZ        1000
#define LED_PWM_RESOLUTION     256

#endif /* SDKCONFIG_H */