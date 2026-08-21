/*
 * power_manager.c — Power state management
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#include "power_manager.h"
#include "main.h"
#include <math.h>

extern ADC_HandleTypeDef hadc1;

static power_state_t g_state = PWR_IDLE;
static float g_bat_voltage = 3.7f;

void power_manager_init(void)
{
    g_state = PWR_IDLE;
}

void power_manager_set_state(power_state_t state)
{
    g_state = state;
    switch (state) {
        case PWR_STOP:
            /* Will enter STOP mode in main loop */
            break;
        case PWR_IDLE:
            break;
        case PWR_RECORDING:
            break;
        case PWR_STREAMING:
            break;
    }
}

power_state_t power_manager_get_state(void)
{
    return g_state;
}

float power_manager_get_battery_voltage(void)
{
    /* Read PA0 (ADC1_IN1) with 1:2 voltage divider */
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 10);
    uint32_t raw = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);

    /* Vref = 3.3V, 12-bit ADC, divider 1:2 → Vbat = raw/4095 × 3.3 × 2 */
    g_bat_voltage = (float)raw / 4095.0f * 3.3f * 2.0f;
    return g_bat_voltage;
}

bool power_manager_is_charging(void)
{
    /* PB15 = CHARGE_STAT from MCP73831 (low = charging, high = done) */
    return (HAL_GPIO_ReadPin(CHARGE_STAT_GPIO_Port, CHARGE_STAT_Pin) == GPIO_PIN_RESET);
}

uint8_t power_manager_get_battery_pct(void)
{
    float v = power_manager_get_battery_voltage();
    /* LiPo: 3.0V = 0%, 4.2V = 100% */
    float pct = (v - 3.0f) / (4.2f - 3.0f) * 100.0f;
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    return (uint8_t)pct;
}

void power_manager_enter_stop(void)
{
    /* Enter STM32 Stop 2 mode — RTC wakes us up */
    HAL_SuspendTick();
    HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_ON, PWR_STOPENTRY_WFI);
    /* On wake: reconfigure clock */
    SystemClock_Config();
    HAL_ResumeTick();
}