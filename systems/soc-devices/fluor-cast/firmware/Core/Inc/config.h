/*
 * config.h — Fluor Cast Pin & Constants Definitions
 * STM32G474RET6
 */

#ifndef CONFIG_H
#define CONFIG_H

#include "stm32g4xx_hal.h"

/* ── System ─────────────────────────────────────────────── */
#define MCU_CLK_MHZ         170
#define SYSTICK_HZ          1000
#define FIRMWARE_VERSION    "1.0.0"

/* ── Pin Definitions (GPIO) ─────────────────────────────── */

/* LED excitation PWM */
#define LED_PWM_GPIO        GPIOA
#define LED_PWM_PIN         GPIO_PIN_0
#define LED_PWM_TIM         TIM2
#define LED_PWM_CHANNEL     TIM_CHANNEL_1

/* Reference photodiode (OPT101) */
#define REF_PD_GPIO         GPIOA
#define REF_PD_PIN          GPIO_PIN_1
#define REF_PD_ADC          ADC1
#define REF_PD_CHANNEL      ADC_CHANNEL_2

/* CCD analog output (TSL1402R) */
#define CCD_AO_GPIO         GPIOA
#define CCD_AO_PIN          GPIO_PIN_3
#define CCD_AO_ADC          ADC2
#define CCD_AO_CHANNEL      ADC_CHANNEL_4

/* CCD control */
#define CCD_SI_GPIO         GPIOA
#define CCD_SI_PIN          GPIO_PIN_5
#define CCD_CLK_GPIO        GPIOA
#define CCD_CLK_PIN         GPIO_PIN_6
#define CCD_CLK_TIM         TIM3
#define CCD_CLK_CHANNEL     TIM_CHANNEL_1

/* LED driver enable */
#define LED_DRV_EN_GPIO     GPIOA
#define LED_DRV_EN_PIN      GPIO_PIN_7

/* Stepper motor (28BYJ-48 via ULN2003) */
#define STEPPER_IN1_GPIO    GPIOA
#define STEPPER_IN1_PIN     GPIO_PIN_8
#define STEPPER_IN2_GPIO    GPIOA
#define STEPPER_IN2_PIN     GPIO_PIN_9
#define STEPPER_IN3_GPIO    GPIOA
#define STEPPER_IN3_PIN     GPIO_PIN_10
#define STEPPER_IN4_GPIO    GPIOA
#define STEPPER_IN4_PIN     GPIO_PIN_11
#define STEPPER_HOME_GPIO   GPIOA
#define STEPPER_HOME_PIN    GPIO_PIN_12

/* SPI (SD card + OLED) */
#define SPI_SCK_GPIO        GPIOB
#define SPI_SCK_PIN         GPIO_PIN_3
#define SPI_MISO_GPIO       GPIOB
#define SPI_MISO_PIN        GPIO_PIN_4
#define SPI_MOSI_GPIO       GPIOB
#define SPI_MOSI_PIN        GPIO_PIN_5

#define SD_CS_GPIO          GPIOB
#define SD_CS_PIN           GPIO_PIN_10
#define OLED_CS_GPIO        GPIOB
#define OLED_CS_PIN         GPIO_PIN_11
#define OLED_DC_GPIO        GPIOB
#define OLED_DC_PIN         GPIO_PIN_12

/* I2C (OLED) */
#define I2C_SCL_GPIO        GPIOB
#define I2C_SCL_PIN         GPIO_PIN_6
#define I2C_SDA_GPIO        GPIOB
#define I2C_SDA_PIN         GPIO_PIN_7

/* UART to ESP32-C3 */
#define UART_TX_GPIO        GPIOB
#define UART_TX_PIN         GPIO_PIN_8  /* USART3_RX pin (STM32 TX → ESP32 RX) */
#define UART_RX_GPIO        GPIOB
#define UART_RX_PIN         GPIO_PIN_9  /* USART3_TX pin (ESP32 TX → STM32 RX) */
#define UART_BAUD           921600

/* 1-Wire (DS18B20) */
#define ONEWIRE_GPIO        GPIOB
#define ONEWIRE_PIN         GPIO_PIN_13

/* LED selection demux (74HC138) */
#define LED_SEL0_GPIO       GPIOC
#define LED_SEL0_PIN        GPIO_PIN_0
#define LED_SEL1_GPIO       GPIOC
#define LED_SEL1_PIN        GPIO_PIN_1
#define LED_SEL2_GPIO       GPIOC
#define LED_SEL2_PIN        GPIO_PIN_2

/* Battery monitoring */
#define BATTERY_V_GPIO      GPIOC
#define BATTERY_V_PIN       GPIO_PIN_4
#define BATTERY_V_ADC       ADC1
#define BATTERY_V_CHANNEL   ADC_CHANNEL_13
#define BATTERY_I_GPIO      GPIOC
#define BATTERY_I_PIN       GPIO_PIN_5
#define BATTERY_I_ADC        ADC1
#define BATTERY_I_CHANNEL   ADC_CHANNEL_14

/* Status LEDs */
#define LED_R_GPIO          GPIOC
#define LED_R_PIN           GPIO_PIN_8
#define LED_G_GPIO          GPIOC
#define LED_G_PIN           GPIO_PIN_9
#define LED_B_GPIO          GPIOC
#define LED_B_PIN           GPIO_PIN_10

/* Safety / interlock */
#define LID_INTERLOCK_GPIO  GPIOB
#define LID_INTERLOCK_PIN   GPIO_PIN_14
#define HV_SAFE_EN_GPIO     GPIOB
#define HV_SAFE_EN_PIN      GPIO_PIN_15

/* User button */
#define BUTTON_GPIO         GPIOC
#define BUTTON_PIN          GPIO_PIN_15

