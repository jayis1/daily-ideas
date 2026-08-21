/*
 * pyro-balance / Core/Inc/main.h
 * Pyro Balance — Pocket Thermogravimetric Analyzer
 * STM32G474RET6 application header.
 * MIT License.
 */
#ifndef PYRO_BALANCE_MAIN_H
#define PYRO_BALANCE_MAIN_H

#include "stm32g4xx_hal.h"
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

/* ---- Pin map (see README pin table) ---- */
#define HX711_SCK_PIN   GPIO_PIN_1
#define HX711_SCK_PORT  GPIOA
#define HX711_DOUT_PIN  GPIO_PIN_2
#define HX711_DOUT_PORT GPIOA
#define HX711_RATE_PIN  GPIO_PIN_3
#define HX711_RATE_PORT GPIOA

#define FURN_PWM_PIN    GPIO_PIN_5   /* HRTIM CHA1 */
#define FURN_PWM_PORT   GPIOA
#define HEATER_EN_PIN   GPIO_PIN_8
#define HEATER_EN_PORT  GPIOA

#define PUMP_PWM_PIN    GPIO_PIN_6
#define PUMP_PWM_PORT   GPIOA
#define LED_PIN         GPIO_PIN_7
#define LED_PORT        GPIOA

#define OVERTEMP_PIN    GPIO_PIN_11
#define OVERTEMP_PORT   GPIOA
#define BUZZER_PIN      GPIO_PIN_12
#define BUZZER_PORT     GPIOA
#define FUSE_SENSE_PIN  GPIO_PIN_15
#define FUSE_SENSE_PORT GPIOA

#define SD_CS_PIN       GPIO_PIN_6
#define SD_CS_PORT      GPIOB
#define OLED_CS_PIN     GPIO_PIN_7
#define OLED_CS_PORT    GPIOB
#define OLED_DC_PIN     GPIO_PIN_1
#define OLED_DC_PORT    GPIOB
#define OLED_RST_PIN    GPIO_PIN_1
#define OLED_RST_PORT   GPIOB

#define INTERLOCK_PIN   GPIO_PIN_13
#define INTERLOCK_PORT  GPIOC
#define N2_VALVE_PIN    GPIO_PIN_14
#define N2_VALVE_PORT   GPIOC
#define FAN_PIN         GPIO_PIN_15
#define FAN_PORT        GPIOC

#define BTN_START_PIN   GPIO_PIN_13
#define BTN_START_PORT  GPIOB
#define BTN_STOP_PIN    GPIO_PIN_14
#define BTN_STOP_PORT   GPIOB
#define BTN_MENU_PIN    GPIO_PIN_15
#define BTN_MENU_PORT   GPIOB

#define VBAT_DIV_PIN    GPIO_PIN_0
#define VBAT_DIV_PORT   GPIOB

/* ---- Global state ---- */
typedef enum {
    PB_IDLE = 0,
    PB_RUNNING,
    PB_COOLING,
    PB_ALARM,
    PB_CALIBRATE
} pb_state_t;

typedef struct {
    pb_state_t state;
    float mass_mg;          /* current sample mass (mg) */
    float temp_c;           /* current furnace temp (°C) */
    float target_c;         /* current ramp target */
    uint32_t t_start_ms;    /* run start */
    uint32_t method_id;     /* method id (0=default) */
    uint16_t heating_rate;  /* °C/min *10 (e.g., 50 = 5 °C/min) */
    uint16_t final_temp_c;
    uint16_t hold_min;
    bool    purge_n2;
    bool    purge_pump_on;
    float   battery_v;
    uint32_t step_count;
} pb_status_t;

extern pb_status_t g_status;
extern TIM_HandleTypeDef htim3;
extern ADC_HandleTypeDef hadc1;
extern I2C_HandleTypeDef hi2c1, hi2c2;
extern SPI_HandleTypeDef hspi1;
extern UART_HandleTypeDef huart1;
extern IWDG_HandleTypeDef hiwdg;

void Error_Handler(void);

#endif /* PYRO_BALANCE_MAIN_H */