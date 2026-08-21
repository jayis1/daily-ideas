/*
 * safety.c — Triple-redundant HV safety subsystem
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * Layers:
 *  1. Reed interlock (PC3): lid must be closed to enable ionizer/HV.
 *  2. TLV3201 over-current comparator (PC4): latches fault, kills HV.
 *  3. IWDG watchdog: firmware hang -> system reset.
 *  4. 250C thermal fuse on HV module (hardware, not firmware-visible).
 *
 * SPDX-License-Identifier: MIT
 */
#include "safety.h"
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"
#include "hv_supply.h"

static bool g_fault = false;
static const char *g_fault_msg = "OK";

void safety_init(void)
{
    /* PC3 interlock input (pull-up: closed->low) */
    GPIO_InitTypeDef io = {0};
    io.Pin = GPIO_PIN_3;
    io.Mode = GPIO_MODE_INPUT;
    io.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOC, &io);

    /* PC4 fault input */
    GPIO_InitTypeDef fio = {0};
    fio.Pin = GPIO_PIN_4;
    fio.Mode = GPIO_MODE_INPUT;
    fio.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOC, &fio);

    /* IWDG: 32 kHz LSI / 256 prescaler, reload ~ 4096 -> ~32s timeout */
    IWDG_HandleTypeDef iw = {0};
    iw.Instance = IWDG;
    iw.Init.Prescaler = IWDG_PRESCALER_256;
    iw.Init.Reload = 4095;
    iw.Init.Window = 4095;
    HAL_IWDG_Init(&iw);
}

bool safety_interlock_closed(void)
{
    /* reed switch: closed (lid down) pulls PC3 low */
    return HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_3) == GPIO_PIN_RESET;
}

bool safety_fault(void)
{
    if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_4) == GPIO_PIN_SET) {
        g_fault = true;
        g_fault_msg = "HV OVERCURRENT";
        hv_emergency_shutdown();
    }
    return g_fault;
}

void safety_clear_fault(void)
{
    g_fault = false;
    g_fault_msg = "OK";
}

void safety_tick(void)
{
    /* refresh IWDG; if safety fault, hold HV off */
    IWDG_HandleTypeDef iw = {0};
    iw.Instance = IWDG;
    HAL_IWDG_Refresh(&iw);
    if (g_fault) hv_emergency_shutdown();
}

const char *safety_fault_msg(void) { return g_fault ? g_fault_msg : "OK"; }