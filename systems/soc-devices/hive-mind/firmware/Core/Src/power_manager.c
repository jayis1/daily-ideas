/*
 * Hive Mind — Power Manager
 * Battery monitoring, solar monitoring, STOP mode, RTC wake
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "power_manager.h"
#include "main.h"

extern ADC_HandleTypeDef hadc;

/* Voltage divider: VBAT → R1 (100k) → R2 (100k) → GND
 * VBAT_ADC = VBAT * R2 / (R1 + R2) = VBAT / 2
 * Full scale at 12-bit ADC with 3.3V ref: 3.3V → 4095
 * VBAT = ADC_count * 3.3 * 2 / 4095
 */
#define VBAT_DIVIDER_RATIO   2.0f
#define ADC_VREF             3.3f
#define ADC_RESOLUTION       4095.0f

/* Solar panel voltage divider: VSOLAR → R1 (200k) → R2 (100k) → GND
 * VSOLAR_ADC = VSOLAR * R2 / (R1 + R2) = VSOLAR / 3
 */
#define VSOLAR_DIVIDER_RATIO 3.0f

static volatile uint8_t user_button_pressed_flag = 0;

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

void power_manager_init(void)
{
    /* ADC and GPIO already initialized by MX_ADC_Init() and MX_GPIO_Init() */
    /* Enable RTC wakeup timer: 30 second interval */
    HAL_RTCEx_SetWakeUpTimer_IT(&hrtc, 30 * 2048, RTC_WAKEUPCLOCK_RTCCLK_DIV16);
}

float power_manager_read_battery(void)
{
    /* Select VBAT channel (ADC channel 5 on PA0) */
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_5;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_24CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc, &sConfig);

    HAL_ADC_Start(&hadc);
    HAL_ADC_PollForConversion(&hadc, 10);
    uint32_t raw = HAL_ADC_GetValue(&hadc);
    HAL_ADC_Stop(&hadc);

    float voltage = (float)raw * ADC_VREF * VBAT_DIVIDER_RATIO / ADC_RESOLUTION;
    return voltage;
}

float power_manager_read_solar(void)
{
    /* Solar panel voltage is on a separate ADC channel (PA7, channel 7)
     * Through voltage divider R1=200k, R2=100k */
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_7;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_24CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc, &sConfig);

    HAL_ADC_Start(&hadc);
    HAL_ADC_PollForConversion(&hadc, 10);
    uint32_t raw = HAL_ADC_GetValue(&hadc);
    HAL_ADC_Stop(&hadc);

    float voltage = (float)raw * ADC_VREF * VSOLAR_DIVIDER_RATIO / ADC_RESOLUTION;
    return voltage;
}

void power_manager_enter_stop(void)
{
    /* Disable unused peripherals to minimize current */
    HAL_I2C_DeInit(&hi2c1);
    HAL_UART_DeInit(&hlpuart1);

    /* Enter STOP mode with RTC wakeup */
    HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_ON, PWR_STOPENTRY_WFI);

    /* After wakeup: re-initialize clocks and peripherals */
    SystemClock_Config();
    MX_I2C1_Init();
    MX_LPUART1_UART_Init();
}

void power_manager_enter_standby(void)
{
    /* Enter STANDBY mode (lowest power, loses RAM) */
    HAL_PWR_EnableWakeUpPin(PWR_WAKEUP_PIN1);  /* User button on PC13 */
    HAL_PWR_EnterSTANDBYMode();
}

uint8_t power_manager_user_button_pressed(void)
{
    uint8_t was_pressed = user_button_pressed_flag;
    user_button_pressed_flag = 0;
    return was_pressed;
}

/* EXTI callback for user button (PC13) */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == GPIO_PIN_13) {
        user_button_pressed_flag = 1;
    }
}

/* RTC wakeup callback */
void HAL_RTCEx_WakeUpTimerCallback(RTC_HandleTypeDef *hrtc)
{
    /* This fires every 30 seconds to wake from STOP mode */
    /* The FreeRTOS tick will handle scheduling the next sensor read */
}