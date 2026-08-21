/*
 * power.c — power-stage, OCP, thermal, fuel-gauge
 */
#include "power.h"
#include <stdint.h>

static bool g_amp_on = false;

void power_init(void)
{
    g_amp_on = false;
    /* MAX17048 I2C init, NTC ADC channel config, LM5035 FLT pin as input. */
}

void power_amp_enable(bool en)
{
    g_amp_on = en;
    /* HAL_GPIO_WritePin(AMP_EN_GPIO_Port, AMP_EN_Pin,
     *                  en ? GPIO_PIN_SET : GPIO_PIN_RESET); */
}

float power_get_temp_c(void)
{
    /* Read ADC1_IN7 (TEMP_NTC) via a 10k/10k divider + B3950 equation. */
    return 25.0f;  /* sim default */
}

uint8_t power_get_soc(void)
{
    /* MAX17048 I2C read. */
    return 80;  /* sim default */
}

float power_get_vbat(void)
{
    /* MAX17048 VCELL register or ADC1_IN9 divider. */
    return 3.85f;  /* sim default */
}

bool power_fault_latched(void)
{
    /* Read OCP_LATCH / LM5035 FLT. */
    return false;
}

void power_clear_fault(void)
{
    /* Toggle AMP_EN off/on to reset the LM5035 latch. */
    power_amp_enable(false);
    power_amp_enable(true);
}