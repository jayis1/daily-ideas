/*
 * dent-scope / Core/Src/loadcell.c
 * Dent Scope — HX711 24-bit load cell ADC driver (force measurement)
 *
 * The HX711 is a 24-bit ADC designed for load cells. It communicates
 * via a simple 2-wire serial interface (SCK + DOUT). Channel A gain 128.
 *
 * At 80 Hz rate, the HX711 outputs one 24-bit reading every 12.5 ms.
 * We do 16× hardware averaging for ~0.5 mN resolution with 20 N cell.
 *
 * MIT License.
 */
#include "loadcell.h"

static float last_mN = 0.0f;
static int32_t raw_offset = 0;

void loadcell_init(void)
{
    HAL_GPIO_WritePin(HX711_RATE_PORT, HX711_RATE_PIN, GPIO_PIN_SET); /* 80 Hz */
    HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);
    /* auto-tare on power-up: read ~32 samples to establish offset */
    int64_t sum = 0; int n = 0;
    for (int i = 0; i < 32; i++) {
        if (!HAL_GPIO_ReadPin(HX711_DOUT_PORT, HX711_DOUT_PIN)) {
            int32_t v = 0;
            for (int b = 0; b < 24; b++) {
                HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_SET);
                for (volatile int d=0; d<100; d++);
                v = (v << 1) | (HAL_GPIO_ReadPin(HX711_DOUT_PORT, HX711_DOUT_PIN) ? 1 : 0);
                HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);
                for (volatile int d=0; d<100; d++);
            }
            /* 25th pulse sets gain/channel for next reading (gain 128 ch A) */
            HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_SET);
            for (volatile int d=0; d<100; d++);
            HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);
            for (volatile int d=0; d<100; d++);
            /* sign-extend 24-bit */
            if (v & 0x800000) v |= 0xFF000000;
            sum += v; n++;
        }
    }
    if (n > 0) raw_offset = (int32_t)(sum / n);
    last_mN = 0.0f;
}

void loadcell_tare(void)
{
    /* re-tare with current load as zero */
    int64_t sum = 0; int n = 0;
    for (int i = 0; i < 16; i++) {
        if (!HAL_GPIO_ReadPin(HX711_DOUT_PORT, HX711_DOUT_PIN)) {
            int32_t v = 0;
            for (int b = 0; b < 24; b++) {
                HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_SET);
                for (volatile int d=0; d<100; d++);
                v = (v << 1) | (HAL_GPIO_ReadPin(HX711_DOUT_PORT, HX711_DOUT_PIN) ? 1 : 0);
                HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);
                for (volatile int d=0; d<100; d++);
            }
            HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_SET);
            for (volatile int d=0; d<100; d++);
            HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);
            for (volatile int d=0; d<100; d++);
            if (v & 0x800000) v |= 0xFF000000;
            sum += v; n++;
        }
    }
    if (n > 0) raw_offset = (int32_t)(sum / n);
    last_mN = 0.0f;
}

static int32_t hx711_read_raw(void)
{
    /* wait for DOUT low (data ready) — timeout 50 ms */
    uint32_t t0 = HAL_GetTick();
    while (HAL_GPIO_ReadPin(HX711_DOUT_PORT, HX711_DOUT_PIN)) {
        if (HAL_GetTick() - t0 > 50) return 0;
    }

    int32_t v = 0;
    for (int b = 0; b < 24; b++) {
        HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_SET);
        for (volatile int d=0; d<50; d++);
        v = (v << 1) | (HAL_GPIO_ReadPin(HX711_DOUT_PORT, HX711_DOUT_PIN) ? 1 : 0);
        HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);
        for (volatile int d=0; d<50; d++);
    }
    /* 25th pulse: gain 128, channel A */
    HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_SET);
    for (volatile int d=0; d<50; d++);
    HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);
    for (volatile int d=0; d<50; d++);

    /* sign-extend 24-bit to 32-bit */
    if (v & 0x800000) v |= 0xFF000000;
    return v;
}

void loadcell_read_mN(void)
{
    /* 16× averaging for noise reduction → ~0.5 mN resolution */
    int64_t sum = 0; int n = 0;
    for (int i = 0; i < 16; i++) {
        int32_t raw = hx711_read_raw();
        sum += (raw - raw_offset);
        n++;
    }
    if (n == 0) return;
    int32_t avg = (int32_t)(sum / n);
    /* g_cfg.hx711_scale has mN per count (calibrated) */
    last_mN = (float)avg * g_cfg.hx711_scale;
    if (last_mN < 0) last_mN = 0; /* clamp negatives (no compression) */
}

float loadcell_last_mN(void) { return last_mN; }