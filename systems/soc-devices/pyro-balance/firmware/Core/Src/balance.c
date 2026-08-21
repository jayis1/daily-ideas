/*
 * pyro-balance / Core/Src/balance.c
 * HX711 24-bit ADC driver for 5g foil-strain load cell.
 * Blocking single-shot reads with 16-sample averaging.
 */
#include "balance.h"
#include "flash_store.h"

static float    g_scale = 1.0f;       /* mg per raw count */
static int32_t  g_offset = 0;
static float    g_last_mg = 0.0f;

void balance_init(void) {
    g_scale = g_cfg.balance_scale;
    g_offset = g_cfg.balance_offset;
    /* RATE pin high → 80 Hz */
    HAL_GPIO_WritePin(HX711_RATE_PORT, HX711_RATE_PIN, GPIO_PIN_SET);
}

static int32_t hx_read_raw(void) {
    /* wait for DOUT low (data ready) */
    uint32_t timeout = HAL_GetTick() + 50;
    while (HAL_GPIO_ReadPin(HX711_DOUT_PORT, HX711_DOUT_PIN)) {
        if (HAL_GetTick() > timeout) return g_offset;
    }
    int32_t v = 0;
    for (int i = 0; i < 24; i++) {
        HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_SET);
        for (volatile int d = 0; d < 50; d++);
        v <<= 1;
        if (HAL_GPIO_ReadPin(HX711_DOUT_PORT, HX711_DOUT_PIN)) v |= 1;
        HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);
        for (volatile int d = 0; d < 50; d++);
    }
    /* 25th pulse: channel A gain 128 */
    HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_SET);
    for (volatile int d = 0; d < 50; d++);
    HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);
    for (volatile int d = 0; d < 50; d++);

    /* sign-extend 24-bit */
    if (v & 0x800000) v |= ~0xFFFFFF;
    return v;
}

float balance_read_mg(void) {
    int32_t sum = 0;
    for (int i = 0; i < 16; i++) sum += hx_read_raw();
    int32_t avg = sum / 16;
    float mg = (avg - g_offset) * g_scale;
    if (mg < 0) mg = 0;
    if (mg > BALANCE_MAX_MG) mg = BALANCE_MAX_MG;
    g_last_mg = mg;
    return mg;
}

float balance_last_mg(void) { return g_last_mg; }
void balance_tare(void) {
    int32_t sum = 0;
    for (int i = 0; i < 32; i++) sum += hx_read_raw();
    g_offset = sum / 32;
    g_cfg.balance_offset = g_offset;
    flash_save();
}
void balance_set_scale(float s) { g_scale = s; g_cfg.balance_scale = s; flash_save(); }
void balance_set_offset(int32_t o) { g_offset = o; g_cfg.balance_offset = o; flash_save(); }
float balance_get_scale(void) { return g_scale; }
int32_t balance_get_offset(void) { return g_offset; }