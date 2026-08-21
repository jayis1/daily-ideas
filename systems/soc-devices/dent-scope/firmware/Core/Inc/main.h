/*
 * dent-scope / Core/Inc/main.h
 * Dent Scope — Pocket Instrumented Indentation Tester
 * STM32G474RET6 application header.
 * MIT License.
 */
#ifndef DENT_SCOPE_MAIN_H
#define DENT_SCOPE_MAIN_H

#include "stm32g4xx_hal.h"
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>

/* ---- Pin map (see README pin table) ---- */

/* HX711 load cell */
#define HX711_SCK_PIN   GPIO_PIN_1
#define HX711_SCK_PORT  GPIOA
#define HX711_DOUT_PIN  GPIO_PIN_2
#define HX711_DOUT_PORT GPIOA
#define HX711_RATE_PIN  GPIO_PIN_3
#define HX711_RATE_PORT GPIOA

/* DRV8833 stepper */
#define STEP_IN1_PIN    GPIO_PIN_4
#define STEP_IN1_PORT   GPIOA
#define STEP_IN2_PIN    GPIO_PIN_5
#define STEP_IN2_PORT   GPIOA
#define STEP_IN3_PIN    GPIO_PIN_6
#define STEP_IN3_PORT   GPIOA
#define STEP_IN4_PIN    GPIO_PIN_7
#define STEP_IN4_PORT   GPIOA
#define STEP_EN_PIN     GPIO_PIN_8
#define STEP_EN_PORT    GPIOA

/* UART to ESP32-C3 */
#define UART_TX_PIN      GPIO_PIN_9
#define UART_TX_PORT     GPIOA
#define UART_RX_PIN      GPIO_PIN_10
#define UART_RX_PORT     GPIOA

/* Safety / I/O */
#define STALL_PIN        GPIO_PIN_11
#define STALL_PORT       GPIOA
#define BUZZER_PIN       GPIO_PIN_12
#define BUZZER_PORT      GPIOA
#define LED_PIN          GPIO_PIN_15
#define LED_PORT         GPIOA

/* DS18B20 1-wire */
#define ONEWIRE_PIN      GPIO_PIN_0
#define ONEWIRE_PORT     GPIOB

/* OLED */
#define OLED_DC_PIN      GPIO_PIN_1
#define OLED_DC_PORT     GPIOB
#define OLED_RST_PIN     GPIO_PIN_14
#define OLED_RST_PORT    GPIOC

/* SPI1: SD + OLED */
#define SPI_SCK_PIN      GPIO_PIN_3
#define SPI_SCK_PORT     GPIOB
#define SPI_MISO_PIN     GPIO_PIN_4
#define SPI_MISO_PORT    GPIOB
#define SPI_MOSI_PIN     GPIO_PIN_5
#define SPI_MOSI_PORT    GPIOB
#define SD_CS_PIN        GPIO_PIN_6
#define SD_CS_PORT       GPIOB
#define OLED_CS_PIN      GPIO_PIN_7
#define OLED_CS_PORT     GPIOB

/* I2C1: AD7746 */
#define I2C1_SCL_PIN     GPIO_PIN_8
#define I2C1_SCL_PORT    GPIOB
#define I2C1_SDA_PIN     GPIO_PIN_9
#define I2C1_SDA_PORT    GPIOB

/* SPI2: ICM-42688-P */
#define SPI2_SCK_PIN     GPIO_PIN_10
#define SPI2_SCK_PORT    GPIOB
#define SPI2_MISO_PIN    GPIO_PIN_11
#define SPI2_MISO_PORT   GPIOB
#define IMU_CS_PIN       GPIO_PIN_12
#define IMU_CS_PORT      GPIOB

/* Buttons */
#define BTN_START_PIN    GPIO_PIN_13
#define BTN_START_PORT   GPIOB
#define BTN_STOP_PIN     GPIO_PIN_14
#define BTN_STOP_PORT    GPIOB
#define BTN_MENU_PIN     GPIO_PIN_15
#define BTN_MENU_PORT    GPIOB

/* Misc */
#define INTERLOCK_PIN    GPIO_PIN_13
#define INTERLOCK_PORT   GPIOC
#define ESP_RST_PIN      GPIO_PIN_6
#define ESP_RST_PORT     GPIOC
#define MOTOR_BRAKE_PIN  GPIO_PIN_15
#define MOTOR_BRAKE_PORT GPIOC

#define VBAT_DIV_PIN     GPIO_PIN_0
#define VBAT_DIV_PORT    GPIOA

/* ---- Test parameters ---- */
typedef enum {
    TIP_VICKERS = 0,
    TIP_BERKOVICH,
    TIP_WC_BALL_1MM
} tip_type_t;

typedef enum {
    DS_IDLE = 0,
    DS_APPROACHING,
    DS_LOADING,
    DS_HOLDING,
    DS_UNLOADING,
    DS_RETRACTING,
    DS_ALARM,
    DS_CALIBRATE
} ds_state_t;

typedef struct {
    ds_state_t  state;
    tip_type_t  tip;
    float       force_mN;       /* current force (mN) */
    float       depth_um;       /* current depth (µm) */
    float       peak_force_mN;  /* P_max */
    float       peak_depth_um;  /* h_max */
    float       final_depth_um; /* h_f (residual) */
    float       hardness_HV;    /* Vickers hardness */
    float       hardness_HB;    /* Brinell hardness */
    float       modulus_E_GPa;  /* Young's modulus (GPa) */
    float       elastic_ratio;  /* η = W_elastic/W_total */
    float       creep_nm_s;     /* creep rate during hold (nm/s) */
    float       temp_c;         /* sample temperature */
    float       tilt_deg;       /* IMU tilt from vertical */
    float       battery_v;
    uint32_t    t_start_ms;
    uint32_t    point_count;
    /* timing sub-states */
    float       contact_time_s;  /* time of surface contact */
    uint32_t    hold_start_ms;   /* start of creep hold */
    uint32_t    unload_start_ms; /* start of unloading */
    float       unload_start_force; /* force at unload start (mN) */
    float       unload_start_depth; /* depth at unload start (µm) */
    /* material match */
    int8_t      matched_material; /* k-NN result index, -1 = none */
    /* test config */
    float       target_force_N;  /* peak load (N) */
    float       loading_rate_Ns; /* N/s */
    float       hold_time_s;     /* hold at peak */
    float       poisson;         /* sample Poisson's ratio */
} ds_status_t;

/* ---- Config stored in flash ---- */
typedef struct {
    uint32_t  magic;
    float     hx711_offset;
    float     hx711_scale;     /* mN per count */
    float     cap_offset;      /* AD7746 raw at 0 µm */
    float     cap_scale;       /* µm per pF */
    float     cap_quad;        /* quadratic term */
    tip_type_t tip;
    float     target_force_N;
    float     loading_rate_Ns;
    float     hold_time_s;
    float     poisson;
} ds_config_t;

extern ds_status_t g_status;
extern ds_config_t g_cfg;

extern TIM_HandleTypeDef htim3;
extern ADC_HandleTypeDef hadc1;
extern I2C_HandleTypeDef hi2c1;
extern SPI_HandleTypeDef hspi1, hspi2;
extern UART_HandleTypeDef huart1;
extern IWDG_HandleTypeDef hiwdg;

void Error_Handler(void);

#endif /* DENT_SCOPE_MAIN_H */