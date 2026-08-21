/*
 * Levia Forge — SDK Configuration
 * Build-time configuration constants for the acoustic levitation controller.
 */
#ifndef LEVIA_FORGE_SDKCONFIG_H
#define LEVIA_FORGE_SDKCONFIG_H

/* ---- Acoustic Parameters ---- */
#define CARRIER_FREQ_HZ     40000       /* 40 kHz ultrasonic carrier */
#define SPEED_OF_SOUND      343.0f      /* m/s at 20°C, 1 atm */
#define PHASE_STEPS         256         /* phase quantization steps */
#define PIO_CLOCK_HZ        10240000    /* 10.24 MHz = 256 × 40 kHz */
#define DMA_BUFFER_SIZE     2304        /* 72 bits × 256 steps ÷ 8 bytes */

/* ---- Array Geometry ---- */
#define NUM_TRANSDUCERS     72          /* 36 top + 36 bottom */
#define NUM_TOP             36
#define NUM_BOTTOM          36
#define ARRAY_COLS          6
#define ARRAY_ROWS          6
#define ELEMENT_SPACING_MM  10.0f       /* center-to-center */
#define CURVATURE_RADIUS_MM 40.0f       /* hemispherical mount radius */
#define TOP_ARRAY_Z_MM      35.0f       /* top array plane above center */
#define BOTTOM_ARRAY_Z_MM   (-35.0f)    /* bottom array plane below center */

/* ---- Working Volume ---- */
#define WORK_VOL_X_MM       15.0f       /* ±15 mm in X */
#define WORK_VOL_Y_MM       15.0f       /* ±15 mm in Y */
#define WORK_VOL_Z_MIN_MM   0.0f
#define WORK_VOL_Z_MAX_MM   20.0f

/* ---- Control Loop ---- */
#define CONTROL_LOOP_HZ     50          /* 50 Hz phase recomputation */
#define CONTROL_LOOP_PERIOD_MS (1000 / CONTROL_LOOP_HZ)
#define DISPLAY_UPDATE_HZ   10
#define SD_LOG_HZ           10
#define BLE_POLL_HZ         10

/* ---- Pin Assignments (RP2040) ---- */
/* PIO0 SM0 — Phase serial stream */
#define PIN_PIO_DATA        0
#define PIN_PIO_CLOCK       1
#define PIN_PIO_LATCH       2
#define PIN_PIO_BLANK       3

/* UART1 — ESP32-C3 bridge */
#define PIN_UART_TX         4
#define PIN_UART_RX         5

/* I2C1 — OLED */
#define PIN_I2C1_SDA        6
#define PIN_I2C1_SCL        7

/* SPI0 — SD card */
#define PIN_SPI_SCK         8
#define PIN_SPI_MOSI        9
#define PIN_SPI_MISO        10
#define PIN_SPI_CS          11

/* Rotary encoder */
#define PIN_ENC_A           12
#define PIN_ENC_B           13
#define PIN_ENC_BTN         14

/* Buttons */
#define PIN_BTN_MODE        15
#define PIN_BTN_RELEASE     16

/* Status LED */
#define PIN_LED_STATUS      17

/* SD card detect */
#define PIN_SD_CD           18

/* Safety */
#define PIN_SAFETY_REED     19
#define PIN_ESP_BOOT        20
#define PIN_ESP_EN          21
#define PIN_TILT_IRQ        22

/* ADC */
#define PIN_ADC_JOY_X       26
#define PIN_ADC_JOY_Y       27
#define PIN_ADC_VBAT        28

/* I2C0 — VL53L0X */
#define PIN_I2C0_SDA        26   /* reused? No — use I2C0 on GP26/GP27? */
/* Actually: I2C0 must be on valid I2C pins. We put I2C0 on GP2/GP3
 * but those are used by PIO. Let's use I2C0 on GP6/GP7 and I2C1 on
 * GP10/GP11. But SPI0 needs those. Resolved: I2C0 on GP14/GP15? No,
 * those are buttons. Use I2C0 on GP18/GP19? GP18=SD_CD, GP19=reed.
 *
 * Final pin plan:
 *   I2C0 (VL53L0X): GP12/GP13 (move encoder to PIO1)
 *   I2C1 (OLED):    GP6/GP7
 *   SPI0 (SD):      GP8/GP9/GP10/GP11
 *   Encoder:        PIO1 SM0 on GP14/GP15
 *   Buttons:        GP16/GP17 (move LED to GP25 on-board)
 *
 * For simplicity in firmware, define here: */
#define PIN_I2C0_SDA        12   /* VL53L0X SDA */
#define PIN_I2C0_SCL        13   /* VL53L0X SCL */
/* Encoder moved to PIO1 SM0: */
#define PIN_ENC_A_PIO1      14
#define PIN_ENC_B_PIO1      15
#define PIN_BTN_MODE_DEF    16
#define PIN_BTN_RELEASE_DEF 17
#define PIN_LED_ONBOARD     25   /* Pico onboard LED */

/* ---- Safety Thresholds ---- */
#define BATTERY_LOW_MV      6000    /* 6.0V = 3.0V/cell */
#define BATTERY_CRIT_MV     5600    /* 5.6V = 2.8V/cell */
#define TILT_MAX_DEGREES    15.0f
#define TEMP_MAX_C          70.0f
#define WATCHDOG_TIMEOUT_MS 100

/* ---- Phase Patterns ---- */
typedef enum {
    PATTERN_POINT = 0,      /* single focused trap */
    PATTERN_TWIN,           /* two traps side by side */
    PATTERN_VORTEX,         /* azimuthal phase gradient (ℓ=1) */
    PATTERN_BOTTLE,         /* hollow surrounding trap */
    PATTERN_BENDING,        /* linear phase gradient (transport) */
    PATTERN_TRANSPORT,      /* moving line trap (conveyor) */
    PATTERN_COUNT
} phase_pattern_t;

/* ---- Safety States ---- */
typedef enum {
    SAFETY_OK = 0,
    SAFETY_LID_OPEN,
    SAFETY_TILT_EXCEEDED,
    SAFETY_BATTERY_LOW,
    SAFETY_OVERTEMP,
    SAFETY_EMERGENCY_RELEASE,
    SAFETY_WATCHDOG,
    SAFETY_DISABLED
} safety_state_t;

#endif /* LEVIA_FORGE_SDKCONFIG_H */