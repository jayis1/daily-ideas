/*
 * main.h — Main application header
 */

#ifndef MAIN_H
#define MAIN_H

#include "stm32g4xx_hal.h"
#include "config.h"

/* Global handles */
extern ADC_HandleTypeDef hadc1;
extern ADC_HandleTypeDef hadc2;
extern I2C_HandleTypeDef hi2c1;
extern SPI_HandleTypeDef hspi1;
extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim3;
extern UART_HandleTypeDef huart3;

/* Global state */
extern volatile device_state_t g_state;
extern acq_params_t g_params;

/* Function prototypes */
void SystemClock_Config(void);
void MX_GPIO_Init(void);
void MX_ADC1_Init(void);
void MX_ADC2_Init(void);
void MX_I2C1_Init(void);
void MX_SPI1_Init(void);
void MX_TIM2_Init(void);
void MX_TIM3_Init(void);
void MX_USART3_UART_Init(void);
void Error_Handler(void);

#endif /* MAIN_H */