/* Charge status */
#define CHARGE_STAT_GPIO    GPIOC
#define CHARGE_STAT_PIN     GPIO_PIN_3

/* Motor enable */
#define MOTOR_EN_GPIO       GPIOC
#define MOTOR_EN_PIN        GPIO_PIN_11

/* ── Excitation LED Wheel ──────────────────────────────── */
#define NUM_EX_WAVELENGTHS  8

typedef enum {
    EX_255NM = 0,
    EX_280NM = 1,
    EX_340NM = 2,
    EX_365NM = 3,
    EX_405NM = 4,
    EX_440NM = 5,
    EX_470NM = 6,
    EX_525NM = 7,
    EX_BLANK = 8  /* dark reference position */
} ex_wavelength_t;

static const uint16_t ex_wavelength_nm[NUM_EX_WAVELENGTHS] = {
    255, 280, 340, 365, 405, 440, 470, 525
};

/* Stepper steps per LED position (28BYJ-48: ~4096 steps/rev, 9 positions) */
#define STEPS_PER_POSITION  456   /* 4096 / 9 ≈ 455 */
#define STEPPER_SPEED_MS    3     /* ms per half-step */

/* ── CCD (TSL1402R) ────────────────────────────────────── */
#define CCD_PIXELS          256
#define CCD_CLK_FREQ_HZ     2000000UL  /* 2 MHz pixel clock */
#define CCD_INT_MIN_MS      10         /* minimum integration time */
#define CCD_INT_MAX_MS      5000       /* maximum integration time */
#define CCD_INT_DEFAULT_MS  500         /* default integration time */
#define CCD_ADC_OVERSAMPLE  4           /* 4× oversampling for 12-bit from 10-bit */

/* Emission wavelength calibration: pixel → wavelength (nm)
 * Polynomial fit: λ = c0 + c1*p + c2*p²
 * Calibrated with Hg pen lamp (436, 546, 577 nm) and quinine sulfate (455 nm) */
#define CCD_WL_C0           340.0f
#define CCD_WL_C1           1.62f
#define CCD_WL_C2           0.0001f

/* Emission range */
#define EM_MIN_NM           340
#define EM_MAX_NM           755

/* ── EEM Matrix ────────────────────────────────────────── */
#define EEM_ROWS            NUM_EX_WAVELENGTHS  /* 8 excitation */
#define EEM_COLS            CCD_PIXELS          /* 256 emission */
#define EEM_SIZE            (EEM_ROWS * EEM_COLS * sizeof(uint16_t))  /* 4 KB */

/* ── Library ───────────────────────────────────────────── */
#define LIBRARY_SIZE        50
#define FEATURE_COUNT       48
#define KNN_K               5

/* ── Acquisition ───────────────────────────────────────── */
#define EEM_SCAN_TIMEOUT_MS 30000
#define MAX_EXPOSURES        3   /* HDR: up to 3 exposure levels per excitation */

/* ── Storage ───────────────────────────────────────────── */
#define SD_LOG_DIR          "/fluor"
#define SD_MAX_FILES        9999

/* ── OLED ───────────────────────────────────────────────── */
#define OLED_WIDTH          128
#define OLED_HEIGHT         64
#define OLED_I2C_ADDR       0x3C

/* ── UART Protocol ─────────────────────────────────────── */
#define UART_SOF            0xAA
#define UART_EOF            0x55
#define UART_MAX_PAYLOAD    4096

/* Commands STM32 → ESP32 */
#define CMD_EEM_DATA        0x01
#define CMD_RESULT          0x02
#define CMD_STATUS          0x03
#define CMD_LOG_ENTRY       0x04
#define CMD_CALIBRATION     0x05

/* Commands ESP32 → STM32 */
#define CMD_START_SCAN      0x10
#define CMD_SET_PARAMS      0x11
#define CMD_GET_STATUS      0x12
#define CMD_CALIBRATE       0x13
#define CMD_SET_LIBRARY     0x14
#define CMD_SET_TIME        0x15

/* ── ADC ────────────────────────────────────────────────── */
#define ADC_REF_V           3.3f
#define ADC_RESOLUTION      4096   /* 12-bit */

/* ── Battery ────────────────────────────────────────────── */
#define BATTERY_MAX_V       4.2f
#define BATTERY_MIN_V       3.3f
#define BATTERY_DIVIDER     2.0f   /* voltage divider ratio */
#define BATTERY_WARN_V      3.5f

/* ── Temperature ────────────────────────────────────────── */
#define TEMP_WARNING_C      50.0f
#define TEMP_SHUTDOWN_C     65.0f

/* ── State Machine ─────────────────────────────────────── */
typedef enum {
    STATE_IDLE = 0,
    STATE_MENU,
    STATE_PREVIEW,
    STATE_ACQUIRE,
    STATE_EEM_SCAN,
    STATE_PROCESS,
    STATE_DISPLAY_RESULT,
    STATE_LOG_STREAM,
    STATE_CALIBRATE,
    STATE_ERROR
} device_state_t;

/* ── Acquisition Parameters ───────────────────────────── */
typedef struct {
    uint16_t integration_ms;    /* CCD integration time */
    uint8_t  hdr_mode;           /* HDR multi-exposure flag */
    uint8_t  scan_mask;           /* bitmask of excitation wavelengths to scan */
    uint8_t  auto_expose;         /* auto-exposure enable */
    uint16_t target_counts;       /* target peak ADC counts for auto-exposure */
    float    led_current_ma;     /* LED drive current (10-80 mA) */
    uint8_t  classify;           /* run k-NN classification after scan */
    uint8_t  log_to_sd;           /* log EEM to SD card */
    uint8_t  stream_ble;          /* stream EEM over BLE */
} acq_params_t;

#endif /* CONFIG_H */