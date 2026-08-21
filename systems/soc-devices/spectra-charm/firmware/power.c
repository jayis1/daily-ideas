/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * power.c — Power management: sleep/wake, rail control
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "power.h"
#include "stm32g4xx_hal.h"
#include "fuel_gauge.h"
#include <stdbool.h>

extern I2C_HandleTypeDef hi2c1;

/* Power states */
typedef enum {
    POWER_STATE_ACTIVE,
    POWER_STATE_IDLE,
    POWER_STATE_SLEEP,
    POWER_STATE_DEEP_SLEEP,
} PowerState_t;

static PowerState_t gPowerState = POWER_STATE_ACTIVE;
static uint32_t gIdleTimer = 0;
static const uint32_t IDLE_TIMEOUT_MS = 30000;   /* 30s to idle */
static const uint32_t SLEEP_TIMEOUT_MS = 120000;  /* 2 min to sleep */

void Power_EnterDeepSleep(void)
{
    /* Turn off LEDs */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_8, GPIO_PIN_RESET); /* UV LED off */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_RESET); /* White LED off */

    /* Disable 3.3V rail (SHUTDOWN_N low) */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_6, GPIO_PIN_RESET);

    /* Enter STOP mode — wake on button press (PC7/PC8 EXTI) */
    HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_LOWDRIVE, PWR_STOPENTRY_WFI);

    /* Woken up — re-enable rails */
    SystemClock_Config(); /* Restore clock after STOP */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_6, GPIO_PIN_SET);
    gPowerState = POWER_STATE_ACTIVE;
    gIdleTimer = 0;
}

void Power_EnterSleep(void)
{
    /* Reduce clock to save power, keep RAM alive */
    gPowerState = POWER_STATE_SLEEP;
    HAL_PWR_EnterSLEEPMode(PWR_MAINREGULATOR_ON, PWR_SLEEPENTRY_WFI);
}

void Power_EnterIdle(void)
{
    gPowerState = POWER_STATE_IDLE;
    /* Keep system running but reduce peripheral activity */
}

void Power_Wakeup(void)
{
    gPowerState = POWER_STATE_ACTIVE;
    gIdleTimer = 0;
}

void Power_Tick(uint32_t elapsed_ms)
{
    gIdleTimer += elapsed_ms;

    switch (gPowerState) {
    case POWER_STATE_ACTIVE:
        if (gIdleTimer > IDLE_TIMEOUT_MS) {
            Power_EnterIdle();
        }
        break;
    case POWER_STATE_IDLE:
        if (gIdleTimer > SLEEP_TIMEOUT_MS) {
            Power_EnterSleep();
        }
        break;
    case POWER_STATE_SLEEP:
        /* Will wake on interrupt */
        break;
    case POWER_STATE_DEEP_SLEEP:
        break;
    }
}

bool Power_IsLowBattery(void)
{
    uint8_t soc = FuelGauge_GetSOC(&hi2c1);
    uint16_t voltage = FuelGauge_GetVoltage(&hi2c1);
    return (soc < 5) || (voltage < 3300);
}

PowerState_t Power_GetState(void)
{
    return gPowerState;
}

/* Weak override to restore clock after STOP mode */
void SystemClock_Config(void);  /* Declared in main.c */